"""Knowledge graph visualization page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Graph — PostmortemIQ", page_icon="🕸️", layout="wide")
st.title("🕸️ Knowledge Graph")

NODE_COLORS = {
    "Service": "#4A90D9",
    "Incident": "#E74C3C",
    "RootCause": "#F39C12",
    "FailureMode": "#9B59B6",
    "Resolution": "#2ECC71",
}


@st.cache_resource
def _get_graph():
    from src.storage.graph_store import KnowledgeGraph
    return KnowledgeGraph()


graph = _get_graph()
stats = graph.get_stats()

if stats["total_nodes"] == 0:
    st.info("No data in the knowledge graph yet. Upload or ingest postmortems first.")
    st.stop()

with st.sidebar:
    st.subheader("Filters")
    selected_types = []
    for ntype in NODE_COLORS:
        if st.checkbox(ntype, value=True, key=f"filter_{ntype}"):
            selected_types.append(ntype)

    severity_options = ["all", "critical", "major", "minor", "unknown"]
    severity_filter = st.selectbox("Severity", severity_options)

try:
    from pyvis.network import Network

    net = Network(height="600px", width="100%", directed=True, bgcolor="#0e1117",
                  font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    g = graph._graph
    visible_nodes = set()

    for node, attrs in g.nodes(data=True):
        ntype = attrs.get("type", "unknown")
        if ntype not in selected_types:
            continue
        if ntype == "Incident" and severity_filter != "all":
            if attrs.get("severity") != severity_filter:
                continue

        color = NODE_COLORS.get(ntype, "#888888")
        label = attrs.get("title") or attrs.get("name") or attrs.get("description", node)
        if len(label) > 30:
            label = label[:27] + "..."
        title_hover = f"{ntype}: {attrs.get('title') or attrs.get('name') or attrs.get('description', node)}"

        net.add_node(node, label=label, color=color, title=title_hover, size=20 if ntype == "Service" else 15)
        visible_nodes.add(node)

    for src, tgt, attrs in g.edges(data=True):
        if src in visible_nodes and tgt in visible_nodes:
            edge_label = attrs.get("type", "")
            net.add_edge(src, tgt, title=edge_label, label=edge_label, font={"size": 8})

    html_str = net.generate_html()
    components.html(html_str, height=620, scrolling=False)

except Exception as exc:
    st.error(f"Graph visualization error: {exc}")

st.subheader("Top Connected Services")
top_services = stats.get("top_services", [])
if top_services:
    cols = st.columns([3, 1])
    cols[0].markdown("**Service**")
    cols[1].markdown("**Connections**")
    for name, degree in top_services[:10]:
        cols = st.columns([3, 1])
        cols[0].write(name)
        cols[1].write(str(degree))
else:
    st.info("No service nodes in the graph yet.")

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Total Nodes", stats["total_nodes"])
col2.metric("Total Edges", stats["total_edges"])
col3.metric("Service Nodes", stats["node_types"].get("Service", 0))
