"""LeetCode importer orchestrating parsing, mapping, validation, and ingestion into CodeMemory Core."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.mapper import LeetCodeMapper
from codememory.connectors.leetcode.parser import LeetCodeParser
from codememory.domain.import_schema import NormalizedSubmissionRecord
from codememory.ingestion.importer import ImportService, ImportSummary
from codememory.storage.composite_repository import CompositeStorage


class LeetCodeImporter:
    """Importer specifically designed for LeetCode JSON and CSV datasets."""

    def __init__(
        self,
        storage: CompositeStorage,
        account_service: Optional[AccountService] = None,
    ):
        self.storage = storage
        self.account_service = account_service
        self.import_service = ImportService(storage=storage)

    def _connected_account(self) -> str | None:
        """Resolve the currently connected LeetCode account username, if any."""
        if not self.account_service:
            return None
        conn = self.account_service.get_connection("LeetCode")
        return conn.username if conn else None

    def parse_and_normalize(self, file_path: Union[str, Path]) -> Tuple[List[NormalizedSubmissionRecord], List[str]]:
        """Parse raw file and map records into CodeMemory normalized submission schema."""
        raw_submissions, parse_errors = LeetCodeParser.parse_file(file_path)
        normalized_records: List[NormalizedSubmissionRecord] = []
        errors = list(parse_errors)
        account = self._connected_account()

        for idx, raw in enumerate(raw_submissions, 1):
            try:
                norm_rec = LeetCodeMapper.to_normalized_record(raw, source_account=account)
                normalized_records.append(norm_rec)
            except Exception as e:
                errors.append(f"Record #{idx} ({raw.title}): Mapping failed: {e}")

        return normalized_records, errors

    def validate(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate LeetCode file format and report valid/invalid record counts."""
        norm_records, errors = self.parse_and_normalize(file_path)
        return {
            "file": str(file_path),
            "total_records": len(norm_records) + len(errors),
            "valid_records": len(norm_records),
            "error_count": len(errors),
            "errors": errors,
        }

    def preview_import(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Preview LeetCode import showing problems, submissions, duplicates, and errors."""
        norm_records, errors = self.parse_and_normalize(file_path)

        duplicate_count = 0
        problem_slugs: set[str] = set()

        for rec in norm_records:
            if rec.submission_hash and self.storage.get_by_hash(rec.submission_hash):
                duplicate_count += 1
            if rec.title:
                problem_slugs.add(rec.title.strip().lower().replace(" ", "-"))

        return {
            "file": str(file_path),
            "total_read": len(norm_records) + len(errors),
            "valid_count": len(norm_records),
            "problems_discovered": len(problem_slugs),
            "duplicate_count": duplicate_count,
            "error_count": len(errors),
            "errors": errors,
            "preview_samples": [r.model_dump(mode="json") for r in norm_records[:3]],
        }

    def import_file(self, file_path: Union[str, Path]) -> ImportSummary:
        """Import LeetCode dataset idempotently into storage."""
        norm_records, errors = self.parse_and_normalize(file_path)
        raw_dicts = [r.model_dump(mode="json") for r in norm_records]
        
        summary = self.import_service._process_records(raw_dicts)
        summary.errors.extend(errors)
        summary.error_count = len(summary.errors)
        return summary
