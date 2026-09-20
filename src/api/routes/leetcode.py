from fastapi import APIRouter, Depends, HTTPException
from codememory.core.service import CodeMemoryService
from codememory.connectors.leetcode.service import LeetCodeAccountError

from api.dependencies import get_service
from api.schemas.leetcode import (
    LeetCodeStatusOut,
    LeetCodeConnectRequest,
    LeetCodeSyncResultOut
)

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
        return LeetCodeSyncResultOut(
            status=result.status.value,
            records_discovered=result.records_discovered,
            records_imported=result.records_imported,
            records_skipped=result.records_skipped,
            records_failed=result.records_failed,
            error_message=result.error_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Sync failed.")

@router.delete("/leetcode/connect")
def disconnect(service: CodeMemoryService = Depends(get_service)):
    """Disconnect the LeetCode account."""
    service._account_service.disconnect("leetcode")
    return {"status": "ok"}
