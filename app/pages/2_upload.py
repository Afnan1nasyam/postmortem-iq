"""Upload postmortem page."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Upload — PostmortemIQ", page_icon="📄", layout="wide")
st.title("📄 Upload Postmortem")

st.markdown("Upload an incident postmortem document to extract structured data and add it to the knowledge graph.")

uploaded = st.file_uploader(
    "Choose a postmortem file",
    type=["md", "txt", "html"],
    help="Supported formats: Markdown (.md), Plain text (.txt), HTML (.html)",
)

if uploaded is not None:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="w", encoding="utf-8") as tmp:
        content = uploaded.read().decode("utf-8")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    with st.status("Processing postmortem...", expanded=True) as status:
        try:
            from src.ingestion.loader import load_document
            from src.ingestion.extractor import PostmortemExtractor
            from src.ingestion.chunker import chunk_postmortem
            from src.storage.graph_store import KnowledgeGraph
            from src.storage.sql_store import SQLStore
            from src.storage.vector_store import VectorStore
            from src.utils.embedding import get_embedding_model

            st.write("Loading document...")
            doc = load_document(tmp_path)

            st.write("Extracting structured data...")
            extractor = PostmortemExtractor()
            extraction = extractor.extract(doc)

            st.write("Saving to database...")
            sql = SQLStore()
            sql.save_incident(extraction, source_file=uploaded.name)

            st.write("Adding to knowledge graph...")
            graph = KnowledgeGraph()
            graph.add_incident(extraction)

            st.write("Chunking and embedding...")
            chunks = chunk_postmortem(doc, extraction.incident_id)
            if chunks:
                emb = get_embedding_model()
                texts = [t for t, _ in chunks]
                metadatas = [m.model_dump() for _, m in chunks]
                embeddings = emb.embed_batch(texts)
                vs = VectorStore()
                vs.add_chunks(texts, metadatas, embeddings)

            status.update(label="Processing complete!", state="complete")
        except Exception as exc:
            status.update(label=f"Error: {exc}", state="error")
            st.stop()

    st.success(f"Successfully ingested: **{extraction.title}**")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Extraction Summary")
        st.markdown(f"**Title:** {extraction.title}")
        st.markdown(f"**Date:** {extraction.date or 'Unknown'}")
        st.markdown(f"**Severity:** {extraction.severity}")
        st.markdown(f"**Duration:** {extraction.duration or 'Unknown'}")
        st.markdown(f"**Trigger:** {extraction.trigger_event}")
        st.markdown(f"**Root Cause:** {extraction.root_cause.description}")
        st.markdown(f"**Root Cause Category:** `{extraction.root_cause.category}`")

    with col2:
        st.subheader("Services & Resolution")
        st.markdown("**Affected Services:**")
        for svc in extraction.affected_services:
            st.markdown(f"- **{svc.name}** ({svc.role}) — {svc.impact}")

        st.markdown(f"**Resolution:** {extraction.resolution.description}")
        st.markdown(f"**Resolution Type:** `{extraction.resolution.type}`")

        if extraction.service_dependencies:
            st.markdown("**Dependencies Added to Graph:**")
            for dep in extraction.service_dependencies:
                st.markdown(f"- {dep.from_service} → {dep.to_service} ({dep.type})")

    if extraction.failure_chain:
        with st.expander("Failure Chain"):
            for step in extraction.failure_chain:
                st.markdown(f"- {step}")

    if extraction.preventive_actions:
        with st.expander("Preventive Actions"):
            for action in extraction.preventive_actions:
                st.markdown(f"- {action}")
