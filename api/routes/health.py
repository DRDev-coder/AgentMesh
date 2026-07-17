from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


router = APIRouter(tags=["health"])


@router.get("/health")
async def legacy_health(request: Request) -> dict:
    ready, dependencies = request.app.state.orchestrator.readiness()
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
    payload = {
        "status": "ready" if ready else "not_ready",
        "dependencies": dependencies,
    }
    return JSONResponse(payload, status_code=200 if ready else 503)
