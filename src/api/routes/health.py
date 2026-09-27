from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from codememory.core.service import CodeMemoryService
from api.dependencies import get_service

router = APIRouter(tags=["health"])

class HealthResponse(BaseModel):
    overall: str
    storage: dict
    timestamp: str
    instance_id: str | None = None

@router.get("/health", response_model=HealthResponse)
def health_check(service: CodeMemoryService = Depends(get_service)):
    """Check API and storage health."""
    health_data = service.health_check()
    # health_data is a dict containing {"status": "ok", "storage": "ok", "timestamp": "..."}
    import os
    return HealthResponse(**health_data, instance_id=os.getenv("CODEMEMORY_SIDECAR_ID"))
