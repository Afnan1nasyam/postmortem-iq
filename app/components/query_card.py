"""Reusable query result display component."""

import streamlit as st

from src.models.schemas import QueryResult


def render_query_result(result: QueryResult, intent: str, latency: float) -> None:
    """Render a QueryResult in the Streamlit UI."""
    intent_colors = {
        "similarity": "blue",
        "blast_radius": "red",
        "pattern": "orange",
        "resolution": "green",
    }
    color = intent_colors.get(intent, "gray")
    st.markdown(f"**Intent:** :{color}[{intent}] &nbsp; | &nbsp; **Latency:** {latency:.2f}s")

    st.container(border=True).markdown(result.answer)

    if result.sources:
        with st.expander(f"Sources ({len(result.sources)})"):
            for src in result.sources:
                st.markdown(
                    f"- **Incident:** `{src.get('incident_id', 'N/A')}`  \n"
                    f"  **File:** {src.get('source_file', 'N/A')}"
                )

    if result.graph_context:
        with st.expander("Graph Insights"):
            st.markdown(result.graph_context)
