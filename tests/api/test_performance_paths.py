"""Performance-path regression tests: history is expanded once per request.

These assert the structural change that removed the repeated full-history
expansion from the dashboard/analytics/knowledge/insight endpoints. They
count ``storage.list_all()`` calls, which is the single expensive history read.
"""

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def _count_expansions(service, monkeypatch):
    calls = {"n": 0}
    original = service.storage.list_all

    def counting():
        calls["n"] += 1
        return original()

    monkeypatch.setattr(service.storage, "list_all", counting)
    return calls


def test_dashboard_expands_history_once(client, mock_service, monkeypatch):
    calls = _count_expansions(mock_service, monkeypatch)
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert calls["n"] == 1


def test_analytics_expands_history_once(client, mock_service, monkeypatch):
    calls = _count_expansions(mock_service, monkeypatch)
    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    assert calls["n"] == 1


def test_knowledge_expands_history_once(client, mock_service, monkeypatch):
    calls = _count_expansions(mock_service, monkeypatch)
    response = client.get("/api/v1/knowledge")
    assert response.status_code == 200
    assert calls["n"] == 1


def _seed_service(service: CodeMemoryService) -> None:
    service.add_problem(title="Two Sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    service.add_submission(problem_identifier="two-sum", code="pass", status=SubmissionStatus.ACCEPTED)
    service.add_problem(title="Word Ladder", difficulty=DifficultyLevel.HARD, topics=["Breadth-First Search"])
    service.add_submission(problem_identifier="word-ladder", code="x", status=SubmissionStatus.WRONG_ANSWER)


def test_collective_insight_reuses_one_history_expansion(tmp_path, monkeypatch):
    """The collective insight expands history once for the snapshot and once
    more for the local problem catalogue used by recommendations (2 total).
    It previously rebuilt history ~11 times across evidence + analytics +
    recommendations."""
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "c.duckdb",
    )
    _seed_service(service)

    calls = _count_expansions(service, monkeypatch)
    insight = service.get_collective_learning_insight()
    assert insight is not None
    assert calls["n"] == 2
    service.close_storage()


def test_recommendations_reuse_snapshot(tmp_path, monkeypatch):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "r.duckdb",
    )
    _seed_service(service)

    calls = _count_expansions(service, monkeypatch)
    snapshot = service.history_snapshot()
    assert calls["n"] == 1
    service.get_next_problem_recommendations(limit=2, snapshot=snapshot)
    # snapshot (1) + local catalogue (1) — the profile itself adds none.
    assert calls["n"] == 2
    service.close_storage()