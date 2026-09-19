"""Settings, Account Connection, and Database Management View for CodeMemory.

Every LeetCode interaction in this view goes through the canonical service
surface ``service.leetcode`` (Phase C). The view never constructs the sync
engine or the GraphQL client, and it never asks for or displays credentials.
"""

from datetime import datetime, timezone
import logging

import streamlit as st

from codememory.app.components import get_service
from codememory.connectors.leetcode.service import safe_error_message

logger = logging.getLogger(__name__)

# Human-readable names for the fields the public sync cannot obtain. Shown
# beside every sync result so the UI never implies metrics were synchronized
# when the public API cannot supply them.
UNAVAILABLE_FIELD_LABELS = {
    "code": "source code",
    "runtime_ms": "runtime",
    "memory_mb": "memory",
}

_COVERAGE_EXPLANATION = (
    "The public LeetCode API exposes only a server-bounded window of your most "
    "recent **accepted** submissions. It is not a complete history, and no "
    "paging cursor exists to reach older submissions."
)

_ACTION_OUTCOME_KEY = "lc_action_outcome"


def _fmt_timestamp(value: datetime | None) -> str:
    """Render a UTC timestamp, or ``"Never"`` when absent."""
    if value is None:
        return "Never"
    moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%b %d, %Y %H:%M UTC")


def _badge_html(label: str, color: str, background: str) -> str:
    """Return an HTML badge chip for a status label."""
    return (
        f'<span style="display:inline-block; padding:4px 12px; border-radius:12px; '
        f'font-size:0.82rem; font-weight:600; color:{color}; background:{background}; '
        f'border:1px solid {color};">{label}</span>'
    )


def _sync_state_badge(sync_state) -> str:
    """Badge for a :class:`SyncState` value, color-coded by outcome."""
    styles = {
        "Success": ("#22C55E", "rgba(34,197,94,0.15)"),
        "Partial": ("#F59E0B", "rgba(245,158,11,0.15)"),
        "Failed": ("#EF4444", "rgba(239,68,68,0.15)"),
        "Running": ("#38BDF8", "rgba(56,189,248,0.15)"),
        "Idle": ("#94A3B8", "rgba(148,163,184,0.15)"),
    }
    color, background = styles.get(sync_state.value, ("#94A3B8", "rgba(148,163,184,0.15)"))
    return _badge_html(sync_state.value, color, background)


def _unavailable_fields_note(status) -> str | None:
    """Explain which fields the public sync cannot supply, if any are reported."""
    missing = [UNAVAILABLE_FIELD_LABELS.get(f, f) for f in (status.unavailable_fields or [])]
    if not missing:
        return None
    return (
        "This sync carries **no " + _natural_join(missing) + "** — the public LeetCode API "
        "does not expose them for recent submissions. Import a LeetCode export file "
        "on the **Data Import** page if you need them."
    )


def _natural_join(items: list[str]) -> str:
    """Join a list as natural prose: "a, b or c"."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " or " + items[-1]


# Record counts are rendered with one canonical label set everywhere in the UI,
# so the sync outcome and the status card can never disagree.
_COUNT_LABELS = (
    ("discovered", "Discovered"),
    ("imported", "Imported"),
    ("skipped", "Skipped"),
    ("failed", "Failed"),
)


def _count_line(counts: dict[str, int | None]) -> str:
    """Render record counts as one line, each shown only where a value is known."""
    return " · ".join(
        f"{label}: {counts[key]}" for key, label in _COUNT_LABELS if counts.get(key) is not None
    )


def _sync_summary_lines(status) -> list[str]:
    """Build the per-count summary line from the last sync, if there was one."""
    counts = {
        "discovered": status.records_discovered,
        "imported": status.records_imported,
        "skipped": status.records_skipped,
        "failed": status.records_failed,
    }
    if not any(v is not None for v in counts.values()):
        return []
    return [_count_line(counts)]


def _sync_result_message(result) -> tuple[str, str]:
    """Classify a ``SyncStatus`` into a (style, message) pair for display.

    The states the UI must keep visibly distinct. The message always names the
    outcome and the counts, so a partial run can never be read as success.
    """
    counts = _count_line(
        {
            "discovered": result.records_discovered,
            "imported": result.records_added,
            "skipped": result.records_skipped,
            "failed": result.records_failed,
        }
    )
    state = result.status.value
    if state == "Success":
        return "success", f"✅ Sync complete! {counts}"
    if state == "Partial":
        detail = f" Error: {result.error_message}" if result.error_message else ""
        return "warning", f"⚠️ Partial sync — some parts failed. {counts}.{detail}"
    if state == "Failed":
        return "error", f"❌ Sync failed: {result.error_message or 'unknown error'}"
    return "info", f"Sync finished in state '{state}'. {counts}"


def _render_action_outcome() -> None:
    """Render the outcome of the last account action once, then clear it."""
    outcome = st.session_state.pop(_ACTION_OUTCOME_KEY, None)
    if not outcome:
        return
    style, message = outcome
    if style == "success":
        st.success(message)
    elif style == "warning":
        st.warning(message)
    elif style == "error":
        st.error(message)
    else:
        st.info(message)


def _store_outcome(style: str, message: str) -> None:
    """Record an outcome for the next render and trigger a rerun."""
    st.session_state[_ACTION_OUTCOME_KEY] = (style, message)
    st.rerun()


def _handle_connect(leetcode, username: str) -> None:
    """Validate and connect an account, surfacing a safe message either way."""
    username_clean = (username or "").strip()
    if not username_clean:
        _store_outcome("error", "Please enter a valid LeetCode username.")
        return

    with st.spinner(f"Validating public LeetCode profile for '{username_clean}'..."):
        try:
            conn = leetcode.connect(username_clean)
        except Exception as exc:  # validation / transport failure — message is safe
            logger.warning("LeetCode connect failed for '%s': %s", username_clean, exc)
            _store_outcome("error", f"❌ {safe_error_message(exc)}")
            return

    _store_outcome(
        "success",
        f"✅ Connected to **{conn.display_name or conn.username}**'s LeetCode profile. "
        "No password, cookie or token was requested or stored.",
    )


def _handle_sync(leetcode) -> None:
    """Run one sync and classify the result for display."""
    with st.spinner("Syncing with LeetCode (public API)..."):
        try:
            result = leetcode.sync()
        except Exception as exc:
            logger.warning("LeetCode sync failed: %s", exc)
            _store_outcome("error", f"❌ {safe_error_message(exc)}")
            return

    style, message = _sync_result_message(result)
    notices = []
    gap = _gap_explanation_for(leetcode.status())
    if gap:
        notices.append(gap)
    unavailable = _unavailable_fields_note(leetcode.status())
    if unavailable:
        notices.append(unavailable)

    _store_outcome(style, "\n\n".join([message, *notices]))


def _gap_explanation_for(status) -> str | None:
    """Honest explanation when the recent window moved past the last watermark."""
    if not status.gap_detected:
        return None
    return (
        "⚠️ **Gap detected.** The oldest submission in this window is newer than the "
        "newest one persisted by the previous sync, so some submissions exist on "
        "LeetCode but fell outside the public recent-submission window. They cannot be "
        "recovered by re-syncing — use a manual import if you have an export of them."
    )


def _render_connected_account(status) -> None:
    """Render the connected-account card with full sync/coverage state."""
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.08) 0%, rgba(56,189,248,0.06) 100%);
                    border: 1px solid rgba(34,197,94,0.25); border-radius: 12px; padding: 20px 24px;
                    margin-bottom: 16px;">
            <div style="display:flex; align-items:center; gap:16px; margin-bottom:12px;">
                <div style="font-size:2rem;">🟢</div>
                <div>
                    <div style="font-size:1.1rem; font-weight:700; color:#F8FAFC;">
                        {status.display_name or status.username}
                    </div>
                    <div style="font-size:0.85rem; color:#94A3B8;">
                        @{status.username} &nbsp;·&nbsp; {_badge_html("Connected", "#22C55E", "rgba(34,197,94,0.15)")}
                        &nbsp; Sync: {_sync_state_badge(status.sync_state)}
                    </div>
                </div>
            </div>
            <div style="display:flex; gap:24px; flex-wrap:wrap; margin-top:8px;">
                <div style="font-size:0.82rem; color:#94A3B8;">
                    Last attempted: <strong style="color:#F8FAFC;">{_fmt_timestamp(status.last_attempted_sync)}</strong>
                </div>
                <div style="font-size:0.82rem; color:#94A3B8;">
                    Last successful: <strong style="color:#4ADE80;">{_fmt_timestamp(status.last_successful_sync)}</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Record counts: shown only where a sync has actually reported them.
    counts = _sync_summary_lines(status)
    if counts:
        st.markdown("**Last sync** — " + counts[0])

    # An honest, persistent signal: a gap means data exists on LeetCode that no
    # amount of re-syncing through the public window can recover.
    gap = _gap_explanation_for(status)
    if gap:
        st.warning(gap)

    # Fields the public API cannot supply — never implied as synchronized.
    unavailable = _unavailable_fields_note(status)
    if unavailable:
        st.info(unavailable)

    # Public solving progress from the profile query.
    if status.solved_all is not None:
        pcols = st.columns(4)
        pcols[0].metric("Total Solved", status.solved_all)
        pcols[1].metric("Easy", status.solved_easy or 0)
        pcols[2].metric("Medium", status.solved_medium or 0)
        pcols[3].metric("Hard", status.solved_hard or 0)

    # The coverage contract: the window is server-bounded, never full history.
    with st.expander("🌐 Sync coverage & window"):
        window_lines = [
            f"**Coverage:** `{status.coverage or 'recent-window'}` — {_COVERAGE_EXPLANATION}",
            f"**Window limit:** `{status.window_limit if status.window_limit is not None else '—'}` submissions requested",
            f"**Records in window:** `{status.records_in_window if status.records_in_window is not None else '—'}`",
        ]
        if status.window_truncated:
            window_lines.append(
                "**Window truncated:** the server returned a full window, so older "
                "submissions may exist that this sync cannot reach."
            )
        if status.gap_detected:
            window_lines.append("⚠️ **Gap detected** — see the explanation above.")
        for line in window_lines:
            st.markdown(f"- {line}")

        expander_unavailable = _unavailable_fields_note(status)
        if expander_unavailable:
            st.markdown(f"- {expander_unavailable}")

    # Capabilities (static declaration; never implies private scraping).
    with st.expander("📋 Integration Capabilities"):
        from codememory.connectors.leetcode.capabilities import LEETCODE_CAPABILITY_EXPLANATIONS

        for cap_key, cap_desc in LEETCODE_CAPABILITY_EXPLANATIONS.items():
            cap_enabled = status.capabilities.get(cap_key, False)
            icon = "✅" if cap_enabled else "🚫"
            st.markdown(f"{icon} **{cap_key.replace('_', ' ').title()}** — {cap_desc}")

    # The last error is scrubbed by the service surface before it reaches here.
    if status.last_error:
        st.warning(f"⚠️ Last sync error: {status.last_error}")


def _render_account_actions(leetcode) -> None:
    """Sync and disconnect actions for a connected account."""
    act_col1, act_col2 = st.columns([1, 1])
    with act_col1:
        if st.button("🔄 Sync Now", type="primary", key="btn_sync_now"):
            _handle_sync(leetcode)

    with act_col2:
        if st.button("🔌 Disconnect Account", key="btn_disconnect"):
            _handle_disconnect(leetcode)


def _handle_disconnect(leetcode) -> None:
    """Drop the connection and sync state, keeping every imported submission.

    History is untouched by the disconnect path; the message says so, because a
    user about to disconnect is most often wondering exactly that.
    """
    try:
        removed = leetcode.disconnect()
    except Exception as exc:
        logger.warning("LeetCode disconnect failed: %s", exc)
        _store_outcome("error", f"❌ {safe_error_message(exc)}")
        return

    if removed:
        _store_outcome(
            "info",
            "🔌 Account disconnected. Connection and sync state were removed; "
            "all of your previously imported CodeMemory history has been preserved.",
        )
    else:
        _store_outcome("info", "🔌 No LeetCode account was connected — nothing to disconnect.")


def _render_connect_form(leetcode) -> None:
    """Username-only connection form; no credentials are ever requested."""
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
        help="Your public LeetCode username. No password or session token is needed or accepted.",
    )

    if st.button("🔗 Connect Account", type="primary", key="btn_connect_account"):
        _handle_connect(leetcode, username_input)

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

            The public API exposes only a **recent, server-bounded window** of accepted
            submissions — it is not a complete history, and it carries **no source code,
            runtime or memory**. Use the **Data Import** page to import a full export
            with code and metrics.
            """
        )


def render_settings_page() -> None:
    """Render application settings with account connection, sync, storage paths, and config UI."""
    st.header("⚙️ Application Settings")
    st.caption("Manage LeetCode account connection, sync, storage paths, and revision formula weights.")

    service = get_service()

    # =====================================================
    # Section 1: LeetCode Account Connection
    # =====================================================
    st.subheader("1. 🔗 LeetCode Account Connection")

    # The outcome of the previous connect/sync/disconnect, if any, is shown once here.
    _render_action_outcome()

    # Single service-level surface for the whole account lifecycle. The view never
    # reaches for the sync engine or the GraphQL client directly.
    leetcode = service.leetcode
    status = leetcode.status()

    if status.connected:
        _render_connected_account(status)
        _render_account_actions(leetcode)
    else:
        _render_connect_form(leetcode)

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
