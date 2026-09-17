"""Pyvis graph rendering helper for Streamlit."""

import streamlit.components.v1 as components

NODE_COLORS = {
    "Service": "#4A90D9",
    "Incident": "#E74C3C",
    "RootCause": "#F39C12",
    "FailureMode": "#9B59B6",
    "Resolution": "#2ECC71",
}


def render_graph(graph, selected_types: list[str] | None = None, height: int = 600) -> None:
    """Render a KnowledgeGraph as an interactive Pyvis visualization."""
    from pyvis.network import Network

    selected_types = selected_types or list(NODE_COLORS.keys())

    net = Network(height=f"{height}px", width="100%", directed=True,
                  bgcolor="#0e1117", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    g = graph._graph
    visible = set()

    for node, attrs in g.nodes(data=True):
        ntype = attrs.get("type", "unknown")
        if ntype not in selected_types:
            continue
        color = NODE_COLORS.get(ntype, "#888888")
        label = attrs.get("title") or attrs.get("name") or attrs.get("description", node)
        if len(label) > 30:
            label = label[:27] + "..."
        net.add_node(node, label=label, color=color, title=f"{ntype}: {label}",
                     size=20 if ntype == "Service" else 15)
        visible.add(node)

    for src, tgt, attrs in g.edges(data=True):
        if src in visible and tgt in visible:
            etype = attrs.get("type", "")
            net.add_edge(src, tgt, title=etype, label=etype, font={"size": 8})

    html_str = net.generate_html()
    components.html(html_str, height=height + 20, scrolling=False)
