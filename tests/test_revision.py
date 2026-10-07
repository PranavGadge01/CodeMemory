"""Unit tests for RevisionService scoring and queue management."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.revision.revision_models import RevisionWeights
from codememory.revision.revision_service import RevisionService


def test_revision_scoring_and_queue(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # 1. Easy Solved Problem
    service.add_problem(title="Easy Solved", difficulty=DifficultyLevel.EASY)
    service.add_submission(problem_identifier="easy-solved", code="pass", status=SubmissionStatus.ACCEPTED)

    # 2. Hard Unsolved Problem with multiple failures
    service.add_problem(title="Hard Struggle", difficulty=DifficultyLevel.HARD, topics=["Dynamic Programming"])
    service.add_submission(problem_identifier="hard-struggle", code="fail 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier="hard-struggle", code="fail 2", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)

    revision = RevisionService(storage=service.storage, analytics_service=service.analytics_service)

    # Priority breakdown
    bd_hard = revision.get_problem_priority("hard-struggle")
    bd_easy = revision.get_problem_priority("easy-solved")

    assert bd_hard.final_score > bd_easy.final_score
    assert bd_hard.difficulty_score == 3.0  # Hard
    assert bd_hard.failure_score >= 2.0

    # Queue ordering
    queue = revision.get_revision_queue(limit=5)
    assert len(queue) == 2
    assert queue[0].slug == "hard-struggle"

    # Mark reviewed
    service.mark_reviewed("hard-struggle", notes="Reviewed DP state transitions")
    prob = service.get_problem("hard-struggle")
    assert len(prob.notes) >= 1


def _seed_revision_history(service: CodeMemoryService) -> None:
    """Create a small mixed history used by the batching regression tests."""
    service.add_problem(title="Two Sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    service.add_submission(problem_identifier="two-sum", code="pass", status=SubmissionStatus.ACCEPTED)

    service.add_problem(title="Climbing Stairs", difficulty=DifficultyLevel.EASY, topics=["Dynamic Programming"])
    service.add_submission(problem_identifier="climbing-stairs", code="pass", status=SubmissionStatus.ACCEPTED)

    service.add_problem(title="Word Ladder", difficulty=DifficultyLevel.HARD, topics=["Breadth-First Search"])
    service.add_submission(problem_identifier="word-ladder", code="fail", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier="word-ladder", code="fail2", status=SubmissionStatus.WRONG_ANSWER)


def test_revision_queue_computes_topic_statistics_once(tmp_path: Path, monkeypatch):
    """Global topic statistics must be calculated once per queue request."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )
    _seed_revision_history(service)
    revision = RevisionService(storage=service.storage, analytics_service=service.analytics_service)

    calls = {"count": 0}
    original = revision.analytics.get_topic_statistics

    def counting_get_topic_statistics(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(revision.analytics, "get_topic_statistics", counting_get_topic_statistics)

    queue = revision.get_revision_queue(limit=10)

    assert calls["count"] == 1
    assert len(queue) == 3


def test_revision_queue_priority_matches_standalone_scoring(tmp_path: Path):
    """Batched scoring must produce identical scores/order to per-problem scoring."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )
    _seed_revision_history(service)
    revision = RevisionService(storage=service.storage, analytics_service=service.analytics_service)

    queue = revision.get_revision_queue(limit=10)

    standalone = sorted(
        (revision.get_problem_priority(p.slug) for p in service.storage.list_all()),
        key=lambda bd: bd.final_score,
        reverse=True,
    )

    assert [item.slug for item in queue] == [bd.slug for bd in standalone]
    for item, bd in zip(queue, standalone):
        assert item.priority_score == bd.final_score
        assert item.breakdown.weakness_score == bd.weakness_score
        assert item.breakdown.failure_score == bd.failure_score
        assert item.breakdown.recency_score == bd.recency_score


def test_revision_queue_empty_history_skips_topic_statistics(tmp_path: Path, monkeypatch):
    """With no problems the queue must not trigger any topic aggregation."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )
    revision = RevisionService(storage=service.storage, analytics_service=service.analytics_service)

    calls = {"count": 0}
    original = revision.analytics.get_topic_statistics

    def counting_get_topic_statistics(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(revision.analytics, "get_topic_statistics", counting_get_topic_statistics)

    assert revision.get_revision_queue(limit=5) == []
    assert calls["count"] == 0


def test_revision_queue_preset_weak_topics_matches_formula(tmp_path: Path):
    """Passing a precomputed weak-topic set must not alter weakness scoring."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )
    _seed_revision_history(service)
    revision = RevisionService(storage=service.storage, analytics_service=service.analytics_service)

    weak = revision._weak_topics()
    problem = service.storage.get_by_slug("word-ladder")
    shared = revision.get_problem_priority("word-ladder", weak_topics=weak)
    standalone = revision.get_problem_priority("word-ladder")

    assert shared == standalone
    assert shared.weakness_score == (2.0 if any(t in weak for t in problem.topics) else 0.0)
