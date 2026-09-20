import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codememory.core.service import CodeMemoryService
from api.config import settings
from api.errors import value_error_handler, exception_handler
import api.errors as errors

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting CodeMemory FastAPI server...")
    service = CodeMemoryService(
        db_path=settings.db_path,
        # In a real environment, we would also configure knowledge/data dirs if the service took them.
    )
    app.state.service = service
    yield
    # Shutdown
    logger.info("Shutting down CodeMemory FastAPI server...")
    service.close_storage()

def create_app() -> FastAPI:
    app = FastAPI(
        title="CodeMemory Local API",
        description="Local thin transport layer for the CodeMemory Next.js UI.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ValueError, value_error_handler)
    from fastapi.exceptions import HTTPException
    app.add_exception_handler(HTTPException, errors.http_exception_handler)
    app.add_exception_handler(Exception, exception_handler)

    # Register routers
    from api.routes import (
        health,
        dashboard,
        problems,
        submissions,
        analytics,
        knowledge,
        revision,
        leetcode,
        settings as settings_router
    )
    
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(problems.router, prefix="/api/v1")
    app.include_router(submissions.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(knowledge.router, prefix="/api/v1")
    app.include_router(revision.router, prefix="/api/v1")
    app.include_router(leetcode.router, prefix="/api/v1")
    app.include_router(settings_router.router, prefix="/api/v1")

    return app
