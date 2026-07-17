from __future__ import annotations

from shared.schemas import (
    AgentState,
    DecisionResult,
    DecisionState,
    EmpathOutput,
    EscalationPriority,
    GuardianOutput,
    GuardianStatus,
    OracleOutput,
    OracleRecommendation,
    SageOutput,
)


class RiskAwareDecisionEngine:
    """Deterministic policy with safety/evidence vetoes and safe degradation."""

    def decide(
        self,
        *,
        states: dict[str, AgentState],
        sage: SageOutput | None,
        guardian: GuardianOutput | None,
        empath: EmpathOutput | None,
        oracle: OracleOutput | None,
        escalation_threshold: int | None = None,
    ) -> DecisionResult:
        if states.get("sage") is not AgentState.AVAILABLE or sage is None:
            return DecisionResult(
                state=DecisionState.SYSTEM_UNAVAILABLE,
                reason="Policy retrieval or grounded response generation is unavailable.",
                create_escalation=True,
                priority=EscalationPriority.HIGH,
                response_source="unavailable",
            )

        if states.get("guardian") is not AgentState.AVAILABLE or guardian is None:
            return DecisionResult(
                state=DecisionState.ESCALATED,
                reason="Security review is unavailable; the pipeline failed closed.",
                create_escalation=True,
                priority=EscalationPriority.CRITICAL,
                response_source="unavailable",
            )

        if guardian.blocking or guardian.status is GuardianStatus.CRITICAL:
            return DecisionResult(
                state=DecisionState.BLOCKED,
                reason="A deterministic or validated critical security control blocked the request.",
                create_escalation=True,
                priority=EscalationPriority.CRITICAL,
                response_source="security",
            )

        if states.get("oracle") is not AgentState.AVAILABLE or oracle is None:
            return DecisionResult(
                state=DecisionState.ESCALATED,
                reason="Evidence verification is unavailable; the answer was not approved.",
                create_escalation=True,
                priority=EscalationPriority.HIGH,
                response_source="unavailable",
            )

        if (
            not oracle.overall_supported
            or oracle.unsupported_claims
            or oracle.recommendation is not OracleRecommendation.APPROVE
        ):
            return DecisionResult(
                state=DecisionState.NEEDS_CLARIFICATION,
                reason="One or more material draft claims are unsupported by retrieved policy evidence.",
                create_escalation=True,
                priority=EscalationPriority.MEDIUM,
                response_source="clarification",
            )

        if sage.insufficient_data or not sage.citations:
            return DecisionResult(
                state=DecisionState.NEEDS_CLARIFICATION,
                reason="No sufficiently relevant approved policy evidence was retrieved.",
                create_escalation=True,
                priority=EscalationPriority.MEDIUM,
                response_source="clarification",
            )

        if guardian.status is GuardianStatus.WARNING:
            return DecisionResult(
                state=DecisionState.ESCALATED,
                reason="A security or policy warning requires prototype human review.",
                create_escalation=True,
                priority=EscalationPriority.HIGH,
                response_source="draft",
                rewrite_tone=empath is not None,
            )

        if empath and empath.requires_urgent_review:
            return DecisionResult(
                state=DecisionState.ESCALATED,
                reason="The customer message indicates a high-risk urgent situation.",
                create_escalation=True,
                priority=EscalationPriority.HIGH,
                response_source="draft",
                rewrite_tone=True,
            )

        if empath and escalation_threshold is not None and (
            empath.urgency >= escalation_threshold
        ):
            return DecisionResult(
                state=DecisionState.ESCALATED,
                reason="The workspace escalation threshold was reached.",
                create_escalation=True,
                priority=EscalationPriority.HIGH,
                response_source="draft",
                rewrite_tone=True,
            )

        if states.get("empath") is AgentState.AVAILABLE and empath and (
            empath.urgency >= 7 or empath.emotion in {"FRUSTRATED", "CONFUSED", "ANXIOUS"}
        ):
            return DecisionResult(
                state=DecisionState.APPROVED_WITH_REWRITE,
                reason="The answer is safe and supported; presentation was adapted to the customer's tone.",
                response_source="draft",
                rewrite_tone=True,
            )

        return DecisionResult(
            state=DecisionState.APPROVED,
            reason="The answer is grounded in approved policy and passed security and claim verification.",
            response_source="draft",
        )
