"""Streamlit view for Lightweight DSA Knowledge Graph."""

import streamlit as st
import pandas as pd
from codememory.app.components import get_service, render_page_header, render_metric_card


def render_graph_page() -> None:
    """Render the Knowledge Graph section."""
    render_page_header("Knowledge Graph", "Lightweight relationship model mapping Topics, Problems, Approaches, Mistakes, and Languages.")

    service = get_service()
    graph = service.get_knowledge_graph()

    if not graph.nodes:
        st.info(
            "🕸️ **Knowledge Graph is empty.**\n\n"
            "Import your submissions or seed the database to populate the graph."
        )
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Total Graph Nodes", len(graph.nodes), "🧠")
    with col2:
        render_metric_card("Total Graph Edges", len(graph.edges), "🔗")
    with col3:
        node_types = set(n.type for n in graph.nodes)
        render_metric_card("Node Entity Types", len(node_types), "🏷️")

    st.markdown("---")

    selected_type = st.selectbox("Filter Graph Nodes by Type", ["All"] + sorted(list(node_types)))

    filtered_nodes = graph.nodes if selected_type == "All" else [n for n in graph.nodes if n.type == selected_type]

    st.markdown(f"### 📍 Graph Nodes ({len(filtered_nodes)})")
    nodes_data = [{"ID": n.id, "Label": n.label, "Type": n.type} for n in filtered_nodes]
    st.dataframe(pd.DataFrame(nodes_data), width='stretch')

    st.markdown("---")
    st.markdown("### 🔗 Graph Relationships & Connections")

    edges_data = [
        {"Source Node": e.source_id, "Relationship": e.relationship, "Target Node": e.target_id}
        for e in graph.edges
    ]
    st.dataframe(pd.DataFrame(edges_data), width='stretch')
