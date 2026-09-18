"""Unit tests for PatternAnalyzer improvements and pattern detection."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from codememory.analytics.pattern_analyzer import PatternAnalyzer
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def test_pattern_detection(tmp_path: Path):
    """Preserve existing test verifying repeated TLE, brute-force-to-optimized, and high attempt problems."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # Add problem with TLE and WA attempts (Brute Force -> Solved)
    prob = service.add_problem(title="N-Queens", difficulty=DifficultyLevel.HARD, topics=["Backtracking", "Recursion"])
    service.add_submission(
        problem_identifier=prob.slug,
        code="bad attempt 1",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        problem_identifier=prob.slug,
        code="bad attempt 2",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        problem_identifier=prob.slug,
        code="good attempt 3",
        status=SubmissionStatus.ACCEPTED,
    )

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze(unpracticed_days_threshold=0)

    assert "N-Queens" in result.repeated_tle_problems
    assert "N-Queens" in result.brute_force_before_optimized_problems
    assert len(result.high_attempt_problems) == 1
    assert result.high_attempt_problems[0]["title"] == "N-Queens"


def test_empty_data_pattern_analyzer(tmp_path: Path):
    """Test PatternAnalyzer safely returns empty PatternAnalysisResult when no data exists."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test_empty.duckdb",
    )
    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze()

    assert result.weak_topics == []
    assert result.high_failure_topics == []
    assert result.repeated_tle_problems == []
    assert result.repeated_wa_problems == []
    assert result.brute_force_before_optimized_problems == []
    assert result.high_attempt_problems == []
    assert result.unpracticed_topics == []
    assert result.most_used_languages == []
    assert result.improvement_patterns == []


def test_weak_topic_detection_and_sample_size(tmp_path: Path):
    """Test weak topic and high-failure topic detection with minimum sample thresholds."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test_weak.duckdb",
    )

    # 1. Topic 'DP': Only 1 problem (unsolved, 1 submission).
    # With min_topic_problems_threshold=2, this should NOT be classified as weak.
    dp1 = service.add_problem(title="Coin Change", difficulty=DifficultyLevel.MEDIUM, topics=["DP"])
    service.add_submission(
        problem_identifier=dp1.slug,
        code="dp fail",
        status=SubmissionStatus.WRONG_ANSWER,
    )

    # 2. Topic 'Graph': 2 problems, both unsolved, 4 submissions total (all WA).
    # Meets min_topic_problems_threshold=2 and min_topic_submissions_threshold=3.
    # Should be classified as BOTH weak topic and high-failure topic.
    g1 = service.add_problem(title="Course Schedule", difficulty=DifficultyLevel.MEDIUM, topics=["Graph"])
    service.add_submission(problem_identifier=g1.slug, code="g1 fail 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=g1.slug, code="g1 fail 2", status=SubmissionStatus.WRONG_ANSWER)

    g2 = service.add_problem(title="Network Delay", difficulty=DifficultyLevel.MEDIUM, topics=["Graph"])
    service.add_submission(problem_identifier=g2.slug, code="g2 fail 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=g2.slug, code="g2 fail 2", status=SubmissionStatus.WRONG_ANSWER)

    # 3. Topic 'Array': 2 problems, both solved on 1st attempt.
    # Not weak, not high-failure.
    a1 = service.add_problem(title="Two Sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
    service.add_submission(problem_identifier=a1.slug, code="a1 acc", status=SubmissionStatus.ACCEPTED)
    a2 = service.add_problem(title="Contains Duplicate", difficulty=DifficultyLevel.EASY, topics=["Array"])
    service.add_submission(problem_identifier=a2.slug, code="a2 acc", status=SubmissionStatus.ACCEPTED)

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze(
        min_topic_problems_threshold=2,
        min_topic_submissions_threshold=3,
        weak_topic_success_threshold=50.0,
        high_failure_acceptance_threshold=40.0,
    )

    # Verify DP is NOT in weak topics due to insufficient sample size (< 2 problems)
    weak_topic_names = [wt["topic"] for wt in result.weak_topics]
    assert "DP" not in weak_topic_names
    assert "Graph" in weak_topic_names
    assert "Array" not in weak_topic_names

    # Verify Graph in high failure topics
    high_fail_names = [hf["topic"] for hf in result.high_failure_topics]
    assert "Graph" in high_fail_names
    assert "DP" not in high_fail_names  # only 1 submission (< 3)

    # Verify configurable threshold works (if we lower min_topic_problems_threshold to 1, DP appears)
    result_lower = analyzer.analyze(min_topic_problems_threshold=1)
    lower_weak_names = [wt["topic"] for wt in result_lower.weak_topics]
    assert "DP" in lower_weak_names


def test_repeated_wa_and_tle_detection(tmp_path: Path):
    """Test detection of repeated Wrong Answers and repeated TLE submissions."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test_wa_tle.duckdb",
    )

    # Problem A: 2 Wrong Answers
    p_wa = service.add_problem(title="Regex Matching", difficulty=DifficultyLevel.HARD, topics=["String"])
    service.add_submission(problem_identifier=p_wa.slug, code="wa 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=p_wa.slug, code="wa 2", status=SubmissionStatus.WRONG_ANSWER)

    # Problem B: 1 TLE, 1 WA (neither has >= 2)
    p_mixed = service.add_problem(title="Wildcard Matching", difficulty=DifficultyLevel.HARD, topics=["String"])
    service.add_submission(problem_identifier=p_mixed.slug, code="tle 1", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
    service.add_submission(problem_identifier=p_mixed.slug, code="wa 1", status=SubmissionStatus.WRONG_ANSWER)

    # Problem C: 2 TLEs, then Accepted
    p_tle = service.add_problem(title="Word Break II", difficulty=DifficultyLevel.HARD, topics=["DP"])
    service.add_submission(problem_identifier=p_tle.slug, code="tle 1", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
    service.add_submission(problem_identifier=p_tle.slug, code="tle 2", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
    service.add_submission(problem_identifier=p_tle.slug, code="acc", status=SubmissionStatus.ACCEPTED)

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze()

    assert "Regex Matching" in result.repeated_wa_problems
    assert "Word Break II" not in result.repeated_wa_problems
    assert "Wildcard Matching" not in result.repeated_wa_problems

    assert "Word Break II" in result.repeated_tle_problems
    assert "Regex Matching" not in result.repeated_tle_problems
    assert "Wildcard Matching" not in result.repeated_tle_problems


def test_high_attempt_problems_deterministic_sorting(tmp_path: Path):
    """Test that high attempt problems (>=2 attempts) are identified and sorted deterministically."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test_high_att.duckdb",
    )

    # Problem 1: 3 attempts, unsolved
    p1 = service.add_problem(title="Problem Zeta", difficulty=DifficultyLevel.MEDIUM)
    service.add_submission(problem_identifier=p1.slug, code="att 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=p1.slug, code="att 2", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=p1.slug, code="att 3", status=SubmissionStatus.WRONG_ANSWER)

    # Problem 2: 3 attempts, solved
    p2 = service.add_problem(title="Problem Alpha", difficulty=DifficultyLevel.MEDIUM)
    service.add_submission(problem_identifier=p2.slug, code="att 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=p2.slug, code="att 2", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=p2.slug, code="att 3", status=SubmissionStatus.ACCEPTED)

    # Problem 3: 2 attempts, solved
    p3 = service.add_problem(title="Problem Beta", difficulty=DifficultyLevel.EASY)
    service.add_submission(problem_identifier=p3.slug, code="att 1", status=SubmissionStatus.WRONG_ANSWER)
    service.add_submission(problem_identifier=p3.slug, code="att 2", status=SubmissionStatus.ACCEPTED)

    # Problem 4: 1 attempt, solved (should not appear in high_attempt_problems)
    p4 = service.add_problem(title="Problem Gamma", difficulty=DifficultyLevel.EASY)
    service.add_submission(problem_identifier=p4.slug, code="att 1", status=SubmissionStatus.ACCEPTED)

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze()

    assert len(result.high_attempt_problems) == 3
    # Sorting order: attempts_count desc, status 'Unsolved' before 'Solved', then title
    # Zeta: 3 attempts, Unsolved
    # Alpha: 3 attempts, Solved
    # Beta: 2 attempts, Solved
    assert result.high_attempt_problems[0]["title"] == "Problem Zeta"
    assert result.high_attempt_problems[0]["status"] == "Unsolved"
    assert result.high_attempt_problems[0]["attempts_count"] == 3

    assert result.high_attempt_problems[1]["title"] == "Problem Alpha"
    assert result.high_attempt_problems[1]["status"] == "Solved"
    assert result.high_attempt_problems[1]["attempts_count"] == 3

    assert result.high_attempt_problems[2]["title"] == "Problem Beta"
    assert result.high_attempt_problems[2]["attempts_count"] == 2


def test_unpracticed_topics_timezone_safety(tmp_path: Path):
    """Test unpracticed topics with both timezone-aware and naive timestamps."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test_unpracticed.duckdb",
    )

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=25)
    recent_time = now - timedelta(days=2)

    # Problem 1: Practiced 25 days ago (Topic "Tree")
    p1 = service.add_problem(title="Inorder Traversal", difficulty=DifficultyLevel.EASY, topics=["Tree"])
    service.add_submission(problem_identifier=p1.slug, code="tree code", status=SubmissionStatus.ACCEPTED)
    # Manually adjust submitted_at to test timezone safety
    for att in service.get_problem(p1.id).attempts:
        for s in att.submissions:
            s.submitted_at = old_time

    # Problem 2: Practiced 2 days ago (Topic "Graph")
    p2 = service.add_problem(title="Clone Graph", difficulty=DifficultyLevel.MEDIUM, topics=["Graph"])
    service.add_submission(problem_identifier=p2.slug, code="graph code", status=SubmissionStatus.ACCEPTED)
    for att in service.get_problem(p2.id).attempts:
        for s in att.submissions:
            s.submitted_at = recent_time

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze(unpracticed_days_threshold=14)

    unpracticed_names = [ut["topic"] for ut in result.unpracticed_topics]
    assert "Tree" in unpracticed_names
    assert "Graph" not in unpracticed_names
    tree_stat = next(ut for ut in result.unpracticed_topics if ut["topic"] == "Tree")
    assert tree_stat["days_unpracticed"] >= 24


def test_improvement_patterns_detection(tmp_path: Path):
    """Test deterministic improvement pattern detection between earlier and recent activity."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test_improvement.duckdb",
    )

    now = datetime.now(timezone.utc)

    # Create 4 earlier problems (days 20-10 ago) with high failures (acceptance = 25%)
    for i in range(1, 5):
        p = service.add_problem(title=f"Old Problem {i}", difficulty=DifficultyLevel.MEDIUM)
        # Attempt 1: WA
        service.add_submission(problem_identifier=p.slug, code="fail", status=SubmissionStatus.WRONG_ANSWER)
        # Attempt 2: WA
        service.add_submission(problem_identifier=p.slug, code="fail 2", status=SubmissionStatus.WRONG_ANSWER)
        # Attempt 3: Only p1 is accepted
        if i == 1:
            service.add_submission(problem_identifier=p.slug, code="acc", status=SubmissionStatus.ACCEPTED)

    # Set timestamps for old problems to 15 days ago
    for prob in service.storage.list_all():
        for att in prob.attempts:
            for s in att.submissions:
                s.submitted_at = now - timedelta(days=15)

    # Create 3 recent problems (days 5-1 ago) with 100% acceptance on 1st attempt
    for i in range(1, 4):
        p = service.add_problem(title=f"New Problem {i}", difficulty=DifficultyLevel.MEDIUM)
        service.add_submission(problem_identifier=p.slug, code="perfect", status=SubmissionStatus.ACCEPTED)

    # Set timestamps for new problems to 2 days ago
    for prob in service.storage.list_all():
        if "New Problem" in prob.title:
            for att in prob.attempts:
                for s in att.submissions:
                    s.submitted_at = now - timedelta(days=2)

    analyzer = PatternAnalyzer(analytics_service=service.analytics_service)
    result = analyzer.analyze()

    assert len(result.improvement_patterns) > 0
    metric_names = [imp["metric"] for imp in result.improvement_patterns]
    assert "acceptance_rate" in metric_names
    acc_imp = next(imp for imp in result.improvement_patterns if imp["metric"] == "acceptance_rate")
    assert acc_imp["recent_pct"] > acc_imp["earlier_pct"]
    assert acc_imp["delta_pct"] > 0
