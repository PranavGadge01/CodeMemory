"""Problem Detail, Chronological Evolution Timeline, AI Analysis & Related Problems View for CodeMemory."""

import streamlit as st

from codememory.app.components import get_service, render_empty_state
from codememory.domain.enums import SubmissionStatus


def _status_badge(status: SubmissionStatus) -> str:
    """Return emoji badge string for a SubmissionStatus."""
    return {
        SubmissionStatus.ACCEPTED: "🟢 Accepted",
        SubmissionStatus.WRONG_ANSWER: "🔴 Wrong Answer",
        SubmissionStatus.TIME_LIMIT_EXCEEDED: "🟡 Time Limit Exceeded",
        SubmissionStatus.MEMORY_LIMIT_EXCEEDED: "🟠 Memory Limit Exceeded",
        SubmissionStatus.RUNTIME_ERROR: "⛔ Runtime Error",
        SubmissionStatus.COMPILE_ERROR: "❌ Compile Error",
    }.get(status, f"⚪ {status.value if hasattr(status, 'value') else str(status)}")


def render_problem_detail_page() -> None:
    """Render detailed problem metadata, attempt evolution timeline, AI code analysis, and related problems."""
    st.header("🔍 Problem Detail & Solution Evolution")

    service = get_service()
    all_problems = service.list_problems()

    if not all_problems:
        render_empty_state(message="No problems available.")
        return

    # Selectbox to pick problem
    slug_options = [p.slug for p in all_problems]
    default_index = 0
    if "selected_problem_slug" in st.session_state and st.session_state["selected_problem_slug"] in slug_options:
        default_index = slug_options.index(st.session_state["selected_problem_slug"])

    selected_slug = st.selectbox("Select Problem to Inspect", options=slug_options, index=default_index)
    prob = service.get_problem(selected_slug)

    # ── Problem Header ──────────────────────────────────────────────────────────
    st.title(prob.title)

    is_solved = prob.latest_accepted_submission is not None
    status_str = "🟢 Solved" if is_solved else "🟡 In Progress"
    first_att_date = prob.created_at.strftime("%Y-%m-%d")
    latest_acc = prob.latest_accepted_submission
    solved_date = (
        latest_acc.submitted_at.strftime("%Y-%m-%d")
        if (latest_acc and latest_acc.submitted_at)
        else ("🟢 Solved" if is_solved else "Unsolved")
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Difficulty", prob.difficulty.value if hasattr(prob.difficulty, "value") else str(prob.difficulty))
    m2.metric("Status", status_str)
    m3.metric("Total Attempts", len(prob.attempts))
    m4.metric("First Attempted", first_att_date)
    m5.metric("Solved Date", solved_date)

    # ── LeetCode / Platform Metadata ────────────────────────────────────────────
    meta_col1, meta_col2 = st.columns([2, 1])
    with meta_col1:
        if prob.topics:
            st.markdown(f"**Topics**: {', '.join(f'`{t}`' for t in prob.topics)}")
        else:
            st.markdown("**Topics**: None")

    with meta_col2:
        platform_val = prob.platform.value if hasattr(prob.platform, "value") else str(prob.platform)
        if platform_val and platform_val != "Custom":
            st.markdown(f"**Platform**: {platform_val}")

    if prob.url:
        st.markdown(f"🔗 **Problem Link**: [{prob.url}]({prob.url})")

    if prob.statement:
        with st.expander("📖 Problem Statement", expanded=False):
            st.markdown(prob.statement)

    st.markdown("---")

    # ── Similar & Related Problems (Phase 7 Memory Engine) ────────────────────
    st.subheader("🔗 Similar Problems & Shared Concepts")
    similar_problems = service.memory_find_similar_problem(prob.id, top_k=3)
    if not similar_problems:
        st.info("No similar problems currently recorded in your CodeMemory database.")
    else:
        sim_cols = st.columns(len(similar_problems))
        for idx, sim in enumerate(similar_problems):
            with sim_cols[idx]:
                st.markdown(f"**{sim.title}** (`{sim.difficulty}`)")
                st.caption(f"Similarity Score: `{sim.similarity_score:.2f}`")
                st.markdown(f"**Why Similar**: {sim.explanation}")
                if st.button("Inspect Problem", key=f"btn_sim_prob_{sim.problem_id}"):
                    sim_prob = service.storage.get_by_id(sim.problem_id)
                    if sim_prob:
                        st.session_state["selected_problem_slug"] = sim_prob.slug
                        st.rerun()

    st.markdown("---")

    # ── AI Solution Evolution Summary ─────────────────────────────────────────
    if len(prob.attempts) > 0:
        st.subheader("🧬 Solution Evolution & AI Analysis")
        evo_col1, evo_col2 = st.columns([1, 4])
        with evo_col1:
            if st.button("✨ Analyze Solution Evolution", key="btn_evo_summary"):
                st.session_state[f"evo_analysis_{prob.id}"] = service.analyze_solution_evolution_ai(prob.slug)

        if f"evo_analysis_{prob.id}" in st.session_state:
            evo = st.session_state[f"evo_analysis_{prob.id}"]
            st.success(f"**AI Evolution Summary**: {evo.overall_summary}")

            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown(f"- **Initial Approach**: `{evo.initial_approach}`")
                st.markdown(f"- **Final Approach**: `{evo.final_approach}`")
                if evo.major_changes:
                    st.markdown("**Major Strategic Changes:**")
                    for mc in evo.major_changes:
                        st.markdown(f"  - {mc}")
            with ec2:
                if evo.optimization_steps:
                    st.markdown("**Optimization Steps:**")
                    for opt in evo.optimization_steps:
                        st.markdown(f"  - {opt}")
                if evo.learning_points:
                    st.markdown("**Key Learning Points:**")
                    for lp in evo.learning_points:
                        st.markdown(f"  - {lp}")

        st.markdown("---")

    # ── Solving History ─────────────────────────────────────────────────────────
    st.subheader("📜 My Solving History & Attempt Evolution")

    if not prob.attempts:
        st.info("No attempt history recorded for this problem yet.")
        return

    total_subs = sum(len(a.submissions) for a in prob.attempts)
    accepted_subs = sum(
        1 for a in prob.attempts for s in a.submissions if s.status == SubmissionStatus.ACCEPTED
    )
    failed_subs = total_subs - accepted_subs

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Total Submissions", total_subs)
    sc2.metric("Accepted", accepted_subs)
    sc3.metric("Failed", failed_subs)

    st.markdown("---")

    # Render attempts in chronological order
    sorted_attempts = sorted(prob.attempts, key=lambda a: a.attempt_number)

    for attempt in sorted_attempts:
        is_acc = attempt.is_accepted
        border_color = "#22c55e" if is_acc else "#f59e0b"
        badge = "🟢" if is_acc else ("🔴" if attempt.status == SubmissionStatus.WRONG_ANSWER else "🟡")

        with st.container():
            st.markdown(
                f"""
                <div style="border-left: 4px solid {border_color}; padding: 8px 14px; margin-bottom: 6px; border-radius: 4px; background: rgba(255,255,255,0.03)">
                    <h4 style="margin:0; padding:0">{badge} Attempt #{attempt.attempt_number} — <code>{attempt.status.value if hasattr(attempt.status, 'value') else attempt.status}</code></h4>
                    <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 0.85em">
                        Started: {attempt.created_at.strftime('%Y-%m-%d %H:%M UTC')}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if attempt.reasoning:
                st.markdown(f"**Reasoning**: {attempt.reasoning}")

            if attempt.analysis:
                c1, c2 = st.columns(2)
                c1.markdown(f"- **Time Complexity**: `{attempt.analysis.time_complexity}`")
                c2.markdown(f"- **Space Complexity**: `{attempt.analysis.space_complexity}`")

            if attempt.mistakes:
                st.markdown(f"- **Mistakes / Learnings**: {', '.join(attempt.mistakes)}")

            if attempt.submissions:
                for sub_idx, sub in enumerate(attempt.submissions, 1):
                    sub_status_badge = _status_badge(sub.status)
                    rt = f"{sub.runtime_ms:.1f} ms" if sub.runtime_ms is not None else "N/A"
                    mem = f"{sub.memory_mb:.1f} MB" if sub.memory_mb is not None else "N/A"
                    sub_date = sub.submitted_at.strftime("%Y-%m-%d %H:%M UTC") if sub.submitted_at else "N/A"
                    lang = sub.language or "Unknown"

                    with st.expander(
                        f"Submission {sub_idx} — {sub_status_badge} | {lang} | {sub_date} | Runtime: {rt} | Memory: {mem}",
                        expanded=(sub.status == SubmissionStatus.ACCEPTED),
                    ):
                        if sub.code and sub.code.strip():
                            st.code(sub.code, language=lang.lower().replace("c++", "cpp").replace("c#", "csharp"))
                        else:
                            st.caption("_(No source code recorded)_")

                        # Single Submission AI Analysis Button
                        if st.button(f"🔍 Analyze Submission {sub_idx}", key=f"btn_sub_ai_{sub.id}"):
                            analysis = service.analyze_submission(sub.id)
                            st.session_state[f"sub_analysis_{sub.id}"] = analysis

                        if f"sub_analysis_{sub.id}" in st.session_state:
                            sa = st.session_state[f"sub_analysis_{sub.id}"]
                            st.info(f"🤖 **AI Analysis Summary**: {sa.concise_explanation}")
                            ac1, ac2 = st.columns(2)
                            with ac1:
                                st.markdown(f"- **Inferred Approach**: `{sa.approach}`")
                                st.markdown(f"- **Pattern**: `{sa.inferred_pattern}`")
                                st.markdown(f"- **Time Complexity**: `{sa.time_complexity}`")
                                st.markdown(f"- **Space Complexity**: `{sa.space_complexity}`")
                            with ac2:
                                if sa.potential_issues:
                                    st.warning(f"**Potential Issue / Bug**: {sa.potential_issues}")
                                if sa.strengths:
                                    st.success(f"**Strengths**: {sa.strengths}")
                                if sa.certain_facts:
                                    st.markdown("**Certain Facts:** " + ", ".join(sa.certain_facts))
                                if sa.likely_explanations:
                                    st.markdown("**Likely Explanations:** " + ", ".join(sa.likely_explanations))

            st.markdown("")
