from typing import List, Dict
from dataclasses import dataclass


@dataclass
class AgentVote:
    agent_id: str
    answer: str
    confidence: int
    vote: str
    flags: List[str]


class ConsensusEngine:
    def __init__(self, total_agents=4, fault_tolerance=1):
        self.total_agents = total_agents
        self.required_agreements = 2 * fault_tolerance + 1

    def reach_consensus(self, votes: List[AgentVote], guardian_flags: List[str]) -> Dict:
        if "CRITICAL" in guardian_flags:
            return {
                "status": "BLOCKED",
                "reason": "GUARDIAN_CRITICAL_SECURITY_VIOLATION",
                "final_answer": None,
                "escalate": True,
                "primary_agent": None
            }

        agree_votes = [v for v in votes if v.vote == "AGREE"]

        if len(agree_votes) >= self.required_agreements:
            best = max(agree_votes, key=lambda x: x.confidence)
            return {
                "status": "CONSENSUS_REACHED",
                "agreements": len(agree_votes),
                "final_answer": best.answer,
                "escalate": False,
                "primary_agent": best.agent_id,
                "confidence": best.confidence
            }

        oracle_flags = [v for v in votes if v.agent_id == "oracle"]
        if oracle_flags and oracle_flags[0].flags and "HALLUCINATION" in oracle_flags[0].flags:
            return {
                "status": "HALLUCINATION_BLOCKED",
                "reason": "ORACLE_DETECTED_FACTUAL_ERROR",
                "escalate": True
            }

        return {
            "status": "NO_CONSENSUS",
            "reason": "INSUFFICIENT_AGENT_AGREEMENT",
            "escalate": True
        }
