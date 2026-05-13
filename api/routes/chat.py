from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from services.orchestrator import AgentOrchestrator
from services.blockchain_logger import BlockchainLogger

router = APIRouter()
orchestrator = AgentOrchestrator()
logger = BlockchainLogger()


class ChatRequest(BaseModel):
    query: str
    session_id: str = None


@router.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    result = await orchestrator.process(request.query, session_id)

    tx_hash = None
    if result.get("consensus_status") == "CONSENSUS_REACHED":
        try:
            tx_hash = logger.log_consensus(
                session_id=session_id,
                query=request.query,
                answer=result.get("final_answer", ""),
                votes=result.get("votes", {}),
                consensus_reached=True,
                status="CONSENSUS_REACHED"
            )
        except Exception as e:
            tx_hash = f"BLOCKCHAIN_ERROR: {str(e)}"

    return {
        "session_id": session_id,
        "query": request.query,
        "final_answer": result.get("final_answer"),
        "consensus_status": result.get("consensus_status"),
        "consensus_reason": result.get("consensus_reason"),
        "agent_votes": result.get("votes"),
        "escalate": result.get("escalate", False),
        "blockchain_tx": tx_hash,
        "primary_agent": result.get("primary_agent"),
        "confidence": result.get("confidence")
    }
