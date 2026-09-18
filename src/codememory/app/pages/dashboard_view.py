"""Dashboard Section View for CodeMemory."""

import plotly.express as px
import streamlit as st

from codememory.app.components import get_service, render_empty_state, render_metric_card


def render_dashboard_page() -> None:
    """Render main dashboard view with analytics, revision priorities, and memory engine metrics."""
    st.header("⚡ Personal DSA Dashboard")
    st.caption("Track your algorithmic problem-solving journey, evolution, and revision priorities.")

    # Sample-data banner
    if st.session_state.get("is_demo_data", False):
        st.info(
            "🌱 **You are viewing sample/demo data.** "
            "Import your own submissions via the **Import** page to see your real history.",
            icon="ℹ️",
        )

    try:
        service = get_service()
        overview = service.analytics_service.get_overview()
    except Exception as exc:
        st.error(f"❌ Dashboard failed to load: {exc}")
        return

    if overview.total_problems == 0:
        render_empty_state(
            message="No problems recorded yet.",
            action_hint="Click 'Seed Database' in Settings or import submissions to see your dashboard stats!",
        )
        if st.button("🌱 Seed Sample Data Now", type="primary"):
            from scripts.seed_data import seed_sample_data
            seed_sample_data(service)
            st.session_state["is_demo_data"] = True
            st.rerun()
        return

    # Top Metric Cards Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Problems Solved", f"{overview.accepted_problems} / {overview.total_problems}", "Tracked Solved")
    with col2:
        render_metric_card("Total Attempts", f"{overview.total_attempts}", f"{overview.total_submissions} submissions")
    with col3:
        render_metric_card("Acceptance Rate", f"{overview.overall_acceptance_rate_pct}%", f"{overview.first_attempt_acceptance_rate_pct}% 1st-try")
    with col4:
        avg_time = f"{overview.avg_solving_time_minutes:.1f}m" if overview.avg_solving_time_minutes else "N/A"
        render_metric_card("Avg Attempts/Solved", f"{overview.avg_attempts_per_solved_problem}", f"Avg solving time: {avg_time}")

    st.markdown("---")

    # Main Grid: Charts & Personal Insights
    c_left, c_right = st.columns([2, 1])

    with c_left:
        st.subheader("📈 Solving Activity Over Time")
        prog = service.analytics_service.get_progress_over_time(granularity="day")
        if prog:
            df_prog = [p.model_dump() for p in prog]
            fig_line = px.line(
                df_prog,
                x="period",
                y="problems_solved",
                title="Problems Solved Daily",
                markers=True,
                labels={"period": "Date", "problems_solved": "Solved Count"},
            )
            fig_line.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_line, width='stretch')
        else:
            st.info("No activity timestamps recorded yet.")

        st.subheader("🎯 Problems by Topic & Difficulty")
        t_col, d_col = st.columns(2)
        with t_col:
            topics = service.analytics_service.get_topic_statistics()
            if topics:
                df_t = [t.model_dump() for t in topics[:6]]
                fig_t = px.bar(df_t, x="solved_problems", y="topic", orientation="h", title="Top Solved Topics")
                fig_t.update_layout(template="plotly_dark", height=250, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_t, width='stretch')
        with d_col:
            diffs = service.analytics_service.get_difficulty_statistics()
            if diffs:
                df_d = [d.model_dump() for d in diffs if d.total_problems > 0]
                fig_d = px.pie(df_d, names="difficulty", values="total_problems", title="Difficulty Breakdown", hole=0.4)
                fig_d.update_layout(template="plotly_dark", height=250, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_d, width='stretch')

    with c_right:
        st.subheader("🧠 Personal DSA Memory Engine")
        mem_stats = service.memory_engine.get_memory_stats()
        st.markdown(f"- **Total Memory Documents**: `{mem_stats['total_documents']}`")
        st.markdown(f"- **Indexed Vectors**: `{mem_stats['indexed_vectors']}`")
        st.markdown(f"- **Tracked Problems**: `{mem_stats['unique_problems']}`")

        st.markdown("---")
        st.subheader("💡 Personal Insights")
        insights = service.generate_insights()
        for ins in insights:
            st.markdown(f"• **{ins}**")

        st.markdown("---")
        st.subheader("🔥 Top Revision Priority")
        queue = service.get_revision_queue(limit=4)
        if queue:
            for q_item in queue:
                st.markdown(
                    f"**[{q_item.title}](/#)** (`{q_item.difficulty}`)  \n"
                    f"Priority Score: **`{q_item.priority_score}`** | `{q_item.breakdown.days_since_last_activity} days inactive`"
                )
                st.markdown("---")

    # LeetCode Account Status Widget (below main grid)
    _render_account_status_widget()


def _render_account_status_widget() -> None:
    """Render a compact LeetCode Account Status card on the dashboard."""
    try:
        from codememory.connectors.account.service import AccountService

        account_service = AccountService()
        conn = account_service.get_connection("LeetCode")
    except Exception:
        return

    st.markdown("---")
    st.subheader("🔗 LeetCode Account")

    if conn and conn.status.value == "Connected":
        meta = conn.metadata or {}
        solved = meta.get("solved_all", 0)
        last_sync = conn.last_sync_at.strftime("%b %d, %H:%M UTC") if conn.last_sync_at else "Never"
        sync_status = conn.last_sync_status.value if conn.last_sync_status else "—"

        status_color = "#22C55E" if sync_status == "Success" else "#F59E0B" if sync_status == "Partial" else "#94A3B8"

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(34,197,94,0.06) 0%, rgba(56,189,248,0.04) 100%);
                        border: 1px solid rgba(34,197,94,0.2); border-radius: 12px; padding: 16px 20px;">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                    <span style="font-size:1.3rem;">🟢</span>
                    <span style="font-size:0.95rem; font-weight:700; color:#F8FAFC;">
                        {conn.display_name or conn.username}
                    </span>
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; line-height:1.8;">
                    Solved on LC: <strong style="color:#4ADE80;">{solved}</strong><br/>
                    Last Sync: <strong style="color:#F8FAFC;">{last_sync}</strong><br/>
                    Status: <strong style="color:{status_color};">{sync_status}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if meta.get("solved_easy") or meta.get("solved_medium") or meta.get("solved_hard"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Easy", meta.get("solved_easy", 0))
            c2.metric("Medium", meta.get("solved_medium", 0))
            c3.metric("Hard", meta.get("solved_hard", 0))

    else:
        st.info(
            "💡 **LeetCode account not connected.**\n\n"
            "Go to **Settings** → **Connect Account** to sync your profile and submissions."
        )

