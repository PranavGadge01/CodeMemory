from typing import Any, List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from api.schemas.common import BaseCamelModel

class LeetCodeConnectRequest(BaseModel):
    username: str

class LeetCodeStatusOut(BaseCamelModel):
    connected: bool
    username: Optional[str] = None
    display_name: Optional[str] = None
    user_avatar: Optional[str] = None
    account_status: str
    sync_state: str
    last_attempted_sync: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    records_discovered: Optional[int] = None
    records_imported: Optional[int] = None
    records_skipped: Optional[int] = None
    records_failed: Optional[int] = None
    coverage: Optional[str] = None
    window_limit: Optional[int] = None
    records_in_window: Optional[int] = None
    window_truncated: Optional[bool] = None
    gap_detected: Optional[bool] = None
    unavailable_fields: List[str]
    solved_all: Optional[int] = None
    solved_easy: Optional[int] = None
    solved_medium: Optional[int] = None
    solved_hard: Optional[int] = None
    ranking: Optional[int] = None
    last_error: Optional[str] = None
    capabilities: Dict[str, bool]

class LeetCodeSyncResultOut(BaseCamelModel):
    status: str
    records_discovered: int
    records_imported: int
    records_skipped: int
    records_failed: int
    error_message: Optional[str] = None

# Authenticated LeetCode schemas
class LeetCodeAuthStoreRequest(BaseModel):
    session: str
    csrf_token: str

class LeetCodeAuthValidateRequest(BaseModel):
    # No fields needed - just validates existing stored credentials
    pass

class LeetCodeAuthStatusOut(BaseCamelModel):
    # Base status fields
    connected: bool
    username: Optional[str] = None
    display_name: Optional[str] = None
    user_avatar: Optional[str] = None
    account_status: str
    sync_state: str
    last_attempted_sync: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    records_discovered: Optional[int] = None
    records_imported: Optional[int] = None
    records_skipped: Optional[int] = None
    records_failed: Optional[int] = None
    coverage: Optional[str] = None
    window_limit: Optional[int] = None
    records_in_window: Optional[int] = None
    window_truncated: Optional[bool] = None
    gap_detected: Optional[bool] = None
    unavailable_fields: List[str]
    solved_all: Optional[int] = None
    solved_easy: Optional[int] = None
    solved_medium: Optional[int] = None
    solved_hard: Optional[int] = None
    ranking: Optional[int] = None
    last_error: Optional[str] = None
    capabilities: Dict[str, bool]
    # Auth-specific fields
    credentials_stored: bool = False
    validation_message: Optional[str] = None

class LeetCodeAuthSyncResultOut(BaseCamelModel):
    status: str
    records_discovered: int
    records_added: int
    records_skipped: int
    records_failed: int
    code_fetched: int = 0
    code_failed: int = 0
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
