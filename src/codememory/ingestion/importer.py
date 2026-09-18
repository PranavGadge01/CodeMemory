"""Data ingestion service supporting JSON, CSV, JSONL with idempotency guarantees."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from pydantic import ValidationError

from codememory.domain.enums import SubmissionStatus
from codememory.domain.exceptions import ImportError
from codememory.domain.import_schema import NormalizedSubmissionRecord
from codememory.domain.models import Attempt, Problem, Submission, generate_slug
from codememory.ingestion.parsers import parse_file
from codememory.storage.composite_repository import CompositeStorage


@dataclass
class ImportSummary:
    """Summary of data ingestion results."""

    total_read: int = 0
    valid_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    imported_problems: list[str] = field(default_factory=list)


class ImportService:
    """Service orchestrating multi-format data ingestion into CodeMemory."""

    def __init__(self, storage: CompositeStorage):
        self.storage = storage

    def validate_import(self, data: Sequence[dict[str, Any]]) -> tuple[list[NormalizedSubmissionRecord], list[str]]:
        """Validate raw dictionary records using NormalizedSubmissionRecord schema."""
        valid_records: list[NormalizedSubmissionRecord] = []
        errors: list[str] = []

        for idx, item in enumerate(data, 1):
            if not isinstance(item, dict):
                errors.append(f"Record #{idx}: Item is not a key-value dictionary.")
                continue
            try:
                rec = NormalizedSubmissionRecord.model_validate(item)
                valid_records.append(rec)
            except ValidationError as ve:
                errors.append(f"Record #{idx} ({item.get('title', 'Unknown')}): Validation failed: {ve}")
            except Exception as e:
                errors.append(f"Record #{idx}: Unexpected error: {e}")

        return valid_records, errors

    def preview_import(self, file_path: str | Path) -> dict[str, Any]:
        """Preview records in file without persisting them."""
        raw_records = parse_file(file_path)
        valid_records, errors = self.validate_import(raw_records)

        # Count duplicates against current storage
        duplicate_count = 0
        for rec in valid_records:
            if self.storage.get_by_hash(rec.submission_hash):
                duplicate_count += 1

        return {
            "file": str(file_path),
            "total_read": len(raw_records),
            "valid_count": len(valid_records),
            "duplicate_count": duplicate_count,
            "error_count": len(errors),
            "errors": errors,
            "preview_samples": [r.model_dump(mode="json") for r in valid_records[:3]],
        }

    def import_file(self, file_path: str | Path) -> ImportSummary:
        """Parse, validate, and idempotently import data from a single file."""
        raw_records = parse_file(file_path)
        return self._process_records(raw_records)

    def import_directory(self, dir_path: str | Path) -> ImportSummary:
        """Recursively import all JSON, CSV, JSONL files in a directory."""
        directory = Path(dir_path)
        if not directory.exists() or not directory.is_dir():
            raise ImportError(f"Directory not found: '{dir_path}'")

        combined_summary = ImportSummary()
        supported_exts = {".json", ".csv", ".jsonl", ".ndjson"}

        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in supported_exts:
                try:
                    summary = self.import_file(path)
                    combined_summary.total_read += summary.total_read
                    combined_summary.valid_count += summary.valid_count
                    combined_summary.imported_count += summary.imported_count
                    combined_summary.duplicate_count += summary.duplicate_count
                    combined_summary.error_count += summary.error_count
                    combined_summary.errors.extend(summary.errors)
                    for p in summary.imported_problems:
                        if p not in combined_summary.imported_problems:
                            combined_summary.imported_problems.append(p)
                except Exception as e:
                    combined_summary.error_count += 1
                    combined_summary.errors.append(f"File '{path.name}': {e}")

        return combined_summary

    def _process_records(self, raw_records: list[dict[str, Any]]) -> ImportSummary:
        """Internal worker converting normalized records into domain entities."""
        summary = ImportSummary(total_read=len(raw_records))
        valid_records, errors = self.validate_import(raw_records)
        summary.valid_count = len(valid_records)
        summary.error_count = len(errors)
        summary.errors = errors

        # Group records by problem
        records_by_problem: dict[str, list[NormalizedSubmissionRecord]] = {}
        for rec in valid_records:
            slug = generate_slug(rec.title)
            records_by_problem.setdefault(slug, []).append(rec)

        for slug, recs in records_by_problem.items():
            # Find existing problem or create new
            prob = self.storage.get_by_slug(slug)
            first_rec = recs[0]

            if not prob:
                prob = Problem(
                    title=first_rec.title,
                    slug=slug,
                    difficulty=first_rec.difficulty,
                    url=first_rec.url,
                    topics=first_rec.topics,
                    statement=first_rec.statement,
                )

            # Sort submissions by timestamp chronologically
            recs_sorted = sorted(recs, key=lambda r: r.timestamp)
            modified_prob = False

            # Existing hashes for idempotency check across entire problem
            existing_hashes: set[str] = set()
            for attempt in prob.attempts:
                for sub in attempt.submissions:
                    if sub.submission_hash:
                        existing_hashes.add(sub.submission_hash)

            for rec in recs_sorted:
                # 1. Idempotency Check
                if rec.submission_hash in existing_hashes or self.storage.get_by_hash(rec.submission_hash):
                    summary.duplicate_count += 1
                    continue

                # Create submission entity
                sub_kwargs = {
                    "problem_id": prob.id,
                    "code": rec.code,
                    "language": rec.language,
                    "status": rec.status,
                    "runtime_ms": rec.runtime_ms,
                    "memory_mb": rec.memory_mb,
                    "submitted_at": rec.timestamp,
                    "submission_hash": rec.submission_hash,
                }
                if rec.submission_id:
                    sub_kwargs["id"] = rec.submission_id
                sub = Submission(**sub_kwargs)

                # Attach to an existing open attempt or create a new attempt block
                target_attempt = None
                if prob.attempts:
                    last_att = prob.attempts[-1]
                    # If last attempt status matches or can receive submission, attach
                    if last_att.status == rec.status or last_att.status == SubmissionStatus.UNKNOWN:
                        target_attempt = last_att
                if not target_attempt:
                    target_attempt = Attempt(
                        problem_id=prob.id,
                        attempt_number=len(prob.attempts) + 1,
                        approach_summary=f"Attempt {len(prob.attempts) + 1}",
                        reasoning=rec.reasoning,
                        status=rec.status,
                        created_at=rec.timestamp,
                        updated_at=rec.timestamp,
                    )
                    prob.attempts.append(target_attempt)

                sub.attempt_id = target_attempt.id
                target_attempt.submissions.append(sub)

                if rec.status == SubmissionStatus.ACCEPTED:
                    target_attempt.status = SubmissionStatus.ACCEPTED

                existing_hashes.add(rec.submission_hash)
                summary.imported_count += 1
                modified_prob = True

            if modified_prob:
                self.storage.save(prob)
                if prob.slug not in summary.imported_problems:
                    summary.imported_problems.append(prob.slug)

        return summary
