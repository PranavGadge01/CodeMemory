from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class ErrorDetail(BaseModel):
    code: str
    message: str

class APIError(BaseModel):
    error: ErrorDetail

def create_error_response(status_code: int, code: str, message: str) -> JSONResponse:
    content = APIError(error=ErrorDetail(code=code, message=message)).model_dump()
    return JSONResponse(status_code=status_code, content=content)

async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return create_error_response(400, "BAD_REQUEST", str(exc))

async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Explicitly scrubbing internal errors from reaching the UI.
    logger.exception("Unhandled error on %s", request.url.path)
    return create_error_response(500, "INTERNAL_ERROR", "An internal server error occurred.")

async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    # exc is an HTTPException
    code = "NOT_FOUND" if exc.status_code == 404 else "ERROR"
    return create_error_response(exc.status_code, code, exc.detail)
