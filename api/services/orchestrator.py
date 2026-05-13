import requests
import asyncio
import sys
from typing import Dict

sys.path.append('/app')
from consensus.pbft_consensus import ConsensusEngine, AgentVote
from consensus.vote_tally import VoteTally

AGENT_URLS = {
    "sage": "http://sage:5000/analyze",
    "guardian": "http://guardian:5000/analyze",
    "empath": "http://empath:5000/analyze",
    "oracle": "http://oracle:5000/analyze"
}


class AgentOrchestrator:
    def __init__(self):
        self.consensus = ConsensusEngine(total_agents=4, fault_tolerance=1)
        self.tally = VoteTally()

    async def call_agent(self, name: str, payload: dict):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.post(AGENT_URLS[name], json=payload, timeout=15)
            )
            return response.json()
        except Exception as e:
            return {"agent": name, "error": str(e), "output": {}}

    async def process(self, query: str, session_id: str):
        # Phase 1: Independent analysis (SAGE + EMPATH can run in parallel)
        sage_task = self.call_agent("sage", {"query": query, "session_id": session_id})
        empath_task = self.call_agent("empath", {"query": query, "session_id": session_id})

        sage_result, empath_result = await asyncio.gather(sage_task, empath_task)

        sage_answer = sage_result.get("output", {}).get("answer", "")

        # Phase 2: Security & Fact Check (depends on SAGE output)
        guardian_task = self.call_agent("guardian", {
            "query": query,
            "session_id": session_id,
            "proposed_answer": sage_answer
        })

        oracle_task = self.call_agent("oracle", {
            "query": query,
            "session_id": session_id,
            "sage_answer": sage_answer,
            "context": "\n".join(sage_result.get("output", {}).get("sources", []))
        })

        guardian_result, oracle_result = await asyncio.gather(guardian_task, oracle_task)

        # Prepare answers for semantic agreement tally
        answers = [
            sage_answer,
            sage_answer,
            sage_answer,
            oracle_result.get("output", {}).get("oracle_answer", sage_answer)
        ]

        agreement_votes = self.tally.calculate_agreement(answers)

        # Build structured votes for consensus engine
        agent_votes = [
            AgentVote(
                agent_id="sage",
                answer=sage_answer,
                confidence=sage_result.get("output", {}).get("confidence", 50),
                vote=agreement_votes[0],
                flags=[]
            ),
            AgentVote(
                agent_id="guardian",
                answer=sage_answer,
                confidence=100 if guardian_result.get("output", {}).get("status") == "SAFE" else 0,
                vote=agreement_votes[1],
                flags=guardian_result.get("output", {}).get("violations", [])
            ),
            AgentVote(
                agent_id="empath",
                answer=sage_answer,
                confidence=100 - empath_result.get("output", {}).get("urgency", 5) * 10,
                vote=agreement_votes[2],
                flags=["CHURN_RISK"] if empath_result.get("output", {}).get("churn_risk") else []
            ),
            AgentVote(
                agent_id="oracle",
                answer=oracle_result.get("output", {}).get("oracle_answer", sage_answer),
                confidence=100 if not oracle_result.get("output", {}).get("hallucination_flag") else 0,
                vote=agreement_votes[3],
                flags=["HALLUCINATION"] if oracle_result.get("output", {}).get("hallucination_flag") else []
            )
        ]

        guardian_flags = guardian_result.get("output", {}).get("violations", [])
        if guardian_result.get("output", {}).get("status") == "CRITICAL":
            guardian_flags.append("CRITICAL")

        result = self.consensus.reach_consensus(agent_votes, guardian_flags)

        votes_dict = {
            "sage": sage_result.get("output", {}),
            "guardian": guardian_result.get("output", {}),
            "empath": empath_result.get("output", {}),
            "oracle": oracle_result.get("output", {})
        }

        return {
            "final_answer": result.get("final_answer"),
            "consensus_status": result.get("status"),
            "consensus_reason": result.get("reason"),
            "escalate": result.get("escalate", False),
            "votes": votes_dict,
            "primary_agent": result.get("primary_agent"),
            "confidence": result.get("confidence")
        }
