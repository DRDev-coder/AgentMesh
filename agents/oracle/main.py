from fastapi import FastAPI

from agents.oracle.service import OracleService
from shared.schemas import AgentState, OracleRequest, OracleResponse


app = FastAPI(title="AgentMesh ORACLE", version="2.0.0")
service = OracleService()


@app.post("/analyze", response_model=OracleResponse)
async def analyze(request: OracleRequest) -> OracleResponse:
    try:
        output = service.analyze(request.draft_answer, request.sources)
        return OracleResponse(
            session_id=request.session_id,
            state=AgentState.AVAILABLE,
            output=output,
        )
    except Exception:
        return OracleResponse(
            session_id=request.session_id,
            state=AgentState.MODEL_ERROR,
            error="ORACLE verification failed",
        )


@app.get("/health")
@app.get("/healthz")
async def health() -> dict:
    return {"status": "alive", "agent": "oracle"}


@app.get("/readyz")
async def readiness() -> dict:
    return {"status": "ready", "agent": "oracle"}
