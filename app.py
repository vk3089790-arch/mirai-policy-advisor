"""
Mirai School of Technology Policy Advisor
AI-powered Academic & Hostel Handbook Assistant
Streamlit Web User Interface
"""

import os
import streamlit as st

# Offline flags for local sentence-transformers cache
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from rag import answer

# Configure Streamlit page layout and metadata
st.set_page_config(
    page_title="Mirai School of Technology Policy Advisor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Design System for Dark Theme UI
st.markdown(
    """
    <style>
    /* Dark Theme Global Adjustments */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header Typography */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #60a5fa;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    .sub-title {
        font-size: 1.05rem;
        font-weight: 400;
        color: #94a3b8;
        margin-bottom: 1.25rem;
        line-height: 1.5;
    }
    
    /* Result Answer Card (Dark Theme) */
    .answer-card {
        background: linear-gradient(180deg, #131d31 0%, #0f172a 100%);
        border: 1px solid #1e293b;
        border-left: 5px solid #3b82f6;
        padding: 1.25rem 1.4rem;
        border-radius: 0.6rem;
        font-size: 1.02rem;
        line-height: 1.65;
        color: #f1f5f9;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    
    /* [not found] Strict Grounding Card (Dark Theme) */
    .not-found-card {
        background: linear-gradient(180deg, #221217 0%, #1a0f12 100%);
        border: 1px solid #4c1d24;
        border-left: 5px solid #f43f5e;
        padding: 1.25rem 1.4rem;
        border-radius: 0.6rem;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .not-found-tag {
        font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
        font-size: 1.2rem;
        font-weight: 700;
        color: #fb7185;
        margin-bottom: 0.35rem;
    }
    .not-found-desc {
        font-size: 0.95rem;
        color: #fda4af;
        line-height: 1.55;
    }
    
    /* Source and Chunk Citations */
    .citation-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        margin-top: 0.4rem;
        margin-bottom: 0.5rem;
    }
    .source-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background-color: #1e3a8a;
        color: #bfdbfe;
        border: 1px solid #2563eb;
        padding: 0.25rem 0.65rem;
        border-radius: 0.375rem;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .chunk-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background-color: #1e293b;
        color: #94a3b8;
        border: 1px solid #334155;
        padding: 0.25rem 0.65rem;
        border-radius: 0.375rem;
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 0.78rem;
    }

    /* Dark-themed Disclaimer Card with Subtle Border */
    .disclaimer-card {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 0.5rem;
        padding: 0.9rem 1.25rem;
        margin-top: 2.25rem;
        font-size: 0.85rem;
        color: #64748b;
        line-height: 1.5;
        text-align: center;
    }
    .disclaimer-card b {
        color: #cbd5e1;
    }

    /* Sidebar Spacing & Polish */
    section[data-testid="stSidebar"] {
        background-color: #0d121f;
        border-right: 1px solid #1e293b;
    }
    .sidebar-section-text {
        font-size: 0.9rem;
        line-height: 1.55;
        color: #94a3b8;
    }
    
    /* Responsive styling for smaller screens */
    @media (max-width: 768px) {
        .main-title {
            font-size: 1.6rem !important;
        }
        .sub-title {
            font-size: 0.95rem !important;
        }
        .answer-card, .not-found-card {
            padding: 1rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "main_query_input" not in st.session_state:
    st.session_state.main_query_input = ""


def set_example_question(question_text: str):
    """Callback to populate the question input before the next script execution."""
    st.session_state.main_query_input = question_text


# Example evaluation questions with official handbook alignment
EXAMPLE_QUESTIONS = [
    {
        "label": "📊 Q1: Attendance (72%) & Exam Debarment",
        "question": "I have 72% attendance this semester. How many attendance marks will I receive, and am I eligible to appear for the final examination?"
    },
    {
        "label": "🏥 Q2: Medical Leave Document Deadline",
        "question": "Within how many days after recovery must a student submit supporting documents for Medical Leave? What happens if the documents are submitted after this period?"
    },
    {
        "label": "🏊 Q3: Swimming Pool & Squash Court Fee",
        "question": "What is the monthly subscription fee for using the campus swimming pool and indoor squash court?"
    },
    {
        "label": "🏛️ Q4: New Student Club Approval Workflow",
        "question": "What minimum percentage of batch-student support is required to propose a new student club, and which authority reviews the proposal first?"
    },
    {
        "label": "📶 Q5: Mirai_Student_5G Wi-Fi Password",
        "question": "What is the default WPA2 password for the Mirai_Student_5G campus Wi-Fi network?"
    }
]


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎓 Mirai Policy Advisor")
    st.caption("Official Institutional Reference System")
    st.markdown("---")

    # Expandable Section: About
    with st.expander("📌 About the Advisor", expanded=True):
        st.markdown(
            "<div class='sidebar-section-text'>"
            "The <b>Mirai School of Technology Policy Advisor</b> provides verified, "
            "zero-hallucination answers to student inquiries regarding academic regulations, "
            "attendance thresholds, hostel conduct, and disciplinary policies."
            "</div>",
            unsafe_allow_html=True
        )

    # Expandable Section: Architecture
    with st.expander("⚙️ System Architecture", expanded=False):
        st.markdown(
            """
            <div class='sidebar-section-text'>
            <b>1. PyMuPDF Ingestion</b>: 50-page official handbook parsed with 1-based page indexing.<br><br>
            <b>2. Semantic Chunking</b>: 146 structured chunks with ~800 character windows and ~150 overlap.<br><br>
            <b>3. Dense Embeddings</b>: 384-dimensional vectors generated via <code>all-MiniLM-L6-v2</code>.<br><br>
            <b>4. ChromaDB Storage</b>: Persistent vector store in <code>./chroma_db</code>.<br><br>
            <b>5. Gemini Grounding</b>: Distance-threshold validation followed by strict system-prompt evaluation.
            </div>
            """,
            unsafe_allow_html=True
        )

    # Expandable Section: Source Document
    with st.expander("📄 Source Document", expanded=False):
        st.markdown(
            """
            <div class='sidebar-section-text'>
            • <b>Corpus</b>: Mirai School of Technology Academic & Hostel Policy Handbook<br>
            • <b>File</b>: <code>handbook.pdf</code><br>
            • <b>Scope</b>: 50 Pages (Chapters 1–5, Modules 1.0–50.0)<br>
            • <b>Indexed Chunks</b>: 146 chunks
            </div>
            """,
            unsafe_allow_html=True
        )

    # Expandable Section: Grounding Policy
    with st.expander("🛡️ Grounding Policy", expanded=False):
        st.info(
            "Zero Hallucination Constraint:\n\n"
            "This advisor answers exclusively using verified context from handbook.pdf. "
            "If a topic is not explicitly documented, it returns exactly [not found] "
            "and suppresses unverified citations."
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Advisory History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.main_query_input = ""
        st.rerun()


# ==============================================================================
# MAIN PAGE CONTENT
# ==============================================================================
st.markdown("<div class='main-title'>Mirai School of Technology Policy Advisor</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Official AI advisory grounded strictly in the <i>Mirai School of Technology Academic & Hostel Policy Handbook</i>.</div>",
    unsafe_allow_html=True
)

# Example Questions Section (Responsive 2-column grid layout)
st.markdown("##### 💡 Example Questions (Click to populate):")
col_left, col_right = st.columns(2)

for idx, ex in enumerate(EXAMPLE_QUESTIONS):
    target_col = col_left if idx % 2 == 0 else col_right
    with target_col:
        st.button(
            ex["label"],
            key=f"ex_btn_{idx}",
            on_click=set_example_question,
            args=(ex["question"],),
            use_container_width=True
        )

st.markdown("<br>", unsafe_allow_html=True)

# Query Input Form
with st.form("advisor_query_form", clear_on_submit=False):
    user_query = st.text_input(
        "Enter your student handbook policy question:",
        key="main_query_input",
        placeholder="Type a policy question (e.g., What happens if medical leave is submitted late?)..."
    )
    col_ask, col_space = st.columns([1, 4])
    with col_ask:
        submitted = st.form_submit_button("🔍 Ask Advisor", type="primary", use_container_width=True)

if submitted:
    if not user_query or not user_query.strip():
        st.warning("Please enter a question before submitting.")
    else:
        with st.spinner("Searching official handbook corpus and synthesizing grounded advice..."):
            try:
                # Call existing backend RAG logic
                result = answer(user_query.strip())
                ans_text = result.get("answer", "")
                sources = result.get("sources", [])
                chunk_ids = result.get("chunk_ids", [])

                # Add to message history (input remains visible for reference)
                st.session_state.messages.insert(0, {
                    "question": user_query.strip(),
                    "answer": ans_text,
                    "sources": sources,
                    "chunk_ids": chunk_ids
                })
            except Exception as e:
                st.error(f"Failed to generate response: {str(e)}")


# ==============================================================================
# RESULTS & CITATIONS
# ==============================================================================
if st.session_state.messages:
    st.markdown("### 📋 Advisor Response History")

    for item in st.session_state.messages:
        st.markdown(f"**Question:** *{item['question']}*")

        ans = item["answer"]
        sources = item.get("sources", [])
        chunk_ids = item.get("chunk_ids", [])

        # Display [not found] card when evidence is missing
        if ans.strip() == "[not found]":
            st.markdown(
                """
                <div class='not-found-card'>
                    <div class='not-found-tag'>[not found]</div>
                    <div class='not-found-desc'>
                        The supplied <b>Mirai School of Technology Academic & Hostel Policy Handbook</b> (<code>handbook.pdf</code>)
                        does not contain information regarding this inquiry. In accordance with the institutional grounding policy,
                        no assumptions, external parameters, or unverified claims are substituted.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Display verified answer card
            st.markdown(
                f"<div class='answer-card'>{ans}</div>",
                unsafe_allow_html=True
            )

            # Display source citations matching the design system
            if sources or chunk_ids:
                st.markdown("**Verified Citations:**")
                badges_html = "<div class='citation-container'>"
                if sources:
                    badges_html += "".join([f"<span class='source-badge'>📄 Page {p}</span>" for p in sources])
                if chunk_ids:
                    badges_html += "".join([f"<span class='chunk-badge'>🧩 {cid}</span>" for cid in chunk_ids])
                badges_html += "</div>"
                st.markdown(badges_html, unsafe_allow_html=True)
            else:
                st.caption("No specific page cited.")

        st.markdown("<hr style='border-color: #1e293b; margin: 1.5rem 0;'>", unsafe_allow_html=True)


# ==============================================================================
# MANDATORY DISCLAIMER
# ==============================================================================
st.markdown(
    """
    <div class='disclaimer-card'>
        ⚠️ <b>Disclaimer:</b> Answers are based exclusively on the official <i>Mirai School of Technology Academic & Hostel Policy Handbook</i> (<code>handbook.pdf</code>).
        Always verify critical academic or disciplinary decisions with the university administration.
    </div>
    """,
    unsafe_allow_html=True
)
