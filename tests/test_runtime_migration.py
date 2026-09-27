from pathlib import Path
import json
import pytest
from codememory.core.runtime import migrate_runtime, runtime_paths


def test_copy_verify_switch_preserves_all_files_and_is_idempotent(tmp_path):
    old = tmp_path / "old"
    (old / "data/accounts").mkdir(parents=True)
    (old / "knowledge/shared").mkdir(parents=True)
    (old / "data/accounts/vault.json").write_bytes(b"encrypted-fixture")
    (old / "data/app_settings.json").write_text('{"theme":"dark"}')
    (old / "knowledge/shared/notes.md").write_text("Private retained note")
    new = tmp_path / "local/CodeMemory"
    result = migrate_runtime(old, new)
    assert result["status"] == "migrated"
    assert len(result["files"]) == 3
    for relative in ("accounts/vault.json", "app_settings.json"):
        assert (old / "data" / relative).read_bytes() == (new / relative).read_bytes()
    assert (new / "knowledge/shared/notes.md").read_text() == "Private retained note"
    assert migrate_runtime(old, new)["status"] == "existing"
    assert (old / "data/accounts/vault.json").exists()


def test_does_not_merge_or_overwrite_existing_data(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    (old / "data").mkdir(parents=True)
    (old / "data/app_settings.json").write_text("old")
    new.mkdir()
    (new / "app_settings.json").write_text("existing")
    with pytest.raises(RuntimeError, match="Refusing to merge"):
        migrate_runtime(old, new)
    assert (new / "app_settings.json").read_text() == "existing"
    assert (old / "data/app_settings.json").read_text() == "old"


def test_desktop_paths_and_explicit_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEMEMORY_DESKTOP", "1")
    monkeypatch.setenv("CODEMEMORY_APP_DIR", str(tmp_path / "app"))
    for key in ("CODEMEMORY_DATA_DIR", "CODEMEMORY_KNOWLEDGE_DIR", "CODEMEMORY_DB_PATH"):
        monkeypatch.delenv(key, raising=False)
    data, knowledge, db = runtime_paths()
    assert data == tmp_path / "app"
    assert knowledge == data / "knowledge"
    assert Path(db) == data / "codememory.duckdb"
    monkeypatch.setenv("CODEMEMORY_DATA_DIR", str(tmp_path / "custom"))
    assert runtime_paths()[0] == tmp_path / "custom"
