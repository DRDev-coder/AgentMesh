from fastapi import FastAPI

from agents.empath.service import EmpathService
from shared.schemas import AgentRequest, AgentState, EmpathResponse


app = FastAPI(title="AgentMesh EMPATH", version="2.0.0")
service = EmpathService()


@app.post("/analyze", response_model=EmpathResponse)
async def analyze(request: AgentRequest) -> EmpathResponse:
    try:
        output = service.analyze(request.query)
        return EmpathResponse(
            session_id=request.session_id,
            state=AgentState.AVAILABLE,
            output=output,
        )
    except Exception:
        return EmpathResponse(
            session_id=request.session_id,
            state=AgentState.MODEL_ERROR,
            error="EMPATH analysis failed",
        )


@app.get("/health")
@app.get("/healthz")
async def health() -> dict:
    return {"status": "alive", "agent": "empath"}


@app.get("/readyz")
async def readiness() -> dict:
    return {"status": "ready", "agent": "empath"}
