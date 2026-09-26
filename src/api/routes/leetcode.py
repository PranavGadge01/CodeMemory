import logging

from fastapi import APIRouter, Depends, HTTPException
from codememory.connectors.account.models import SyncState
from codememory.core.service import CodeMemoryService
from codememory.connectors.leetcode.service import LeetCodeAccountError, safe_error_message
from codememory.connectors.leetcode.errors import LeetCodeError

from api.dependencies import get_service
from api.schemas.leetcode import (
    LeetCodeStatusOut,
    LeetCodeConnectRequest,
    LeetCodeSyncResultOut,
    LeetCodeAuthStatusOut,
    LeetCodeAuthSyncResultOut,
    LeetCodeAuthStoreRequest,
    LeetCodeAuthValidateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["leetcode"])

@router.get("/leetcode/status", response_model=LeetCodeStatusOut)
def get_status(service: CodeMemoryService = Depends(get_service)):
    """Get LeetCode connection and sync status."""
    status = service.leetcode.status()
    # Pydantic handles mapping because properties match 
    return LeetCodeStatusOut(**status.model_dump())

@router.post("/leetcode/connect", response_model=LeetCodeStatusOut)
def connect(
    request: LeetCodeConnectRequest,
    service: CodeMemoryService = Depends(get_service)
):
    """Connect to a public LeetCode account."""
    try:
        service.leetcode.connect(request.username)
        # Return updated status
        status = service.leetcode.status()
        return LeetCodeStatusOut(**status.model_dump())
    except LeetCodeAccountError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Avoid leaking exact network internal exceptions like httpcore.ConnectError
        raise HTTPException(status_code=503, detail="Unable to connect to LeetCode right now.")

@router.post("/leetcode/sync", response_model=LeetCodeSyncResultOut)
def sync(service: CodeMemoryService = Depends(get_service)):
    """Trigger a synchronous sync with LeetCode (public sync)."""
    if not service.leetcode.is_connected():
        raise HTTPException(status_code=400, detail="LeetCode account not connected.")
    try:
        result = service.leetcode.sync()
        # The engine reports the records it persisted as ``records_added``; the
        # API field is named ``records_imported`` for the UI.
        return LeetCodeSyncResultOut(
            status=result.status.value,
            records_discovered=result.records_discovered,
            records_imported=result.records_added,
            records_skipped=result.records_skipped,
            records_failed=result.records_failed,
            error_message=result.error_message
        )
    except Exception as e:
        # The engine absorbs expected transport failures into a FAILED
        # SyncStatus, so an exception reaching here is a real defect. Log the
        # traceback server-side (it never reached the log before, which is why
        # this failure showed up as a bare 500) and surface only the scrubbed
        # message to the caller.
        logger.exception("LeetCode sync failed")
        raise HTTPException(status_code=500, detail=safe_error_message(e) or "Sync failed.")

@router.post("/leetcode/auth/store", response_model=LeetCodeAuthStatusOut)
def store_authenticated_credentials(
    request: LeetCodeAuthStoreRequest,
    service: CodeMemoryService = Depends(get_service)
):
    """Store authenticated LeetCode credentials."""
    try:
        service.leetcode.store_authenticated_credentials(request.session, request.csrf_token)
        status = service.leetcode.status()
        # Add auth-specific fields to status
        auth_status = LeetCodeAuthStatusOut(**status.model_dump())
        auth_status.credentials_stored = True
        return auth_status
    except LeetCodeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not validate LeetCode credentials: {safe_error_message(e)}",
        )
    except Exception as e:
        logger.exception("Failed to store authenticated credentials")
        raise HTTPException(status_code=500, detail=safe_error_message(e) or "Failed to store credentials")

@router.post("/leetcode/auth/validate", response_model=LeetCodeAuthStatusOut)
def validate_authenticated_credentials(
    service: CodeMemoryService = Depends(get_service)
):
    """Validate stored authenticated LeetCode credentials."""
    try:
        is_valid = service.leetcode.validate_authenticated_credentials()
        status = service.leetcode.status()
        # Add auth-specific fields to status
        auth_status = LeetCodeAuthStatusOut(**status.model_dump())
        auth_status.credentials_stored = is_valid
        auth_status.validation_message = (
            None if is_valid else "No valid authenticated LeetCode session was confirmed. Check or refresh the stored credentials."
        )
        auth_status.connected = is_valid and status.connected
        return auth_status
    except Exception as e:
        logger.exception("Failed to validate authenticated credentials")
        raise HTTPException(status_code=500, detail=safe_error_message(e) or "Failed to validate credentials")

@router.post("/leetcode/auth/revoke", response_model=LeetCodeAuthStatusOut)
@router.delete("/leetcode/auth/revoke", response_model=LeetCodeAuthStatusOut)
def revoke_authenticated_credentials(
    service: CodeMemoryService = Depends(get_service)
):
    """Revoke stored authenticated LeetCode credentials."""
    try:
        service.leetcode.revoke_authenticated_credentials()
        status = service.leetcode.status()
        # Add auth-specific fields to status
        auth_status = LeetCodeAuthStatusOut(**status.model_dump())
        auth_status.credentials_stored = False
        return auth_status
    except Exception as e:
        logger.exception("Failed to revoke authenticated credentials")
        raise HTTPException(status_code=500, detail=safe_error_message(e) or "Failed to revoke credentials")

@router.post("/leetcode/auth/sync", response_model=LeetCodeAuthSyncResultOut)
def sync_authenticated_full_history(
    service: CodeMemoryService = Depends(get_service)
):
    """Trigger authenticated full-history sync with LeetCode."""
    if not service.leetcode.is_connected():
        raise HTTPException(status_code=400, detail="LeetCode account not connected.")
    try:
        result = service.leetcode.sync_authenticated_full_history()
        if result.status == SyncState.FAILED:
            raise HTTPException(
                status_code=502,
                detail=safe_error_message(result.error_message) or "Authenticated LeetCode sync failed.",
            )
        return LeetCodeAuthSyncResultOut(
            status=result.status.value,
            records_discovered=result.records_discovered,
            records_added=result.records_added,
            records_skipped=result.records_skipped,
            records_failed=result.records_failed,
            code_fetched=result.details.get("code_fetched", 0) if result.details else 0,
            code_failed=result.details.get("code_failed", 0) if result.details else 0,
            diagnostics={
                key: value
                for key, value in (result.details or {}).items()
                if key in {
                    "pages_fetched",
                    "raw_records_discovered",
                    "records_parsed",
                    "records_mapped",
                    "records_failed_to_parse",
                    "records_failed_to_map",
                    "records_failed_storage",
                    "records_skipped_duplicate",
                    "records_updated",
                    "code_fetch_attempted",
                    "raw_records_per_page",
                    "parsed_records_per_page",
                    "offsets_per_page",
                    "has_next_per_page",
                    "final_offset",
                }
            },
            error_message=result.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Authenticated LeetCode sync failed")
        raise HTTPException(status_code=500, detail=safe_error_message(e) or "Sync failed")

@router.delete("/leetcode/connect")
def disconnect(service: CodeMemoryService = Depends(get_service)):
    """Disconnect the LeetCode account."""
    result = service.leetcode.disconnect()
    return {"status": "ok", "disconnected": result}
