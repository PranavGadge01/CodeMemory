"""Core application service API for CodeMemory."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Sequence

from codememory.analytics.analytics_models import AnalyticsOverview
from codememory.analytics.analytics_service import AnalyticsService
from codememory.analytics.insights import InsightsGenerator
from codememory.analytics.pattern_analyzer import PatternAnalysisResult, PatternAnalyzer
from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
from codememory.domain.exceptions import ProblemNotFoundError
from codememory.domain.models import (
    Attempt,
    Problem,
    ProblemNote,
    SolutionAnalysis,
    Submission,
    _ensure_utc as ensure_utc,
    compute_submission_hash,
    generate_slug,
)
from codememory.exporters.knowledge_exporter import KnowledgeExporter
from codememory.ingestion.importer import ImportService, ImportSummary
from codememory.revision.revision_models import RevisionQueueItem, RevisionScoreBreakdown, RevisionWeights
from codememory.revision.revision_service import RevisionService
from codememory.search.search_service import SearchService
from codememory.storage.composite_repository import CompositeStorage
from codememory.core.settings import SettingsStore, UserSettings
from codememory.ai.fallback_provider import HeuristicAIProvider
from codememory.ai.evolution_service import EvolutionService, EvolutionSummary
from codememory.ai.analyzer import AICodeAnalyzer
from codememory.ai.memory_service import MemoryService as AIMemoryService
from codememory.ai.models import SubmissionAnalysis, SolutionEvolution
from codememory.memory.service import MemoryService as MemoryEngineService
from codememory.search.semantic_search import LocalSemanticSearchEngine, SemanticSearchResult
from codememory.patterns.my_patterns_service import MyPatternsService, PersonalPatternSummary
from codememory.graph.knowledge_graph import KnowledgeGraphBuilder, KnowledgeGraph

if TYPE_CHECKING:
    from codememory.connectors.leetcode.service import LeetCodeAccountService

logger = logging.getLogger(__name__)


class CodeMemoryService:
    """Master application service orchestrating storage, ingestion, search, analytics, revision, AI analysis, and knowledge graph."""

    def __init__(
        self,
        base_dir: str | Path = "data",
        knowledge_dir: str | Path = "knowledge",
        db_path: str | Path = "data/codememory.duckdb",
        *,
        shared_duckdb_connection: bool = True,
        account_service: Optional["AccountService"] = None,
    ):
        # Ensure base directories exist before storage layer initializes
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        Path(knowledge_dir).mkdir(parents=True, exist_ok=True)
        self.base_dir = Path(base_dir)
        self.knowledge_dir = Path(knowledge_dir)
        self._db_path = str(db_path)
        # When using an in-memory database, avoid inheriting the real data
        # directory's account connections — tests injecting db_path=":memory:"
        # must not see the dev environment's connected account.
        if db_path == ":memory:":
            import tempfile
            self._tmp_base = tempfile.mkdtemp(prefix="codememory_mem_")
            self._account_data_dir = Path(self._tmp_base) / "accounts"
        else:
            self._account_data_dir = self.base_dir / "accounts"
        # If an explicit account service is provided (e.g. by tests or the
        # LeetCodeAccountService constructor), use it instead of creating one
        # from the default data dir.
        self._explicit_account_service = account_service
        self.storage = CompositeStorage(
            base_dir=base_dir,
            knowledge_dir=knowledge_dir,
            db_path=db_path,
            shared_duckdb_connection=shared_duckdb_connection,
        )
        self.import_service = ImportService(storage=self.storage)
        self.exporter = KnowledgeExporter(output_dir=knowledge_dir)
        self.settings_store = SettingsStore(data_dir=self.base_dir)
        self.analytics_service = AnalyticsService(storage=self.storage)
        self.search_service = SearchService(storage=self.storage)
        self.pattern_analyzer = PatternAnalyzer(analytics_service=self.analytics_service)
        self.revision_service = RevisionService(storage=self.storage, analytics_service=self.analytics_service)
        self.insights_generator = InsightsGenerator(analytics_service=self.analytics_service, pattern_analyzer=self.pattern_analyzer)

        # Phase 5, 6, & 7 services
        self.ai_provider = HeuristicAIProvider()
        self.evolution_service = EvolutionService(ai_provider=self.ai_provider)
        self.ai_analyzer = AICodeAnalyzer(provider=self.ai_provider, cache_dir=base_dir)
        self.memory_service = AIMemoryService(storage=self.storage, search_service=self.search_service, ai_provider=self.ai_provider)
        self.memory_engine = MemoryEngineService(storage=self.storage, base_dir=base_dir, ai_analyzer=self.ai_analyzer)
        self.semantic_search_engine = LocalSemanticSearchEngine()
        self.my_patterns_service = MyPatternsService()
        self.knowledge_graph_builder = KnowledgeGraphBuilder()

        # Phase C account/sync surface. Lazily built: constructing it eagerly
        # would pull the LeetCode transport into every service instantiation,
        # including processes that never touch LeetCode.
        self._leetcode_service: Optional["LeetCodeAccountService"] = None
        # Phase E automatic sync. Also lazy, and deliberately *not* constructed
        # here: a process that never opts in must never spawn a worker thread.
        self._autosync: Optional["LeetCodeSyncScheduler"] = None

    # 1. Problem operations

    @property
    def active_account(self) -> str | None:
        """Resolve the currently connected LeetCode account username.

        Returns the active ``source_account`` used to scope all user-facing
        queries. When no LeetCode account is connected, returns ``None`` and
        user-facing queries exclude LeetCode-sourced submissions to prevent
        cross-account aggregation.
        """
        try:
            conn = self.leetcode._account_service.get_connection("LeetCode")
            if conn and conn.username:
                return conn.username
        except Exception:
            pass
        return None

    def get_settings(self) -> UserSettings:
        """Load persisted user settings (backend is the single source of truth)."""
        return self.settings_store.load()

    def update_setting(self, key: str, value: Any) -> UserSettings:
        """Persist a single setting and return the updated model."""
        return self.settings_store.update(**{key: value})

    def update_settings(self, **fields: Any) -> UserSettings:
        """Persist one or more settings and return the updated model."""
        return self.settings_store.update(**fields)

    def list_problems(self) -> Sequence[Problem]:
        """List stored problems, scoped to the active account.

        When a LeetCode account is connected, only problems with submissions
        belonging to that account are returned, with non-matching submissions
        stripped.

        When no LeetCode account is connected, problems with only LeetCode-sourced
        submissions are excluded — only problems with non-LeetCode or legacy
        (NULL source_provider) submissions are returned, preventing cross-account
        aggregation.
        """
        all_problems = self.storage.list_all()
        active = self.active_account
        if active is not None:
            # Filter to problems that have submissions from the active account,
            # stripping submissions from other accounts or unattributed/legacy records.
            filtered: list[Problem] = []
            for p in all_problems:
                kept_attempts = []
                for a in p.attempts:
                    matching = [s for s in a.submissions if s.source_account == active]
                    if not matching:
                        continue
                    import copy
                    a_copy = copy.copy(a)
                    a_copy.submissions = matching
                    kept_attempts.append(a_copy)
                if not kept_attempts:
                    continue
                import copy
                p_copy = copy.copy(p)
                p_copy.attempts = kept_attempts
                filtered.append(p_copy)
            return filtered
        # No active account: exclude problems that have ONLY LeetCode-sourced
        # submissions (source_provider is not None). Keep problems with no
        # source_provider (manually added) or mixed/no provenance.
        from codememory.domain.enums import Platform
        unscoped: list[Problem] = []
        for p in all_problems:
            is_leetcode_only = False
            for a in p.attempts:
                for s in a.submissions:
                    if s.source_provider is not None:
                        is_leetcode_only = True
                        break
                if is_leetcode_only:
                    break
            if not is_leetcode_only:
                unscoped.append(p)
        return unscoped

    def add_problem(
        self,
        title: str,
        difficulty: str | DifficultyLevel = DifficultyLevel.UNKNOWN,
        topics: list[str] | None = None,
        url: str | None = None,
        platform: str | Platform = Platform.LEETCODE,
        statement: str | None = None,
        slug: str | None = None,
    ) -> Problem:
        """Create and save a new problem."""
        p_slug = slug or generate_slug(title)
        diff = DifficultyLevel.parse(difficulty) if isinstance(difficulty, str) else difficulty

        problem = Problem(
            title=title,
            slug=p_slug,
            difficulty=diff,
            platform=platform,
            url=url,
            topics=topics or [],
            statement=statement,
        )
        return self.storage.save(problem)

    def get_problem(self, identifier: str, account: str | None = None) -> Problem:
        """Retrieve problem by ID or slug.

        When ``account`` is provided, only submissions from that account are
        included in the returned problem. The caller is responsible for passing
        the active account; most service methods default to ``self.active_account``.

        When ``account`` is None (no active LeetCode account), LeetCode-sourced
        submissions are excluded to prevent cross-account aggregation.
        """
        prob = self.storage.get_by_slug(identifier) or self.storage.get_by_id(identifier)
        if not prob:
            raise ProblemNotFoundError(identifier)
        if account is None:
            # No active account: strip LeetCode-sourced submissions to prevent
            # cross-account data exposure. Keep submissions with NULL
            # source_provider (non-LeetCode / legacy).
            import copy
            filtered_attempts = []
            for a in prob.attempts:
                non_leetcode = [s for s in a.submissions if s.source_provider is None]
                if not non_leetcode:
                    continue
                a_copy = copy.copy(a)
                a_copy.submissions = non_leetcode
                filtered_attempts.append(a_copy)
            if not filtered_attempts:
                return copy.copy(prob)
            prob_copy = copy.copy(prob)
            prob_copy.attempts = filtered_attempts
            return prob_copy
        # Filter submissions to only those belonging to the specified account.
        import copy
        filtered_attempts = []
        for a in prob.attempts:
            matching = [s for s in a.submissions if s.source_account == account]
            if not matching:
                continue
            a_copy = copy.copy(a)
            a_copy.submissions = matching
            filtered_attempts.append(a_copy)
        if not filtered_attempts:
            raise ProblemNotFoundError(identifier)
        prob_copy = copy.copy(prob)
        prob_copy.attempts = filtered_attempts
        return prob_copy


    # 2. Submission & Attempt operations
    def add_submission(
        self,
        problem_identifier: str,
        code: str,
        language: str = "python",
        status: str | SubmissionStatus = SubmissionStatus.UNKNOWN,
        runtime_ms: float | None = None,
        memory_mb: float | None = None,
        error_message: str | None = None,
        reasoning: str | None = None,
        submitted_at: datetime | str | None = None,
        submission_id: str | None = None,
        submission_hash: str | None = None,
        source_provider: str | None = None,
        source_account: str | None = None,
    ) -> tuple[Problem, Submission]:
        """Add a submission to a problem, automatically creating attempts.

        Identity-aware and idempotent: callers may supply the external
        ``submission_id`` (used as the stored record's primary key), the original
        ``submitted_at`` timestamp, and/or a precomputed ``submission_hash``.
        A supplied upstream ID is authoritative; hashes are only a fallback
        identity when no external ID is available.
        """
        # Mutations must start from the canonical, unfiltered aggregate. The
        # public get_problem() view is account-scoped and would otherwise
        # replace submissions owned by a different account when saving.
        prob = self.storage.get_by_slug(problem_identifier) or self.storage.get_by_id(problem_identifier)
        if prob is None:
            raise ProblemNotFoundError(problem_identifier)
        sub_status = SubmissionStatus.parse(status) if isinstance(status, str) else status

        submitted_dt = ensure_utc(submitted_at) if submitted_at is not None else datetime.now(timezone.utc)

        # An upstream ID is the strongest identity available. Preserve it for
        # ordinary records, and namespace it only when another account already
        # owns the same global storage key.
        if submission_id:
            submission_id = self.resolve_submission_id(
                submission_id,
                source_provider=source_provider,
                source_account=source_account,
            )
            existing_by_id = self._find_submission_by_id(submission_id)
            if existing_by_id is not None:
                return prob, existing_by_id

        # Canonical hash: prefer the caller's, otherwise derive it from the
        # problem slug so that the sync and import paths agree. When
        # source_account provenance is available it is folded into the hash
        # so equivalent submissions from different accounts are not
        # cross-deduplicated.
        sub_hash = submission_hash or compute_submission_hash(
            problem_title=prob.slug,
            language=language,
            code=code,
            submitted_at=submitted_dt,
            status=sub_status.value,
            source_account=source_account,
        )

        # Without an upstream ID, use the canonical hash as the fallback key.
        if sub_hash and not submission_id:
            existing = self.storage.get_by_hash(sub_hash)
            # Only treat as a duplicate if the existing record belongs to the
            # same account. A hash collision across accounts is not a duplicate.
            if existing is not None and (
                source_account is None
                or source_account == ""
                or existing.source_account == source_account
            ):
                return prob, existing

        sub_kwargs: dict[str, Any] = {
            "problem_id": prob.id,
            "code": code,
            "language": language,
            "status": sub_status,
            "runtime_ms": runtime_ms,
            "memory_mb": memory_mb,
            "submitted_at": submitted_dt,
            "error_message": error_message,
            "submission_hash": sub_hash,
            "source_provider": source_provider,
            "source_account": source_account,
        }
        if submission_id:
            # Preserve the external identity (e.g. "leetcode_1003") as the
            # stored primary key.
            sub_kwargs["id"] = submission_id
        sub = Submission(**sub_kwargs)

        # Attach to latest attempt or create new one
        target_attempt = None
        if prob.attempts:
            last_att = prob.attempts[-1]
            if not last_att.is_accepted and last_att.status == sub_status:
                target_attempt = last_att

        if not target_attempt:
            att_num = len(prob.attempts) + 1
            target_attempt = Attempt(
                problem_id=prob.id,
                attempt_number=att_num,
                approach_summary=f"Attempt {att_num}",
                reasoning=reasoning,
                status=sub_status,
            )
            prob.attempts.append(target_attempt)
        elif reasoning and not target_attempt.reasoning:
            target_attempt.reasoning = reasoning

        sub.attempt_id = target_attempt.id
        target_attempt.submissions.append(sub)

        if sub_status == SubmissionStatus.ACCEPTED:
            target_attempt.status = SubmissionStatus.ACCEPTED

        updated_prob = self.storage.save(prob)
        return updated_prob, sub

    def get_submission(self, submission_id: str, account: str | None = None) -> Submission | None:
        """Find submission by ID, scoped to the given account.

        When ``account`` is provided, only submissions from that account are
        considered. When ``account`` is None (no active LeetCode account),
        LeetCode-sourced submissions are excluded — matching the isolation
        guarantees of ``list_problems`` and ``get_problem``.
        """
        active = account if account is not None else self.active_account
        if active is not None:
            # Account-collision IDs are deterministically namespaced on write.
            # Resolve the same way for re-sync lookups.
            submission_id = self.resolve_submission_id(
                submission_id,
                source_provider="leetcode",
                source_account=active,
            )
        submission = self._find_submission_by_id(submission_id)
        if submission is None:
            return None
        if active is None and submission.source_provider is not None:
            return None
        if active is not None and submission.source_account != active:
            return None
        return submission

    def _find_submission_by_id(self, submission_id: str) -> Submission | None:
        """Find an ID across all accounts without applying the active filter."""
        get_by_external_id = getattr(self.storage, "get_submission_by_external_id", None)
        if get_by_external_id is not None:
            return get_by_external_id(submission_id)
        for problem in self.storage.list_all():
            for attempt in problem.attempts:
                for submission in attempt.submissions:
                    if submission.id == submission_id:
                        return submission
        return None

    def resolve_submission_id(
        self,
        submission_id: str,
        *,
        source_provider: str | None,
        source_account: str | None,
    ) -> str:
        """Return a stable storage key for an external submission identity.

        DuckDB uses a global primary key for submission IDs while upstream IDs
        are only unique within their account. In a collision, retain the
        original ID for its existing owner and assign the other owner a stable
        account-scoped key.
        """
        existing = self._find_submission_by_id(submission_id)
        owner = (existing.source_provider, existing.source_account) if existing else None
        requested_owner = (source_provider, source_account)
        if owner is None or owner == requested_owner:
            return submission_id

        import hashlib

        scope = f"{source_provider or ''}\0{source_account or ''}"
        suffix = hashlib.sha256(scope.encode("utf-8")).hexdigest()[:12]
        candidate = f"{submission_id}__{suffix}"
        collision = self._find_submission_by_id(candidate)
        if collision is None or (
            collision.source_provider,
            collision.source_account,
        ) == requested_owner:
            return candidate
        # Avoid overwriting even in the extraordinarily unlikely event of a
        # truncated digest collision.
        suffix = hashlib.sha256(f"{scope}\0{submission_id}".encode("utf-8")).hexdigest()
        return f"{submission_id}__{suffix}"

    def list_attempts(self, problem_identifier: str) -> Sequence[Attempt]:
        """List all attempts for a problem."""
        prob = self.get_problem(problem_identifier, account=self.active_account)
        return sorted(prob.attempts, key=lambda a: a.attempt_number)

    def add_attempt(
        self,
        problem_identifier: str,
        approach_summary: str,
        reasoning: str | None = None,
        time_complexity: str = "O(N)",
        space_complexity: str = "O(1)",
        mistakes: list[str] | None = None,
    ) -> Attempt:
        """Create a new attempt with detailed solution analysis."""
        prob = self.get_problem(problem_identifier)
        att_num = len(prob.attempts) + 1

        analysis = SolutionAnalysis(
            approach_name=approach_summary,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
        )

        attempt = Attempt(
            problem_id=prob.id,
            attempt_number=att_num,
            approach_summary=approach_summary,
            reasoning=reasoning,
            mistakes=mistakes or [],
            analysis=analysis,
        )

        prob.attempts.append(attempt)
        self.storage.save(prob)
        return attempt

    def add_note(
        self,
        problem_identifier: str,
        content: str,
        note_type: str | NoteType = NoteType.GENERAL,
        attempt_id: str | None = None,
    ) -> ProblemNote:
        """Add learning note or intuition to a problem."""
        prob = self.get_problem(problem_identifier)
        nt = NoteType(note_type) if isinstance(note_type, str) and note_type in NoteType.__members__.values() else NoteType.GENERAL

        note = ProblemNote(
            problem_id=prob.id,
            attempt_id=attempt_id,
            content=content,
            note_type=nt,
        )
        prob.notes.append(note)
        self.storage.save(prob)
        return note

    # 3. History Reconstruction Concept
    def get_problem_history(self, problem_identifier: str) -> dict[str, Any]:
        """Reconstruct chronological evolution history of a problem.

        When a LeetCode account is connected, only that account's submissions
        are included in the history.
        """
        prob = self.get_problem(problem_identifier, account=self.active_account)
        history_events: list[dict[str, Any]] = []

        all_submissions: list[tuple[Attempt, Submission]] = []
        for attempt in prob.attempts:
            for sub in attempt.submissions:
                all_submissions.append((attempt, sub))

        # Sort all submissions chronologically
        all_submissions.sort(key=lambda item: item[1].submitted_at)

        best_runtime: float | None = None
        best_memory: float | None = None
        accepted_count = 0

        for idx, (attempt, sub) in enumerate(all_submissions, 1):
            if sub.status == SubmissionStatus.ACCEPTED:
                accepted_count += 1
                if sub.runtime_ms is not None:
                    best_runtime = sub.runtime_ms if best_runtime is None else min(best_runtime, sub.runtime_ms)
                if sub.memory_mb is not None:
                    best_memory = sub.memory_mb if best_memory is None else min(best_memory, sub.memory_mb)

            history_events.append(
                {
                    "step": idx,
                    "attempt_number": attempt.attempt_number,
                    "attempt_approach": attempt.approach_summary,
                    "submitted_at": sub.submitted_at.isoformat(),
                    "language": sub.language,
                    "status": sub.status.value,
                    "runtime_ms": sub.runtime_ms,
                    "memory_mb": sub.memory_mb,
                    "code_snippet": sub.code[:150] + ("..." if len(sub.code) > 150 else ""),
                    "reasoning": attempt.reasoning,
                }
            )

        return {
            "problem_id": prob.id,
            "title": prob.title,
            "slug": prob.slug,
            "difficulty": prob.difficulty.value,
            "total_attempts": len(prob.attempts),
            "total_submissions": len(all_submissions),
            "accepted_submissions": accepted_count,
            "best_runtime_ms": best_runtime,
            "best_memory_mb": best_memory,
            "latest_accepted_solution": prob.latest_accepted_submission.code if prob.latest_accepted_submission else None,
            "timeline": history_events,
        }

    # 4. Ingestion & Exporter wrappers
    def import_data(self, path: str | Path) -> ImportSummary:
        """Import data from file or directory."""
        p = Path(path)
        if p.is_dir():
            return self.import_service.import_directory(p)
        return self.import_service.import_file(p)

    def export_knowledge(self) -> list[Path]:
        """Export all problems into Git-friendly knowledge markdown directory."""
        problems = list(self.list_problems())
        return self.exporter.export_all(problems)

    # 5. Search, Revision, and Insights API
    def search(
        self,
        query: str | None = None,
        topics: list[str] | str | None = None,
        difficulty: str | DifficultyLevel | None = None,
        language: str | None = None,
        status: str | SubmissionStatus | None = None,
        from_date: Any = None,
        to_date: Any = None,
        min_attempts: int | None = None,
        max_attempts: int | None = None,
        solved: bool | None = None,
    ) -> list[Problem]:
        """Multi-criteria search engine wrapper."""
        return self.search_service.search(
            query=query,
            topics=topics,
            difficulty=difficulty,
            language=language,
            status=status,
            from_date=from_date,
            to_date=to_date,
            min_attempts=min_attempts,
            max_attempts=max_attempts,
            solved=solved,
        )

    def global_search(self, query: str, limit: int = 20) -> list[dict]:
        """Deterministic lexical search across problems and submissions.

        Returns a list of result dicts with a ``_search_rank`` key (lower is
        better) for stable ordering. Each dict is a lightweight projection of
        either a :class:`Problem` or a :class:`Submission`, keyed by the same
        field names the API response schemas use.

        Account scoping follows the same rule as ``list_problems`` and
        ``list_submissions``: LeetCode-sourced records are only returned when
        their ``source_account`` matches ``service.active_account``; when no
        account is connected, LeetCode-sourced submissions are hidden entirely.
        """
        if not query or not query.strip():
            return []

        q_lower = query.strip().lower()
        active = self.active_account
        max_results = max(1, limit)

        results: list[dict] = []

        # --- Problems ---
        # Rank: 0 = exact title match, 1 = title starts with, 2 = title contains,
        # 3 = slug match, 4 = topic match
        for p in self.list_problems():
            title_lower = p.title.lower()
            slug_lower = p.slug.lower()

            if q_lower == title_lower:
                rank = 0
            elif title_lower.startswith(q_lower):
                rank = 1
            elif q_lower in title_lower:
                rank = 2
            elif q_lower in slug_lower:
                rank = 3
            elif any(q_lower in t.lower() for t in p.topics):
                rank = 4
            else:
                continue

            results.append({
                "_type": "problem",
                "_rank": rank,
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty),
                "platform": p.platform,
                "topics": p.topics,
            })

        # --- Submissions ---
        # Submissions are already filtered by the active account inside
        # _get_all_submissions-equivalent logic (list_problems scoping).
        for p in self.list_problems():
            for a in p.attempts:
                for s in a.submissions:
                    title_lower = p.title.lower()
                    slug_lower = p.slug.lower()

                    # Only match if the query hits the problem title/slug or
                    # the submission's language or status.
                    if q_lower in title_lower:
                        rank = 0
                    elif q_lower in slug_lower:
                        rank = 1
                    elif q_lower in s.language.lower():
                        rank = 2
                    elif q_lower in s.status.value.lower():
                        rank = 3
                    else:
                        continue

                    results.append({
                        "_type": "submission",
                        "_rank": rank,
                        "id": s.id,
                        "title": p.title,
                        "slug": p.slug,
                        "language": s.language,
                        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                        "runtime_ms": s.runtime_ms,
                        "memory_mb": s.memory_mb,
                        "source_provider": s.source_provider,
                        "source_account": s.source_account,
                        "submitted_at": s.submitted_at.isoformat() if hasattr(s.submitted_at, "isoformat") else str(s.submitted_at),
                    })

        # Sort by rank (exact first), then by recency for ties, then id for stability
        from datetime import datetime as _dt
        def _sort_key(r: dict):
            rank = r["_rank"]
            submitted_str = r.get("submitted_at")
            if submitted_str:
                try:
                    ts = _dt.fromisoformat(submitted_str.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    ts = _dt.min.replace(tzinfo=timezone.utc)
            else:
                ts = _dt.min.replace(tzinfo=timezone.utc)
            return (rank, -ts.timestamp(), r["id"])

        results.sort(key=_sort_key)

        # --- Knowledge (Memory Engine hybrid search) ---
        # The MemoryEngine provides hybrid vector+keyword search over memory
        # documents (attempts, submissions, mistakes, notes). When an active
        # account is connected, the search is automatically scoped to that
        # account's documents.
        #
        # Knowledge results are only surfaced when the lexical search already
        # found matching problems or submissions, and only when the hybrid
        # score is high enough to indicate a real match. This prevents the
        # Knowledge section from showing noise for queries that have no genuine
        # match — e.g. searching "xyznonexistent" should not return unrelated
        # documents that happen to share a token.
        lexical_result_count = len(results)
        if lexical_result_count > 0:
            try:
                knowledge_results = self.memory_search(query=q_lower, top_k=max_results)
                for kr in knowledge_results:
                    if kr.score < 0.55:
                        continue
                    rank = 5
                    problem_slug = ""
                    try:
                        prob_for_slug = self.storage.get_by_id(kr.problem_id)
                        if prob_for_slug:
                            problem_slug = prob_for_slug.slug
                    except Exception:
                        pass
                    results.append({
                        "_type": "knowledge",
                        "_rank": rank,
                        "id": kr.memory_id,
                        "title": kr.title,
                        "slug": problem_slug,
                        "memoryType": kr.memory_type.value,
                        "problemId": kr.problem_id,
                        "score": kr.score,
                        "snippet": kr.snippet,
                        "source": kr.source,
                        "sourceProvider": kr.source_provider,
                        "sourceAccount": kr.source_account,
                    })
            except Exception:
                pass

        results.sort(key=_sort_key)

        # Convert metadata keys to camelCase so the API response is consistent
        # with the rest of the schema (which uses BaseCamelModel alias_generator).
        camelCase_map = {
            "runtime_ms": "runtimeMs",
            "memory_mb": "memoryMb",
            "source_provider": "sourceProvider",
            "source_account": "sourceAccount",
            "submitted_at": "submittedAt",
        }
        for r in results:
            r["metadata"] = {
                camelCase_map.get(k, k): v for k, v in r.items()
                if k not in ("_type", "_rank", "id", "title", "slug")
            }

        return results[:max_results]

    def get_revision_queue(self, limit: int = 10, topic: str | None = None, weights: RevisionWeights | None = None) -> list[RevisionQueueItem]:
        """Fetch prioritized revision queue."""
        return self.revision_service.get_revision_queue(limit=limit, topic=topic, weights=weights)

    def get_due_problems(self, threshold_days: int = 7, limit: int = 10) -> list[RevisionQueueItem]:
        """Fetch problems due for review."""
        return self.revision_service.get_due_problems(threshold_days=threshold_days, limit=limit)

    def mark_reviewed(self, problem_identifier: str, notes: str | None = None) -> Problem:
        """Mark a problem as reviewed."""
        return self.revision_service.mark_reviewed(problem_identifier=problem_identifier, notes=notes)

    def get_problem_priority(self, problem_identifier: str, weights: RevisionWeights | None = None) -> RevisionScoreBreakdown:
        """Get priority score breakdown for a problem."""
        return self.revision_service.get_problem_priority(problem_identifier=problem_identifier, weights=weights)

    def analyze_patterns(self, unpracticed_days_threshold: int = 14) -> PatternAnalysisResult:
        """Analyze personal problem-solving patterns."""
        return self.pattern_analyzer.analyze(unpracticed_days_threshold=unpracticed_days_threshold)

    def generate_insights(self) -> list[str]:
        """Generate deterministic natural language insights."""
        return self.insights_generator.generate_insights()

    # 6. Analytics summary
    def get_analytics_summary(self) -> dict[str, Any]:
        """Compute system-wide DSA problem solving statistics."""
        overview = self.analytics_service.get_overview(account=self.active_account)
        diff_stats = self.analytics_service.get_difficulty_statistics(account=self.active_account)
        difficulty_counts = {ds.difficulty: ds.total_problems for ds in diff_stats}

        return {
            "total_problems": overview.total_problems,
            "difficulty_breakdown": difficulty_counts,
            "total_attempts": overview.total_attempts,
            "total_submissions": overview.total_submissions,
            "accepted_submissions": overview.accepted_problems,
            "overall_acceptance_rate_pct": overview.overall_acceptance_rate_pct,
            "avg_attempts_per_solved": overview.avg_attempts_per_solved_problem,
            "first_attempt_acceptance_rate_pct": overview.first_attempt_acceptance_rate_pct,
        }

    # 7. Phase 5 Intelligent & Semantic API
    def get_solution_evolution(self, problem_identifier: str) -> EvolutionSummary:
        """Get chronological evolution summary and narrative across attempts for a problem."""
        prob = self.get_problem(problem_identifier, account=self.active_account)
        submissions: list[Submission] = []
        for attempt in prob.attempts:
            submissions.extend(attempt.submissions)
        return self.evolution_service.generate_evolution(prob, submissions)

    def semantic_search(self, query: str, top_k: int = 10) -> list[SemanticSearchResult]:
        """Perform semantic TF-IDF query search matching problem titles, concepts, notes, and mistakes."""
        problems = list(self.list_problems())
        submissions: list[Submission] = []
        for prob in problems:
            for attempt in prob.attempts:
                submissions.extend(attempt.submissions)

        self.semantic_search_engine.index_dataset(problems, submissions)
        return self.semantic_search_engine.search(query, top_k=top_k)

    def get_personal_patterns(self) -> PersonalPatternSummary:
        """Compute actionable long-term personal DSA pattern summary."""
        problems = list(self.list_problems())
        submissions: list[Submission] = []
        for prob in problems:
            for attempt in prob.attempts:
                submissions.extend(attempt.submissions)
        return self.my_patterns_service.analyze_patterns(problems, submissions)

    def get_knowledge_graph(self, account: str | None = None) -> KnowledgeGraph:
        """Construct lightweight DSA relationship graph mapping topics, problems, approaches, and mistakes.

        When ``account`` is provided, only submissions from that account are
        included in the graph.
        """
        problems = self.list_problems()
        submissions: list[Submission] = []
        for prob in problems:
            for attempt in prob.attempts:
                for s in attempt.submissions:
                    if account is None or s.source_account == account:
                        submissions.append(s)
        return self.knowledge_graph_builder.build_graph(problems, submissions)

    # 8. Phase 7 Memory Engine — account-scoped wrappers
    def memory_index_all(self, force_rebuild: bool = False) -> dict[str, int]:
        """Index all problems into the memory engine, scoped to the active account."""
        return self.memory_engine.index_all(force_rebuild=force_rebuild, account=self.active_account)

    def memory_search(
        self,
        query: str,
        filters: dict[str, str] | None = None,
        top_k: int = 10,
    ) -> list:
        """Hybrid memory search scoped to the active account."""
        return self.memory_engine.search(
            query=query, filters=filters, top_k=top_k, account=self.active_account
        )

    def memory_find_similar_problem(self, problem_id: str, top_k: int = 5) -> list:
        """Find similar problems scoped to the active account."""
        return self.memory_engine.find_similar_problem(problem_id, top_k=top_k, account=self.active_account)

    def memory_find_common_mistakes(self, topic: str | None = None) -> list:
        """Find common mistakes scoped to the active account."""
        return self.memory_engine.find_common_mistakes(topic=topic, account=self.active_account)

    def memory_find_previous_approaches(self, problem_id: str) -> list:
        """Find previous approaches for a problem, scoped to the active account."""
        return self.memory_engine.find_previous_approaches(problem_id, account=self.active_account)

    def memory_stats(self) -> dict[str, Any]:
        """Get memory stats scoped to the active account."""
        return self.memory_engine.get_memory_stats(account=self.active_account)

    def analyze_submission(self, submission_id: str, force_refresh: bool = False) -> SubmissionAnalysis:
        """Perform AI code analysis for a submission using cached identity checks."""
        problems = self.list_problems()
        target_sub = None
        target_prob = None
        prev_sub = None

        for prob in problems:
            all_subs = []
            for att in sorted(prob.attempts, key=lambda a: a.attempt_number):
                all_subs.extend(att.submissions)
            
            for idx, sub in enumerate(all_subs):
                if sub.id == submission_id:
                    target_sub = sub
                    target_prob = prob
                    if idx > 0:
                        prev_sub = all_subs[idx - 1]
                    break
            if target_sub:
                break

        if not target_sub or not target_prob:
            raise ValueError(f"Submission ID '{submission_id}' not found.")

        return self.ai_analyzer.analyze_submission(
            submission=target_sub,
            problem=target_prob,
            previous_submission=prev_sub,
            force_refresh=force_refresh,
        )

    def analyze_solution_evolution_ai(self, problem_identifier: str, force_refresh: bool = False) -> SolutionEvolution:
        """Perform multi-attempt AI solution evolution analysis for a problem."""
        prob = self.get_problem(problem_identifier, account=self.active_account)
        submissions: list[Submission] = []
        for attempt in sorted(prob.attempts, key=lambda a: a.attempt_number):
            submissions.extend(attempt.submissions)
        return self.ai_analyzer.analyze_evolution(prob, submissions, force_refresh=force_refresh)

    def ask_codememory(self, question: str) -> dict[str, Any]:
        """Ask natural language question grounded in personal CodeMemory records."""
        return self.memory_service.ask_codememory(question)

    def health_check(self) -> dict[str, Any]:
        """Run per-component health check and return status report."""
        import time
        results: dict[str, Any] = {}

        # Storage layer: health is probed through the storage abstraction,
        # which delegates to each coordinated tier (DuckDB primary + Parquet +
        # Filesystem). The service never reaches into repository internals.
        try:
            tier_health = self.storage.tier_health()
            results["storage"] = {
                "status": "ok" if self.storage.health() else "error",
                "problems": len(self.storage.list_all()),
                "tiers": ", ".join(f"{tier}={'ok' if ok else 'error'}" for tier, ok in tier_health.items()),
            }
            results["duckdb"] = {"status": "ok" if tier_health.get("duckdb") else "error"}
        except Exception as e:
            results["storage"] = {"status": "error", "detail": str(e)}
            results["duckdb"] = {"status": "error", "detail": str(e)}

        # AI provider
        try:
            provider_name = type(self.ai_provider).__name__
            results["ai_provider"] = {"status": "ok", "provider": provider_name}
        except Exception as e:
            results["ai_provider"] = {"status": "error", "detail": str(e)}

        # Memory engine
        try:
            mem_stats = self.memory_engine.get_memory_stats()
            results["memory_engine"] = {
                "status": "ok",
                "documents": mem_stats.get("total_documents", 0),
                "vectors": mem_stats.get("indexed_vectors", 0),
            }
        except Exception as e:
            results["memory_engine"] = {"status": "error", "detail": str(e)}

        # Search service
        try:
            self.search_service.search(query=None)
            results["search"] = {"status": "ok"}
        except Exception as e:
            results["search"] = {"status": "error", "detail": str(e)}

        results["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        results["overall"] = "ok" if all(
            v.get("status") == "ok" for k, v in results.items() if isinstance(v, dict) and "status" in v
        ) else "degraded"
        return results

    def close_storage(self) -> None:
        """Release the live storage resources this service instance holds.

        Called when the instance is being retired — most importantly by "Clear
        All Data", which deletes the storage tree out from under it. The DuckDB
        connection it owns is registered process-wide by database path, so
        unless it is unregistered here, the next service built against the same
        path is handed this same dead handle and reads rows that no longer exist
        on disk while its writes vanish.

        The automatic sync worker is stopped first: it holds its own connection
        into the same tree and must never outlive the service it belongs to.
        """
        self.stop_autosync()
        try:
            self.storage.close()
        except Exception as exc:  # teardown must never block a rebuild
            logger.warning("Failed to close storage while retiring a service: %s", exc)

    def stop_autosync(self) -> None:
        """Stop this service's automatic sync worker, if one was ever started.

        Retiring a service (notably through ``reset_service`` after "Clear All
        Data") must not leave a worker thread syncing into a storage tree that
        is about to be rebuilt. Safe to call when auto-sync was never used.
        """
        scheduler = self._autosync
        if scheduler is None:
            return
        try:
            scheduler.stop()
        except Exception as exc:
            logger.warning("Failed to stop LeetCode auto-sync worker: %s", exc)

    # 9. LeetCode account & sync surface

    @property
    def leetcode(self) -> "LeetCodeAccountService":
        """Single service-level entry point for the LeetCode account/sync lifecycle.

        Exposes ``connect``/``sync``/``status``/``disconnect`` so UI and CLI
        consumers never touch the low-level LeetCode client. The underlying sync
        engine and its Phase B contract are unchanged.
        """
        if self._leetcode_service is None:
            from codememory.connectors.account.service import AccountService
            from codememory.connectors.leetcode.service import LeetCodeAccountService

            acct_svc = self._explicit_account_service or AccountService(data_dir=self._account_data_dir)
            self._leetcode_service = LeetCodeAccountService(
                app_service=self,
                account_service=acct_svc,
            )
        return self._leetcode_service

    @property
    def autosync(self) -> "LeetCodeSyncScheduler":
        """Optional background LeetCode sync scheduler (Phase E).

        Lazily built so a process that never touches automatic sync never
        spawns a worker thread. The scheduler runs each sync on a service of its
        own with a *dedicated* DuckDB connection: the pooled connection the UI
        thread uses is not safe for concurrent access, while two separate
        connections to the same file are serialised by DuckDB.
        """
        if self._autosync is None:
            from codememory.connectors.leetcode.scheduler import LeetCodeSyncScheduler

            self._autosync = LeetCodeSyncScheduler(
                base_dir=self.base_dir,
                knowledge_dir=self.knowledge_dir,
                db_path=self._db_path,
            )
        return self._autosync
