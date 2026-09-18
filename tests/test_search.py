"""Unit tests for Phase 3 multi-criteria SearchService."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.search.search_service import SearchService


def test_multi_criteria_search(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # 1. Add Graph problem (Medium, Solved, Python)
    service.add_problem(title="Course Schedule", difficulty=DifficultyLevel.MEDIUM, topics=["Graph", "BFS"])
    service.add_submission(
        problem_identifier="course-schedule",
        code="def canFinish(): pass",
        language="python",
        status=SubmissionStatus.ACCEPTED,
    )

    # 2. Add Array problem (Easy, Unsolved, TLE, C++)
    service.add_problem(title="Subarray Sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
    service.add_submission(
        problem_identifier="subarray-sum",
        code="void solve() {}",
        language="cpp",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )

    search_svc = SearchService(storage=service.storage)

    # Search by topic
    res_topic = search_svc.search(topics="Graph")
    assert len(res_topic) == 1
    assert res_topic[0].slug == "course-schedule"

    # Search by difficulty
    res_diff = search_svc.search(difficulty="Easy")
    assert len(res_diff) == 1
    assert res_diff[0].slug == "subarray-sum"

    # Search by status
    res_status = search_svc.search(status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
    assert len(res_status) == 1
    assert res_status[0].slug == "subarray-sum"

    # Search by solved flag
    res_solved = search_svc.search(solved=True)
    assert len(res_solved) == 1
    assert res_solved[0].slug == "course-schedule"

    # Search by text query
    res_query = search_svc.search(query="canFinish")
    assert len(res_query) == 1
    assert res_query[0].slug == "course-schedule"

    # Search intent string helper
    res_tle = search_svc.search_by_query_string("problems where I got TLE")
    assert len(res_tle) == 1
    assert res_tle[0].slug == "subarray-sum"
