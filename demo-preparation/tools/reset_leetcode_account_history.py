"""Safely remove one connected LeetCode account's imported local history.

This is an explicit-path, dry-run-by-default maintenance command. It never
opens CredentialVault files. It backs up the database, account metadata,
account-related derived caches, and affected knowledge exports before writing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


EXPORT_NAMES = {"problem.md", "attempts.md", "metadata.json", "notes.md"}


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def account_fingerprint(account: str) -> str:
    return hashlib.sha256(account.encode("utf-8")).hexdigest()[:8]


def read_active_account(data_root: Path) -> tuple[str, Path, dict[str, Any]]:
    metadata_path = data_root / "accounts" / "account_connections.json"
    obj = json.loads(metadata_path.read_text(encoding="utf-8"))
    conn = obj.get("leetcode")
    if not isinstance(conn, dict) or not conn.get("username"):
        raise RuntimeError("No connected LeetCode account metadata exists at the explicit data root.")
    return str(conn["username"]), metadata_path, obj


def connected_account_rows(con: duckdb.DuckDBPyConnection, account: str) -> dict[str, Any]:
    if not con.execute("select count(*) from information_schema.tables where table_name='submissions'").fetchone()[0]:
        raise RuntimeError("The target database has no submissions table.")

    before = {
        "problems": con.execute("select count(*) from problems").fetchone()[0],
        "attempts": con.execute("select count(*) from attempts").fetchone()[0],
        "submissions": con.execute("select count(*) from submissions").fetchone()[0],
        "notes": con.execute("select count(*) from notes").fetchone()[0],
    }
    target_rows = con.execute(
        """select id, problem_id, attempt_id
           from submissions
           where lower(coalesce(source_provider,''))='leetcode' and source_account=?""",
        [account],
    ).fetchall()
    if not target_rows:
        raise RuntimeError("The connected account has no LeetCode submission rows in the explicit database.")

    target_submission_ids = [r[0] for r in target_rows]
    target_attempt_ids = sorted({r[2] for r in target_rows if r[2]})
    target_problem_ids = sorted({r[1] for r in target_rows if r[1]})

    # Attempts have no provider/account columns. Remove only rows whose entire
    # submission set is this account, have no notes, and still contain the
    # default generated placeholder rather than user-authored analysis.
    eligible_attempts = con.execute(
        """select a.id
           from attempts a
           where a.id in (select unnest(?))
             and a.approach_summary = 'Attempt ' || cast(a.attempt_number as varchar)
             and coalesce(a.reasoning,'')=''
             and coalesce(a.time_complexity,'')=''
             and coalesce(a.space_complexity,'')=''
             and not exists (select 1 from notes n where n.attempt_id=a.id)
             and not exists (
                 select 1 from submissions s where s.attempt_id=a.id
                   and not (lower(coalesce(s.source_provider,''))='leetcode' and s.source_account=?)
             )""",
        [target_attempt_ids, account],
    ).fetchall()
    eligible_attempt_ids = sorted(r[0] for r in eligible_attempts)

    # Delete a parent problem only when every linked submission belongs to the
    # target, no notes or retained attempts refer to it, and no human-authored
    # statement/URL/topic data would be discarded. Shared parents are retained.
    eligible_problems = con.execute(
        """select p.id, p.slug
           from problems p
           where p.id in (select unnest(?))
             and coalesce(p.statement,'')=''
             and coalesce(p.url,'')=''
             and coalesce(p.topics,'')=''
             and not exists (select 1 from notes n where n.problem_id=p.id)
             and not exists (
                 select 1 from submissions s where s.problem_id=p.id
                   and not (lower(coalesce(s.source_provider,''))='leetcode' and s.source_account=?)
             )
             and not exists (
                 select 1 from attempts a where a.problem_id=p.id
                   and a.id not in (select unnest(?))
             )""",
        [target_problem_ids, account, eligible_attempt_ids],
    ).fetchall()
    eligible_problem_ids = sorted(r[0] for r in eligible_problems)
    eligible_problem_slugs = sorted(r[1] for r in eligible_problems)

    target_code_hashes: dict[str, set[str]] = {}
    preserved_code_hashes: dict[str, set[str]] = {}
    for problem_id, source_account, code in con.execute(
        """select problem_id, source_account, code from submissions
           where problem_id in (select unnest(?))""",
        [target_problem_ids],
    ).fetchall():
        digest = hashlib.sha256((code or "").encode("utf-8")).hexdigest()
        destination = target_code_hashes if source_account == account else preserved_code_hashes
        destination.setdefault(problem_id, set()).add(digest)

    if len(eligible_attempt_ids) != len(target_attempt_ids):
        raise RuntimeError("At least one target-linked attempt contains mixed or authored data; reset is not safe.")

    return {
        "before": before,
        "submission_ids": target_submission_ids,
        "attempt_ids": eligible_attempt_ids,
        "target_problem_ids": target_problem_ids,
        "problem_ids": eligible_problem_ids,
        "problem_slugs": eligible_problem_slugs,
        "target_code_hashes": target_code_hashes,
        "preserved_code_hashes": preserved_code_hashes,
        "target_attempt_count": len(target_attempt_ids),
        "target_problem_count": len(target_problem_ids),
    }


def parquet_counts(con: duckdb.DuckDBPyConnection, data_root: Path, account: str, info: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    ai_path = data_root / "ai_analyses.parquet"
    if ai_path.exists():
        counts["ai_analyses_total"] = con.execute(
            "select count(*) from read_parquet(?)", [str(ai_path)]
        ).fetchone()[0]
        counts["ai_analyses_target"] = con.execute(
            "select count(*) from read_parquet(?) where submission_id in (select unnest(?))",
            [str(ai_path), info["submission_ids"]],
        ).fetchone()[0]
    else:
        counts["ai_analyses_total"] = counts["ai_analyses_target"] = 0

    memory_path = data_root / "memory_embeddings.parquet"
    if memory_path.exists():
        cols = {r[0] for r in con.execute("describe select * from read_parquet(?)", [str(memory_path)]).fetchall()}
        counts["memory_vectors_total"] = con.execute(
            "select count(*) from read_parquet(?)", [str(memory_path)]
        ).fetchone()[0]
        if "problem_id" not in cols:
            raise RuntimeError("Memory index has no problem_id provenance; cannot invalidate it narrowly.")
        counts["memory_vectors_target_problems"] = con.execute(
            "select count(*) from read_parquet(?) where problem_id in (select unnest(?))",
            [str(memory_path), info["target_problem_ids"]],
        ).fetchone()[0]
    else:
        counts["memory_vectors_total"] = counts["memory_vectors_target_problems"] = 0
    return counts


def copy_backup_file(source: Path, backup_root: Path, source_root: Path) -> None:
    relative = source.relative_to(source_root)
    target = backup_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def create_backup(
    backup_root: Path,
    db_path: Path,
    data_root: Path,
    knowledge_root: Path,
    info: dict[str, Any],
) -> dict[str, str]:
    if backup_root.exists():
        raise RuntimeError("Backup destination already exists; choose a new empty path.")
    backup_root.mkdir(parents=True)
    sources = [db_path, data_root / "accounts" / "account_connections.json"]
    for name in ("ai_analyses.parquet", "memory_embeddings.parquet"):
        path = data_root / name
        if path.exists():
            sources.append(path)
    for slug in info["problem_slugs"]:
        path = knowledge_root / slug
        if path.exists() and path.is_dir():
            sources.extend(p for p in path.rglob("*") if p.is_file())

    unique_sources = sorted(set(sources), key=lambda p: str(p))
    hashes: dict[str, str] = {}
    for source in unique_sources:
        if not source.is_file():
            raise RuntimeError(f"Expected backup source file is absent: {source}")
        if source == db_path or data_root in source.parents:
            relative_root = db_path.parent.parent if source == db_path else data_root.parent
        else:
            relative_root = knowledge_root.parent
        copy_backup_file(source, backup_root, relative_root)
        dest = backup_root / source.relative_to(relative_root)
        src_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        dst_hash = hashlib.sha256(dest.read_bytes()).hexdigest()
        if src_hash != dst_hash:
            raise RuntimeError("Backup hash verification failed.")
        hashes[str(source)] = src_hash

    backup_db = backup_root / db_path.relative_to(db_path.parent.parent)
    verify = duckdb.connect(str(backup_db), read_only=True)
    backup_counts = {
        name: verify.execute(f"select count(*) from {name}").fetchone()[0]
        for name in ("problems", "attempts", "submissions", "notes")
    }
    verify.close()
    if backup_counts != info["before"]:
        raise RuntimeError("Backup database row counts do not match the source database.")
    cache_verification = {}
    cache_reader = duckdb.connect(":memory:")
    for name in ("ai_analyses.parquet", "memory_embeddings.parquet"):
        cached_copy = backup_root / "data" / name
        if cached_copy.exists():
            cache_verification[name] = cache_reader.execute(
                "select count(*) from read_parquet(?)", [str(cached_copy)]
            ).fetchone()[0]
    cache_reader.close()
    account_copy = backup_root / "data" / "accounts" / "account_connections.json"
    json.loads(account_copy.read_text(encoding="utf-8"))

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(data_root),
        "database": str(db_path),
        "knowledge_root": str(knowledge_root),
        "account_fingerprint": info["account_fingerprint"],
        "database_counts": backup_counts,
        "derived_cache_counts": cache_verification,
        "files": hashes,
        "credential_vault_files_included": False,
    }
    (backup_root / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return hashes


def write_filtered_parquet(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    where_sql: str,
    id_values: list[str],
) -> int:
    if not path.exists():
        return 0
    before = con.execute("select count(*) from read_parquet(?)", [str(path)]).fetchone()[0]
    tmp = path.with_name(path.name + ".reset-tmp")
    if tmp.exists():
        raise RuntimeError(f"Refusing to overwrite existing temporary file: {tmp}")
    con.execute("create or replace temp table _reset_keys(value varchar)")
    if id_values:
        con.executemany("insert into _reset_keys values (?)", [(v,) for v in id_values])
    src = sql_literal(path)
    dst = sql_literal(tmp)
    con.execute(f"copy (select * from read_parquet({src}) where {where_sql}) to {dst} (format parquet)")
    after = con.execute("select count(*) from read_parquet(?)", [str(tmp)]).fetchone()[0]
    if after > before:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Filtered cache unexpectedly grew: {path}")
    os.replace(tmp, path)
    return before - after


def _code_digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _write_problem_export(problem: Any, folder: Path) -> None:
    """Refresh the same generated files as FilesystemStorage without importing Polars."""
    extensions = {
        "python": ".py", "py": ".py", "python3": ".py", "cpp": ".cpp", "c++": ".cpp",
        "c": ".c", "java": ".java", "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts", "rust": ".rs", "rs": ".rs", "go": ".go",
        "golang": ".go", "kotlin": ".kt", "swift": ".swift", "sql": ".sql",
    }

    def extension(language: str) -> str:
        return extensions.get(str(language or "").strip().lower(), ".txt")

    folder.mkdir(parents=True, exist_ok=True)
    topics = ", ".join(f"`{topic}`" for topic in problem.topics) if problem.topics else "None"
    url = f"[{problem.url}]({problem.url})" if problem.url else "N/A"
    statement = problem.statement or "No problem description provided."
    (folder / "problem.md").write_text(
        f"""# {problem.title}

- **Difficulty**: `{problem.difficulty.value}`
- **Platform**: `{problem.platform.value if hasattr(problem.platform, 'value') else problem.platform}`
- **Topics**: {topics}
- **URL**: {url}
- **Created**: `{problem.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`

---

## Problem Statement

{statement}
""",
        encoding="utf-8",
    )

    attempts = [f"# Attempts History: {problem.title}\n"]
    if not problem.attempts:
        attempts.append("*No attempts recorded yet.*\n")
    else:
        for attempt in sorted(problem.attempts, key=lambda item: item.attempt_number):
            attempts.append(f"## Attempt {attempt.attempt_number}: {attempt.approach_summary}")
            attempts.append(f"- **Status**: `{attempt.status.value}`")
            attempts.append(f"- **Date**: `{attempt.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
            if attempt.reasoning:
                attempts.append(f"- **Reasoning**: {attempt.reasoning}")
            if attempt.analysis:
                analysis = attempt.analysis
                attempts.append(f"- **Time Complexity**: `{analysis.time_complexity}`")
                attempts.append(f"- **Space Complexity**: `{analysis.space_complexity}`")
                if analysis.key_insights:
                    attempts.append(f"- **Key Insights**: {', '.join(analysis.key_insights)}")
            if attempt.mistakes:
                attempts.append(f"- **Mistakes / Lessons**: {'; '.join(attempt.mistakes)}")
            attempts.append("\n### Submissions")
            if not attempt.submissions:
                attempts.append("*No code submission recorded for this attempt.*\n")
            else:
                for index, submission in enumerate(sorted(attempt.submissions, key=lambda item: item.submitted_at), 1):
                    runtime = f"{submission.runtime_ms:.1f} ms" if submission.runtime_ms is not None else "N/A"
                    memory = f"{submission.memory_mb:.1f} MB" if submission.memory_mb is not None else "N/A"
                    attempts.append(f"#### Submission {index} ({submission.language})")
                    attempts.append(f"- **Result**: `{submission.status.value}` | **Runtime**: `{runtime}` | **Memory**: `{memory}`")
                    attempts.append(f"- **Timestamp**: `{submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
                    if submission.error_message:
                        attempts.append(f"- **Error Message**: `{submission.error_message}`")
                    ext = extension(submission.language).lstrip(".")
                    attempts.append(f"\n```{ext}\n{submission.code}\n```\n")
    (folder / "attempts.md").write_text("\n".join(attempts), encoding="utf-8")

    chosen = problem.latest_accepted_submission or problem.latest_submission
    if chosen:
        ext = extension(chosen.language)
        header = f"# Solution for {problem.title}\n# Status: {chosen.status.value}\n# Language: {chosen.language}\n\n"
        (folder / f"solution{ext}").write_text(header + chosen.code, encoding="utf-8")
    if problem.notes:
        lines = [f"# Notes: {problem.title}\n"]
        for note in sorted(problem.notes, key=lambda item: item.created_at):
            lines.append(f"### [{note.note_type.value}] - `{note.created_at.strftime('%Y-%m-%d %H:%M:%S')}`")
            lines.append(f"{note.content}\n")
        (folder / "notes.md").write_text("\n".join(lines), encoding="utf-8")
    (folder / "metadata.json").write_text(
        json.dumps(problem.model_dump(mode="json"), indent=2), encoding="utf-8"
    )


def rebuild_problem_exports(
    db_path: Path,
    knowledge_root: Path,
    slugs: list[str],
    target_code_hashes: dict[str, set[str]],
    preserved_code_hashes: dict[str, set[str]],
) -> tuple[int, int]:
    if not slugs:
        return 0, 0
    # Reconstruct domain models directly from the canonical rows, then refresh
    # their known generated export files. Avoid importing the storage package:
    # its package initializer imports Polars, whose current CPU-flag error is
    # unrelated to and must not be bypassed for the application/test runtime.
    from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
    from codememory.domain.models import Attempt, Problem, ProblemNote, SolutionAnalysis, Submission

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        problem_rows = con.execute(
            "select id,title,slug,difficulty,platform,url,topics,statement,created_at,updated_at from problems where slug in (select unnest(?))",
            [slugs],
        ).fetchall()
        attempt_rows = con.execute(
            """select id,problem_id,attempt_number,approach_summary,reasoning,status,
                      time_complexity,space_complexity,NULL as mistakes,created_at,updated_at
               from attempts where problem_id in (select id from problems where slug in (select unnest(?)))
               order by problem_id,attempt_number""",
            [slugs],
        ).fetchall()
        submission_rows = con.execute(
            """select id,problem_id,attempt_id,code,language,status,runtime_ms,memory_mb,
                      submitted_at,error_message,submission_hash,source_provider,source_account
               from submissions where problem_id in (select id from problems where slug in (select unnest(?)))
               order by attempt_id,submitted_at""",
            [slugs],
        ).fetchall()
        note_rows = con.execute(
            """select id,problem_id,attempt_id,content,note_type,created_at from notes
               where problem_id in (select id from problems where slug in (select unnest(?)))
               order by problem_id,created_at""",
            [slugs],
        ).fetchall()
        attempts_by_problem: dict[str, list[tuple]] = {}
        for row in attempt_rows:
            attempts_by_problem.setdefault(row[1], []).append(row)
        submissions_by_attempt: dict[str, list[tuple]] = {}
        for row in submission_rows:
            submissions_by_attempt.setdefault(row[2], []).append(row)
        notes_by_problem: dict[str, list[tuple]] = {}
        for row in note_rows:
            notes_by_problem.setdefault(row[1], []).append(row)
        all_problems = {}
        for row in problem_rows:
            pid, title, slug, difficulty, platform, url, topics_text, statement, created_at, updated_at = row
            attempts = []
            for a in attempts_by_problem.get(pid, []):
                aid, _, number, summary, reasoning, status, tc, sc, mistakes_text, a_created, a_updated = a
                submissions = []
                for s in submissions_by_attempt.get(aid, []):
                    sid, s_pid, s_aid, code, language, s_status, runtime, memory, submitted_at, error, s_hash, provider, account = s
                    submissions.append(Submission(
                        id=sid, problem_id=s_pid, attempt_id=s_aid, code=code or "", language=language or "python",
                        status=SubmissionStatus.parse(s_status), runtime_ms=runtime, memory_mb=memory,
                        submitted_at=submitted_at, error_message=error, submission_hash=s_hash or "",
                        source_provider=provider, source_account=account,
                    ))
                analysis = SolutionAnalysis(time_complexity=tc or "O(N)", space_complexity=sc or "O(1)") if (tc or sc) else None
                attempts.append(Attempt(
                    id=aid, problem_id=pid, attempt_number=int(number or 1),
                    approach_summary=summary or f"Attempt {number or 1}", reasoning=reasoning,
                    analysis=analysis, status=SubmissionStatus.parse(status),
                    mistakes=[m.strip() for m in (mistakes_text or "").split(",") if m.strip()],
                    created_at=a_created, updated_at=a_updated, submissions=submissions,
                ))
            notes = []
            for note in notes_by_problem.get(pid, []):
                nid, _, note_attempt, content, note_type, note_created = note
                try:
                    parsed_type = NoteType(note_type)
                except ValueError:
                    parsed_type = NoteType.GENERAL
                notes.append(ProblemNote(
                    id=nid, problem_id=pid, attempt_id=note_attempt, content=content,
                    note_type=parsed_type, created_at=note_created,
                ))
            try:
                parsed_platform = Platform(platform)
            except ValueError:
                parsed_platform = platform
            problem = Problem(
                id=pid, title=title, slug=slug, difficulty=DifficultyLevel.parse(difficulty),
                platform=parsed_platform, url=url,
                topics=[t.strip() for t in (topics_text or "").split(",") if t.strip()],
                statement=statement, created_at=created_at, updated_at=updated_at,
                attempts=attempts, notes=notes,
            )
            all_problems[problem.slug] = problem
        removed_target_solution_files = 0
        unknown_solution_files_preserved = 0
        for slug in slugs:
            problem = all_problems.get(slug)
            if problem is None:
                continue
            folder = (knowledge_root / slug).resolve()
            if knowledge_root.resolve() not in folder.parents:
                raise RuntimeError("Refusing to rewrite an export outside the knowledge root.")
            _write_problem_export(problem, folder)
            target_hashes = target_code_hashes.get(problem.id, set())
            retained_hashes = preserved_code_hashes.get(problem.id, set())
            for path in folder.glob("solution.*"):
                if not path.is_file() or path.is_symlink():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
                    digest = _code_digest(body)
                except (OSError, UnicodeError, IndexError):
                    unknown_solution_files_preserved += 1
                    continue
                if digest in target_hashes and digest not in retained_hashes:
                    path.unlink()
                    removed_target_solution_files += 1
                elif digest not in target_hashes and digest not in retained_hashes:
                    # Preserve any hand-edited or otherwise unrecognized file.
                    unknown_solution_files_preserved += 1
    finally:
        con.close()
    return removed_target_solution_files, unknown_solution_files_preserved


def execute_reset(
    db_path: Path,
    data_root: Path,
    knowledge_root: Path,
    account: str,
    metadata_path: Path,
    account_data: dict[str, Any],
    info: dict[str, Any],
    caches: dict[str, int],
) -> dict[str, Any]:
    con = duckdb.connect(str(db_path))
    try:
        con.execute("begin transaction")
        con.execute(
            "delete from submissions where lower(coalesce(source_provider,''))='leetcode' and source_account=?",
            [account],
        )
        if info["attempt_ids"]:
            con.execute("delete from attempts where id in (select unnest(?))", [info["attempt_ids"]])
        if info["problem_ids"]:
            con.execute("delete from problems where id in (select unnest(?))", [info["problem_ids"]])
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise

    cache_removed = {}
    cache_removed["ai_analyses"] = write_filtered_parquet(
        con,
        data_root / "ai_analyses.parquet",
        "submission_id not in (select value from _reset_keys)",
        info["submission_ids"],
    )
    cache_removed["memory_vectors"] = write_filtered_parquet(
        con,
        data_root / "memory_embeddings.parquet",
        "problem_id not in (select value from _reset_keys)",
        info["target_problem_ids"],
    )
    con.close()

    # Rebuild all touched problem exports from canonical records. Parent
    # problems are retained because their own source is not recorded. The
    # only removed solution files are generated exports whose body hash matches
    # a target submission and no remaining account's canonical submission.
    removed_target_solution_files, unknown_solution_files_preserved = rebuild_problem_exports(
        db_path,
        knowledge_root,
        info["problem_slugs"],
        info["target_code_hashes"],
        info["preserved_code_hashes"],
    )

    # Match the supported AccountService.remove_connection behavior locally:
    # remove only the LeetCode metadata entry. Importing that service traverses
    # connectors/__init__.py and the known Polars error, so do this one atomic
    # JSON update without loading connector code or CredentialVault.
    current_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    disconnected = "leetcode" in current_metadata
    if disconnected:
        current_metadata.pop("leetcode", None)
        tmp_metadata = metadata_path.with_name(metadata_path.name + ".reset-tmp")
        if tmp_metadata.exists():
            raise RuntimeError("Account metadata temporary file already exists; manual recovery required.")
        tmp_metadata.write_text(json.dumps(current_metadata, indent=2, default=str), encoding="utf-8")
        os.replace(tmp_metadata, metadata_path)
    if not disconnected:
        raise RuntimeError("The LeetCode account connection was not removed from its active metadata store.")

    check = duckdb.connect(str(db_path), read_only=True)
    after = {name: check.execute(f"select count(*) from {name}").fetchone()[0]
             for name in ("problems", "attempts", "submissions", "notes")}
    remaining_target = check.execute(
        "select count(*) from submissions where lower(coalesce(source_provider,''))='leetcode' and source_account=?",
        [account],
    ).fetchone()[0]
    remaining_by_provider = check.execute(
        "select lower(coalesce(source_provider,'<null>')),count(*) from submissions group by 1 order by 1"
    ).fetchall()
    check.close()

    meta_after = json.loads(metadata_path.read_text(encoding="utf-8"))
    if "leetcode" in meta_after:
        raise RuntimeError("Connection metadata still contains LeetCode after supported disconnect.")
    if remaining_target:
        raise RuntimeError("Target account submissions remain after reset.")

    return {
        "after": after,
        "remaining_target": remaining_target,
        "remaining_by_provider": remaining_by_provider,
        "cache_removed": cache_removed,
        "removed_target_solution_files": removed_target_solution_files,
        "unknown_solution_files_preserved": unknown_solution_files_preserved,
        "disconnected": disconnected,
        "caches_before": caches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--knowledge-root", required=True, type=Path)
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--execute", action="store_true", help="Perform the reset; without this, only dry-run.")
    parser.add_argument("--confirm-account-fingerprint", help="Required on execution: first 8 hex characters of SHA256(account id).")
    args = parser.parse_args()

    db_path = args.db_path.resolve()
    data_root = args.data_root.resolve()
    knowledge_root = args.knowledge_root.resolve()
    backup_root = args.backup_dir.resolve()
    for p, label in ((db_path, "database"), (data_root, "data root"), (knowledge_root, "knowledge root")):
        if not p.exists():
            raise SystemExit(f"Explicit {label} path does not exist: {p}")
    if db_path.parent != data_root:
        raise SystemExit("Explicit database must be directly inside the explicit data root.")
    if backup_root == data_root or data_root in backup_root.parents or backup_root == knowledge_root or knowledge_root in backup_root.parents:
        raise SystemExit("Backup must be outside the affected data and knowledge roots.")
    for cache_name in ("ai_analyses.parquet", "memory_embeddings.parquet"):
        tmp = data_root / (cache_name + ".reset-tmp")
        if tmp.exists():
            raise SystemExit(f"A reset temporary file already exists; no changes made: {tmp}")
    metadata_tmp = data_root / "accounts" / "account_connections.json.reset-tmp"
    if metadata_tmp.exists():
        raise SystemExit(f"Account metadata temporary file already exists; no changes made: {metadata_tmp}")

    account, metadata_path, account_data = read_active_account(data_root)
    fingerprint = account_fingerprint(account)
    con = duckdb.connect(str(db_path), read_only=True)
    info = connected_account_rows(con, account)
    caches = parquet_counts(con, data_root, account, info)
    target_problem_rows = con.execute(
        "select id,slug from problems where id in (select unnest(?))", [info["target_problem_ids"]]
    ).fetchall()
    con.close()

    all_target_slugs = sorted({r[1] for r in target_problem_rows})
    eligible_problem_ids = set(info["problem_ids"])
    deleted_slugs = sorted(slug for pid, slug in target_problem_rows if pid in eligible_problem_ids)
    # Parent problems not eligible for deletion are shared or have authored data.
    retained_slugs = sorted(set(all_target_slugs) - set(deleted_slugs))
    info.update({
        "account": account,
        "account_fingerprint": fingerprint,
        "problem_slugs": all_target_slugs,
        "deleted_problem_slugs": deleted_slugs,
        "retained_problem_slugs": retained_slugs,
    })

    # Preserve the filesystem-only note and all nonstandard files. The actual
    # data observed for this account has one note on a shared parent and no
    # unknown files; fail closed if that changes before execution.
    for slug in all_target_slugs:
        folder = knowledge_root / slug
        if folder.exists():
            if folder.is_symlink() or not folder.is_dir() or knowledge_root not in folder.resolve().parents:
                raise SystemExit("An affected knowledge path is unsafe; no changes made.")
            if any(p.is_dir() for p in folder.iterdir()):
                raise SystemExit("Unexpected nested knowledge folder; no changes made.")

    print("MODE", "EXECUTE" if args.execute else "DRY_RUN")
    print("DB_PATH", db_path)
    print("DATA_ROOT", data_root)
    print("KNOWLEDGE_ROOT", knowledge_root)
    print("ACCOUNT_FINGERPRINT", fingerprint)
    print("BEFORE_COUNTS", json.dumps(info["before"], sort_keys=True))
    print("TARGET_SUBMISSIONS", len(info["submission_ids"]))
    print("TARGET_ATTEMPTS_ELIGIBLE", len(info["attempt_ids"]))
    print("TARGET_PARENT_PROBLEMS", info["target_problem_count"])
    print("PARENT_PROBLEMS_ELIGIBLE_FOR_REMOVAL", len(info["problem_ids"]))
    print("PARENT_PROBLEMS_RETAINED_AS_SHARED_OR_UNPROVEN", len(retained_slugs))
    print("DERIVED_CACHE_ROWS", json.dumps(caches, sort_keys=True))
    print("TARGET_KNOWLEDGE_DIRS", len(all_target_slugs))
    print("ACCOUNT_METADATA_BACKUP_REQUIRED", metadata_path)
    print("BACKUP_DESTINATION", backup_root)

    if not args.execute:
        print("RESULT Dry-run only; no files or records changed.")
        return 0

    if args.confirm_account_fingerprint != fingerprint:
        raise SystemExit("Confirmation fingerprint mismatch; no changes made.")
    if backup_root.exists():
        raise SystemExit("Backup destination already exists; no changes made.")

    # Back up only affected sources and the account metadata file. Credential
    # vault files are intentionally never opened, copied, or included.
    info["account"] = account
    hashes = create_backup(backup_root, db_path, data_root, knowledge_root, info)
    print("BACKUP_FILE_COUNT", len(hashes))
    print("BACKUP_HASH_VERIFIED", True)
    result = execute_reset(db_path, data_root, knowledge_root, account, metadata_path, account_data, info, caches)
    print("AFTER_COUNTS", json.dumps(result["after"], sort_keys=True))
    print("REMAINING_TARGET_SUBMISSIONS", result["remaining_target"])
    print("REMAINING_SUBMISSIONS_BY_PROVIDER", json.dumps(result["remaining_by_provider"]))
    print("REMOVED_AI_ANALYSIS_ROWS", result["cache_removed"]["ai_analyses"])
    print("INVALIDATED_MEMORY_VECTOR_ROWS", result["cache_removed"]["memory_vectors"])
    print("REMOVED_TARGET_ONLY_SOLUTION_EXPORTS", result["removed_target_solution_files"])
    print("UNRECOGNIZED_SOLUTION_EXPORTS_PRESERVED", result["unknown_solution_files_preserved"])
    print("CONNECTION_METADATA_REMOVED", result["disconnected"])
    print("CREDENTIAL_VAULTS_TOUCHED", False)
    print("BACKUP_PATH", backup_root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESET_ABORTED {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
