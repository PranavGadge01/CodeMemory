"""
Tests for the settings API: GET defaults, PUT partial patch, PUT full patch
with reload, and type validation.
"""

import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from codememory.core.service import CodeMemoryService
from api.app import create_app
from api.dependencies import get_service


def _fresh_service_with_settings(tmp_path: Path) -> CodeMemoryService:
    base = tmp_path / "data"
    base.mkdir(parents=True, exist_ok=True)
    service = CodeMemoryService(base_dir=str(base), db_path=str(base / "test.duckdb"))
    return service


def _make_client(service: CodeMemoryService) -> TestClient:
    app = create_app(service=service)
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    return client


def test_get_settings_returns_defaults(tmp_path):
    service = _fresh_service_with_settings(tmp_path)
    client = _make_client(service)
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "system"
    assert data["accentEmphasis"] is True
    assert data["compactDensity"] is False
    assert data["reducedMotion"] is False
    assert data["codeFontSize"] == "13"
    assert data["defaultCodeLanguage"] == "python3"
    assert data["defaultDifficulty"] == "all"
    assert data["showFailedAttempts"] is True
    assert data["autoExpandEvolution"] is False
    assert data["timestampDisplay"] == "local"


def test_update_settings_persists_and_reloads(tmp_path):
    service = _fresh_service_with_settings(tmp_path)
    client = _make_client(service)
    patch = {
        "theme": "dark",
        "accentEmphasis": False,
        "codeFontSize": "14",
        "defaultDifficulty": "hard",
    }
    resp = client.put("/api/v1/settings", json=patch)
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "dark"
    assert data["accentEmphasis"] is False
    assert data["codeFontSize"] == "14"
    assert data["defaultDifficulty"] == "hard"

    # Reload from the persisted JSON file.
    reloaded = client.get("/api/v1/settings")
    assert reloaded.status_code == 200
    rd = reloaded.json()
    assert rd["theme"] == "dark"
    assert rd["accentEmphasis"] is False
    assert rd["codeFontSize"] == "14"
    assert rd["defaultDifficulty"] == "hard"


def test_update_settings_partial_patch(tmp_path):
    service = _fresh_service_with_settings(tmp_path)
    client = _make_client(service)
    resp = client.put("/api/v1/settings", json={"reducedMotion": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reducedMotion"] is True
    # Untouched fields keep their defaults.
    assert data["theme"] == "system"
    assert data["accentEmphasis"] is True


def test_update_settings_rejects_invalid_type(tmp_path):
    """A non-boolean value for a boolean field should be rejected by Pydantic."""
    service = _fresh_service_with_settings(tmp_path)
    client = _make_client(service)
    resp = client.put("/api/v1/settings", json={"accent_emphasis": "not-a-bool"})
    assert resp.status_code == 422
