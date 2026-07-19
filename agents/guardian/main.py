from fastapi import FastAPI

from agents.guardian.service import GuardianService
from shared.schemas import AgentState, GuardianRequest, GuardianResponse


app = FastAPI(title="AgentMesh GUARDIAN", version="2.0.0")
service = GuardianService()


@app.post("/analyze", response_model=GuardianResponse)
async def analyze(request: GuardianRequest) -> GuardianResponse:
    try:
        output = await service.analyze(request.query, request.proposed_answer)
        return GuardianResponse(
            session_id=request.session_id,
            state=AgentState.AVAILABLE,
            output=output,
        )
    except Exception:
        return GuardianResponse(
            session_id=request.session_id,
            state=AgentState.MODEL_ERROR,
            error="GUARDIAN analysis failed",
        )


@app.get("/health")
@app.get("/healthz")
async def health() -> dict:
    return {"status": "alive", "agent": "guardian"}


@app.get("/readyz")
async def readiness() -> dict:
    return {"status": "ready", "agent": "guardian", "deterministic_controls": True}
