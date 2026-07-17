from __future__ import annotations

import asyncio
import json
import os
from typing import Awaitable, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from agents.empath.service import EmpathService
from agents.guardian.service import GuardianService
from agents.oracle.service import OracleService
from agents.sage.service import SageService
from api.schemas import ChatResponse
from api.services.blockchain_logger import BlockchainLogger
from api.services.storage import SQLiteRepository
from api.services.tone_adapter import ToneAdapter
from consensus.risk_engine import RiskAwareDecisionEngine
from shared.schemas import (
    AgentFinding,
    AgentState,
    AuditOutcome,
    AuditStatus,
    DecisionState,
    GuardianOutput,
)


T = TypeVar("T")


class _InvalidAgentOutputError(TypeError):
    pass


def _validated_output(output: object) -> tuple[object, dict]:
    if not isinstance(output, BaseModel):
        raise _InvalidAgentOutputError
    return output, output.model_dump(mode="json")


class AgentOrchestrator:
    def __init__(
        self,
        *,
        sage: SageService | None = None,
        guardian: GuardianService | None = None,
        empath: EmpathService | None = None,
        oracle: OracleService | None = None,
        decision_engine: RiskAwareDecisionEngine | None = None,
        tone_adapter: ToneAdapter | None = None,
        repository: SQLiteRepository | None = None,
        blockchain: BlockchainLogger | None = None,
    ):
        self.sage = sage or SageService()
        self.guardian = guardian or GuardianService()
        self.empath = empath or EmpathService()
        self.oracle = oracle or OracleService()
        self.decision_engine = decision_engine or RiskAwareDecisionEngine()
        self.tone_adapter = tone_adapter or ToneAdapter()
        self.repository = repository or SQLiteRepository()
        self.blockchain = blockchain or BlockchainLogger()
        self.agent_timeout = float(os.getenv("AGENT_TIMEOUT_SECONDS", "15"))

    async def process(self, query: str, session_id: str) -> ChatResponse:
        states: dict[str, AgentState] = {}
        findings: dict[str, AgentFinding] = {}

        sage_output, sage_finding = await self._run_async(
            "sage", lambda: self.sage.analyze(query)
        )
        states["sage"] = sage_finding.state
        findings["sage"] = sage_finding
        draft = sage_output.answer if sage_output else ""
        sources = sage_output.citations if sage_output else []

        guardian_task = self._run_async(
            "guardian", lambda: self.guardian.analyze(query, draft)
        )
        empath_task = self._run_sync("empath", lambda: self.empath.analyze(query))
        oracle_task = self._run_sync(
            "oracle", lambda: self.oracle.analyze(draft, sources)
        )
        (guardian_output, guardian_finding), (
            empath_output,
            empath_finding,
        ), (oracle_output, oracle_finding) = await asyncio.gather(
            guardian_task, empath_task, oracle_task
        )

        states.update(
            {
                "guardian": guardian_finding.state,
                "empath": empath_finding.state,
                "oracle": oracle_finding.state,
            }
        )
        findings.update(
            {
                "guardian": guardian_finding,
                "empath": empath_finding,
                "oracle": oracle_finding,
            }
        )

        decision = self.decision_engine.decide(
            states=states,
            sage=sage_output,
            guardian=guardian_output,
            empath=empath_output,
            oracle=oracle_output,
        )
        factual_answer = draft or self._unavailable_message()
        final_answer = self._select_response(
            decision.state,
            decision.response_source,
            factual_answer,
            guardian_output,
        )
        if decision.rewrite_tone and decision.response_source == "draft":
            final_answer = self.tone_adapter.adapt(final_answer, empath_output)

        serialized_findings = {
            name: finding.model_dump(mode="json") for name, finding in findings.items()
        }
        escalation_ticket_id: str | None = None
        if decision.create_escalation and decision.priority:
            try:
                escalation = await asyncio.to_thread(
                    self.repository.create_escalation,
                    session_id=session_id,
                    query=query,
                    draft_answer=factual_answer,
                    reason=decision.reason,
                    priority=decision.priority,
                    agent_findings=serialized_findings,
                )
                escalation_ticket_id = escalation.ticket_id
                final_answer += (
                    f"\n\nPrototype human-review ticket: {escalation_ticket_id}. "
                    "No bank employee is contacted automatically."
                )
            except Exception:
                decision = decision.model_copy(
                    update={
                        "state": DecisionState.SYSTEM_UNAVAILABLE,
                        "reason": "The prototype review record could not be persisted.",
                        "create_escalation": False,
                        "priority": None,
                        "response_source": "unavailable",
                    }
                )
                final_answer = self._unavailable_message()

        trace = {
            "session_id": session_id,
            "query": query,
            "decision_state": decision.state.value,
            "decision_reason": decision.reason,
            "agent_findings": serialized_findings,
            "citations": [citation.model_dump(mode="json") for citation in sources],
            "escalation_ticket_id": escalation_ticket_id,
        }
        pending_audit = AuditOutcome(
            status=(
                AuditStatus.PENDING
                if self.blockchain.enabled
                else AuditStatus.DISABLED
            ),
            network=getattr(self.blockchain, "network", None),
            explorer_url=getattr(self.blockchain, "explorer_url", None),
        )
        decision_id: str | None = None
        try:
            decision_id = await asyncio.to_thread(
                self.repository.create_decision,
                session_id=session_id,
                query=query,
                factual_answer=factual_answer,
                final_answer=final_answer,
                decision_state=decision.state.value,
                decision_reason=decision.reason,
                agent_findings=serialized_findings,
                citations=[citation.model_dump(mode="json") for citation in sources],
                audit=pending_audit.model_dump(mode="json"),
                escalation_ticket_id=escalation_ticket_id,
            )
            # A session can contain identical repeated messages. Include the
            # per-request SQLite identifier in the canonical chain trace so an
            # optional immutable ledger record never collides on a retry.
            trace["decision_id"] = decision_id
        except Exception:
            pending_audit = AuditOutcome(
                status=AuditStatus.FAILED,
                error="Primary SQLite decision audit could not be persisted.",
            )
            if decision.state in {
                DecisionState.APPROVED,
                DecisionState.APPROVED_WITH_REWRITE,
            }:
                decision = decision.model_copy(
                    update={
                        "state": DecisionState.SYSTEM_UNAVAILABLE,
                        "reason": "The decision audit could not be persisted.",
                        "response_source": "unavailable",
                        "rewrite_tone": False,
                    }
                )
                final_answer = self._unavailable_message()

        audit = pending_audit
        if decision_id is not None:
            audit = await asyncio.to_thread(
                self.blockchain.log_decision,
                session_id=session_id,
                status=decision.state.value,
                trace=trace,
            )
            try:
                await asyncio.to_thread(
                    self.repository.update_decision_audit,
                    decision_id,
                    audit.model_dump(mode="json"),
                )
            except Exception:
                audit = AuditOutcome(
                    status=AuditStatus.FAILED,
                    error=(
                        "The optional audit outcome could not be persisted to the "
                        "primary SQLite decision record."
                    ),
                    network=audit.network,
                    explorer_url=audit.explorer_url,
                )

        public_findings = self._public_findings(findings, decision.response_source)
        public_factual_answer = (
            factual_answer if decision.response_source == "draft" else ""
        )
        agent_votes = {
            name: (finding.output or {"state": finding.state.value, "error": finding.error})
            for name, finding in public_findings.items()
        }
        return ChatResponse(
            session_id=session_id,
            query=query,
            final_answer=final_answer,
            factual_answer=public_factual_answer,
            decision_state=decision.state,
            decision_reason=decision.reason,
            citations=sources,
            agent_findings=public_findings,
            completed_agents=[
                name for name, state in states.items() if state is AgentState.AVAILABLE
            ],
            escalation_ticket_id=escalation_ticket_id,
            audit=audit,
            consensus_status=decision.state.value,
            consensus_reason=decision.reason,
            agent_votes=agent_votes,
            escalate=decision.create_escalation,
            blockchain_tx=audit.transaction_hash,
            primary_agent=(
                "sage" if decision.response_source == "draft" else None
            ),
            confidence=sage_output.confidence if sage_output else None,
        )

    def readiness(self) -> tuple[bool, dict[str, dict[str, object]]]:
        dependencies = {
            "sage": {"ready": self.sage.ready},
            "guardian": {"ready": self.guardian.ready},
            "empath": {"ready": self.empath.ready},
            "oracle": {"ready": self.oracle.ready},
            "sqlite": {"ready": self.repository.health()},
            "blockchain": {
                "ready": self.blockchain.configured,
                "required": False,
                "enabled": self.blockchain.enabled,
            },
        }
        required_ready = all(
            dependency["ready"]
            for dependency in dependencies.values()
            if dependency.get("required", True)
        )
        return required_ready, dependencies

    async def _run_async(
        self, name: str, function: Callable[[], Awaitable[T]]
    ) -> tuple[T | None, AgentFinding]:
        try:
            output = await asyncio.wait_for(function(), timeout=self.agent_timeout)
            output, serialized = _validated_output(output)
            return output, AgentFinding(
                state=AgentState.AVAILABLE,
                output=serialized,
            )
        except TimeoutError:
            return None, AgentFinding(
                state=AgentState.TIMEOUT, error=f"{name} timed out"
            )
        except RuntimeError:
            return None, AgentFinding(
                state=AgentState.DEPENDENCY_UNAVAILABLE,
                error=f"{name} dependency unavailable",
            )
        except (ValidationError, json.JSONDecodeError, _InvalidAgentOutputError):
            return None, AgentFinding(
                state=AgentState.INVALID_OUTPUT, error=f"{name} returned invalid output"
            )
        except Exception:
            return None, AgentFinding(
                state=AgentState.MODEL_ERROR, error=f"{name} analysis failed"
            )

    async def _run_sync(
        self, name: str, function: Callable[[], T]
    ) -> tuple[T | None, AgentFinding]:
        try:
            output = await asyncio.wait_for(
                asyncio.to_thread(function), timeout=self.agent_timeout
            )
            output, serialized = _validated_output(output)
            return output, AgentFinding(
                state=AgentState.AVAILABLE,
                output=serialized,
            )
        except TimeoutError:
            return None, AgentFinding(
                state=AgentState.TIMEOUT, error=f"{name} timed out"
            )
        except RuntimeError:
            return None, AgentFinding(
                state=AgentState.DEPENDENCY_UNAVAILABLE,
                error=f"{name} dependency unavailable",
            )
        except (ValidationError, json.JSONDecodeError, _InvalidAgentOutputError):
            return None, AgentFinding(
                state=AgentState.INVALID_OUTPUT, error=f"{name} returned invalid output"
            )
        except Exception:
            return None, AgentFinding(
                state=AgentState.MODEL_ERROR, error=f"{name} analysis failed"
            )

    @staticmethod
    def _select_response(
        state: DecisionState,
        response_source: str,
        factual_answer: str,
        guardian: GuardianOutput | None,
    ) -> str:
        if response_source == "security":
            return guardian.safe_guidance if guardian and guardian.safe_guidance else (
                "I cannot safely assist with that request. Use an official support channel."
            )
        if response_source == "clarification":
            return (
                "I cannot safely approve an answer because the approved policy evidence "
                "is missing or does not support every material claim."
            )
        if response_source == "unavailable":
            return AgentOrchestrator._unavailable_message()
        return factual_answer

    @staticmethod
    def _public_findings(
        findings: dict[str, AgentFinding], response_source: str
    ) -> dict[str, AgentFinding]:
        """Withhold unapproved model prose while retaining decision transparency."""
        if response_source == "draft":
            return findings

        public: dict[str, AgentFinding] = {}
        for name, finding in findings.items():
            payload = finding.model_dump(mode="json")
            output = payload.get("output")
            if name == "sage" and isinstance(output, dict) and "answer" in output:
                output["answer"] = "[Draft withheld because it was not approved for customer display.]"
            if name == "oracle" and isinstance(output, dict):
                claims = output.get("claims")
                if isinstance(claims, list):
                    for claim in claims:
                        if isinstance(claim, dict) and "claim" in claim:
                            claim["claim"] = "[Unapproved material claim withheld.]"
                unsupported = output.get("unsupported_claims")
                if isinstance(unsupported, list) and unsupported:
                    output["unsupported_claims"] = [
                        "The withheld draft contained unsupported material claims."
                    ]
            public[name] = AgentFinding.model_validate(payload)
        return public

    @staticmethod
    def _unavailable_message() -> str:
        return (
            "The support review pipeline is temporarily unavailable, so no answer was "
            "approved. Please try again or use an official support channel."
        )
