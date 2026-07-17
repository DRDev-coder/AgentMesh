from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.rate_limit import InMemoryRateLimitMiddleware
from api.routes.chat import router as chat_router
from api.routes.escalations import router as escalation_router
from api.routes.health import router as health_router
from api.services.orchestrator import AgentOrchestrator
from api.services.storage import SQLiteRepository


logger = logging.getLogger("agentmesh")


def _cors_origins() -> list[str]:
    configured = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app(
    *,
    repository: SQLiteRepository | None = None,
    orchestrator: AgentOrchestrator | None = None,
) -> FastAPI:
    repository = repository or (orchestrator.repository if orchestrator else SQLiteRepository())
    orchestrator = orchestrator or AgentOrchestrator(repository=repository)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        yield

    application = FastAPI(
        title="AgentMesh Risk-Aware Support API",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.state.repository = repository
    application.state.orchestrator = orchestrator
    application.add_middleware(InMemoryRateLimitMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Review-API-Key"],
    )
    application.include_router(chat_router, prefix="/api/v1")
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(health_router)
    application.include_router(escalation_router, prefix="/api/v1")

    @application.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        request_id = str(uuid.uuid4())
        logger.exception(
            "Unhandled API error request_id=%s path=%s type=%s",
            request_id,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            {"detail": "Internal server error", "request_id": request_id},
            status_code=500,
        )

    @application.get("/")
    async def root() -> dict:
        return {
            "message": "AgentMesh risk-aware support API",
            "status": "operational",
            "docs": "/docs",
        }

    return application


app = create_app()
