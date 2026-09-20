from fastapi import APIRouter, Depends, HTTPException
from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.settings import SettingsOut

router = APIRouter(tags=["settings"])

@router.get("/settings", response_model=SettingsOut)
def get_settings(service: CodeMemoryService = Depends(get_service)):
    """Expose safe application settings."""
    # Derive leetcode_connected
    leetcode_connected = service.leetcode.is_connected()
    
    # Derive autosync state safely
    # If service._autosync doesn't expose is_running, we default to false safely.
    autosync_enabled = getattr(service, "_autosync", None) is not None and getattr(service._autosync, "is_running", lambda: False)()
    
    return SettingsOut(
        leetcode_connected=leetcode_connected,
        autosync_enabled=autosync_enabled,
        data_dir="data", # Masking absolute path for safety
        version="1.0.0"
    )
