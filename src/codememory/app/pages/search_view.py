"""Hybrid Semantic & Structured Search View for CodeMemory."""

import streamlit as st

from codememory.app.components import get_service, render_empty_state


def render_search_page() -> None:
    """Render hybrid semantic and structured search UI over CodeMemory memory documents."""
    st.header("🔎 Hybrid Semantic & Memory Search")
    st.caption("Search across concepts, submission code, attempt reasoning, mistakes, and AI analyses using vector similarity + keyword matching.")

    service = get_service()

    search_input = st.text_input(
        "Enter Concept, Code Fragment, or Intent Query",
        placeholder="e.g., 'sliding window', 'problems where I struggled with duplicate elements', 'O(n) HashMap'",
    )

    with st.expander("⚙️ Memory Document Filters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_type = st.selectbox(
                "Memory Type Filter",
                options=["Any", "Problem", "Attempt", "Submission", "Mistake", "Note", "AI Analysis"],
            )
        with c2:
            sel_diff = st.selectbox("Difficulty Filter", options=["Any", "Easy", "Medium", "Hard"])
        with c3:
            sel_status = st.selectbox("Status Filter", options=["Any", "Accepted", "Time Limit Exceeded", "Wrong Answer"])

    if not search_input.strip() and sel_type == "Any" and sel_diff == "Any" and sel_status == "Any":
        st.info("Enter a concept or search phrase above to query your personal CodeMemory database.")
        return

    # Prepare filters dictionary
    filters = {}
    if sel_type != "Any":
        filters["memory_type"] = sel_type
    if sel_diff != "Any":
        filters["difficulty"] = sel_diff
    if sel_status != "Any":
        filters["status"] = sel_status

    with st.spinner("Executing hybrid vector & keyword retrieval..."):
        results = service.memory_search(query=search_input, filters=filters, top_k=15)

    st.subheader(f"Hybrid Search Results ({len(results)})")

    if not results:
        st.warning("No memory records matched your query and filter criteria.")
        return

    for res in results:
        badge = "🟢" if res.status == "Accepted" else ("🔴" if "Wrong" in res.status or "Limit" in res.status else "🟡")
        topics_str = ", ".join(res.topics) if res.topics else "None"

        with st.container():
            st.markdown(
                f"""
                <div style="border-left: 4px solid #6366f1; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; background: rgba(255,255,255,0.03)">
                    <h4 style="margin:0; padding:0">{badge} {res.title} <span style="font-size:0.8em; color:#818cf8;">[{res.memory_type.value}]</span></h4>
                    <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 0.85em">
                        Relevance Score: <code>{res.score:.2f}</code> | Source: <b>{res.source}</b> | Difficulty: <code>{res.difficulty}</code> | Topics: {topics_str}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(f"**Snippet Preview:**")
            st.code(res.snippet, language="text")

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Inspect Problem Detail", key=f"mem_det_{res.memory_id}"):
                    prob = service.storage.get_by_id(res.problem_id)
                    if prob:
                        st.session_state["selected_problem_slug"] = prob.slug
                        st.session_state["active_tab"] = "Problem Detail"
                        st.rerun()
            with col_b2:
                if st.button("View Solution", key=f"mem_sol_{res.memory_id}"):
                    prob = service.storage.get_by_id(res.problem_id)
                    if prob:
                        st.session_state["selected_problem_slug"] = prob.slug
                        st.session_state["active_tab"] = "Solution View"
                        st.rerun()

            st.markdown("")
