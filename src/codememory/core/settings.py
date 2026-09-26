"""
Persistent user-appearance and preference settings.

Backed by a JSON file (``<base_dir>/app_settings.json``) following the same
on-demand directory-creation pattern as ``AccountService``.  The backend API
layer is the single source of truth; the frontend mirrors the state in memory
and reconciles on every hard refresh from ``GET /settings``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserSettings(BaseModel):
    """Canonical representation of every persisted user preference."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    theme: str = "system"
    accent_emphasis: bool = True
    compact_density: bool = False
    reduced_motion: bool = False
    code_font_size: str = "13"

    default_code_language: str = "python3"
    default_difficulty: str = "all"
    show_failed_attempts: bool = True
    auto_expand_evolution: bool = False
    timestamp_display: str = "local"


# File-level constant used by the no-flash layout script.
SETTINGS_FILENAME = "app_settings.json"


class SettingsStore:
    """Thin JSON-file persistence layer for :class:`UserSettings`."""

    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / SETTINGS_FILENAME

    def load(self) -> UserSettings:
        """Load persisted settings, falling back to defaults on any error."""
        if not self.file_path.exists():
            return UserSettings()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return UserSettings(**raw)
        except Exception:
            return UserSettings()

    def save(self, settings: UserSettings | dict[str, Any]) -> UserSettings:
        """Persist settings atomically; returns the canonical model."""
        if isinstance(settings, UserSettings):
            data = settings.model_dump(mode="json")
        else:
            data = settings
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.file_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self.file_path)
        return UserSettings(**data)

    def update(self, **fields: Any) -> UserSettings:
        """Merge ``fields`` into the current settings and persist."""
        current = self.load()
        for key, value in fields.items():
            if value is not None:
                setattr(current, key, value)
        return self.save(current)

    def reset(self) -> UserSettings:
        """Reset to factory defaults."""
        defaults = UserSettings()
        return self.save(defaults)
