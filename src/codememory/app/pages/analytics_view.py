"""Personal Analytics & Visualizations View for CodeMemory."""

import plotly.express as px
import streamlit as st

from codememory.app.components import get_service, render_empty_state


def render_analytics_page() -> None:
    """Render personal analytics dashboard with Plotly charts and tables."""
    st.header("📊 Deep Personal Analytics")
    st.caption("Inspect topic performance, difficulty breakdown, language share, attempt distributions, and failure patterns.")

    service = get_service()
    overview = service.analytics_service.get_overview()

    if overview.total_problems == 0:
        render_empty_state(message="No analytics data available.")
        return

    # Section 1: Topic Mastery Performance
    st.subheader("1. Topic Performance & Mastery")
    topic_stats = service.analytics_service.get_topic_statistics()

    if topic_stats:
        df_t = [ts.model_dump() for ts in topic_stats]
        fig_topic = px.bar(
            df_t,
            x="topic",
            y=["solved_problems", "total_problems"],
            barmode="group",
            title="Solved vs Total Problems by Topic",
            labels={"value": "Count", "topic": "Topic"},
        )
        fig_topic.update_layout(template="plotly_dark", height=320)
        st.plotly_chart(fig_topic, width='stretch')

        with st.expander("📋 Detailed Topic Statistics Table"):
            st.dataframe(df_t, width='stretch')

    st.markdown("---")

    # Section 2: Difficulty & Language Usage
    st.subheader("2. Difficulty & Language Breakdown")
    c1, c2 = st.columns(2)

    with c1:
        diff_stats = service.analytics_service.get_difficulty_statistics()
        if diff_stats:
            df_d = [ds.model_dump() for ds in diff_stats if ds.total_problems > 0]
            fig_diff = px.pie(
                df_d,
                names="difficulty",
                values="total_problems",
                title="Problems by Difficulty",
                color="difficulty",
                color_discrete_map={"Easy": "#4ADE80", "Medium": "#FCD34D", "Hard": "#FCA5A5"},
                hole=0.4,
            )
            fig_diff.update_layout(template="plotly_dark", height=280)
            st.plotly_chart(fig_diff, width='stretch')

    with c2:
        lang_stats = service.analytics_service.get_language_statistics()
        if lang_stats:
            df_l = [ls.model_dump() for ls in lang_stats]
            fig_lang = px.pie(
                df_l,
                names="language",
                values="total_submissions",
                title="Language Usage Share",
                hole=0.4,
            )
            fig_lang.update_layout(template="plotly_dark", height=280)
            st.plotly_chart(fig_lang, width='stretch')

    st.markdown("---")

    # Section 3: Attempt Distribution & Struggle Problems
    st.subheader("3. Attempt Progression & Struggle Problems")
    att_stats = service.analytics_service.get_attempt_statistics()

    ac1, ac2, ac3 = st.columns(3)
    ac1.metric("Single-Attempt Solved", att_stats.single_attempt_solved_count)
    ac2.metric("Multi-Attempt Solved", att_stats.multiple_attempt_solved_count)
    ac3.metric("Brute-Force to Optimized", att_stats.brute_force_to_optimized_count)

    st.markdown("##### 🚨 Struggle Problems List")
    struggles = service.analytics_service.get_struggle_problems(limit=10)
    if struggles:
        df_str = [s.model_dump() for s in struggles]
        st.dataframe(df_str, width='stretch')
    else:
        st.info("No struggle problems identified.")
