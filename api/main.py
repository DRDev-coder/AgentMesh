from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.rate_limit import InMemoryRateLimitMiddleware
from api.config import Settings, get_settings
from api.db.base import Database
from api.errors import (
    APIError,
    api_error_handler,
    error_payload,
    validation_error_handler,
)
from api.routes.api_keys import router as api_keys_router
from api.routes.billing import router as billing_router
from api.routes.chat import router as chat_router
from api.routes.decisions import router as decisions_router
from api.routes.documents import router as documents_router
from api.routes.escalations import router as escalation_router
from api.routes.health import router as health_router
from api.routes.platform import router as platform_router
from api.routes.reviews import router as reviews_router
from api.routes.tenants import router as tenants_router
from api.routes.usage import router as usage_router
from api.routes.webhooks import router as webhooks_router
from api.services.orchestrator import AgentOrchestrator
from api.services.object_storage import create_object_storage
from api.services.rate_limiter import DistributedRateLimiter
from api.services.storage import SQLiteRepository
from api.services.tenants import seed_industry_templates


logger = logging.getLogger("agentmesh")


def _cors_origins(settings: Settings) -> list[str]:
    return list(settings.cors_origins)


def create_app(
    *,
    repository: SQLiteRepository | None = None,
    orchestrator: AgentOrchestrator | None = None,
    settings: Settings | None = None,
    database: Database | None = None,
    enable_saas: bool | None = None,
) -> FastAPI:
    injected_legacy_runtime = repository is not None or orchestrator is not None
    settings = settings or get_settings()
    if enable_saas is None:
        enable_saas = settings.saas_enabled and not injected_legacy_runtime
    repository = repository or (orchestrator.repository if orchestrator else SQLiteRepository())
    orchestrator = orchestrator or AgentOrchestrator(repository=repository)
    database = database or Database(settings)
    object_storage = create_object_storage(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        if enable_saas:
            database.initialize()
            with database.session() as session:
                seed_industry_templates(session)
        yield
        database.dispose()

    application = FastAPI(
        title="AgentMesh Risk-Aware Support API",
        version="3.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
    )
    application.state.repository = repository
    application.state.orchestrator = orchestrator
    application.state.settings = settings
    application.state.database = database
    application.state.object_storage = object_storage
    application.state.saas_enabled = enable_saas
    application.state.rate_limiter = DistributedRateLimiter(settings)
    application.add_middleware(InMemoryRateLimitMiddleware)
    application.include_router(chat_router, prefix="/api/v1")
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(health_router)
    application.include_router(escalation_router, prefix="/api/v1")
    if enable_saas:
        for router in (
            tenants_router,
            documents_router,
            api_keys_router,
            decisions_router,
            reviews_router,
            webhooks_router,
            usage_router,
            billing_router,
            platform_router,
        ):
            application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "Unhandled API error request_id=%s path=%s type=%s",
                request.state.request_id,
                request.url.path,
                type(exc).__name__,
            )
            response = JSONResponse(
                error_payload(request, "internal_error", "Internal server error."),
                status_code=500,
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'"
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Keep CORS outside the request middleware so even sanitized 500 responses
    # receive the configured origin header instead of being masked as CORS failures.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(settings),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Razorpay-Signature",
            "X-Razorpay-Event-Id",
            "X-Dev-User",
            "X-Dev-Email",
            "X-Dev-AAL",
            "X-Review-API-Key",
        ],
    )

    application.add_exception_handler(APIError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    @application.get("/")
    async def root() -> dict:
        return {
            "message": "AgentMesh risk-aware support API",
            "status": "operational",
            "docs": "/docs",
        }

    return application


app = create_app()
