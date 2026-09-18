"""DuckDB storage implementation for relational querying and analytics."""

from pathlib import Path
from typing import Sequence

import duckdb

from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
from codememory.domain.models import Attempt, Problem, ProblemNote, SolutionAnalysis, Submission
from codememory.storage.base import AttemptRepository, ProblemRepository, SubmissionRepository


_shared_duckdb_connections: dict[str, duckdb.DuckDBPyConnection] = {}


class DuckDBStorage(ProblemRepository, SubmissionRepository, AttemptRepository):
    """DuckDB relational storage repository."""

    def __init__(self, db_path: str | Path = "data/codememory.duckdb"):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # 1. Reuse active connection in current process if available
        if self.db_path in _shared_duckdb_connections:
            try:
                _shared_duckdb_connections[self.db_path].execute("SELECT 1")
                self.conn = _shared_duckdb_connections[self.db_path]
                return
            except Exception:
                _shared_duckdb_connections.pop(self.db_path, None)

        # 2. Connect to disk file or fall back gracefully
        try:
            self.conn = duckdb.connect(self.db_path)
            _shared_duckdb_connections[self.db_path] = self.conn
            self._init_tables()
        except duckdb.IOException:
            try:
                self.conn = duckdb.connect(self.db_path, read_only=True)
            except duckdb.IOException:
                self.conn = duckdb.connect(":memory:")
                self._init_tables()

    def close(self) -> None:
        """Close active DuckDB database connection."""
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            finally:
                if hasattr(self, "db_path"):
                    _shared_duckdb_connections.pop(self.db_path, None)

    def __del__(self) -> None:
        self.close()

    def health(self) -> bool:
        """Verify the DuckDB connection can execute a trivial query."""
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
                submission_hash VARCHAR UNIQUE NOT NULL
            );
        """
        )

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

    def close(self) -> None:
        """Close connection gracefully."""
        if self.conn:
            self.conn.close()

    def save(self, problem: Problem) -> Problem:
        """Upsert problem, attempts, submissions, and notes into DuckDB."""
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
                problem.created_at,
                problem.updated_at,
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
                    attempt.created_at,
                    attempt.updated_at,
                ],
            )

            # Upsert submissions
            for sub in attempt.submissions:
                sub_status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
                self.conn.execute(
                    """
                    INSERT INTO submissions (id, problem_id, attempt_id, code, language, status, runtime_ms, memory_mb, submitted_at, error_message, submission_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (submission_hash) DO UPDATE SET
                        status = excluded.status,
                        runtime_ms = excluded.runtime_ms,
                        memory_mb = excluded.memory_mb,
                        error_message = excluded.error_message;
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
                        sub.submitted_at,
                        sub.error_message,
                        sub.submission_hash,
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
                    note.created_at,
                ],
            )

        return problem

    def get_by_id(self, problem_id: str) -> Problem | None:
        res = self.conn.execute("SELECT * FROM problems WHERE id = ?", [problem_id]).fetchone()
        if not res:
            return None
        return self._build_problem_from_row(res)

    def get_by_slug(self, slug: str) -> Problem | None:
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
                sid, _, _, code, lang, s_status, rt, mem, s_time, err, s_hash = s_row
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
        rows = self.conn.execute("SELECT * FROM problems ORDER BY title ASC").fetchall()
        return [self._build_problem_from_row(r) for r in rows]

    def delete(self, problem_id: str) -> bool:
        res = self.conn.execute("DELETE FROM problems WHERE id = ?", [problem_id])
        return res.rowcount > 0

    def save_submission(self, submission: Submission) -> Submission:
        prob = self.get_by_id(submission.problem_id) or self.get_by_slug(submission.problem_id)
        if prob:
            if not prob.attempts:
                prob.attempts.append(Attempt(problem_id=prob.id, attempt_number=1, status=submission.status))
            prob.attempts[-1].submissions.append(submission)
            self.save(prob)
        return submission

    def get_by_hash(self, submission_hash: str) -> Submission | None:
        res = self.conn.execute("SELECT * FROM submissions WHERE submission_hash = ?", [submission_hash]).fetchone()
        if not res:
            return None
        sid, pid, aid, code, lang, status, rt, mem, s_time, err, s_hash = res
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
        )

    def list_by_problem(self, problem_id: str) -> Sequence[Submission]:
        prob = self.get_by_id(problem_id) or self.get_by_slug(problem_id)
        if not prob:
            return []
        subs: list[Submission] = []
        for a in prob.attempts:
            subs.extend(a.submissions)
        return sorted(subs, key=lambda s: s.submitted_at)

    def list_by_attempt(self, attempt_id: str) -> Sequence[Submission]:
        rows = self.conn.execute("SELECT * FROM submissions WHERE attempt_id = ? ORDER BY submitted_at ASC", [attempt_id]).fetchall()
        subs: list[Submission] = []
        for r in rows:
            sid, pid, aid, code, lang, status, rt, mem, s_time, err, s_hash = r
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
                )
            )
        return subs

    def save_attempt(self, attempt: Attempt) -> Attempt:
        prob = self.get_by_id(attempt.problem_id)
        if prob:
            for i, a in enumerate(prob.attempts):
                if a.id == attempt.id:
                    prob.attempts[i] = attempt
                    break
            else:
                prob.attempts.append(attempt)
            self.save(prob)
        return attempt
