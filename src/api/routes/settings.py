from fastapi import APIRouter, Depends, HTTPException
from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.settings import SettingsOut, SettingsUpdate

router = APIRouter(tags=["settings"])

@router.get("/settings", response_model=SettingsOut)
def get_settings(service: CodeMemoryService = Depends(get_service)):
    """Expose application settings."""
    settings = service.get_settings()
    leetcode_connected = service.leetcode.is_connected()
    autosync_enabled = (
        getattr(service, "_autosync", None) is not None
        and getattr(service._autosync, "is_running", lambda: False)()
    )
    return SettingsOut(
        leetcode_connected=leetcode_connected,
        autosync_enabled=autosync_enabled,
        data_dir="data",
        version="1.0.0",
        theme=settings.theme,
        accent_emphasis=settings.accent_emphasis,
        compact_density=settings.compact_density,
        reduced_motion=settings.reduced_motion,
        code_font_size=settings.code_font_size,
        default_code_language=settings.default_code_language,
        default_difficulty=settings.default_difficulty,
        show_failed_attempts=settings.show_failed_attempts,
        auto_expand_evolution=settings.auto_expand_evolution,
        timestamp_display=settings.timestamp_display,
    )

@router.put("/settings", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    service: CodeMemoryService = Depends(get_service),
):
    """Persist one or more user preference fields."""
    update_data = payload.model_dump(exclude_unset=True)
    settings = service.update_settings(**update_data)
    return SettingsOut(
        leetcode_connected=service.leetcode.is_connected(),
        autosync_enabled=(
            getattr(service, "_autosync", None) is not None
            and getattr(service._autosync, "is_running", lambda: False)()
        ),
        data_dir="data",
        version="1.0.0",
        theme=settings.theme,
        accent_emphasis=settings.accent_emphasis,
        compact_density=settings.compact_density,
        reduced_motion=settings.reduced_motion,
        code_font_size=settings.code_font_size,
        default_code_language=settings.default_code_language,
        default_difficulty=settings.default_difficulty,
        show_failed_attempts=settings.show_failed_attempts,
        auto_expand_evolution=settings.auto_expand_evolution,
        timestamp_display=settings.timestamp_display,
    )
