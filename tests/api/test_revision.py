"""Regression tests for the /revision routes."""


def test_get_revision_queue(client):
    # The route reached for ``service.revision`` — an attribute that never
    # existed; the public surface is ``revision_service``. That AttributeError
    # surfaced as a 500 on every call.
    response = client.get("/api/v1/revision?limit=50")
    assert response.status_code == 200

    queue = response.json()
    assert isinstance(queue, list)
    assert len(queue) >= 1

    first = queue[0]
    assert first["slug"] == "two-sum"
    assert isinstance(first["priorityScore"], float)
    assert "breakdown" in first
    assert "Array" in first["topics"]


def test_get_revision_queue_limit_is_honoured(client):
    response = client.get("/api/v1/revision?limit=1")
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_get_revision_queue_unknown_topic_is_empty(client):
    response = client.get("/api/v1/revision?topic=does-not-exist")
    assert response.status_code == 200
    assert response.json() == []


def test_mark_reviewed(client):
    # Shares the same wrong accessor as the GET route; it also regressed.
    response = client.post("/api/v1/revision/two-sum/reviewed")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_mark_reviewed_unknown_problem(client):
    response = client.post("/api/v1/revision/nope/reviewed")
    assert response.status_code in (400, 404)
