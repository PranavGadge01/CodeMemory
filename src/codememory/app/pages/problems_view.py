"""Problems Search and Directory View for CodeMemory."""

import streamlit as st

from codememory.app.components import get_service, render_empty_state
from codememory.domain.enums import DifficultyLevel


def render_problems_page() -> None:
    """Render searchable problems list with filters and sorting."""
    st.header("📚 Problems Knowledge Base")
    st.caption("Search, filter, and inspect your complete library of algorithmic problems.")

    service = get_service()
    all_problems = service.list_problems()

    if not all_problems:
        render_empty_state(message="No problems found in library.")
        return

    # Filter Bar
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    with f_col1:
        search_query = st.text_input("🔍 Search Keyword", placeholder="Title, slug, or content...")
    with f_col2:
        all_topics = sorted({t for p in all_problems for t in p.topics if t})
        sel_topic = st.selectbox("🏷️ Topic", options=["All Topics"] + all_topics)
    with f_col3:
        sel_diff = st.selectbox("⚡ Difficulty", options=["All Difficulties", "Easy", "Medium", "Hard"])
    with f_col4:
        sel_status = st.selectbox("🎯 Status", options=["All Statuses", "Solved Only", "Unsolved Only"])

    # Sorting bar
    s_col1, s_col2 = st.columns([3, 1])
    with s_col2:
        sort_by = st.selectbox("Sort By", options=["Date Added (Newest)", "Title (A-Z)", "Difficulty", "Attempts Count"])

    # Execute Search Filtering
    topic_filter = None if sel_topic == "All Topics" else sel_topic
    diff_filter = None if sel_diff == "All Difficulties" else sel_diff
    solved_filter = True if sel_status == "Solved Only" else (False if sel_status == "Unsolved Only" else None)

    filtered = service.search(
        query=search_query,
        topics=topic_filter,
        difficulty=diff_filter,
        solved=solved_filter,
    )

    # Sorting
    if sort_by == "Title (A-Z)":
        filtered.sort(key=lambda p: p.title.lower())
    elif sort_by == "Difficulty":
        d_map = {"Easy": 1, "Medium": 2, "Hard": 3, "Unknown": 0}
        filtered.sort(key=lambda p: d_map.get(p.difficulty.value, 0), reverse=True)
    elif sort_by == "Attempts Count":
        filtered.sort(key=lambda p: len(p.attempts), reverse=True)
    else:  # Date Added (Newest)
        filtered.sort(key=lambda p: p.created_at, reverse=True)

    st.markdown(f"Found **{len(filtered)}** matching problems.")

    if not filtered:
        st.warning("No problems match the selected filters.")
        return

    # Pagination
    items_per_page = 10
    total_pages = max((len(filtered) - 1) // items_per_page + 1, 1)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1) if total_pages > 1 else 1

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_problems = filtered[start_idx:end_idx]

    # Render Table / Cards
    for p in page_problems:
        is_solved = p.latest_accepted_submission is not None
        status_badge = "🟢 Solved" if is_solved else "🟡 In Progress"
        topics_str = ", ".join(f"`{t}`" for t in p.topics) if p.topics else "None"

        with st.expander(f"{status_badge} | **{p.title}** (`{p.difficulty.value}`) — {len(p.attempts)} Attempts"):
            st.markdown(f"- **Topics**: {topics_str}")
            st.markdown(f"- **Platform**: `{p.platform.value if hasattr(p.platform, 'value') else p.platform}`")
            if p.url:
                st.markdown(f"- **URL**: [{p.url}]({p.url})")
            if p.statement:
                st.markdown(f"**Statement Preview**: {p.statement[:200]}...")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(f"🔍 Inspect Detail ({p.slug})", key=f"det_{p.id}"):
                    st.session_state["selected_problem_slug"] = p.slug
                    st.session_state["active_tab"] = "Problem Detail"
                    st.rerun()
            with col_btn2:
                if st.button(f"💻 View Solution ({p.slug})", key=f"sol_{p.id}"):
                    st.session_state["selected_problem_slug"] = p.slug
                    st.session_state["active_tab"] = "Solution View"
                    st.rerun()
