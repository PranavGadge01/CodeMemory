"""Deterministic whole-history learning profile.

The profile is the single source of truth for roadmap and recommendation
decisions.  It is computed from stored problems, attempts and submissions
only: no LLM is involved, and no statistic is inferred beyond what the data
supports.  Each signal is labelled ``observed``, ``interpretation`` or
``recommendation`` so the UI never presents a guess as a fact.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from codememory.analytics.analytics_service import AnalyticsService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission
from codememory.learning.models import (
    DifficultyObservation,
    LearningProfile,
    ProfileSignal,
    TopicObservation,
)
from codememory.learning.taxonomy import (
    FOUNDATIONAL_PATTERNS,
    adjacent_of,
    is_foundational,
    patterns_for_topics,
    skill_label,
    topics_for_pattern,
)
from codememory.storage.history import HistorySnapshot

# Failure statuses that indicate a concrete execution problem (as opposed to
# "Unknown", which must never be counted as a failure).
_FAILURE_STATUSES = {
    SubmissionStatus.WRONG_ANSWER,
    SubmissionStatus.TIME_LIMIT_EXCEEDED,
    SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
    SubmissionStatus.RUNTIME_ERROR,
    SubmissionStatus.COMPILE_ERROR,
}

_DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2, "Unknown": -1}

# A topic needs at least this many tracked problems before a success rate is
# treated as evidence of strength or struggle (rather than noise).
_MIN_TOPIC_SAMPLE = 2
_STRENGTH_SUCCESS_RATE = 60.0
_STRUGGLE_SUCCESS_RATE = 60.0


def _iter_submissions(problem: Problem) -> Iterable[tuple[Attempt, Submission]]:
    for attempt in problem.attempts:
        for submission in attempt.submissions:
            yield attempt, submission


def _difficulty_value(problem: Problem) -> str:
    value = getattr(problem.difficulty, "value", problem.difficulty)
    return str(value) if value else "Unknown"


def _is_solved(problem: Problem) -> bool:
    return problem.latest_accepted_submission is not None


def build_learning_profile(
    analytics: AnalyticsService,
    account: str | None = None,
    *,
    now: datetime | None = None,
    recent_days: int = 14,
    max_topics: int = 40,
    snapshot: HistorySnapshot | None = None,
) -> LearningProfile:
    """Build a deterministic :class:`LearningProfile` from scoped storage data.

    Args:
        analytics: Analytics service used for the established account-scoping
            rules (so the profile cannot disagree with the rest of the product
            about which submissions belong to the user).
        account: Active LeetCode account, or ``None`` for the legacy path.
        now: Injectable clock for deterministic tests.
        recent_days: Window used to mark problems as "recently attempted".
    """
    all_problems = list(analytics._get_all_problems(snapshot))
    problems = list(analytics._scope_problems(all_problems, account))
    return profile_from_problems(
        problems, account=account, now=now, recent_days=recent_days, max_topics=max_topics
    )


def profile_from_problems(
    problems: Sequence[Problem],
    account: str | None = None,
    *,
    now: datetime | None = None,
    recent_days: int = 14,
    max_topics: int = 40,
) -> LearningProfile:
    """Build a profile directly from a list of problems.

    Used by callers (such as AI providers) that hold already-scoped problems
    rather than an :class:`AnalyticsService`.
    """
    now = now or datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=recent_days)

    profile = LearningProfile(account=account, generated_at=now)

    topic_problems: dict[str, dict[str, int]] = {}
    topic_subs: dict[str, int] = {}
    topic_accepted: dict[str, int] = {}
    topic_failed: dict[str, int] = {}
    topic_attempts: dict[str, int] = {}

    diff_problems: dict[str, int] = {}
    diff_solved: dict[str, int] = {}
    diff_subs: dict[str, int] = {}
    diff_accepted: dict[str, int] = {}

    languages: set[str] = set()
    patterns_practiced: set[str] = set()
    solved_keys: list[str] = []
    attempted_keys: list[str] = []
    recent_keys: set[str] = set()

    seed: tuple[datetime, Problem, Submission] | None = None
    mistakes_by_topic: dict[str, set[str]] = {}
    tle_topic_counts: dict[str, int] = {}
    wa_topic_counts: dict[str, int] = {}
    refinement_topic_counts: dict[str, int] = {}

    for problem in problems:
        key = (problem.slug or problem.id or "").strip().lower()
        if not key:
            continue

        submissions = list(_iter_submissions(problem))
        accepted_subs = [s for _, s in submissions if s.status == SubmissionStatus.ACCEPTED]
        failed_subs = [s for _, s in submissions if s.status in _FAILURE_STATUSES]
        solved = bool(accepted_subs)

        profile.total_problems += 1
        profile.total_submissions += len(submissions)
        profile.accepted_submissions += len(accepted_subs)
        profile.failed_submissions += len(failed_subs)
        profile.breadth = max(profile.breadth, 0)

        if solved:
            solved_keys.append(key)
            profile.solved_problems += 1
            if len(problem.attempts) == 1 and problem.attempts[0].is_accepted:
                profile.first_attempt_accepts += 1
        elif submissions:
            attempted_keys.append(key)
            profile.attempted_problems += 1
        else:
            profile.unsolved_problems += 1

        if submissions:
            latest_sub = max((s for _, s in submissions), key=lambda s: s.submitted_at)
            if latest_sub.submitted_at >= recent_cutoff:
                recent_keys.add(key)
            languages.add((latest_sub.language or "").strip())
            if solved:
                latest_accepted = max(accepted_subs, key=lambda s: s.submitted_at)
                if seed is None or latest_accepted.submitted_at > seed[0]:
                    seed = (latest_accepted.submitted_at, problem, latest_accepted)

        problem_patterns = patterns_for_topics(problem.topics)
        if solved or submissions:
            patterns_practiced.update(problem_patterns)

        difficulty = _difficulty_value(problem)
        diff_problems[difficulty] = diff_problems.get(difficulty, 0) + 1
        diff_subs[difficulty] = diff_subs.get(difficulty, 0) + len(submissions)
        diff_accepted[difficulty] = diff_accepted.get(difficulty, 0) + len(accepted_subs)
        if solved:
            diff_solved[difficulty] = diff_solved.get(difficulty, 0) + 1

        for topic in problem.topics:
            clean = (topic or "").strip()
            if not clean:
                continue
            bucket = topic_problems.setdefault(clean, {"problems": 0, "solved": 0})
            bucket["problems"] += 1
            if solved:
                bucket["solved"] += 1
            topic_subs[clean] = topic_subs.get(clean, 0) + len(submissions)
            topic_accepted[clean] = topic_accepted.get(clean, 0) + len(accepted_subs)
            topic_failed[clean] = topic_failed.get(clean, 0) + len(failed_subs)
            topic_attempts[clean] = topic_attempts.get(clean, 0) + len(problem.attempts)

            for attempt in problem.attempts:
                for mistake in attempt.mistakes or []:
                    text = (mistake or "").strip()
                    if text:
                        mistakes_by_topic.setdefault(clean, set()).add(text)

            tle_count = sum(1 for s in failed_subs if s.status == SubmissionStatus.TIME_LIMIT_EXCEEDED)
            wa_count = sum(1 for s in failed_subs if s.status == SubmissionStatus.WRONG_ANSWER)
            if tle_count >= 2:
                tle_topic_counts[clean] = tle_topic_counts.get(clean, 0) + 1
            if wa_count >= 2:
                wa_topic_counts[clean] = wa_topic_counts.get(clean, 0) + 1
            if solved and failed_subs and len(problem.attempts) >= 2:
                refinement_topic_counts[clean] = refinement_topic_counts.get(clean, 0) + 1

    profile.solved_keys = sorted(solved_keys)
    profile.attempted_keys = sorted(attempted_keys)
    profile.recent_keys = sorted(recent_keys)
    profile.languages = sorted(lang for lang in languages if lang)
    profile.breadth = len(topic_problems)

    # --- Topic observations -------------------------------------------------
    observations: list[TopicObservation] = []
    for topic, bucket in topic_problems.items():
        problems_count = bucket["problems"]
        subs = topic_subs.get(topic, 0)
        accepted = topic_accepted.get(topic, 0)
        obs = TopicObservation(
            topic=topic,
            problems=problems_count,
            solved=bucket["solved"],
            submissions=subs,
            accepted=accepted,
            failed=topic_failed.get(topic, 0),
            success_rate_pct=round((accepted / subs) * 100.0, 1) if subs else 0.0,
            total_attempts=topic_attempts.get(topic, 0),
        )
        observations.append(obs)
    observations.sort(key=lambda o: (-o.problems, -o.solved, o.topic))
    profile.topics = observations[:max_topics]

    profile.difficulties = [
        DifficultyObservation(
            difficulty=diff,
            problems=diff_problems.get(diff, 0),
            solved=diff_solved.get(diff, 0),
            submissions=diff_subs.get(diff, 0),
            accepted=diff_accepted.get(diff, 0),
        )
        for diff in ("Easy", "Medium", "Hard", "Unknown")
        if diff_problems.get(diff)
    ]

    profile.patterns_practiced = sorted(patterns_practiced)

    # --- Seed (most recently solved) problem -------------------------------
    if seed is not None:
        _, seed_problem, _seed_sub = seed
        profile.seed_problem_key = (seed_problem.slug or seed_problem.id).strip().lower()
        profile.seed_problem_slug = seed_problem.slug or None
        profile.seed_topics = list(seed_problem.topics)
        profile.seed_patterns = list(patterns_for_topics(seed_problem.topics))

    _populate_strengths_and_gaps(profile, observations, topic_problems)
    _populate_improvement_areas(
        profile,
        observations,
        tle_topic_counts,
        wa_topic_counts,
        refinement_topic_counts,
        mistakes_by_topic,
    )
    _populate_difficulty_ceiling(profile)
    _populate_limitations(profile, now)
    return profile


def _populate_strengths_and_gaps(
    profile: LearningProfile,
    observations: Sequence[TopicObservation],
    topic_problems: dict[str, dict[str, int]],
) -> None:
    """Fill observed strengths and *unpracticed* (not weak) gaps."""
    for obs in observations:
        if obs.problems < _MIN_TOPIC_SAMPLE:
            continue
        if obs.success_rate_pct >= _STRENGTH_SUCCESS_RATE and obs.solved >= 1:
            profile.strengths.append(
                ProfileSignal(
                    key=f"strength.{obs.topic}",
                    category="observed",
                    statement=(
                        f"Solved {obs.solved} of {obs.problems} tracked {obs.topic} problems "
                        f"({obs.success_rate_pct:.1f}% submission acceptance)."
                    ),
                    evidence=(
                        f"{obs.accepted} accepted submissions across {obs.submissions} recorded "
                        f"submissions on {obs.problems} {obs.topic} problems."
                    ),
                    topics=[obs.topic],
                    patterns=list(patterns_for_topics([obs.topic])),
                    sample_size=obs.problems,
                )
            )

    practiced = set(profile.patterns_practiced)
    unpracticed_patterns = [p for p in FOUNDATIONAL_PATTERNS if p not in practiced]
    profile.unpracticed_patterns = unpracticed_patterns

    unpracticed_topics: list[str] = []
    for pattern in unpracticed_patterns:
        for topic in topics_for_pattern(pattern):
            if topic in topic_problems:
                continue
            if topic not in unpracticed_topics:
                unpracticed_topics.append(topic)
    profile.unpracticed_topics = unpracticed_topics[:20]

    if unpracticed_patterns:
        labels = ", ".join(skill_label(p) for p in unpracticed_patterns[:5])
        profile.improvement_areas.append(
            ProfileSignal(
                key="gap.unpracticed_foundations",
                category="observed",
                statement=(
                    "No practice recorded yet in foundational areas: " + labels + "."
                ),
                evidence=(
                    "These patterns do not appear in any tracked problem's topic tags. "
                    "This is a coverage gap, not evidence of difficulty."
                ),
                patterns=unpracticed_patterns[:5],
                sample_size=profile.total_problems,
            )
        )


def _populate_improvement_areas(
    profile: LearningProfile,
    observations: Sequence[TopicObservation],
    tle_topic_counts: dict[str, int],
    wa_topic_counts: dict[str, int],
    refinement_topic_counts: dict[str, int],
    mistakes_by_topic: dict[str, set[str]],
) -> None:
    """Fill improvement areas that are backed by concrete failure evidence."""
    # Repeated time-limit failures are strong, concrete evidence.
    for topic, count in sorted(tle_topic_counts.items()):
        obs = next((o for o in observations if o.topic == topic), None)
        profile.improvement_areas.append(
            ProfileSignal(
                key=f"struggle.tle.{topic}",
                category="observed",
                statement=(
                    f"{count} {topic} problem(s) recorded at least two Time Limit Exceeded "
                    "submissions."
                ),
                evidence=(
                    "Repeated TLE verdicts indicate the accepted-or-attempted approach was not "
                    "efficient enough for the input bounds."
                ),
                topics=[topic],
                patterns=list(patterns_for_topics([topic])),
                sample_size=obs.problems if obs else count,
            )
        )

    for topic, count in sorted(wa_topic_counts.items()):
        obs = next((o for o in observations if o.topic == topic), None)
        profile.improvement_areas.append(
            ProfileSignal(
                key=f"struggle.wa.{topic}",
                category="observed",
                statement=(
                    f"{count} {topic} problem(s) recorded at least two Wrong Answer submissions."
                ),
                evidence=(
                    "Repeated Wrong Answer verdicts point to recurring correctness or edge-case "
                    "issues in this topic."
                ),
                topics=[topic],
                patterns=list(patterns_for_topics([topic])),
                sample_size=obs.problems if obs else count,
            )
        )

    # Low success rate, but only with enough sample to mean something.
    for obs in observations:
        if obs.problems < _MIN_TOPIC_SAMPLE:
            continue
        if obs.failed == 0:
            continue
        if obs.success_rate_pct < _STRUGGLE_SUCCESS_RATE:
            profile.improvement_areas.append(
                ProfileSignal(
                    key=f"struggle.rate.{obs.topic}",
                    category="interpretation",
                    statement=(
                        f"{obs.topic} has a {obs.success_rate_pct:.1f}% submission acceptance rate "
                        f"across {obs.problems} tracked problems."
                    ),
                    evidence=(
                        f"{obs.failed} of {obs.submissions} recorded submissions were unsuccessful. "
                        "Treat as an area to reinforce, not a definitive verdict."
                    ),
                    topics=[obs.topic],
                    patterns=list(patterns_for_topics([obs.topic])),
                    sample_size=obs.problems,
                )
            )

    # Iterative refinement (needed more than one attempt) is a learning signal.
    for topic, count in sorted(refinement_topic_counts.items()):
        profile.improvement_areas.append(
            ProfileSignal(
                key=f"refinement.{topic}",
                category="observed",
                statement=(
                    f"{count} {topic} problem(s) required more than one attempt before acceptance."
                ),
                evidence=(
                    "Multiple attempts followed by acceptance demonstrate productive iteration; "
                    "the first approach was not yet optimal or correct."
                ),
                topics=[topic],
                patterns=list(patterns_for_topics([topic])),
                sample_size=count,
            )
        )

    for topic, mistakes in sorted(mistakes_by_topic.items()):
        if not mistakes:
            continue
        listed = "; ".join(sorted(mistakes)[:3])
        profile.recurring_mistakes.append(
            ProfileSignal(
                key=f"mistakes.{topic}",
                category="observed",
                statement=f"Recorded mistakes in {topic}: {listed}.",
                evidence="Taken from the mistakes recorded on your attempts.",
                topics=[topic],
                patterns=list(patterns_for_topics([topic])),
                sample_size=len(mistakes),
            )
        )


def _populate_difficulty_ceiling(profile: LearningProfile) -> None:
    """Set the highest difficulty the user has demonstrably solved."""
    solved_difficulties = [
        obs.difficulty for obs in profile.difficulties if obs.solved > 0 and obs.difficulty in _DIFFICULTY_ORDER
    ]
    if not solved_difficulties:
        profile.difficulty_ceiling = "Easy" if profile.total_problems else "Easy"
        return
    profile.difficulty_ceiling = max(solved_difficulties, key=lambda d: _DIFFICULTY_ORDER[d])


def _populate_limitations(profile: LearningProfile, now: datetime) -> None:
    """Attach honest caveats when the history is too small to support claims."""
    if profile.total_problems == 0:
        profile.limitations.append(
            "No problems are stored yet; no personalised weaknesses can be claimed."
        )
    elif profile.total_problems < 5:
        profile.limitations.append(
            f"Only {profile.total_problems} problem(s) are stored. Signals below the "
            "minimum sample size are reported as coverage notes, not weaknesses."
        )
    if profile.total_submissions == 0:
        profile.limitations.append(
            "No submissions are recorded, so difficulty and optimization signals are unavailable."
        )
    elif profile.failed_submissions == 0:
        profile.limitations.append(
            "No failed submissions are recorded; struggle signals cannot be established."
        )
    if profile.total_problems and not profile.seed_problem_key:
        profile.limitations.append(
            "No accepted submission is recorded yet, so there is no most-recently-solved problem."
        )
    profile.limitations.append(
        "Profile generated at " + now.strftime("%Y-%m-%dT%H:%M:%SZ") + " from stored records."
    )


def adjacent_patterns(patterns: Sequence[str]) -> list[str]:
    """Return useful adjacent patterns for a set of pattern ids."""
    seen: list[str] = []
    for pattern in patterns:
        for adjacent in adjacent_of(pattern):
            if adjacent not in seen and adjacent not in patterns:
                seen.append(adjacent)
    return seen


def foundational_of(pattern: str) -> bool:
    """Expose foundational check for callers ranking prerequisite coverage."""
    return is_foundational(pattern)


def _snapshot_topics_by_key(evidence) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for snap in evidence.supporting_problems:
        key = (snap.slug or snap.problem_id or "").strip().lower()
        if key:
            mapping[key] = list(snap.topics or [])
    return mapping


def profile_from_evidence(evidence, *, account: str | None = None) -> LearningProfile:
    """Build a profile from an already-computed :class:`InsightEvidence` bundle.

    This is the provider-side path (used when a caller supplies evidence rather
    than storage).  It never invents values: every field maps to an existing
    evidence item or supporting snapshot.
    """
    profile = LearningProfile(account=account, generated_at=evidence.generated_at)
    profile.evidence_refs = sorted(evidence.all_evidence_ids())

    overview = evidence.metrics.overview or {}
    profile.total_problems = int(overview.get("total_problems", 0) or 0)
    profile.total_submissions = int(overview.get("total_submissions", 0) or 0)
    profile.solved_problems = int(overview.get("accepted_problems", 0) or 0)
    profile.unsolved_problems = int(overview.get("unsolved_problems", 0) or 0)
    profile.first_attempt_accepts = int(
        round(
            (float(overview.get("first_attempt_acceptance_rate_pct", 0.0) or 0.0) / 100.0)
            * max(profile.solved_problems, 0)
        )
    )

    solved_keys: list[str] = []
    attempted_keys: list[str] = []
    for snap in evidence.supporting_problems:
        key = (snap.slug or snap.problem_id or "").strip().lower()
        if not key:
            continue
        if snap.status == "Solved":
            solved_keys.append(key)
        elif snap.total_attempts:
            attempted_keys.append(key)
    profile.solved_keys = sorted(set(solved_keys))
    profile.attempted_keys = sorted(set(attempted_keys))
    if profile.total_problems == 0:
        profile.total_problems = len(evidence.supporting_problems)
    if profile.solved_problems == 0:
        profile.solved_problems = len(profile.solved_keys)
    profile.attempted_problems = len(profile.attempted_keys)

    topics: list[TopicObservation] = []
    for stat in evidence.metrics.topic_stats or []:
        submissions = int(stat.get("total_submissions", 0) or 0)
        accepted = int(stat.get("accepted_submissions", 0) or 0)
        topics.append(
            TopicObservation(
                topic=str(stat.get("topic", "") or ""),
                problems=int(stat.get("total_problems", 0) or 0),
                solved=int(stat.get("solved_problems", 0) or 0),
                submissions=submissions,
                accepted=accepted,
                failed=max(0, submissions - accepted),
                success_rate_pct=float(stat.get("success_rate_pct", 0.0) or 0.0),
                total_attempts=int(stat.get("total_attempts", 0) or 0),
            )
        )
    profile.topics = topics
    profile.breadth = len(topics)

    difficulties: list[DifficultyObservation] = []
    for stat in evidence.metrics.difficulty_stats or []:
        difficulties.append(
            DifficultyObservation(
                difficulty=str(stat.get("difficulty", "") or ""),
                problems=int(stat.get("total_problems", 0) or 0),
                solved=int(stat.get("solved_problems", 0) or 0),
                submissions=int(stat.get("total_submissions", 0) or 0),
                accepted=int(stat.get("accepted_submissions", 0) or 0),
            )
        )
    profile.difficulties = [d for d in difficulties if d.difficulty]

    practiced: set[str] = set()
    for obs in profile.topics:
        practiced.update(patterns_for_topics([obs.topic]))
    for snap in evidence.supporting_problems:
        practiced.update(patterns_for_topics(list(snap.topics or [])))
    profile.patterns_practiced = sorted(practiced)

    for obs in profile.topics:
        if obs.problems >= _MIN_TOPIC_SAMPLE and obs.success_rate_pct >= _STRENGTH_SUCCESS_RATE and obs.solved >= 1:
            profile.strengths.append(
                ProfileSignal(
                    key=f"strength.{obs.topic}",
                    category="observed",
                    statement=(
                        f"Solved {obs.solved} of {obs.problems} tracked {obs.topic} problems "
                        f"({obs.success_rate_pct:.1f}% submission acceptance)."
                    ),
                    evidence=f"{obs.accepted} accepted of {obs.submissions} submissions.",
                    topics=[obs.topic],
                    patterns=list(patterns_for_topics([obs.topic])),
                    sample_size=obs.problems,
                )
            )

    topics_by_key = _snapshot_topics_by_key(evidence)

    def _signal_for_problems(key_prefix: str, statement: str, evidence_text: str, keys: list[str]) -> None:
        signal_topics: list[str] = []
        for key in keys:
            for topic in topics_by_key.get(key.strip().lower(), []):
                if topic not in signal_topics:
                    signal_topics.append(topic)
        patterns: list[str] = []
        for topic in signal_topics:
            for pattern in patterns_for_topics([topic]):
                if pattern not in patterns:
                    patterns.append(pattern)
        profile.improvement_areas.append(
            ProfileSignal(
                key=f"{key_prefix}.{len(profile.improvement_areas)}",
                category="observed",
                statement=statement,
                evidence=evidence_text,
                topics=signal_topics,
                patterns=patterns,
                sample_size=len(keys),
            )
        )

    tle_keys = list(evidence.patterns.repeated_tle_problems or [])
    if tle_keys:
        _signal_for_problems(
            "struggle.tle",
            f"{len(tle_keys)} problem(s) recorded repeated Time Limit Exceeded submissions.",
            "Repeated TLE verdicts indicate the recorded approach was not efficient enough.",
            tle_keys,
        )
    wa_keys = list(evidence.patterns.repeated_wa_problems or [])
    if wa_keys:
        _signal_for_problems(
            "struggle.wa",
            f"{len(wa_keys)} problem(s) recorded repeated Wrong Answer submissions.",
            "Repeated Wrong Answer verdicts point to correctness or edge-case issues.",
            wa_keys,
        )
    brute_keys = list(evidence.patterns.brute_force_before_optimized_problems or [])
    if brute_keys:
        _signal_for_problems(
            "refinement.optimization",
            f"{len(brute_keys)} problem(s) were solved via an initial approach that was later optimised.",
            "Recorded optimization from an initial approach to a better one shows iterative refinement.",
            brute_keys,
        )

    for weak in evidence.patterns.weak_topics or []:
        topic = str(weak.get("topic", "") or "")
        if not topic:
            continue
        profile.improvement_areas.append(
            ProfileSignal(
                key=f"struggle.rate.{topic}",
                category="interpretation",
                statement=(
                    f"{topic} has a {float(weak.get('success_rate_pct', 0.0) or 0.0):.1f}% "
                    "submission acceptance rate."
                ),
                evidence="Derived from recorded weak-topic analysis; treat as an area to reinforce.",
                topics=[topic],
                patterns=list(patterns_for_topics([topic])),
                sample_size=int(weak.get("total_problems", 0) or 0),
            )
        )

    unpracticed_patterns = [p for p in FOUNDATIONAL_PATTERNS if p not in practiced]
    profile.unpracticed_patterns = unpracticed_patterns
    profile.unpracticed_topics = [
        str(item.get("topic", "") or "")
        for item in (evidence.patterns.unpracticed_topics or [])
        if item.get("topic")
    ][:20]

    solved_snaps = [s for s in evidence.supporting_problems if s.status == "Solved"]
    if solved_snaps:
        seed_snap = solved_snaps[0]
        profile.seed_problem_key = (seed_snap.slug or seed_snap.problem_id or "").strip().lower() or None
        profile.seed_problem_slug = seed_snap.slug or None
        profile.seed_topics = list(seed_snap.topics or [])
        profile.seed_patterns = list(patterns_for_topics(profile.seed_topics))

    _populate_difficulty_ceiling(profile)
    _populate_limitations(profile, evidence.generated_at)
    return profile
