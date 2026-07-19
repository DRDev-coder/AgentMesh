from __future__ import annotations

from consensus.risk_engine import RiskAwareDecisionEngine
from shared.schemas import (
    AgentState,
    ClaimVerification,
    DecisionState,
    EmpathOutput,
    EscalationPriority,
    GuardianAction,
    GuardianOutput,
    GuardianStatus,
    OracleOutput,
    OracleRecommendation,
    SageOutput,
    SourceRecord,
)


def _source() -> SourceRecord:
    return SourceRecord(
        document_id="refund_policy_1",
        chunk_id="refund_policy_1:0",
        text="Standard customers must wait 7 business days for refund investigation.",
        metadata={"approved": True},
        distance_or_similarity=0.9,
    )


def _sage(*, insufficient: bool = False) -> SageOutput:
    return SageOutput(
        answer="Standard customers must wait 7 business days for refund investigation.",
        confidence=90,
        citations=[] if insufficient else [_source()],
        retrieval_quality=0 if insufficient else 0.9,
        insufficient_data=insufficient,
        generation_mode="deterministic",
    )


def _guardian(status: GuardianStatus = GuardianStatus.SAFE) -> GuardianOutput:
    blocking = status is GuardianStatus.CRITICAL
    action = (
        GuardianAction.BLOCK
        if blocking
        else GuardianAction.ESCALATE
        if status is GuardianStatus.WARNING
        else GuardianAction.ALLOW
    )
    return GuardianOutput(
        status=status,
        violations=["RISK"] if status is not GuardianStatus.SAFE else [],
        action=action,
        reasoning="deterministic test finding",
        confidence=100,
        blocking=blocking,
        deterministic_violations=["RISK"] if blocking else [],
        semantic_violations=[],
    )


def _empath(
    *, emotion: str = "NEUTRAL", urgency: int = 4, urgent_review: bool = False
) -> EmpathOutput:
    return EmpathOutput(
        emotion=emotion,
        urgency=urgency,
        sentiment_label="NEGATIVE" if emotion != "NEUTRAL" else "NEUTRAL",
        sentiment_score=0.8 if emotion != "NEUTRAL" else 0.5,
        recommended_tone="APOLOGETIC" if emotion == "FRUSTRATED" else "PROFESSIONAL",
        churn_risk=emotion == "FRUSTRATED",
        requires_urgent_review=urgent_review,
    )


def _oracle(*, unsupported: bool = False) -> OracleOutput:
    claim = "Standard customers must wait 7 business days for refund investigation."
    return OracleOutput(
        claims=[
            ClaimVerification(
                claim=claim,
                supported=not unsupported,
                source_ids=[] if unsupported else ["refund_policy_1"],
                reason="test verification",
                support_score=0 if unsupported else 1,
            )
        ],
        overall_supported=not unsupported,
        unsupported_claims=[claim] if unsupported else [],
        confidence=0 if unsupported else 100,
        recommendation=(
            OracleRecommendation.ESCALATE
            if unsupported
            else OracleRecommendation.APPROVE
        ),
    )


def _states(**overrides: AgentState) -> dict[str, AgentState]:
    states = {name: AgentState.AVAILABLE for name in ("sage", "guardian", "empath", "oracle")}
    states.update(overrides)
    return states


def _decide(
    *,
    states: dict[str, AgentState] | None = None,
    sage: SageOutput | None = None,
    guardian: GuardianOutput | None = None,
    empath: EmpathOutput | None = None,
    oracle: OracleOutput | None = None,
):
    return RiskAwareDecisionEngine().decide(
        states=states or _states(),
        sage=_sage() if sage is None else sage,
        guardian=_guardian() if guardian is None else guardian,
        empath=_empath() if empath is None else empath,
        oracle=_oracle() if oracle is None else oracle,
    )


def test_approved_state_for_safe_grounded_neutral_answer() -> None:
    decision = _decide()
    assert decision.state is DecisionState.APPROVED
    assert decision.create_escalation is False
    assert decision.response_source == "draft"


def test_approved_with_rewrite_state_for_frustrated_customer() -> None:
    decision = _decide(empath=_empath(emotion="FRUSTRATED", urgency=8))
    assert decision.state is DecisionState.APPROVED_WITH_REWRITE
    assert decision.rewrite_tone is True


def test_needs_clarification_state_for_unsupported_material_claim() -> None:
    decision = _decide(oracle=_oracle(unsupported=True))
    assert decision.state is DecisionState.NEEDS_CLARIFICATION
    assert decision.create_escalation is True
    assert decision.priority is EscalationPriority.MEDIUM


def test_oracle_with_no_verified_claims_cannot_approve() -> None:
    oracle = OracleOutput(
        claims=[],
        overall_supported=False,
        unsupported_claims=[],
        confidence=0,
        recommendation=OracleRecommendation.ESCALATE,
    )

    decision = _decide(oracle=oracle)

    assert decision.state is DecisionState.NEEDS_CLARIFICATION
    assert decision.create_escalation is True


def test_needs_clarification_state_for_insufficient_retrieval() -> None:
    decision = _decide(sage=_sage(insufficient=True), oracle=_oracle())
    assert decision.state is DecisionState.NEEDS_CLARIFICATION
    assert decision.response_source == "clarification"


def test_blocked_state_has_precedence_over_oracle_failure() -> None:
    states = _states(oracle=AgentState.TIMEOUT)
    decision = _decide(
        states=states,
        guardian=_guardian(GuardianStatus.CRITICAL),
        oracle=None,
    )
    assert decision.state is DecisionState.BLOCKED
    assert decision.priority is EscalationPriority.CRITICAL
    assert decision.response_source == "security"


def test_escalated_state_for_security_warning() -> None:
    decision = _decide(guardian=_guardian(GuardianStatus.WARNING))
    assert decision.state is DecisionState.ESCALATED
    assert decision.priority is EscalationPriority.HIGH


def test_escalated_state_for_urgent_high_risk_customer() -> None:
    decision = _decide(
        empath=_empath(emotion="ANXIOUS", urgency=10, urgent_review=True)
    )
    assert decision.state is DecisionState.ESCALATED
    assert decision.rewrite_tone is True


def test_system_unavailable_state_when_sage_is_unavailable() -> None:
    decision = _decide(states=_states(sage=AgentState.DEPENDENCY_UNAVAILABLE))
    assert decision.state is DecisionState.SYSTEM_UNAVAILABLE
    assert decision.create_escalation is True
    assert decision.response_source == "unavailable"


def test_guardian_unavailable_fails_closed() -> None:
    decision = _decide(states=_states(guardian=AgentState.TIMEOUT))
    assert decision.state is DecisionState.ESCALATED
    assert decision.priority is EscalationPriority.CRITICAL
    assert "failed closed" in decision.reason


def test_oracle_unavailable_never_claims_verified_approval() -> None:
    decision = _decide(states=_states(oracle=AgentState.INVALID_OUTPUT))
    assert decision.state is DecisionState.ESCALATED
    assert decision.create_escalation is True
    assert "not approved" in decision.reason


def test_empath_unavailable_degrades_to_neutral_without_blocking() -> None:
    decision = _decide(states=_states(empath=AgentState.MODEL_ERROR))
    assert decision.state is DecisionState.APPROVED
    assert decision.rewrite_tone is False


def test_precedence_is_independent_of_synthetic_agent_vote_counts() -> None:
    decision = _decide(guardian=_guardian(GuardianStatus.CRITICAL))
    assert decision.state is DecisionState.BLOCKED
    assert not hasattr(decision, "agreements")
