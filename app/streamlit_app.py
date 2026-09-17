"""PostmortemIQ — Main Streamlit entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="PostmortemIQ",
    page_icon="🔍",
    layout="wide",
)


@st.cache_resource
def _get_stores():
    from src.storage.graph_store import KnowledgeGraph
    from src.storage.sql_store import SQLStore
    from src.storage.vector_store import VectorStore

    return {
        "vector": VectorStore(),
        "graph": KnowledgeGraph(),
        "sql": SQLStore(),
    }


stores = _get_stores()

with st.sidebar:
    st.header("System Stats")
    graph_stats = stores["graph"].get_stats()
    col1, col2 = st.columns(2)
    col1.metric("Incidents", len(stores["sql"].get_all_incidents()))
    col2.metric("Vector Chunks", stores["vector"].count())
    col1.metric("Graph Nodes", graph_stats["total_nodes"])
    col2.metric("Graph Edges", graph_stats["total_edges"])

    if graph_stats["node_types"]:
        st.caption("Node types")
        for ntype, count in graph_stats["node_types"].items():
            st.text(f"  {ntype}: {count}")

    st.divider()
    st.caption("PostmortemIQ v0.1.0")

st.title("🔍 PostmortemIQ")
st.markdown(
    "**Incident Postmortem Knowledge Graph + RAG System**\n\n"
    "Ingest engineering postmortems, extract causal chains into a knowledge graph, "
    "and query past incidents using graph-augmented retrieval."
)

st.markdown("### Navigate")
col1, col2, col3, col4 = st.columns(4)
col1.page_link("pages/1_query.py", label="🔍 Query Incidents", icon="🔍")
col2.page_link("pages/2_upload.py", label="📄 Upload Postmortem", icon="📄")
col3.page_link("pages/3_graph.py", label="🕸️ Knowledge Graph", icon="🕸️")
col4.page_link("pages/4_analytics.py", label="📊 Analytics", icon="📊")
