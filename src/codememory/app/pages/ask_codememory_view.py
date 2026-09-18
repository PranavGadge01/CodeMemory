"""Ask CodeMemory Streamlit view for grounded natural-language querying of DSA history."""

import streamlit as st
from codememory.app.components import get_service


def render_ask_codememory_page() -> None:
    """Render Ask CodeMemory UI with sample questions, grounded answers, and source citations."""
    st.header("🤖 Ask CodeMemory")
    st.caption("Ask natural-language questions about your personal DSA history, submission attempts, and pattern evolution.")

    service = get_service()
    all_problems = service.list_problems()

    if not all_problems:
        st.info(
            "💭 **No history to query yet.**\n\n"
            "CodeMemory answers questions grounded strictly in *your* recorded submissions and attempts. "
            "Import your data or seed the database first, then come back here to ask questions about your DSA journey."
        )
        return

    st.markdown("##### Quick Sample Questions")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)

    sample_query = None
    if q_col1.button("⚠️ What mistakes do I repeat?"):
        sample_query = "What mistakes do I repeat?"
    if q_col2.button("💡 How did I solve Two Sum?"):
        sample_query = "How did I solve Two Sum?"
    if q_col3.button("🧬 Show my evolution in DP"):
        sample_query = "Show my evolution in dynamic programming."
    if q_col4.button("🔁 Which problems to revise?"):
        sample_query = "Which problems should I revise?"

    query_input = st.text_input(
        "Ask about your DSA history...",
        value=sample_query if sample_query else "",
        placeholder="e.g. What approaches do I try first? / Why did I fail binary search problems?",
    )

    if st.button("🔎 Submit Query", type="primary") or sample_query:
        target_q = query_input or sample_query
        if target_q:
            with st.spinner("Retrieving records & synthesizing grounded response..."):
                result = service.ask_codememory(target_q)

            st.markdown("### Answer")
            st.markdown(result["answer"])

            st.markdown("---")
            st.markdown("### 📚 Sources from your CodeMemory")
            sources = result.get("sources", [])
            if not sources:
                st.info("No matching historical records found in your CodeMemory database.")
            else:
                for src in sources:
                    st.markdown(
                        f"- **{src['title']}** (`{src['difficulty']}`) — {src['attempts_count']} attempts recorded. Topics: {', '.join(src['topics']) if src['topics'] else 'None'}"
                    )

            with st.expander("🔍 View Raw Grounding Context Sent to AI", expanded=False):
                st.code(result.get("context_used", ""))
