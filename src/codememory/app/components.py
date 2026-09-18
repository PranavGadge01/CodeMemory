"""Reusable UI components, custom CSS theme, and service caching for Streamlit."""

import streamlit as st

from codememory.core.service import CodeMemoryService


_global_service_instance: CodeMemoryService | None = None


@st.cache_resource
def _cached_service() -> CodeMemoryService:
    """Module-level Streamlit cached resource singleton."""
    return CodeMemoryService()


def get_service() -> CodeMemoryService:
    """Get cached CodeMemoryService singleton, falling back gracefully outside Streamlit runtime."""
    global _global_service_instance
    if _global_service_instance is not None:
        return _global_service_instance
    try:
        return _cached_service()
    except Exception:
        _global_service_instance = CodeMemoryService()
        return _global_service_instance


def apply_custom_css() -> None:
    """Inject custom CSS for premium developer UI aesthetics."""
    st.markdown(
        """
    <style>
    /* Global Font & Background Styling */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Metric Card Component */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .metric-subtitle {
        font-size: 0.8rem;
        color: #38BDF8;
        margin-top: 4px;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: capitalize;
        margin-right: 6px;
    }
    .badge-accepted { background-color: rgba(34, 197, 94, 0.2); color: #4ADE80; border: 1px solid #22C55E; }
    .badge-wrong { background-color: rgba(239, 68, 68, 0.2); color: #FCA5A5; border: 1px solid #EF4444; }
    .badge-tle { background-color: rgba(245, 158, 11, 0.2); color: #FCD34D; border: 1px solid #F59E0B; }
    .badge-easy { background-color: rgba(34, 197, 94, 0.15); color: #4ADE80; }
    .badge-medium { background-color: rgba(245, 158, 11, 0.15); color: #FCD34D; }
    .badge-hard { background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5; }

    /* Timeline Cards for Attempts */
    .timeline-card {
        border-left: 3px solid #38BDF8;
        background: rgba(15, 23, 42, 0.6);
        padding: 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, subtitle: str = "") -> None:
    """Render a styled metric card."""
    sub_html = f'<div class="metric-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(message: str = "No problems recorded yet.", action_hint: str = "Seed sample data or import submissions to get started.") -> None:
    """Render a friendly empty state component."""
    st.info(f"💡 **{message}**\n\n{action_hint}")


def render_page_header(title: str, subtitle: str = "") -> None:
    """Render a unified page header with title and subtitle."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")
