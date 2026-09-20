from typing import Any
from fastapi import Request
from codememory.core.service import CodeMemoryService

def get_service(request: Request) -> CodeMemoryService:
    """Provide the application-scoped CodeMemoryService singleton."""
    return request.app.state.service
