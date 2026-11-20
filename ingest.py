"""
Mirai School of Technology Academic & Hostel Policy Advisor
Module: PDF Ingestion, Text Chunking, and Vector Indexing (ChromaDB)
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Any, Optional

# Suppress noisy library warnings
import warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
DEFAULT_PDF_PATH = "handbook.pdf"
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "mirai_handbook"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def extract_pages_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text from each page of a PDF document using PyMuPDF.
    
    Args:
        pdf_path: Path to the target PDF file.
        
    Returns:
        List of dictionaries containing 'page_number' (1-indexed) and 'text'.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    pages_data = []
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"Opened PDF '{pdf_path}' with {len(doc)} pages.")

        for page_idx in range(len(doc)):
            try:
                page = doc[page_idx]
                text = page.get_text()
                page_num = page_idx + 1  # 1-indexed

                # Ignore empty or whitespace-only pages
                if not text or not text.strip():
                    logger.debug(f"Skipping empty page {page_num}.")
                    continue

                pages_data.append({
                    "page_number": page_num,
                    "text": text.strip()
                })
            except Exception as e:
                logger.error(f"Error extracting text from page {page_idx + 1}: {e}")
                continue

        doc.close()
        logger.info(f"Successfully extracted {len(pages_data)} non-empty pages.")
        return pages_data
    except Exception as e:
        logger.error(f"Failed to open or process PDF document '{pdf_path}': {e}")
        raise


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Splits text into chunks of approximately chunk_size characters with overlap,
    aligning boundaries to paragraph, line, sentence, or word breaks.
    
    Args:
        text: Source text to split.
        chunk_size: Target maximum characters per chunk (~800).
        overlap: Character overlap between consecutive chunks (~150).
        
    Returns:
        List of text chunks.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            final_chunk = text[start:].strip()
            if final_chunk:
                chunks.append(final_chunk)
            break

        # Search for natural boundary in preferred order
        split_idx = text.rfind("\n\n", start, end)
        if split_idx == -1 or split_idx <= start + (chunk_size // 2):
            split_idx = text.rfind("\n", start, end)
        if split_idx == -1 or split_idx <= start + (chunk_size // 2):
            split_idx = text.rfind(". ", start, end)
            if split_idx != -1:
                split_idx += 1  # Include period
        if split_idx == -1 or split_idx <= start + (chunk_size // 2):
            split_idx = text.rfind(" ", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = end

        chunk = text[start:split_idx].strip()
        if chunk:
            chunks.append(chunk)

        # Calculate next start point respecting overlap and aligning to word boundary
        new_start = split_idx - overlap
        if new_start <= start:
            new_start = start + 1
        else:
            space_pos = text.find(" ", new_start)
            if space_pos != -1 and space_pos < split_idx:
                new_start = space_pos + 1
        start = new_start

    return chunks


def build_chunks(pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes extracted page dictionaries and produces chunked documents with metadata.
    
    Returns:
        List of dictionaries with 'id', 'text', and 'metadata'.
    """
    chunked_documents = []

    for page_info in pages_data:
        page_num = page_info["page_number"]
        page_text = page_info["text"]

        text_chunks = chunk_text(page_text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        for chunk_idx, chunk in enumerate(text_chunks):
            chunk_id = f"page_{page_num}_chunk_{chunk_idx}"
            chunked_documents.append({
                "id": chunk_id,
                "text": chunk,
                "metadata": {
                    "page": page_num,
                    "chunk_id": chunk_id,
                    "source": "handbook.pdf"
                }
            })

    logger.info(f"Created {len(chunked_documents)} total chunks across {len(pages_data)} pages.")
    return chunked_documents


def get_embedding_function(model_name: str = EMBEDDING_MODEL_NAME):
    """
    Initializes and returns ChromaDB SentenceTransformerEmbeddingFunction.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)


def ingest_pdf(
    pdf_path: str = DEFAULT_PDF_PATH,
    db_dir: str = CHROMA_DB_DIR,
    collection_name: str = COLLECTION_NAME,
    rebuild: bool = False
) -> chromadb.Collection:
    """
    Ingests handbook.pdf into persistent ChromaDB.
    
    Checks if collection exists and has documents; skips regeneration unless rebuild=True.
    
    Args:
        pdf_path: Path to handbook.pdf.
        db_dir: Local ChromaDB storage path.
        collection_name: Name of the vector collection.
        rebuild: Whether to drop existing collection and rebuild from scratch.
        
    Returns:
        ChromaDB Collection instance.
    """
    embedding_fn = get_embedding_function(EMBEDDING_MODEL_NAME)
    client = chromadb.PersistentClient(path=db_dir)

    # Check if collection exists
    existing_collections = [c.name for c in client.list_collections()]
    
    if rebuild and collection_name in existing_collections:
        logger.info(f"Rebuild requested. Deleting existing collection '{collection_name}'...")
        client.delete_collection(name=collection_name)
        existing_collections.remove(collection_name)

    if collection_name in existing_collections:
        collection = client.get_collection(name=collection_name, embedding_function=embedding_fn)
        count = collection.count()
        if count > 0 and not rebuild:
            logger.info(f"Collection '{collection_name}' already exists and contains {count} chunks. Skipping ingestion.")
            return collection

    # Create new collection and populate
    logger.info(f"Creating and populating collection '{collection_name}'...")
    collection = client.create_collection(name=collection_name, embedding_function=embedding_fn)

    pages = extract_pages_from_pdf(pdf_path)
    chunks = build_chunks(pages)

    if not chunks:
        logger.warning("No chunks generated from PDF.")
        return collection

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Ingest in batches to handle memory and progress cleanly
    batch_size = 64
    for i in range(0, len(chunks), batch_size):
        end = min(i + batch_size, len(chunks))
        collection.add(
            ids=ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end]
        )
        logger.info(f"Added chunks {i + 1} to {end} of {len(chunks)} into ChromaDB.")

    logger.info(f"Ingestion complete! Total documents in collection: {collection.count()}")
    return collection


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest handbook.pdf into ChromaDB vector database.")
    parser.add_argument("--pdf", default=DEFAULT_PDF_PATH, help="Path to input PDF file")
    parser.add_argument("--db", default=CHROMA_DB_DIR, help="Path to ChromaDB directory")
    parser.add_argument("--collection", default=COLLECTION_NAME, help="Collection name")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild collection from scratch")
    args = parser.parse_args()

    ingest_pdf(
        pdf_path=args.pdf,
        db_dir=args.db,
        collection_name=args.collection,
        rebuild=args.rebuild
    )
