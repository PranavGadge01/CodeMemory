"""Unit tests for Pydantic domain models."""

from datetime import datetime, timezone
import pytest

from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
from codememory.domain.models import (
    Attempt,
    Problem,
    ProblemNote,
    SolutionAnalysis,
    Submission,
    compute_submission_hash,
    generate_slug,
)


def test_slug_generation():
    assert generate_slug("Two Sum") == "two-sum"
    assert generate_slug("LRU Cache - 146!") == "lru-cache-146"
    assert generate_slug("   Binary Tree   Level Order   ") == "binary-tree-level-order"


def test_problem_model_creation():
    prob = Problem(
        title="Valid Anagram",
        difficulty=DifficultyLevel.EASY,
        topics=["Array", "Hash Table"],
        url="https://leetcode.com/problems/valid-anagram/",
    )
    assert prob.title == "Valid Anagram"
    assert prob.slug == "valid-anagram"
    assert prob.difficulty == DifficultyLevel.EASY
    assert len(prob.attempts) == 0
    assert len(prob.notes) == 0


def test_submission_hash_computation():
    now = datetime.now(timezone.utc)
    hash1 = compute_submission_hash("Two Sum", "python", "print(1)", now, "Accepted")
    hash2 = compute_submission_hash("Two Sum", "python", "print(1)", now, "Accepted")
    hash3 = compute_submission_hash("Two Sum", "python", "print(2)", now, "Accepted")

    assert hash1 == hash2
    assert hash1 != hash3


def test_attempt_and_latest_submission():
    sub1 = Submission(
        problem_id="p1",
        code="code1",
        status=SubmissionStatus.WRONG_ANSWER,
        submitted_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    sub2 = Submission(
        problem_id="p1",
        code="code2",
        status=SubmissionStatus.ACCEPTED,
        submitted_at=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
    )

    attempt = Attempt(
        problem_id="p1",
        attempt_number=1,
        approach_summary="Initial",
        submissions=[sub1, sub2],
    )

    assert attempt.latest_submission == sub2
    assert attempt.is_accepted is True


def test_problem_latest_accepted():
    prob = Problem(title="Test Problem")
    sub1 = Submission(problem_id=prob.id, code="bad", status=SubmissionStatus.WRONG_ANSWER)
    sub2 = Submission(problem_id=prob.id, code="good", status=SubmissionStatus.ACCEPTED)

    att1 = Attempt(problem_id=prob.id, attempt_number=1, submissions=[sub1])
    att2 = Attempt(problem_id=prob.id, attempt_number=2, submissions=[sub2])

    prob.attempts = [att1, att2]
    assert prob.latest_accepted_submission == sub2
    assert prob.latest_accepted_attempt == att2
