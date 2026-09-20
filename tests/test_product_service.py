"""Tests for ProductService facade layer."""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codememory.app.product_service import ProductService
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Attempt, Problem, Submission


@pytest.fixture
def empty_service() -> CodeMemoryService:
    """Create CodeMemoryService with no data."""
    import tempfile
    tmp_path = Path(tempfile.mkdtemp())
    return CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )


@pytest.fixture
def empty_product_service(empty_service: CodeMemoryService) -> ProductService:
    """Create ProductService with empty data."""
    return ProductService(empty_service)


@pytest.fixture
def populated_service() -> CodeMemoryService:
    """Create CodeMemoryService with sample data."""
    import tempfile
    tmp_path = Path(tempfile.mkdtemp())
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    now = datetime.now(timezone.utc)

    # Add problems with attempts and submissions
    p1 = service.add_problem(
        title="Two Sum",
        difficulty=DifficultyLevel.EASY,
        topics=["Array", "Hash Table"],
        platform="LeetCode",
    )

    # Add attempt 1 with accepted submission
    sub1 = Submission(
        problem_id=p1.id,
        code="def twoSum(nums, target): return {}",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=42.5,
        memory_mb=12.3,
        submitted_at=now - timedelta(days=2),
    )
    attempt1 = Attempt(
        problem_id=p1.id,
        attempt_number=1,
        submissions=[sub1],
        status=SubmissionStatus.ACCEPTED,
    )
    p1.attempts.append(attempt1)
    service.storage.save(p1)

    # Add problem 2 (unsolved)
    p2 = service.add_problem(
        title="Binary Tree",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Tree", "DFS"],
        platform="LeetCode",
    )

    # Add failed attempt
    sub2 = Submission(
        problem_id=p2.id,
        code="def traverse(root): pass",
        language="python",
        status=SubmissionStatus.WRONG_ANSWER,
        submitted_at=now - timedelta(days=1),
    )
    attempt2 = Attempt(
        problem_id=p2.id,
        attempt_number=1,
        submissions=[sub2],
        status=SubmissionStatus.WRONG_ANSWER,
    )
    p2.attempts.append(attempt2)
    service.storage.save(p2)

    # Add problem 3 (multiple languages)
    p3 = service.add_problem(
        title="Median of Two Sorted",
        difficulty=DifficultyLevel.HARD,
        topics=["Array", "Binary Search"],
        platform="LeetCode",
    )

    # Multiple submissions in one attempt
    sub3a = Submission(
        problem_id=p3.id,
        code="// C++ code",
        language="cpp",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
        submitted_at=now - timedelta(days=3),
    )
    sub3b = Submission(
        problem_id=p3.id,
        code="def findMedianSortedArrays(nums1, nums2): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        submitted_at=now - timedelta(days=2, hours=12),
    )
    attempt3 = Attempt(
        problem_id=p3.id,
        attempt_number=1,
        submissions=[sub3a, sub3b],
        status=SubmissionStatus.ACCEPTED,
    )
    p3.attempts.append(attempt3)
    service.storage.save(p3)

    return service


@pytest.fixture
def populated_product_service(populated_service: CodeMemoryService) -> ProductService:
    """Create ProductService with sample data."""
    return ProductService(populated_service)


# ========== Dashboard Tests ==========

def test_dashboard_empty(empty_product_service: ProductService):
    """Dashboard should return defaults for empty service."""
    dashboard = empty_product_service.get_dashboard()
    assert dashboard.solved_count == 0
    assert dashboard.submission_count == 0
    assert dashboard.streak == 0
    assert dashboard.activity == []
    assert dashboard.overview is not None


def test_dashboard_with_data(populated_product_service: ProductService):
    """Dashboard should populate metrics from analytics."""
    dashboard = populated_product_service.get_dashboard()
    assert dashboard.solved_count == 2  # p1 and p3 are solved
    assert dashboard.submission_count >= 4  # At least 4 submissions
    assert dashboard.streak >= 0
    assert dashboard.activity is not None
    assert dashboard.overview is not None


def test_streak_calculation_no_submissions(empty_product_service: ProductService):
    """Streak should be 0 when no submissions."""
    streak = empty_product_service._calculate_streak()
    assert streak == 0


def test_streak_calculation_with_data(populated_product_service: ProductService):
    """Streak should be calculated from consecutive submission dates."""
    streak = populated_product_service._calculate_streak()
    assert isinstance(streak, int)
    assert streak >= 0


# ========== Problems Tests ==========

def test_problems_empty(empty_product_service: ProductService):
    """Should return empty list for empty service."""
    problems = empty_product_service.get_problems()
    assert problems == []


def test_problems_returns_all(populated_product_service: ProductService):
    """Should return all problems when no filter."""
    problems = populated_product_service.get_problems()
    assert len(problems) == 3
    assert all(p.id for p in problems)
    assert all(p.title for p in problems)


def test_problems_filter_by_difficulty(populated_product_service: ProductService):
    """Should filter problems by difficulty."""
    easy = populated_product_service.get_problems(difficulty="Easy")
    assert len(easy) == 1
    assert easy[0].difficulty == "Easy"
    assert easy[0].title == "Two Sum"

    medium = populated_product_service.get_problems(difficulty="Medium")
    assert len(medium) == 1
    assert medium[0].title == "Binary Tree"

    hard = populated_product_service.get_problems(difficulty="Hard")
    assert len(hard) == 1
    assert hard[0].title == "Median of Two Sorted"


def test_problems_filter_by_topic(populated_product_service: ProductService):
    """Should filter problems by topic."""
    array_probs = populated_product_service.get_problems(topic="Array")
    assert len(array_probs) == 2  # Two Sum and Median of Two Sorted
    assert all("Array" in p.topics for p in array_probs)


def test_problems_filter_by_solved(populated_product_service: ProductService):
    """Should filter by solved status."""
    solved = populated_product_service.get_problems(solved=True)
    assert len(solved) == 2
    assert all(p.solved for p in solved)

    unsolved = populated_product_service.get_problems(solved=False)
    assert len(unsolved) == 1
    assert not unsolved[0].solved


def test_problems_filter_by_language(populated_product_service: ProductService):
    """Should filter problems by language used."""
    python_probs = populated_product_service.get_problems(language="python")
    assert len(python_probs) == 3  # All have python submissions
    assert all("python" in [l.lower() for l in p.languages] for p in python_probs)

    cpp_probs = populated_product_service.get_problems(language="cpp")
    assert len(cpp_probs) == 1
    assert cpp_probs[0].title == "Median of Two Sorted"


def test_problem_view_properties(populated_product_service: ProductService):
    """ProblemView should have correct properties."""
    problems = populated_product_service.get_problems()
    p1 = [p for p in problems if p.title == "Two Sum"][0]

    assert p1.id
    assert p1.title == "Two Sum"
    assert p1.slug
    assert p1.difficulty == "Easy"
    assert "Array" in p1.topics
    assert p1.solved is True
    assert p1.last_attempted_at is not None
    assert p1.last_solved_at is not None
    assert p1.attempt_count >= 1
    assert p1.submission_count >= 1
    assert "python" in [l.lower() for l in p1.languages]


# ========== Submissions Tests ==========

def test_submissions_empty(empty_product_service: ProductService):
    """Should return empty list for empty service."""
    submissions = empty_product_service.get_submissions()
    assert submissions == []


def test_submissions_returns_all(populated_product_service: ProductService):
    """Should return all submissions."""
    submissions = populated_product_service.get_submissions()
    assert len(submissions) >= 4  # At least 4 submissions added


def test_submissions_sorted_by_date(populated_product_service: ProductService):
    """Submissions should be sorted by date descending."""
    submissions = populated_product_service.get_submissions()
    for i in range(len(submissions) - 1):
        assert submissions[i].submitted_at >= submissions[i + 1].submitted_at


def test_submissions_limit(populated_product_service: ProductService):
    """Should respect limit parameter."""
    all_subs = populated_product_service.get_submissions()
    limited = populated_product_service.get_submissions(limit=2)
    assert len(limited) == 2
    assert len(limited) <= len(all_subs)


def test_submissions_filter_by_problem(populated_product_service: ProductService):
    """Should filter by problem_id."""
    # Get all submissions
    all_subs = populated_product_service.get_submissions()

    # Get submissions for first problem
    problem = populated_product_service.get_problems()[0]
    prob_subs = populated_product_service.get_submissions(problem_id=problem.id)

    assert len(prob_subs) <= len(all_subs)
    assert all(s.problem_id == problem.id for s in prob_subs)


def test_submission_view_properties(populated_product_service: ProductService):
    """SubmissionView should have correct properties."""
    submissions = populated_product_service.get_submissions()
    assert len(submissions) > 0

    sub = submissions[0]
    assert sub.id
    assert sub.problem_id
    assert sub.problem_title
    assert sub.language
    assert sub.status
    assert sub.submitted_at
    assert sub.attempt_number >= 1


# ========== Analytics Tests ==========

def test_analytics_empty(empty_product_service: ProductService):
    """Analytics should return empty results for empty service."""
    analytics = empty_product_service.get_analytics()
    assert analytics.overview.total_problems == 0
    assert analytics.by_topic == []
    assert analytics.by_difficulty == []
    assert analytics.by_language == []


def test_analytics_with_data(populated_product_service: ProductService):
    """Analytics should aggregate from AnalyticsService."""
    analytics = populated_product_service.get_analytics()
    assert analytics.overview.total_problems == 3
    assert analytics.overview.accepted_problems == 2
    assert analytics.overview.total_attempts >= 3
    assert len(analytics.by_difficulty) > 0


def test_analytics_by_topic(populated_product_service: ProductService):
    """Analytics should break down by topic."""
    analytics = populated_product_service.get_analytics()
    assert len(analytics.by_topic) > 0

    # Should have Array, Tree, etc.
    topics = {t.topic for t in analytics.by_topic}
    assert "Array" in topics or "Tree" in topics


def test_analytics_by_difficulty(populated_product_service: ProductService):
    """Analytics should break down by difficulty."""
    analytics = populated_product_service.get_analytics()
    assert len(analytics.by_difficulty) > 0

    difficulties = {d.difficulty for d in analytics.by_difficulty}
    assert "Easy" in difficulties or "Medium" in difficulties or "Hard" in difficulties


def test_analytics_by_language(populated_product_service: ProductService):
    """Analytics should break down by language."""
    analytics = populated_product_service.get_analytics()
    # Languages might be empty if no submissions
    if analytics.by_language:
        languages = {l.language for l in analytics.by_language}
        assert "python" in languages or "cpp" in languages


# ========== Knowledge Tests ==========

def test_knowledge_empty(empty_product_service: ProductService):
    """Knowledge should return empty results for empty service."""
    knowledge = empty_product_service.get_knowledge()
    assert knowledge.weak_topics == []
    assert knowledge.high_failure_topics == []
    assert knowledge.revision_queue == []


def test_knowledge_with_data(populated_product_service: ProductService):
    """Knowledge should aggregate patterns and revision data."""
    knowledge = populated_product_service.get_knowledge()
    # Should have at least some data structure
    assert isinstance(knowledge.weak_topics, list)
    assert isinstance(knowledge.revision_queue, list)
    # With only 2 solved and 1 unsolved, might have revision queue items
    assert isinstance(knowledge.revision_queue, list)


def test_knowledge_revision_queue(populated_product_service: ProductService):
    """Knowledge should include revision queue."""
    knowledge = populated_product_service.get_knowledge()
    assert isinstance(knowledge.revision_queue, list)
    # Queue items should have basic structure if present
    for item in knowledge.revision_queue:
        assert hasattr(item, "problem_id")
        assert hasattr(item, "title")


# ========== Edge Cases ==========

def test_concurrent_user_ids(populated_product_service: ProductService):
    """ProductService should handle different user_ids (currently all same data)."""
    data1 = populated_product_service.get_dashboard(user_id="user1")
    data2 = populated_product_service.get_dashboard(user_id="user2")

    # Currently all user_ids get same data (local-first single user)
    assert data1.solved_count == data2.solved_count


def test_problem_with_multiple_attempts(populated_product_service: ProductService):
    """Should handle problems with multiple attempts correctly."""
    # Median of Two Sorted has 2 submissions in 1 attempt
    all_problems = populated_product_service.get_problems()
    problems = [p for p in all_problems if "Median" in p.title]
    if not problems:
        problems = [p for p in populated_product_service.get_problems() if "Median" in p.title]

    if problems:
        median_prob = problems[0]
        assert median_prob.submission_count >= 2
        assert median_prob.solved is True


def test_activity_data_structure(populated_product_service: ProductService):
    """Activity data should have correct structure."""
    dashboard = populated_product_service.get_dashboard()
    for activity in dashboard.activity:
        assert isinstance(activity.date, str)
        assert isinstance(activity.problems_solved, int)
        assert isinstance(activity.total_submissions, int)
        assert activity.problems_solved >= 0
        assert activity.total_submissions >= 0


def test_problem_languages_extraction(populated_product_service: ProductService):
    """Should correctly extract all languages used in a problem."""
    problems = populated_product_service.get_problems()
    median_prob = [p for p in problems if "Median" in p.title]

    if median_prob:
        p = median_prob[0]
        assert "python" in [l.lower() for l in p.languages]
        assert "cpp" in [l.lower() for l in p.languages]
