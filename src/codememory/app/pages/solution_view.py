"""Solution View for CodeMemory."""

import streamlit as st

from codememory.app.components import get_service, render_empty_state


def render_solution_page() -> None:
    """Render solution view showing final code, complexity, notes, and related problems."""
    st.header("💻 Final Solution View")

    service = get_service()
    all_problems = service.list_problems()

    if not all_problems:
        render_empty_state(message="No problems in database.")
        return

    slug_options = [p.slug for p in all_problems]
    default_index = 0
    if "selected_problem_slug" in st.session_state and st.session_state["selected_problem_slug"] in slug_options:
        default_index = slug_options.index(st.session_state["selected_problem_slug"])

    selected_slug = st.selectbox("Select Problem Solution", options=slug_options, index=default_index)
    prob = service.get_problem(selected_slug)

    st.title(f"{prob.title} Solution")

    target_sub = prob.latest_accepted_submission or prob.latest_submission
    if not target_sub:
        st.warning("No code submission available for this problem.")
        return

    st.markdown(f"**Language**: `{target_sub.language}` | **Status**: `{target_sub.status.value}`")

    # Final Solution Code Block
    st.code(target_sub.code, language=target_sub.language)

    # Complexity Analysis & Performance Badges
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    target_att = prob.latest_accepted_attempt or (prob.attempts[-1] if prob.attempts else None)
    tc = target_att.analysis.time_complexity if target_att and target_att.analysis else "O(N)"
    sc = target_att.analysis.space_complexity if target_att and target_att.analysis else "O(1)"
    rt_str = f"{target_sub.runtime_ms:.1f} ms" if target_sub.runtime_ms is not None else "N/A"
    mem_str = f"{target_sub.memory_mb:.1f} MB" if target_sub.memory_mb is not None else "N/A"

    col_c1.metric("Time Complexity", tc)
    col_c2.metric("Space Complexity", sc)
    col_c3.metric("Runtime", rt_str)
    col_c4.metric("Memory", mem_str)

    st.markdown("---")

    # Notes & Previous Approaches & Mistakes
    n_col1, n_col2 = st.columns(2)

    with n_col1:
        st.subheader("📝 User Learnings & Notes")
        if prob.notes:
            for note in prob.notes:
                nt_str = note.note_type.value if hasattr(note.note_type, "value") else str(note.note_type)
                st.markdown(f"**[{nt_str}]** (`{note.created_at.strftime('%Y-%m-%d')}`)\n{note.content}")
                st.markdown("---")
        else:
            st.info("No personal notes recorded yet.")

        # Quick note adder
        with st.form("add_note_form"):
            new_note = st.text_area("Add New Intuition/Note")
            submitted = st.form_submit_button("Save Note")
            if submitted and new_note.strip():
                service.add_note(problem_identifier=prob.slug, content=new_note)
                st.success("Note saved successfully!")
                st.rerun()

    with n_col2:
        st.subheader("🔄 Previous Approaches & Mistakes")
        if prob.attempts:
            for att in prob.attempts:
                st.markdown(f"**Attempt #{att.attempt_number}**: `{att.approach_summary}` ({att.status.value})")
                if att.reasoning:
                    st.caption(f"Reasoning: {att.reasoning}")
                if att.mistakes:
                    st.warning(f"Mistakes: {', '.join(att.mistakes)}")
                st.markdown("---")

    # Related Problems (same topics)
    st.subheader("🔗 Related Problems")
    if prob.topics:
        related = service.search(topics=prob.topics[0])
        related_filtered = [r for r in related if r.id != prob.id]
        if related_filtered:
            for r in related_filtered[:4]:
                st.markdown(f"- **[{r.title}](/#)** (`{r.difficulty.value}`) — Topics: {', '.join(r.topics)}")
        else:
            st.info("No other problems found in this topic category.")
