from fastapi import FastAPI, HTTPException

from agents.sage.service import SageService
from shared.schemas import AgentRequest, AgentState, SageResponse


app = FastAPI(title="AgentMesh SAGE", version="2.0.0")
service = SageService()


@app.post("/analyze", response_model=SageResponse)
async def analyze(request: AgentRequest) -> SageResponse:
    try:
        output = await service.analyze(request.query)
        return SageResponse(
            session_id=request.session_id,
            state=AgentState.AVAILABLE,
            output=output,
        )
    except RuntimeError as exc:
        return SageResponse(
            session_id=request.session_id,
            state=AgentState.DEPENDENCY_UNAVAILABLE,
            error=str(exc),
        )
    except Exception:
        return SageResponse(
            session_id=request.session_id,
            state=AgentState.MODEL_ERROR,
            error="SAGE analysis failed",
        )


@app.get("/health")
@app.get("/healthz")
async def health() -> dict:
    return {"status": "alive", "agent": "sage"}


@app.get("/readyz")
async def readiness() -> dict:
    if not service.ready:
        raise HTTPException(status_code=503, detail=service.engine.error)
    return {"status": "ready", "agent": "sage", "knowledge_base": str(service.engine.path)}
