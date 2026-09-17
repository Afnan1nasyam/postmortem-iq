"""Query interface page."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Query — PostmortemIQ", page_icon="🔍", layout="wide")
st.title("🔍 Query Incidents")

EXAMPLE_QUERIES = [
    "Have we seen Redis memory issues before?",
    "What happens if payment-service goes down?",
    "What is our most common root cause?",
    "How did we fix the connection pool issue?",
    "Show me incidents similar to Kafka lag",
]


@st.cache_resource
def _get_retriever_and_generator():
    from src.retrieval.generator import AnswerGenerator
    from src.retrieval.hybrid_retriever import HybridRetriever
    return HybridRetriever(), AnswerGenerator()


if "query_text" not in st.session_state:
    st.session_state.query_text = ""

st.markdown("**Example queries:**")
cols = st.columns(len(EXAMPLE_QUERIES))
for i, eq in enumerate(EXAMPLE_QUERIES):
    if cols[i].button(eq, key=f"ex_{i}", use_container_width=True):
        st.session_state.query_text = eq

query = st.text_input("Ask a question about past incidents:",
                       value=st.session_state.query_text,
                       key="query_input")
search = st.button("Search", type="primary")

if search and query:
    try:
        retriever, generator = _get_retriever_and_generator()
    except Exception as exc:
        st.error(f"Failed to initialize retrieval system: {exc}")
        st.stop()

    with st.spinner("Searching incidents..."):
        t0 = time.time()
        context = retriever.retrieve(query)
        answer = generator.generate(query, context)
        elapsed = time.time() - t0

    intent = context["intent"]
    intent_colors = {
        "similarity": "blue",
        "blast_radius": "red",
        "pattern": "orange",
        "resolution": "green",
    }
    color = intent_colors.get(str(intent), "gray")
    st.markdown(f"**Intent:** :{color}[{intent}] &nbsp; | &nbsp; **Latency:** {elapsed:.2f}s")

    st.container(border=True).markdown(answer.answer)

    if answer.sources:
        with st.expander(f"📚 Sources ({len(answer.sources)})"):
            for src in answer.sources:
                st.markdown(
                    f"- **Incident:** `{src.get('incident_id', 'N/A')}`  \n"
                    f"  **File:** {src.get('source_file', 'N/A')}  \n"
                    f"  **Distance:** {src.get('distance', 'N/A')}"
                )

    if answer.graph_context:
        with st.expander("🕸️ Graph Insights"):
            st.markdown(answer.graph_context)

elif search and not query:
    st.warning("Please enter a query.")
