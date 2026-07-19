import uuid

from fastapi import APIRouter, Request

from api.schemas import ChatRequest, ChatResponse


router = APIRouter(tags=["support"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    session_id = payload.session_id or str(uuid.uuid4())
    return await request.app.state.orchestrator.process(payload.query, session_id)
