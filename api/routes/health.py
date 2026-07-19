from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


router = APIRouter(tags=["health"])


@router.get("/health")
async def legacy_health(request: Request) -> dict:
    ready, dependencies = request.app.state.orchestrator.readiness()
    database = getattr(request.app.state, "database", None)
    if database is not None and getattr(request.app.state, "saas_enabled", False):
        database_ready = database.health()
        dependencies["postgresql"] = {"ready": database_ready}
        ready = ready and database_ready
    return {
        "gateway": "healthy" if ready else "degraded",
        "ready": ready,
        "dependencies": dependencies,
    }


@router.get("/healthz")
async def liveness() -> dict:
    return {"status": "alive"}


@router.get("/readyz")
async def readiness(request: Request):
    ready, dependencies = request.app.state.orchestrator.readiness()
    database = getattr(request.app.state, "database", None)
    if database is not None and getattr(request.app.state, "saas_enabled", False):
        database_ready = database.health()
        dependencies["postgresql"] = {"ready": database_ready}
        ready = ready and database_ready
    payload = {
        "status": "ready" if ready else "not_ready",
        "dependencies": dependencies,
    }
    return JSONResponse(payload, status_code=200 if ready else 503)
