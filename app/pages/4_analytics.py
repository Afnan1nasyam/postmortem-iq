"""Incident analytics dashboard."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Analytics — PostmortemIQ", page_icon="📊", layout="wide")
st.title("📊 Incident Analytics")


@st.cache_resource
def _get_stores():
    from src.storage.graph_store import KnowledgeGraph
    from src.storage.sql_store import SQLStore
    return SQLStore(), KnowledgeGraph()


sql_store, graph = _get_stores()
incidents = sql_store.get_all_incidents()
graph_stats = graph.get_stats()

if not incidents:
    st.info("No incidents ingested yet. Upload or ingest postmortems to see analytics.")
    st.stop()

# --- Metric cards ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Incidents", len(incidents))
col2.metric("Graph Nodes", graph_stats["total_nodes"])
col3.metric("Graph Edges", graph_stats["total_edges"])
col4.metric("Services Tracked", graph_stats["node_types"].get("Service", 0))

st.divider()

# --- Charts ---
import plotly.graph_objects as go
from plotly.subplots import make_subplots

severity_counts = {}
root_cause_counts = {}
service_counts = {}
resolution_type_counts = {}

for inc in incidents:
    sev = inc.get("severity", "unknown")
    severity_counts[sev] = severity_counts.get(sev, 0) + 1

    try:
        rc = json.loads(inc.get("root_cause_json", "{}"))
        cat = rc.get("category", "unknown")
        root_cause_counts[cat] = root_cause_counts.get(cat, 0) + 1
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        services = json.loads(inc.get("affected_services_json", "[]"))
        for svc in services:
            name = svc.get("name", "unknown")
            service_counts[name] = service_counts.get(name, 0) + 1
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        res = json.loads(inc.get("resolution_json", "{}"))
        rtype = res.get("type", "unknown")
        resolution_type_counts[rtype] = resolution_type_counts.get(rtype, 0) + 1
    except (json.JSONDecodeError, TypeError):
        pass

severity_colors = {
    "critical": "#E74C3C",
    "major": "#F39C12",
    "minor": "#3498DB",
    "unknown": "#95A5A6",
}

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Severity Distribution")
    labels = list(severity_counts.keys())
    values = list(severity_counts.values())
    colors = [severity_colors.get(l, "#95A5A6") for l in labels]
    fig_sev = go.Figure(data=[go.Pie(labels=labels, values=values, marker=dict(colors=colors),
                                      hole=0)])
    fig_sev.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_sev, use_container_width=True)

with col_right:
    st.subheader("Root Cause Categories")
    rc_sorted = sorted(root_cause_counts.items(), key=lambda x: x[1], reverse=True)
    if rc_sorted:
        labels, values = zip(*rc_sorted)
        fig_rc = go.Figure(data=[go.Bar(x=list(values), y=list(labels), orientation="h",
                                         marker_color="#4A90D9")])
        fig_rc.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20),
                              yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_rc, use_container_width=True)

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Most Affected Services")
    svc_sorted = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    if svc_sorted:
        labels, values = zip(*svc_sorted)
        fig_svc = go.Figure(data=[go.Bar(x=list(values), y=list(labels), orientation="h",
                                          marker_color="#2ECC71")])
        fig_svc.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20),
                               yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_svc, use_container_width=True)

with col_right2:
    st.subheader("Resolution Types")
    if resolution_type_counts:
        labels = list(resolution_type_counts.keys())
        values = list(resolution_type_counts.values())
        fig_res = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig_res.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_res, use_container_width=True)

# --- Query stats ---
st.divider()
st.subheader("Query Log Stats")
query_stats = sql_store.get_query_stats()
qcol1, qcol2 = st.columns(2)
qcol1.metric("Total Queries", query_stats["total_queries"])
if query_stats["by_intent"]:
    qcol2.markdown("**Queries by Intent:**")
    for intent, count in query_stats["by_intent"].items():
        qcol2.text(f"  {intent}: {count}")
