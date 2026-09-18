"""Revision Engine View for CodeMemory."""

import streamlit as st

from codememory.app.components import get_service, render_empty_state


def render_revision_page() -> None:
    """Render prioritized revision queue and review tracking UI."""
    st.header("🧠 Deterministic Revision Engine")
    st.caption("Prioritize practice based on difficulty, failure history, topic weaknesses, and recency.")

    service = get_service()
    all_problems = service.list_problems()

    if not all_problems:
        render_empty_state(message="No problems available for revision.")
        return

    # Filter & Controls
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        all_topics = sorted({t for p in all_problems for t in p.topics if t})
        sel_topic = st.selectbox("Filter Revision Queue by Topic", options=["All Topics"] + all_topics)
    with c2:
        only_due = st.checkbox("Show Only Due (>7 Days Unreviewed)", value=False)
    with c3:
        queue_limit = st.number_input("Max Queue Items", min_value=5, max_value=50, value=10, step=5)

    topic_filter = None if sel_topic == "All Topics" else sel_topic

    # Use session-state revision weights if the user has saved custom ones
    custom_weights = None
    if any(k in st.session_state for k in ("rev_w_diff", "rev_w_fail", "rev_w_recency", "rev_w_weakness")):
        from codememory.revision.revision_models import RevisionWeights
        custom_weights = RevisionWeights(
            difficulty_weight=st.session_state.get("rev_w_diff", 2.0),
            failure_weight=st.session_state.get("rev_w_fail", 3.0),
            recency_weight=st.session_state.get("rev_w_recency", 2.5),
            weakness_weight=st.session_state.get("rev_w_weakness", 2.0),
        )

    if only_due:
        queue = service.get_due_problems(threshold_days=7, limit=queue_limit)
    else:
        queue = service.get_revision_queue(limit=queue_limit, topic=topic_filter, weights=custom_weights)

    st.markdown(f"Displaying **{len(queue)}** prioritized revision targets.")

    if not queue:
        st.success("🎉 Outstanding job! No problems currently due in your revision queue.")
        return

    # Render Revision Queue Cards
    for idx, item in enumerate(queue, 1):
        bd = item.breakdown
        with st.expander(f"#{idx} | **{item.title}** (`{item.difficulty}`) — Priority Score: **{item.priority_score:.1f}**", expanded=(idx <= 2)):
            st.markdown(f"- **Topics**: {', '.join(f'`{t}`' for t in item.topics) if item.topics else 'None'}")
            st.markdown(f"- **Days Since Inactive/Reviewed**: `{bd.days_since_last_activity} days`")

            # Score Breakdown Badges
            st.caption(
                f"Breakdown: Difficulty ({bd.difficulty_score:.1f}) + Failures ({bd.failure_score:.1f}) + Recency ({bd.recency_score:.1f}) + Weakness ({bd.weakness_score:.1f}) - Recent Penalty ({bd.recent_solved_penalty:.1f})"
            )

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✅ Mark as Reviewed", key=f"rev_{item.problem_id}"):
                    service.mark_reviewed(item.slug, notes="Reviewed problem from Streamlit Revision Queue")
                    st.success(f"Marked '{item.title}' as reviewed!")
                    st.rerun()
            with btn_col2:
                if st.button("📖 Open Problem Detail", key=f"open_{item.problem_id}"):
                    st.session_state["selected_problem_slug"] = item.slug
                    st.session_state["active_tab"] = "Problem Detail"
                    st.rerun()
