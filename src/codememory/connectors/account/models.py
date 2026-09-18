"""Account connection and sync status domain models for external platforms."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AccountStatus(str, Enum):
    """Connection status for an external platform account."""

    CONNECTED = "Connected"
    NOT_CONNECTED = "Not Connected"
    SYNCING = "Syncing"
    FAILED = "Failed"


class SyncState(str, Enum):
    """Execution state of a synchronization job."""

    IDLE = "Idle"
    RUNNING = "Running"
    SUCCESS = "Success"
    PARTIAL = "Partial"
    FAILED = "Failed"


class AccountConnection(BaseModel):
    """Local representation of a connected external platform account."""

    provider: str = "LeetCode"
    username: str
    display_name: Optional[str] = None
    user_avatar: Optional[str] = None
    status: AccountStatus = AccountStatus.CONNECTED
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[SyncState] = None
    last_sync_error: Optional[str] = None
    capabilities: Dict[str, bool] = Field(
        default_factory=lambda: {
            "profile_sync": True,
            "progress_sync": True,
            "recent_submissions": True,
            "private_code_scraping": False,
        }
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyncStatus(BaseModel):
    """Detailed summary status of a sync execution job."""

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: SyncState = SyncState.IDLE
    records_discovered: int = 0
    records_added: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
