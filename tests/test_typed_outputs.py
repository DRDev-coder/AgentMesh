from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from api.services.orchestrator import AgentOrchestrator
from shared.schemas import (
    AgentState,
    ClaimVerification,
    EmpathOutput,
    GuardianOutput,
    OracleOutput,
    SageOutput,
    SourceRecord,
)


def source_record(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "document_id": "refund_policy_1",
        "chunk_id": "refund_policy_1:0",
        "text": "Standard refunds require seven business days for investigation.",
        "metadata": {"approved": True},
        "distance_or_similarity": 0.9,
    }
    values.update(overrides)
    return SourceRecord.model_validate(values)


def test_source_record_accepts_complete_structured_provenance() -> None:
    source = source_record()
    assert source.document_id == "refund_policy_1"
    assert source.metadata["approved"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {
            "document_id": "refund_policy_1",
            "chunk_id": "refund_policy_1:0",
            "text": "policy",
            "metadata": {},
            "distance_or_similarity": 1.1,
        },
        {
            "document_id": "refund_policy_1",
            "chunk_id": "refund_policy_1:0",
            "text": "policy",
            "metadata": {},
            "distance_or_similarity": 0.8,
            "model_supplied_source": True,
        },
    ],
)
def test_source_record_rejects_invalid_or_extra_fields(payload: dict) -> None:
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(payload)


def test_sage_output_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        SageOutput(
            answer="answer",
            confidence=101,
            citations=[],
            retrieval_quality=0.5,
            insufficient_data=False,
            generation_mode="deterministic",
        )


def test_guardian_output_rejects_unknown_status_and_extra_fields() -> None:
    payload = {
        "status": "MAYBE",
        "violations": [],
        "action": "allow",
        "reasoning": "none",
        "confidence": 50,
        "blocking": False,
        "deterministic_violations": [],
        "semantic_violations": [],
        "safe_guidance": None,
        "untrusted": "value",
    }
    with pytest.raises(ValidationError):
        GuardianOutput.model_validate(payload)


def test_empath_output_rejects_invalid_urgency() -> None:
    with pytest.raises(ValidationError):
        EmpathOutput(
            emotion="neutral",
            urgency=11,
            sentiment_label="neutral",
            sentiment_score=0.5,
            recommended_tone="neutral",
            churn_risk=False,
        )


def test_oracle_claim_requires_claim_level_reason_and_source_ids() -> None:
    with pytest.raises(ValidationError):
        ClaimVerification.model_validate(
            {
                "claim": "Refunds take seven days",
                "supported": True,
                "source_ids": ["refund_policy_1"],
                "support_score": 0.9,
            }
        )


def test_oracle_output_validates_nested_claims() -> None:
    output = OracleOutput(
        claims=[
            ClaimVerification(
                claim="Standard refunds take seven business days for investigation.",
                supported=True,
                source_ids=["refund_policy_1"],
                reason="The approved policy states this timeline.",
                support_score=1.0,
            )
        ],
        overall_supported=True,
        unsupported_claims=[],
        confidence=100,
        recommendation="APPROVE",
    )
    assert output.claims[0].supported is True


def test_agent_state_is_a_closed_enum() -> None:
    assert AgentState("AVAILABLE") is AgentState.AVAILABLE
    with pytest.raises(ValueError):
        AgentState("UNKNOWN")


def test_async_component_non_model_output_is_reported_as_invalid() -> None:
    async def invalid_component() -> dict:
        return {"untyped": True}

    output, finding = asyncio.run(
        AgentOrchestrator()._run_async("test", invalid_component)
    )

    assert output is None
    assert finding.state is AgentState.INVALID_OUTPUT
    assert finding.error == "test returned invalid output"


def test_sync_component_non_model_output_is_reported_as_invalid() -> None:
    output, finding = asyncio.run(
        AgentOrchestrator()._run_sync("test", lambda: {"untyped": True})
    )

    assert output is None
    assert finding.state is AgentState.INVALID_OUTPUT
    assert finding.error == "test returned invalid output"
