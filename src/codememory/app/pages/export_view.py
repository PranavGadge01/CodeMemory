"""Knowledge Base & Multi-Format Exporter View for CodeMemory."""

import json
from pathlib import Path
import streamlit as st

from codememory.app.components import get_service, render_empty_state


def render_export_page() -> None:
    """Render export UI for Markdown knowledge base, JSON, CSV, and Parquet."""
    st.header("📤 Knowledge Base & Dataset Exporter")
    st.caption("Export your personal DSA knowledge base into Git-friendly Markdown files or structured JSON/CSV/Parquet datasets.")

    service = get_service()
    all_problems = service.list_problems()

    if not all_problems:
        render_empty_state(message="No problems available to export.")
        return

    st.subheader("1. Export Git-Friendly Markdown Knowledge Base")
    st.markdown(
        "Generates clean human-readable Markdown files (`problem.md`, `attempts.md`, `solution.<ext>`, `metadata.json`) in `knowledge/<problem-slug>/` suitable for committing to GitHub."
    )
    if st.button("📦 Generate Markdown Knowledge Base", type="primary"):
        paths = service.export_knowledge()
        st.success(f"🎉 Generated Markdown knowledge base for {len(paths)} problems in `knowledge/` folder!")

    st.markdown("---")

    st.subheader("2. Export Datasets (JSON / CSV / Parquet)")

    format_choice = st.radio("Select Export Format", options=["JSON Format", "CSV Submissions", "Parquet Columnar Files"])

    if format_choice == "JSON Format":
        data = [p.model_dump(mode="json") for p in all_problems]
        json_str = json.dumps(data, indent=2)
        st.download_button(
            label="💾 Download Complete JSON Library",
            data=json_str,
            file_name="codememory_export.json",
            mime="application/json",
        )

    elif format_choice == "CSV Submissions":
        sub_rows = []
        for p in all_problems:
            for a in p.attempts:
                for s in a.submissions:
                    sub_rows.append(
                        {
                            "title": p.title,
                            "slug": p.slug,
                            "difficulty": p.difficulty.value,
                            "topics": ", ".join(p.topics),
                            "language": s.language,
                            "code": s.code,
                            "status": s.status.value,
                            "runtime_ms": s.runtime_ms,
                            "memory_mb": s.memory_mb,
                            "timestamp": s.submitted_at.isoformat(),
                        }
                    )
        import pandas as pd
        df = pd.DataFrame(sub_rows)
        csv_str = df.to_csv(index=False)
        st.download_button(
            label="💾 Download Submissions CSV",
            data=csv_str,
            file_name="codememory_submissions.csv",
            mime="text/csv",
        )

    elif format_choice == "Parquet Columnar Files":
        st.info("Parquet dataset files are maintained automatically in `data/parquet/` directory.")
