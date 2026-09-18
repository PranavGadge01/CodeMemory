"""Settings, Account Connection, and Database Management View for CodeMemory."""

from datetime import datetime, timezone
import streamlit as st

from codememory.app.components import get_service


def _get_sync_engine():
    """Lazy-load the sync engine to avoid import-time side effects."""
    from codememory.connectors.account.service import AccountService
    from codememory.connectors.leetcode.sync import LeetCodeSyncEngine

    return LeetCodeSyncEngine(account_service=AccountService())


def _render_health_check(service) -> None:
    """Render per-component health check results."""
    import time
    with st.spinner("Running health checks..."):
        report = service.health_check()
    overall = report.pop("overall", "unknown")
    ts = report.pop("timestamp", "")
    if overall == "ok":
        st.success(f"✅ All components healthy. ({ts})")
    else:
        st.warning(f"⚠️ System is degraded. Check component details below. ({ts})")

    rows = []
    for comp, data in report.items():
        if not isinstance(data, dict):
            continue
        status = data.get("status", "unknown")
        detail = "  ".join(f"{k}={v}" for k, v in data.items() if k != "status")
        rows.append({"Component": comp, "Status": status.upper(), "Detail": detail})
    if rows:
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), hide_index=True)


def _render_account_status_badge(status_str: str) -> str:
    """Return HTML badge for account connection status."""
    color_map = {
        "Connected": ("#22C55E", "rgba(34,197,94,0.15)"),
        "Not Connected": ("#94A3B8", "rgba(148,163,184,0.15)"),
        "Syncing": ("#38BDF8", "rgba(56,189,248,0.15)"),
        "Failed": ("#EF4444", "rgba(239,68,68,0.15)"),
    }
    color, bg = color_map.get(status_str, ("#94A3B8", "rgba(148,163,184,0.15)"))
    return (
        f'<span style="display:inline-block; padding:4px 12px; border-radius:12px; '
        f'font-size:0.82rem; font-weight:600; color:{color}; background:{bg}; '
        f'border:1px solid {color};">{status_str}</span>'
    )


def render_settings_page() -> None:
    """Render application settings with account connection, sync, database, and config UI."""
    st.header("⚙️ Application Settings")
    st.caption("Manage LeetCode account connection, sync, storage paths, and revision formula weights.")

    service = get_service()

    # =====================================================
    # Section 1: LeetCode Account Connection
    # =====================================================
    st.subheader("1. 🔗 LeetCode Account Connection")

    sync_engine = _get_sync_engine()
    account_service = sync_engine.account_service
    conn = account_service.get_connection("LeetCode")

    if conn and conn.status.value == "Connected":
        # ── Connected State ──
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(34,197,94,0.08) 0%, rgba(56,189,248,0.06) 100%);
                        border: 1px solid rgba(34,197,94,0.25); border-radius: 12px; padding: 20px 24px;
                        margin-bottom: 16px;">
                <div style="display:flex; align-items:center; gap:16px; margin-bottom:12px;">
                    <div style="font-size:2rem;">🟢</div>
                    <div>
                        <div style="font-size:1.1rem; font-weight:700; color:#F8FAFC;">
                            {conn.display_name or conn.username}
                        </div>
                        <div style="font-size:0.85rem; color:#94A3B8;">
                            @{conn.username} &nbsp;·&nbsp; {_render_account_status_badge(conn.status.value)}
                        </div>
                    </div>
                </div>
                <div style="display:flex; gap:24px; flex-wrap:wrap; margin-top:8px;">
                    <div style="font-size:0.82rem; color:#94A3B8;">
                        Connected: <strong style="color:#F8FAFC;">{conn.connected_at.strftime('%b %d, %Y %H:%M UTC') if conn.connected_at else 'N/A'}</strong>
                    </div>
                    <div style="font-size:0.82rem; color:#94A3B8;">
                        Last Sync: <strong style="color:#F8FAFC;">{conn.last_sync_at.strftime('%b %d, %Y %H:%M UTC') if conn.last_sync_at else 'Never'}</strong>
                    </div>
                    <div style="font-size:0.82rem; color:#94A3B8;">
                        Sync Status: <strong style="color:#F8FAFC;">{conn.last_sync_status.value if conn.last_sync_status else '—'}</strong>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # LeetCode Progress from account metadata
        meta = conn.metadata or {}
        if meta.get("solved_all"):
            pcols = st.columns(4)
            pcols[0].metric("Total Solved", meta.get("solved_all", 0))
            pcols[1].metric("Easy", meta.get("solved_easy", 0))
            pcols[2].metric("Medium", meta.get("solved_medium", 0))
            pcols[3].metric("Hard", meta.get("solved_hard", 0))

        # Capabilities
        with st.expander("📋 Integration Capabilities"):
            from codememory.connectors.leetcode.capabilities import LEETCODE_CAPABILITY_EXPLANATIONS
            for cap_key, cap_desc in LEETCODE_CAPABILITY_EXPLANATIONS.items():
                cap_enabled = conn.capabilities.get(cap_key, False)
                icon = "✅" if cap_enabled else "🚫"
                st.markdown(f"{icon} **{cap_key.replace('_', ' ').title()}** — {cap_desc}")

        # Sync & Disconnect Actions
        act_col1, act_col2 = st.columns([1, 1])
        with act_col1:
            if st.button("🔄 Sync Now", type="primary", key="btn_sync_now"):
                with st.spinner("Syncing with LeetCode..."):
                    try:
                        sync_result = sync_engine.sync(service)
                        if sync_result.status.value == "Success":
                            st.success(
                                f"✅ Sync complete! "
                                f"Discovered: {sync_result.records_discovered} · "
                                f"Added: {sync_result.records_added} · "
                                f"Skipped: {sync_result.records_skipped} · "
                                f"Failed: {sync_result.records_failed}"
                            )
                        elif sync_result.status.value == "Partial":
                            st.warning(
                                f"⚠️ Partial sync. Added: {sync_result.records_added}, "
                                f"Failed: {sync_result.records_failed}. Error: {sync_result.error_message}"
                            )
                        else:
                            st.error(f"❌ Sync failed: {sync_result.error_message}")
                    except Exception as e:
                        st.error(f"Sync error: {e}")
                st.rerun()

        with act_col2:
            if st.button("🔌 Disconnect Account", key="btn_disconnect"):
                sync_engine.disconnect_account()
                st.info("Account disconnected. All your existing CodeMemory data has been preserved.")
                st.rerun()

        # Last sync error display
        if conn.last_sync_error:
            st.warning(f"⚠️ Last sync error: {conn.last_sync_error}")

    else:
        # ── Not Connected State ──
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(148,163,184,0.08) 0%, rgba(56,189,248,0.04) 100%);
                        border: 1px solid rgba(148,163,184,0.2); border-radius: 12px; padding: 20px 24px;
                        margin-bottom: 16px;">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                    <div style="font-size:1.8rem;">🔗</div>
                    <div>
                        <div style="font-size:1.05rem; font-weight:700; color:#F8FAFC;">Connect Your LeetCode Account</div>
                        <div style="font-size:0.82rem; color:#94A3B8;">
                            Enter your LeetCode username to sync public profile data and recent submissions.
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        username_input = st.text_input(
            "LeetCode Username",
            placeholder="e.g. neal_wu",
            key="lc_username_input",
            help="Your public LeetCode username. No password or session token needed.",
        )

        if st.button("🔗 Connect Account", type="primary", key="btn_connect_account"):
            if not username_input or not username_input.strip():
                st.error("Please enter a valid LeetCode username.")
            else:
                with st.spinner(f"Validating LeetCode profile for '{username_input.strip()}'..."):
                    try:
                        new_conn = sync_engine.connect_account(username_input.strip())
                        st.success(
                            f"✅ Successfully connected to **{new_conn.display_name or new_conn.username}**'s LeetCode profile!"
                        )
                        st.rerun()
                    except ValueError as ve:
                        st.error(f"❌ {ve}")
                    except Exception as ex:
                        st.error(f"Connection failed: {ex}")

        st.markdown("")
        with st.expander("ℹ️ What data does CodeMemory sync?"):
            st.markdown(
                """
                **CodeMemory uses LeetCode's public GraphQL API to sync:**

                ✅ **Public Profile** — username, display name, avatar, ranking
                ✅ **Solving Progress** — total problems solved by difficulty (Easy/Medium/Hard)
                ✅ **Recent Accepted Submissions** — title, language, timestamp, status

                **CodeMemory does NOT:**

                🚫 Collect passwords or session tokens
                🚫 Scrape private submission code
                🚫 Access cookie data or browser sessions
                🚫 Violate LeetCode Terms of Service

                For full submission code, use the **Data Import** page to upload LeetCode export files.
                """
            )

    st.markdown("---")

    # =====================================================
    # Section 2: Database & Seed Tools
    # =====================================================
    st.subheader("2. 🗄️ Database & Seed Tools")
    st.markdown("Populate your local CodeMemory database with sample classic DSA problems (Two Sum, Reverse Linked List, LRU Cache, BFS).")

    if st.button("🌱 Seed Database with Sample Problems", type="primary"):
        from scripts.seed_data import seed_sample_data
        seed_sample_data(service)
        st.session_state["is_demo_data"] = True
        st.success("🎉 Database successfully seeded with sample DSA problems!")
        st.rerun()

    st.markdown("---")

    # =====================================================
    # Section 3: Storage Paths
    # =====================================================
    st.subheader("3. 📂 Storage Paths")
    st.text_input("Local Base Data Directory", value="data", disabled=True)
    st.text_input("Filesystem Knowledge Directory", value="knowledge", disabled=True)
    st.text_input("DuckDB Database Path", value="data/codememory.duckdb", disabled=True)

    st.markdown("---")

    # =====================================================
    # Section 4: Revision Scoring Weights
    # =====================================================
    st.subheader("4. ⚖️ Revision Scoring Formula Weights")
    st.caption("Adjust relative weights for problem priority calculation:")

    w1 = st.slider("Difficulty Weight", min_value=0.0, max_value=5.0, value=st.session_state.get("rev_w_diff", 2.0), step=0.5)
    w2 = st.slider("Failure Weight", min_value=0.0, max_value=5.0, value=st.session_state.get("rev_w_fail", 3.0), step=0.5)
    w3 = st.slider("Recency Weight", min_value=0.0, max_value=5.0, value=st.session_state.get("rev_w_recency", 2.5), step=0.5)
    w4 = st.slider("Weakness Weight", min_value=0.0, max_value=5.0, value=st.session_state.get("rev_w_weakness", 2.0), step=0.5)

    if st.button("Save Weight Settings"):
        st.session_state["rev_w_diff"] = w1
        st.session_state["rev_w_fail"] = w2
        st.session_state["rev_w_recency"] = w3
        st.session_state["rev_w_weakness"] = w4
        st.success("✅ Revision weights saved for this session. Revision Queue will now use these weights.")

    st.markdown("---")

    # =====================================================
    # Section 5: System Health Check
    # =====================================================
    st.subheader("5. 🩺 System Health Check")
    st.markdown("Verify that all CodeMemory components (storage, DuckDB, AI provider, memory engine, search) are operational.")
    if st.button("📊 Run Health Check", key="btn_health_check"):
        _render_health_check(service)

    st.markdown("---")

    # =====================================================
    # Section 6: Danger Zone — Clear All Data
    # =====================================================
    st.subheader("6. 🗑️ Danger Zone")
    st.markdown("⚠️ **Clear all CodeMemory data.** This permanently deletes all problems, submissions, attempts, notes, and cached analyses.")
    if st.checkbox("☑️ I understand this will permanently delete ALL my CodeMemory data", key="confirm_clear"):
        if st.button("🗑️ Clear All Data", type="primary", key="btn_clear_all"):
            import shutil
            from pathlib import Path
            for d in ["data", "knowledge"]:
                p = Path(d)
                if p.exists():
                    shutil.rmtree(p)
                p.mkdir(parents=True, exist_ok=True)
            st.session_state.pop("is_demo_data", None)
            st.success("🧹 All data cleared. CodeMemory has been reset to a fresh state.")
            st.rerun()

