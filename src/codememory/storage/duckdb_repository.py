"""DuckDB storage implementation for relational querying and analytics."""

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import duckdb

from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
from codememory.domain.models import Attempt, Problem, ProblemNote, SolutionAnalysis, Submission, compute_submission_hash
from codememory.storage.base import AttemptRepository, ProblemRepository, SubmissionRepository


_shared_duckdb_connections: dict[str, duckdb.DuckDBPyConnection] = {}

# Guards mutation of the connection/lock registries themselves, so two threads
# constructing a DuckDBStorage against the same path at once agree on which
# connection — and therefore which lock — they share.
_shared_duckdb_registry_lock = threading.Lock()

# One re-entrant lock per database path, held by every instance whose connection
# came from the pooled handle for that path. See DuckDBStorage: a single
# DuckDBPyConnection is not safe for concurrent use, so all access to it is
# serialised through this lock. Re-entrance is required because the public
# methods nest (``save`` inside ``save_submission``, ``_build_problem_from_row``
# inside ``get_by_slug``).
_shared_duckdb_locks: dict[str, threading.RLock] = {}


def _lock_for(db_path: str) -> threading.RLock:
    """Return the lock guarding the pooled connection for ``db_path``."""
    with _shared_duckdb_registry_lock:
        lock = _shared_duckdb_locks.get(db_path)
        if lock is None:
            lock = threading.RLock()
            _shared_duckdb_locks[db_path] = lock
        return lock



def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """Bind datetimes as naive UTC.

    DuckDB's TIMESTAMP type is timezone-naive, and its Python binder converts a
    tz-aware datetime by shifting it into the *host's local* timezone before
    dropping the offset. Binding a tz-aware UTC value would therefore silently
    shift every stored timestamp by the local UTC offset (invisible on a UTC CI
    runner, wrong everywhere else). Domain models re-tag naive values as UTC on
    read, so naive-UTC is the correct wire format — the same convention the
    Parquet tier already uses.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None)


class DuckDBStorage(ProblemRepository, SubmissionRepository, AttemptRepository):
    """DuckDB relational storage repository.

    Connections are normally pooled per database path for the process
    (``shared=True``, the default). A background worker must ask for
    ``shared=False`` instead: a single DuckDB connection is not safe for
    concurrent use from two threads — interleaved statements corrupt each
    other's result sets — while two separate connections to the same file are
    serialised by DuckDB itself and are safe.

    The pooled connection is shared by every instance in the process built
    against the same path, including all of a threaded server's request
    threads. Because one connection cannot serve two statements at once, every
    access is serialised through a per-path re-entrant lock: a read holds it for
    the whole multi-statement graph build, so a concurrent request can never
    reset another's pending result set. Callers still run concurrently; only
    the connection access is ordered, and each critical section is a few
    indexed lookups.
    """

    def __init__(
        self,
        db_path: str | Path = "data/codememory.duckdb",
        *,
        shared: bool = True,
    ):
        self.db_path = str(db_path)
        self._lock = _lock_for(self.db_path)
        # Track whether this instance owns a private (non-shared) connection.
        # Only private connections should be closed in __del__; shared
        # connections are process-global and belong to the registry, not to any
        # individual instance. Closing a shared connection in __del__ when the
        # instance goes out of scope would kill an active connection that other
        # instances are still using, causing "Connection already closed!" errors.
        self._owns_private_connection: bool = False
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # 1. Reuse active connection in current process if available
        if shared and self.db_path in _shared_duckdb_connections:
            try:
                _shared_duckdb_connections[self.db_path].execute("SELECT 1")
                self.conn = _shared_duckdb_connections[self.db_path]
                # Tables are already initialized on this connection, but an empty
                # submission hash can be written at any point in a process's
                # lifetime, so the repair must run here too.
                self._repair_empty_submission_hashes()
                return
            except Exception:
                _shared_duckdb_connections.pop(self.db_path, None)

        # 2. Connect to the on-disk file.
        #
        # A read-only connection is a legitimate mode for an inspection tool
        # that never writes. Substituting an in-memory database is not: a
        # writable server that silently connected to ":memory:" would serve an
        # empty database forever, still report ``duckdb=ok`` on the health
        # endpoint, and discard every write on shutdown. That is exactly how a
        # second server pointed at an already-locked database ended up showing a
        # permanently zeroed dashboard. The fallback therefore stops at
        # read-only and surfaces the failure instead of hiding it.
        try:
            self.conn = duckdb.connect(self.db_path)
            if shared:
                _shared_duckdb_connections[self.db_path] = self.conn
            else:
                # Private connection: this instance is responsible for closing it.
                self._owns_private_connection = True
            self._init_tables()
            self._repair_empty_submission_hashes()
        except duckdb.IOException:
            try:
                self.conn = duckdb.connect(self.db_path, read_only=True)
                self._owns_private_connection = not shared
            except duckdb.IOException:
                raise

    def _repair_empty_submission_hashes(self) -> None:
        """Backfill canonical hashes for legacy rows persisted with an empty hash.

        Older code paths only hashed a submission when source code was present,
        which left code-less records with an empty ``submission_hash``. Because
        that column is UNIQUE, at most one such row could survive per database —
        a silent data-loss path.

        The repair is non-destructive: rows with an empty hash are given the
        canonical hash derived from their stored fields. If that hash is already
        claimed, the legacy row keeps a unique ``legacy_<id>`` placeholder so no
        record is ever deleted or merged. Runs on both fresh and reused
        connections because an empty hash can be written at any point in a
        process's lifetime; the no-op cost is a single indexed scan.
        """
        with self._lock:
            try:
                rows = self.conn.execute(
                    """
                    SELECT id, problem_id, code, language, status, submitted_at
                    FROM submissions
                    WHERE submission_hash IS NULL OR submission_hash = ''
                    """
                ).fetchall()
            except Exception:
                return

            if not rows:
                return

            taken = {
                row[0]
                for row in self.conn.execute(
                    "SELECT submission_hash FROM submissions WHERE submission_hash <> ''"
                ).fetchall()
            }

            for sid, pid, code, lang, status, submitted_at in rows:
                slug_row = self.conn.execute("SELECT slug FROM problems WHERE id = ?", [pid]).fetchone()
                slug = slug_row[0] if slug_row else pid
                new_hash = compute_submission_hash(
                    problem_title=slug,
                    language=lang or "",
                    code=code or "",
                    submitted_at=submitted_at,
                    status=status or "",
                )
                if not new_hash or new_hash in taken:
                    new_hash = f"legacy_{sid}"
                try:
                    self.conn.execute(
                        "UPDATE submissions SET submission_hash = ? WHERE id = ?", [new_hash, sid]
                    )
                except Exception:
                    # A read-only or otherwise constrained connection cannot repair;
                    # leave the row untouched rather than failing construction.
                    continue
                taken.add(new_hash)

    def close(self) -> None:
        """Close this instance's connection and drop it from the shared registry.

        The registry is keyed by path and lives for the whole process, so a
        handle left registered there is handed to a later ``DuckDBStorage``
        instance — even after the database file has been deleted from disk,
        which is exactly what "Clear All Data" does. A closing instance must
        unregister its own handle, otherwise the next instance built against the
        same path reads and writes through a connection to a file that no longer
        exists.
        """
        if not (hasattr(self, "conn") and self.conn):
            return
        # No lock here: a caller closing a connection must not block behind a
        # thread that holds the lock through a query on that same connection,
        # and teardown is already idempotent and exception-safe.
        registered = _shared_duckdb_connections.get(self.db_path)
        # Only unregister a handle this instance actually owns; a different
        # instance may already have reopened the path underneath this one.
        if registered is self.conn:
            _shared_duckdb_connections.pop(self.db_path, None)
            try:
                self.conn.close()
            except Exception:
                pass

    def __del__(self) -> None:
        if getattr(self, "_owns_private_connection", False):
            self.close()


    def health(self) -> bool:
        """Verify the DuckDB connection can execute a trivial query."""
        with self._lock:
            try:
                row = self.conn.execute("SELECT 1").fetchone()
            except Exception:
                return False
            return bool(row) and row[0] == 1

    def _init_tables(self) -> None:
        """Create tables if they do not exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS problems (
                id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                slug VARCHAR UNIQUE NOT NULL,
                difficulty VARCHAR NOT NULL,
                platform VARCHAR NOT NULL,
                url VARCHAR,
                topics VARCHAR,
                statement TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id VARCHAR PRIMARY KEY,
                problem_id VARCHAR NOT NULL,
                attempt_number INTEGER NOT NULL,
                approach_summary TEXT,
                reasoning TEXT,
                status VARCHAR NOT NULL,
                time_complexity VARCHAR,
                space_complexity VARCHAR,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id VARCHAR PRIMARY KEY,
                problem_id VARCHAR NOT NULL,
                attempt_id VARCHAR NOT NULL,
                code TEXT NOT NULL,
                language VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                runtime_ms DOUBLE,
                memory_mb DOUBLE,
                submitted_at TIMESTAMP NOT NULL,
                error_message TEXT,
                submission_hash VARCHAR NOT NULL,
                source_provider VARCHAR,
                source_account VARCHAR
            );
        """
        )

        # Migration: add provenance columns to pre-existing databases.
        # ALTER TABLE ... ADD COLUMN IF NOT EXISTS is a DuckDB no-op when the
        # column already exists, so this is safe to run on every connection.
        self.conn.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS source_provider VARCHAR;")
        self.conn.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS source_account VARCHAR;")

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id VARCHAR PRIMARY KEY,
                problem_id VARCHAR NOT NULL,
                attempt_id VARCHAR,
                content TEXT NOT NULL,
                note_type VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """
        )

    def save(self, problem: Problem) -> Problem:
        """Upsert problem, attempts, submissions, and notes into DuckDB."""
        with self._lock:
            return self._save_locked(problem)

    def _save_locked(self, problem: Problem) -> Problem:
        topics_str = ", ".join(problem.topics) if problem.topics else ""
        platform_str = problem.platform.value if hasattr(problem.platform, "value") else str(problem.platform)
        diff_str = problem.difficulty.value if hasattr(problem.difficulty, "value") else str(problem.difficulty)

        # Upsert problem
        self.conn.execute(
            """
            INSERT INTO problems (id, title, slug, difficulty, platform, url, topics, statement, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                title = excluded.title,
                slug = excluded.slug,
                difficulty = excluded.difficulty,
                platform = excluded.platform,
                url = excluded.url,
                topics = excluded.topics,
                statement = excluded.statement,
                updated_at = excluded.updated_at;
        """,
            [
                str(problem.id),
                str(problem.title),
                str(problem.slug),
                diff_str,
                platform_str,
                problem.url,
                topics_str,
                problem.statement,
                _to_naive_utc(problem.created_at),
                _to_naive_utc(problem.updated_at),
            ],
        )

        # Upsert attempts
        for attempt in problem.attempts:
            tc = attempt.analysis.time_complexity if attempt.analysis else None
            sc = attempt.analysis.space_complexity if attempt.analysis else None
            att_status = attempt.status.value if hasattr(attempt.status, "value") else str(attempt.status)

            self.conn.execute(
                """
                INSERT INTO attempts (id, problem_id, attempt_number, approach_summary, reasoning, status, time_complexity, space_complexity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    attempt_number = excluded.attempt_number,
                    approach_summary = excluded.approach_summary,
                    reasoning = excluded.reasoning,
                    status = excluded.status,
                    time_complexity = excluded.time_complexity,
                    space_complexity = excluded.space_complexity,
                    updated_at = excluded.updated_at;
            """,
                [
                    str(attempt.id),
                    str(problem.id),
                    int(attempt.attempt_number),
                    attempt.approach_summary,
                    attempt.reasoning,
                    att_status,
                    tc,
                    sc,
                    _to_naive_utc(attempt.created_at),
                    _to_naive_utc(attempt.updated_at),
                ],
            )

            # Upsert submissions.
            # The conflict target is the record's primary key — the external
            # submission id (e.g. "leetcode_1003") — which is the canonical
            # submission identity. Re-importing the same submission refreshes all
            # of its fields in place, including code and submission_hash, rather
            # than the previous partial update that silently kept stale code.
            for sub in attempt.submissions:
                sub_status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
                self.conn.execute(
                    """
                    INSERT INTO submissions (id, problem_id, attempt_id, code, language, status, runtime_ms, memory_mb, submitted_at, error_message, submission_hash, source_provider, source_account)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        problem_id = excluded.problem_id,
                        attempt_id = excluded.attempt_id,
                        code = excluded.code,
                        language = excluded.language,
                        status = excluded.status,
                        runtime_ms = excluded.runtime_ms,
                        memory_mb = excluded.memory_mb,
                        submitted_at = excluded.submitted_at,
                        error_message = excluded.error_message,
                        submission_hash = excluded.submission_hash,
                        source_provider = excluded.source_provider,
                        source_account = excluded.source_account;
                """,
                    [
                        str(sub.id),
                        str(problem.id),
                        str(attempt.id),
                        sub.code,
                        sub.language,
                        sub_status,
                        sub.runtime_ms,
                        sub.memory_mb,
                        _to_naive_utc(sub.submitted_at),
                        sub.error_message,
                        str(sub.submission_hash),
                        sub.source_provider,
                        sub.source_account,
                    ],
                )

        # Upsert notes
        for note in problem.notes:
            n_type = note.note_type.value if hasattr(note.note_type, "value") else str(note.note_type)
            self.conn.execute(
                """
                INSERT INTO notes (id, problem_id, attempt_id, content, note_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    content = excluded.content,
                    note_type = excluded.note_type;
            """,
                [
                    str(note.id),
                    str(problem.id),
                    note.attempt_id,
                    note.content,
                    n_type,
                    _to_naive_utc(note.created_at),
                ],
            )

        return problem

    def get_by_id(self, problem_id: str) -> Problem | None:
        with self._lock:
            res = self.conn.execute("SELECT * FROM problems WHERE id = ?", [problem_id]).fetchone()
            if not res:
                return None
            return self._build_problem_from_row(res)

    def get_by_slug(self, slug: str) -> Problem | None:
        # The lock spans the problem lookup *and* the child-row builds: a
        # concurrent statement on the same connection would reset this query's
        # pending result and hand one thread the other's rows, which is how a
        # problem row reaches the attempt-row unpack and ``attempt_number``
        # ends up validating a slug string.
        with self._lock:
            res = self.conn.execute("SELECT * FROM problems WHERE slug = ?", [slug]).fetchone()
            if not res:
                return None
            return self._build_problem_from_row(res)

    def _build_problem_from_row(self, row: tuple) -> Problem:
        pid, title, slug, diff, platform, url, topics_str, stmt, created_at, updated_at = row
        topics = [t.strip() for t in topics_str.split(",") if t.strip()] if topics_str else []

        # Load attempts
        att_rows = self.conn.execute("SELECT * FROM attempts WHERE problem_id = ? ORDER BY attempt_number ASC", [pid]).fetchall()
        attempts: list[Attempt] = []

        for a_row in att_rows:
            aid, _, att_num, app_sum, reasoning, att_status, tc, sc, a_created, a_updated = a_row

            # Load submissions for this attempt
            sub_rows = self.conn.execute("SELECT * FROM submissions WHERE attempt_id = ? ORDER BY submitted_at ASC", [aid]).fetchall()
            submissions: list[Submission] = []
            for s_row in sub_rows:
                sid, _, _, code, lang, s_status, rt, mem, s_time, err, s_hash, s_provider, s_account = s_row
                sub = Submission(
                    id=sid,
                    problem_id=pid,
                    attempt_id=aid,
                    code=code,
                    language=lang,
                    status=SubmissionStatus.parse(s_status),
                    runtime_ms=rt,
                    memory_mb=mem,
                    submitted_at=s_time,
                    error_message=err,
                    submission_hash=s_hash,
                    source_provider=s_provider,
                    source_account=s_account,
                )
                submissions.append(sub)

            analysis = SolutionAnalysis(time_complexity=tc or "O(N)", space_complexity=sc or "O(1)") if (tc or sc) else None

            att = Attempt(
                id=aid,
                problem_id=pid,
                attempt_number=att_num,
                approach_summary=app_sum or f"Attempt {att_num}",
                reasoning=reasoning,
                analysis=analysis,
                status=SubmissionStatus.parse(att_status),
                created_at=a_created,
                updated_at=a_updated,
                submissions=submissions,
            )
            attempts.append(att)

        # Load notes
        note_rows = self.conn.execute("SELECT * FROM notes WHERE problem_id = ? ORDER BY created_at ASC", [pid]).fetchall()
        notes: list[ProblemNote] = []
        for n_row in note_rows:
            nid, _, n_aid, content, n_type, n_created = n_row
            note = ProblemNote(
                id=nid,
                problem_id=pid,
                attempt_id=n_aid,
                content=content,
                note_type=NoteType(n_type) if n_type in NoteType.__members__.values() else NoteType.GENERAL,
                created_at=n_created,
            )
            notes.append(note)

        return Problem(
            id=pid,
            title=title,
            slug=slug,
            difficulty=DifficultyLevel.parse(diff),
            platform=Platform(platform) if platform in Platform.__members__.values() else platform,
            url=url,
            topics=topics,
            statement=stmt,
            created_at=created_at,
            updated_at=updated_at,
            attempts=attempts,
            notes=notes,
        )

    def list_all(self) -> Sequence[Problem]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM problems ORDER BY title ASC").fetchall()
            return [self._build_problem_from_row(r) for r in rows]

    def delete(self, problem_id: str) -> bool:
        with self._lock:
            res = self.conn.execute("DELETE FROM problems WHERE id = ?", [problem_id])
            return res.rowcount > 0

    def save_submission(self, submission: Submission) -> Submission:
        with self._lock:
            prob = self.get_by_id(submission.problem_id) or self.get_by_slug(submission.problem_id)
            if prob:
                if not prob.attempts:
                    prob.attempts.append(Attempt(problem_id=prob.id, attempt_number=1, status=submission.status))
                prob.attempts[-1].submissions.append(submission)
                self._save_locked(prob)
            return submission

    def get_by_hash(self, submission_hash: str) -> Submission | None:
        with self._lock:
            res = self.conn.execute("SELECT * FROM submissions WHERE submission_hash = ?", [submission_hash]).fetchone()
            if not res:
                return None
            sid, pid, aid, code, lang, status, rt, mem, s_time, err, s_hash, s_provider, s_account = res
            return Submission(
                id=sid,
                problem_id=pid,
                attempt_id=aid,
                code=code,
                language=lang,
                status=SubmissionStatus.parse(status),
                runtime_ms=rt,
                memory_mb=mem,
                submitted_at=s_time,
                error_message=err,
                submission_hash=s_hash,
                source_provider=s_provider,
                source_account=s_account,
            )

    def list_by_problem(self, problem_id: str) -> Sequence[Submission]:
        with self._lock:
            prob = self.get_by_id(problem_id) or self.get_by_slug(problem_id)
            if not prob:
                return []
            subs: list[Submission] = []
            for a in prob.attempts:
                subs.extend(a.submissions)
            return sorted(subs, key=lambda s: s.submitted_at)

    def list_by_attempt(self, attempt_id: str) -> Sequence[Submission]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM submissions WHERE attempt_id = ? ORDER BY submitted_at ASC", [attempt_id]
            ).fetchall()
            subs: list[Submission] = []
            for r in rows:
                sid, pid, aid, code, lang, status, rt, mem, s_time, err, s_hash, s_provider, s_account = r
                subs.append(
                    Submission(
                        id=sid,
                        problem_id=pid,
                        attempt_id=aid,
                        code=code,
                        language=lang,
                        status=SubmissionStatus.parse(status),
                        runtime_ms=rt,
                        memory_mb=mem,
                        submitted_at=s_time,
                        error_message=err,
                        submission_hash=s_hash,
                        source_provider=s_provider,
                        source_account=s_account,
                    )
                )
            return subs

    def save_attempt(self, attempt: Attempt) -> Attempt:
        with self._lock:
            prob = self.get_by_id(attempt.problem_id)
            if prob:
                for i, a in enumerate(prob.attempts):
                    if a.id == attempt.id:
                        prob.attempts[i] = attempt
                        break
                else:
                    prob.attempts.append(attempt)
                self._save_locked(prob)
            return attempt
