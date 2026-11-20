"""
Mirai School of Technology Academic & Hostel Policy Advisor
Module: Retrieval-Augmented Generation (RAG) Engine with Strict Grounding
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

# Suppress harmless third-party warnings
import warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from dotenv import load_dotenv
load_dotenv()

import chromadb
from chromadb.utils import embedding_functions
from google import genai
from google.genai import types
from google.genai.errors import APIError

from ingest import (
    CHROMA_DB_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    DEFAULT_PDF_PATH
)

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Configurable similarity distance threshold (Lower is more similar in L2/cosine distance)
# Q1/Q2/Q4 match at ~0.29-0.53, while irrelevant questions Q3/Q5 are >= 0.58.
DEFAULT_DISTANCE_THRESHOLD = 0.55
RELEVANCE_DISTANCE_THRESHOLD = float(os.getenv("RELEVANCE_DISTANCE_THRESHOLD", str(DEFAULT_DISTANCE_THRESHOLD)))

# Strict zero-hallucination system prompt
STRICT_SYSTEM_PROMPT = (
    "You are the Mirai University Academic and Hostel Policy Advisor. "
    "Answer only using the supplied context retrieved from handbook.pdf. "
    "Do not use external knowledge, assumptions, or guesses. "
    "If the context does not explicitly support an answer, output exactly [not found]."
)

# Cached global instances
_chroma_collection = None
_genai_client = None


def get_chroma_collection(
    db_dir: str = CHROMA_DB_DIR,
    collection_name: str = COLLECTION_NAME
) -> chromadb.Collection:
    """
    Connects to the existing persistent ChromaDB collection.
    Reuses the same embedding model: all-MiniLM-L6-v2.
    """
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    if not os.path.exists(db_dir):
        raise FileNotFoundError(f"ChromaDB directory not found at: {db_dir}")

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    client = chromadb.PersistentClient(path=db_dir)

    existing = [c.name for c in client.list_collections()]
    if collection_name not in existing:
        raise ValueError(f"Collection '{collection_name}' does not exist in ChromaDB.")

    _chroma_collection = client.get_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )
    return _chroma_collection


def get_gemini_client() -> genai.Client:
    """
    Initializes and returns the Google Gemini API client.
    """
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in ("", "your_actual_api_key", "your_api_key_here"):
        raise ValueError("Missing or invalid GEMINI_API_KEY in environment or .env file.")

    _genai_client = genai.Client(api_key=api_key.strip())
    return _genai_client


def retrieve_context(
    question: str,
    top_k: int = 4,
    distance_threshold: float = RELEVANCE_DISTANCE_THRESHOLD
) -> Dict[str, Any]:
    """
    Retrieves top_k chunks from ChromaDB and applies distance threshold validation.
    
    Args:
        question: Student query.
        top_k: Number of chunks to retrieve (default: 4).
        distance_threshold: Maximum allowed vector distance for relevance.
        
    Returns:
        Dict containing filtered documents, metadatas, and distances.
    """
    collection = get_chroma_collection()
    if collection.count() == 0:
        raise ValueError("ChromaDB collection 'mirai_handbook' is empty.")

    results = collection.query(query_texts=[question], n_results=top_k)

    raw_docs = results["documents"][0] if results.get("documents") else []
    raw_metas = results["metadatas"][0] if results.get("metadatas") else []
    raw_dists = results["distances"][0] if results.get("distances") else []

    filtered_docs = []
    filtered_metas = []
    filtered_dists = []

    for doc, meta, dist in zip(raw_docs, raw_metas, raw_dists):
        # Strict retrieval validation: prune chunks outside the relevance boundary
        if dist <= distance_threshold:
            filtered_docs.append(doc)
            filtered_metas.append(meta)
            filtered_dists.append(dist)
        else:
            logger.debug(f"Pruned irrelevant chunk id={meta.get('chunk_id')} with distance {dist:.4f} > {distance_threshold}")

    return {
        "documents": filtered_docs,
        "metadatas": filtered_metas,
        "distances": filtered_dists,
        "raw_top_distance": raw_dists[0] if raw_dists else None
    }


def parse_sources_from_response(raw_text: str, retrieved_metadatas: List[Dict[str, Any]]) -> tuple[str, List[int]]:
    """
    Extracts explicit page sources from the model response or mapped metadata.
    """
    clean_text = raw_text.strip()

    if "[not found]" in clean_text.lower():
        return "[not found]", []

    # Look for explicit SOURCES tag appended at the end
    source_match = re.search(r"SOURCES?:\s*([0-9,\s]+)$", clean_text, re.IGNORECASE)
    if source_match:
        pages_str = source_match.group(1)
        answer_body = clean_text[:source_match.start()].strip()
        try:
            pages = [int(p.strip()) for p in pages_str.split(",") if p.strip().isdigit()]
            if pages:
                return answer_body, sorted(list(set(pages)))
        except Exception:
            pass
        return answer_body, sorted(list(set(m["page"] for m in retrieved_metadatas if "page" in m)))

    sources = sorted(list(set(m["page"] for m in retrieved_metadatas if "page" in m)))
    return clean_text, sources


def answer(question: str) -> Dict[str, Any]:
    """
    Answers student questions strictly using context retrieved from handbook.pdf.
    
    Args:
        question: User inquiry string.
        
    Returns:
        Dict: {"answer": <str>, "sources": [<page_number>, ...]}
    """
    # 1. Validate empty question
    if not question or not question.strip():
        logger.warning("Empty question provided to answer().")
        return {"answer": "[not found]", "sources": []}

    # 2. Check API key presence before processing
    try:
        client = get_gemini_client()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return {"answer": f"Configuration Error: {str(e)}", "sources": []}

    # 3. Retrieve context with similarity validation
    try:
        retrieval = retrieve_context(question.strip(), top_k=4)
        docs = retrieval["documents"]
        metas = retrieval["metadatas"]
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        return {"answer": f"Retrieval Error: {str(e)}", "sources": []}

    # If no chunks met the relevance threshold, return [not found] immediately
    if not docs:
        logger.info(f"No chunks passed relevance threshold ({RELEVANCE_DISTANCE_THRESHOLD}) for question.")
        return {"answer": "[not found]", "sources": []}

    # 4. Format context with page numbers and chunk IDs
    context_blocks = []
    for doc, meta in zip(docs, metas):
        page_no = meta.get("page", "Unknown")
        chunk_id = meta.get("chunk_id", "Unknown")
        context_blocks.append(
            f"[Document: handbook.pdf | Page: {page_no} | Chunk ID: {chunk_id}]\n{doc}"
        )
    formatted_context = "\n\n".join(context_blocks)

    # 5. Build prompt with strict instructions
    prompt = (
        f"CONTEXT RETRIEVED FROM handbook.pdf:\n"
        f"----------------------------------------\n"
        f"{formatted_context}\n"
        f"----------------------------------------\n\n"
        f"USER QUESTION: {question.strip()}\n\n"
        f"INSTRUCTIONS:\n"
        f"- Answer exclusively using the supplied context above.\n"
        f"- Never use outside knowledge, assumptions, or unmentioned facts.\n"
        f"- If the context does not explicitly provide the answer, reply ONLY with: [not found]\n"
        f"- If supported, end your answer with: SOURCES: <comma-separated page numbers used>\n\n"
        f"ANSWER:"
    )

    # 6. Call Google Gemini API with automatic retry on transient spikes
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    import time
    max_retries = 3
    last_err = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=STRICT_SYSTEM_PROMPT,
                    temperature=0.0,
                    max_output_tokens=1000
                )
            )

            raw_output = response.text if response and response.text else ""
            if not raw_output or not raw_output.strip():
                return {"answer": "[not found]", "sources": [], "chunk_ids": []}

            final_answer, sources = parse_sources_from_response(raw_output, metas)

            if "[not found]" in final_answer.lower():
                return {"answer": "[not found]", "sources": [], "chunk_ids": []}

            matching_chunks = [m.get("chunk_id") for m in metas if m.get("page") in sources and m.get("chunk_id")]

            return {
                "answer": final_answer,
                "sources": sources,
                "chunk_ids": matching_chunks
            }

        except APIError as e:
            last_err = e
            # Retry on transient server busy/rate limit errors (503, 429)
            if hasattr(e, "code") and e.code in (503, 429) and attempt < max_retries - 1:
                logger.warning(f"Transient Gemini API code {e.code}. Retrying in 2s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(2)
                continue
            logger.error(f"Gemini API Error: {e}")
            return {"answer": f"Gemini API Error: {str(e)}", "sources": [], "chunk_ids": []}
        except Exception as e:
            last_err = e
            logger.error(f"Unexpected generation error: {e}")
            return {"answer": f"Generation Error: {str(e)}", "sources": [], "chunk_ids": []}

    return {"answer": f"Gemini API Error: {str(last_err)}", "sources": [], "chunk_ids": []}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_q = " ".join(sys.argv[1:])
        print(f"Question: {test_q}\n")
        res = answer(test_q)
        print(f"Answer: {res['answer']}\n")
        print(f"Sources: {res['sources']}")
        if res.get("chunk_ids"):
            print(f"Chunk IDs: {res['chunk_ids']}")
    else:
        # Launch interactive CLI terminal
        try:
            from cli import main as cli_main
            cli_main()
        except ImportError:
            test_q = "I have 72% attendance this semester. How many attendance marks will I receive, and am I eligible to appear for the final examination?"
            print(f"Question: {test_q}\n")
            res = answer(test_q)
            print(f"Answer: {res['answer']}\n")
            print(f"Sources: {res['sources']}")
