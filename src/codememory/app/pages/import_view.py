"""Data Ingestion & Import View for CodeMemory supporting standard formats and LeetCode datasets."""

from pathlib import Path
import tempfile
import streamlit as st

from codememory.app.components import get_service
from codememory.connectors.leetcode.importer import LeetCodeImporter


def render_import_page() -> None:
    """Render file upload, format tabs, validation preview, and import confirmation UI."""
    st.header("📥 Data Ingestion & Import")
    st.caption("Import coding problems and submissions from standard JSON/CSV files or LeetCode exported datasets.")

    service = get_service()

    source_type = st.radio(
        "Select Import Source / Dataset Type",
        options=["Standard CodeMemory JSON / CSV / JSONL", "LeetCode Export Dataset (JSON / CSV)"],
        horizontal=True,
    )

    if "LeetCode" in source_type:
        _render_leetcode_import(service)
    else:
        _render_standard_import(service)


def _render_standard_import(service) -> None:
    """Render standard CodeMemory format importer."""
    uploaded_file = st.file_uploader("Upload Submissions File", type=["json", "csv", "jsonl", "ndjson"], key="std_upload")

    if not uploaded_file:
        st.info("Upload a file above to preview records and validate idempotency before importing.")
        with st.expander("ℹ️ Supported File Formats & Example JSON"):
            st.markdown(
                """
                **JSON Format Example:**
                ```json
                [
                  {
                    "title": "Two Sum",
                    "difficulty": "Easy",
                    "topics": ["Array", "Hash Table"],
                    "language": "python",
                    "code": "def twoSum(nums, target): pass",
                    "timestamp": "2026-09-06T10:00:00Z",
                    "status": "Accepted",
                    "runtime": "45 ms",
                    "memory": "16.4 MB"
                  }
                ]
                ```
                """
            )
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        preview = service.import_service.preview_import(tmp_path)

        st.subheader("🔍 Import Validation Preview")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Records Read", preview["total_read"])
        col2.metric("Valid Records", preview["valid_count"])
        col3.metric("Duplicates (Skipped)", preview["duplicate_count"])
        col4.metric("Errors Found", preview["error_count"])

        if preview["errors"]:
            st.error("Validation Errors Found:")
            for err in preview["errors"][:5]:
                st.markdown(f"- `{err}`")

        if preview["preview_samples"]:
            st.subheader("Preview Sample Records")
            st.json(preview["preview_samples"])

        if st.button("🚀 Confirm & Import Standard Data", type="primary", key="btn_std_import"):
            summary = service.import_service.import_file(tmp_path)
            st.success(f"🎉 Successfully imported {summary.imported_count} new submissions! (Skipped {summary.duplicate_count} duplicates)")
            if summary.imported_problems:
                st.markdown(f"**Affected Problems:** {', '.join(f'`{p}`' for p in summary.imported_problems)}")
            if summary.imported_count > 0:
                st.session_state["is_demo_data"] = False
            st.rerun()

    except Exception as e:
        st.error(f"Failed to parse file: {e}")


def _render_leetcode_import(service) -> None:
    """Render LeetCode dataset importer."""
    st.subheader("🧩 LeetCode Dataset Import")
    uploaded_file = st.file_uploader("Upload LeetCode JSON or CSV Export", type=["json", "csv"], key="lc_upload")

    if not uploaded_file:
        st.info("Upload a LeetCode export file (.json or .csv) to validate normalization and idempotency.")
        with st.expander("ℹ️ Supported LeetCode Formats & Sample"):
            st.markdown(
                """
                **LeetCode Export JSON Example:**
                ```json
                [
                  {
                    "submission_id": "1003",
                    "title": "Two Sum",
                    "title_slug": "two-sum",
                    "difficulty": "Easy",
                    "topics": ["Array", "Hash Table"],
                    "language": "python3",
                    "status": "Accepted",
                    "runtime": "45 ms",
                    "memory": "17.2 MB",
                    "timestamp": 1700007200,
                    "code": "class Solution:\\n    def twoSum(self, nums: list[int], target: int) -> list[int]: pass"
                  }
                ]
                ```
                """
            )
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        lc_importer = LeetCodeImporter(storage=service.storage)
        preview = lc_importer.preview_import(tmp_path)

        st.subheader("🔍 LeetCode Normalization & Validation Preview")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Records", preview["total_read"])
        col2.metric("Valid Records", preview["valid_count"])
        col3.metric("Problems Discovered", preview["problems_discovered"])
        col4.metric("Duplicates (Skipped)", preview["duplicate_count"])
        col5.metric("Validation Errors", preview["error_count"])

        if preview["errors"]:
            st.warning("Validation Warnings / Errors:")
            for err in preview["errors"][:5]:
                st.markdown(f"- `{err}`")

        if preview["preview_samples"]:
            st.subheader("Normalized Sample Records")
            st.json(preview["preview_samples"])

        if st.button("🚀 Confirm & Import LeetCode Dataset", type="primary", key="btn_lc_import"):
            summary = lc_importer.import_file(tmp_path)
            st.success(
                f"🎉 LeetCode Import Complete: {summary.imported_count} new submissions imported across {len(summary.imported_problems)} problems! "
                f"({summary.duplicate_count} duplicates skipped)"
            )
            if summary.imported_problems:
                st.markdown(f"**Imported Problems:** {', '.join(f'`{p}`' for p in summary.imported_problems)}")
            if summary.imported_count > 0:
                st.session_state["is_demo_data"] = False
            st.rerun()

    except Exception as e:
        st.error(f"Failed to process LeetCode dataset: {e}")
