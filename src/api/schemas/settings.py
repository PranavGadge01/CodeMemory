from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from api.schemas.common import BaseCamelModel

class _AppSettingsBase(BaseModel):
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

class SettingsOut(BaseCamelModel):
    leetcode_connected: bool
    autosync_enabled: bool
    data_dir: str
    version: str
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

class SettingsUpdate(BaseCamelModel):
    theme: Optional[str] = None
    accent_emphasis: Optional[bool] = None
    compact_density: Optional[bool] = None
    reduced_motion: Optional[bool] = None
    code_font_size: Optional[str] = None
    default_code_language: Optional[str] = None
    default_difficulty: Optional[str] = None
    show_failed_attempts: Optional[bool] = None
    auto_expand_evolution: Optional[bool] = None
    timestamp_display: Optional[str] = None
