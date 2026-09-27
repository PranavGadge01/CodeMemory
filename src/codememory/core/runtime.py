"""Installed-app paths and verified, copy-preserving legacy migration."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path


def desktop_mode():
    return os.getenv("CODEMEMORY_DESKTOP") == "1" or bool(getattr(sys, "frozen", False))


def app_directory() -> Path:
    if os.getenv("CODEMEMORY_APP_DIR"):
        return Path(os.environ["CODEMEMORY_APP_DIR"]).resolve()
    local = os.getenv("LOCALAPPDATA")
    if not local:
        raise RuntimeError("LOCALAPPDATA is unavailable; set CODEMEMORY_APP_DIR")
    return Path(local) / "CodeMemory"


def runtime_paths():
    base = app_directory() if desktop_mode() else Path("data")
    data = Path(os.getenv("CODEMEMORY_DATA_DIR", str(base)))
    knowledge = Path(os.getenv("CODEMEMORY_KNOWLEDGE_DIR", str(base / "knowledge") if desktop_mode() else "knowledge"))
    db = os.getenv("CODEMEMORY_DB_PATH", str(data / "codememory.duckdb"))
    return data, knowledge, db


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_runtime(source_root: Path, target: Path) -> dict:
    """Copy data/ and knowledge/, verify every byte, then publish the new root.

    Source directories are never removed. Refuse to merge two existing stores.
    Failed copies stay in a named staging directory for inspection/recovery.
    """
    source_root, target = source_root.resolve(), target.resolve()
    source_data = source_root / "data"
    marker = target / "runtime-migration.json"
    if marker.exists() or (target / "codememory.duckdb").exists():
        return {"status": "existing", "target": str(target)}
    if not source_data.exists() or not any(source_data.iterdir()):
        target.mkdir(parents=True, exist_ok=True)
        return {"status": "new", "target": str(target)}
    if target == source_data or target.is_relative_to(source_data):
        raise ValueError("Migration target must be separate from the legacy data directory")
    if target.exists() and any(p.name != "logs" for p in target.iterdir()):
        raise RuntimeError(f"Refusing to merge existing runtime files in {target}; legacy data is unchanged")
    database = source_data / "codememory.duckdb"
    if database.exists():
        import duckdb
        # Replay/checkpoint any WAL before copying. Fails if another app owns it.
        connection = duckdb.connect(str(database))
        try:
            connection.execute("CHECKPOINT")
        finally:
            connection.close()
    stage = target.with_name(target.name + ".migration-" + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    sources = [(source_data, stage)]
    if (source_root / "knowledge").exists():
        sources.append((source_root / "knowledge", stage / "knowledge"))
    manifest = {}
    for source, destination in sources:
        for item in source.rglob("*"):
            if item.is_symlink():
                raise RuntimeError(f"Legacy data contains a symbolic link: {item}")
            if not item.is_file():
                continue
            copied = destination / item.relative_to(source)
            copied.parent.mkdir(parents=True, exist_ok=True)
            before = file_digest(item)
            shutil.copy2(item, copied)
            if before != file_digest(copied) or before != file_digest(item):
                raise RuntimeError("Runtime data changed during copy; legacy data remains authoritative")
            manifest[str(copied.relative_to(stage))] = before
    result = {"status": "migrated", "source": str(source_root), "target": str(target), "files": manifest}
    (stage / "runtime-migration.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if target.exists():
        if (target / "logs").exists():
            shutil.copytree(target / "logs", stage / "logs", dirs_exist_ok=True)
        target.rename(target.with_name(target.name + ".bootstrap-" + uuid.uuid4().hex))
    stage.rename(target)
    return result


def prepare_runtime():
    if not desktop_mode():
        return
    # Explicit path overrides remain authoritative; never migrate into them.
    if any(os.getenv(key) for key in ("CODEMEMORY_DATA_DIR", "CODEMEMORY_DB_PATH", "CODEMEMORY_KNOWLEDGE_DIR")):
        return
    legacy = Path(os.getenv("CODEMEMORY_LEGACY_DIR", str(Path.cwd())))
    migrate_runtime(legacy, app_directory())
