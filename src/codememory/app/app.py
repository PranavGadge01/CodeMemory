"""Main Streamlit Application Entrypoint for CodeMemory."""

import streamlit as st

from codememory.app.components import apply_custom_css, get_service
from codememory.app.pages.analytics_view import render_analytics_page
from codememory.app.pages.dashboard_view import render_dashboard_page
from codememory.app.pages.export_view import render_export_page
from codememory.app.pages.import_view import render_import_page
from codememory.app.pages.problem_detail_view import render_problem_detail_page
from codememory.app.pages.problems_view import render_problems_page
from codememory.app.pages.revision_view import render_revision_page
from codememory.app.pages.search_view import render_search_page
from codememory.app.pages.settings_view import render_settings_page
from codememory.app.pages.solution_view import render_solution_page


from codememory.app.pages.patterns_view import render_patterns_page
from codememory.app.pages.graph_view import render_graph_page
from codememory.app.pages.ask_codememory_view import render_ask_codememory_page


def main() -> None:
    """Streamlit application entry point."""
    st.set_page_config(
        page_title="CodeMemory - Personal DSA Knowledge Engine",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply CSS aesthetics
    apply_custom_css()

    # Navigation Sidebar
    st.sidebar.title("🧠 CodeMemory")
    st.sidebar.caption("Personal DSA Knowledge System")
    st.sidebar.markdown("---")

    tabs = [
        "Dashboard",
        "Problems Directory",
        "Problem Detail",
        "Solution View",
        "Revision Queue",
        "Ask CodeMemory 🤖",
        "My Patterns",
        "Knowledge Graph",
        "Deep Analytics",
        "Data Import",
        "Knowledge Export",
        "Global Search",
        "Settings",
    ]

    # Initialize active tab in session state if not set
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "Dashboard"

    # Find index of current active tab
    active_index = tabs.index(st.session_state["active_tab"]) if st.session_state["active_tab"] in tabs else 0

    selected_tab = st.sidebar.radio(
        "Navigation",
        options=tabs,
        index=active_index,
        key="nav_radio",
    )

    st.session_state["active_tab"] = selected_tab

    # Quick seed action in sidebar
    st.sidebar.markdown("---")
    service = get_service()
    overview = service.analytics_service.get_overview()
    st.sidebar.markdown(f"**Tracked Problems**: `{overview.total_problems}`")
    st.sidebar.markdown(f"**Accepted Solutions**: `{overview.accepted_problems}`")

    if overview.total_problems == 0:
        if st.sidebar.button("🌱 Seed Sample Data"):
            from scripts.seed_data import seed_sample_data
            seed_sample_data(service)
            st.rerun()

    # LeetCode Account Sidebar Indicator — read from the service status surface
    # so it always agrees with Settings and the dashboard.
    st.sidebar.markdown("---")
    try:
        _lc_status = service.leetcode.status()
        if _lc_status.connected:
            st.sidebar.markdown(f"🟢 **LC**: `@{_lc_status.username}`")
        else:
            st.sidebar.markdown("🔗 *LC: Not connected*")
    except Exception:
        pass

    # Route to selected page view
    if selected_tab == "Dashboard":
        render_dashboard_page()
    elif selected_tab == "Problems Directory":
        render_problems_page()
    elif selected_tab == "Problem Detail":
        render_problem_detail_page()
    elif selected_tab == "Solution View":
        render_solution_page()
    elif selected_tab == "Revision Queue":
        render_revision_page()
    elif selected_tab == "Ask CodeMemory 🤖":
        render_ask_codememory_page()
    elif selected_tab == "My Patterns":
        render_patterns_page()
    elif selected_tab == "Knowledge Graph":
        render_graph_page()
    elif selected_tab == "Deep Analytics":
        render_analytics_page()
    elif selected_tab == "Data Import":
        render_import_page()
    elif selected_tab == "Knowledge Export":
        render_export_page()
    elif selected_tab == "Global Search":
        render_search_page()
    elif selected_tab == "Settings":
        render_settings_page()


if __name__ == "__main__":
    main()
