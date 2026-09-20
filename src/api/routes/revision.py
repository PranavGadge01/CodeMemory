from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional

from codememory.core.service import CodeMemoryService
from api.dependencies import get_service
from api.schemas.revision import RevisionQueueItemOut

router = APIRouter(tags=["revision"])

@router.get("/revision", response_model=List[RevisionQueueItemOut])
def get_revision_queue(
    limit: Optional[int] = Query(50, ge=1, le=100),
    topic: Optional[str] = None,
    service: CodeMemoryService = Depends(get_service)
):
    """Get the prioritized revision queue."""
    # service.revision.get_revision_queue might not support `topic` directly if we inspect it closely,
    # but based on reconnaissance it was assumed. If it doesn't, we filter python-side.
    try:
        queue = service.revision.get_revision_queue(limit=limit)
    except Exception as e:
        # Fallback if the signature differs or it throws
        raise HTTPException(status_code=500, detail=str(e))
        
    if topic:
        topic_lower = topic.lower()
        queue = [q for q in queue if any(topic_lower in t.lower() for t in q.topics)]
        
    return [RevisionQueueItemOut(**q.model_dump()) for q in queue]

@router.post("/revision/{slug}/reviewed")
def mark_reviewed(slug: str, service: CodeMemoryService = Depends(get_service)):
    """Mark a problem as reviewed."""
    try:
        service.revision.mark_reviewed(slug)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail="Problem not found")
