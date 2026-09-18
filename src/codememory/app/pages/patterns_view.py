"""Streamlit view for 'My Patterns' personal DSA memory."""

import streamlit as st
import plotly.express as px
from codememory.app.components import get_service, render_page_header


def render_patterns_page() -> None:
    """Render the 'My Patterns' section."""
    render_page_header("My Patterns", "Data-driven memory summary of your problem-solving habits, strengths, and struggle areas.")

    service = get_service()
    all_problems = service.list_problems()
    if not all_problems:
        st.info(
            "🤔 **No patterns to analyze yet.**\n\n"
            "Import your submissions or seed the database to discover your personal DSA patterns."
        )
        return

    patterns = service.get_personal_patterns()

    st.markdown("### 🎯 Core Practice Strengths & Weaknesses")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💪 Topic Strengths")
        for item in patterns.strengths:
            st.success(f"• {item}")

    with col2:
        st.markdown("#### ⚠️ Struggle Areas & Weaknesses")
        for item in patterns.weaknesses:
            st.warning(f"• {item}")

    st.markdown("---")
    st.markdown("### 🛠️ Frequent Techniques & Failure Modes")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### 💡 Frequently Utilized Approaches")
        for item in patterns.frequent_approaches:
            st.info(f"• {item}")

    with col4:
        st.markdown("#### 🐛 Frequently Encountered Mistakes")
        for item in patterns.frequent_mistakes:
            st.error(f"• {item}")

    st.markdown("---")
    st.markdown("### 🕒 Practice Recency & Language Usage")

    col5, col6 = st.columns(2)
    with col5:
        st.markdown("#### 💤 Neglected Topics (>30 Days Inactive)")
        if patterns.neglected_topics:
            for item in patterns.neglected_topics:
                st.markdown(f"- ⏳ **{item}**")
        else:
            st.success("All practiced topics are recently active!")

        st.markdown("#### 🔄 Repeatedly Revisited Problems (3+ Attempts)")
        if patterns.revisited_problems:
            for prob in patterns.revisited_problems:
                st.markdown(f"- 📌 `{prob}`")
        else:
            st.info("No problems revisited 3+ times.")

    with col6:
        st.markdown("#### 💻 Preferred Languages (%)")
        if patterns.preferred_languages:
            fig = px.pie(
                names=list(patterns.preferred_languages.keys()),
                values=list(patterns.preferred_languages.values()),
                title="Language Usage Distribution",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Darkmint,
            )
            st.plotly_chart(fig, width='stretch')

    st.markdown("---")
    st.markdown("### 📈 Practice Evolution Insights")
    for ins in patterns.improvement_insights:
        st.markdown(f"👉 **{ins}**")
