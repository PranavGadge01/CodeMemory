import logging

from fastapi import APIRouter, Depends, HTTPException
from codememory.core.service import CodeMemoryService
from codememory.connectors.leetcode.service import LeetCodeAccountError, safe_error_message

from api.dependencies import get_service
from api.schemas.leetcode import (
    LeetCodeStatusOut,
    LeetCodeConnectRequest,
    LeetCodeSyncResultOut
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
    """Trigger a synchronous sync with LeetCode."""
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

@router.delete("/leetcode/connect")
def disconnect(service: CodeMemoryService = Depends(get_service)):
    """Disconnect the LeetCode account."""
    result = service.leetcode.disconnect()
    return {"status": "ok", "disconnected": result}
