from __future__ import annotations

import pytest

from agents.oracle.fact_checker import FactChecker
from shared.schemas import OracleRecommendation, SourceRecord


def _source(document_id: str, text: str) -> SourceRecord:
    return SourceRecord(
        document_id=document_id,
        chunk_id=f"{document_id}:0",
        text=text,
        metadata={"approved": True},
        distance_or_similarity=0.9,
    )


REFUND_SOURCE = _source(
    "refund_policy_1",
    "Standard customers must wait 7 business days for refund investigation. "
    "Premium customers receive instant refund up to 10000.",
)


def test_exact_policy_claim_is_supported_with_source_id() -> None:
    output = FactChecker().verify(
        "Standard customers must wait 7 business days for refund investigation.",
        [REFUND_SOURCE],
    )

    assert output.overall_supported is True
    assert output.unsupported_claims == []
    assert output.recommendation is OracleRecommendation.APPROVE
    assert len(output.claims) == 1
    assert output.claims[0].supported is True
    assert output.claims[0].source_ids == ["refund_policy_1"]


def test_material_claim_missing_from_evidence_is_not_approved() -> None:
    output = FactChecker().verify(
        "Every refund is guaranteed within one hour.",
        [REFUND_SOURCE],
    )

    assert output.overall_supported is False
    assert output.unsupported_claims == ["Every refund is guaranteed within one hour."]
    assert output.recommendation is OracleRecommendation.ESCALATE
    assert output.claims[0].source_ids == []


def test_numeric_contradiction_is_rejected_even_with_similar_words() -> None:
    output = FactChecker().verify(
        "Standard customers must wait 2 business days for refund investigation.",
        [REFUND_SOURCE],
    )

    claim = output.claims[0]
    assert claim.supported is False
    assert claim.support_score < FactChecker.support_threshold
    assert output.overall_supported is False


def test_claims_are_verified_individually() -> None:
    output = FactChecker().verify(
        "Standard customers must wait 7 business days for refund investigation.\n"
        "All customers receive a free replacement card the same day.",
        [REFUND_SOURCE],
    )

    assert [claim.supported for claim in output.claims] == [True, False]
    assert output.unsupported_claims == [
        "All customers receive a free replacement card the same day."
    ]
    assert output.overall_supported is False


def test_claim_without_retrieved_evidence_requests_clarification() -> None:
    output = FactChecker().verify("Home loans have a fixed 4 percent rate.", [])

    assert output.overall_supported is False
    assert output.recommendation is OracleRecommendation.CLARIFY
    assert output.claims[0].supported is False
    assert output.claims[0].reason == "No approved evidence was retrieved."


def test_empty_draft_is_not_treated_as_verified() -> None:
    output = FactChecker().verify("", [REFUND_SOURCE])

    assert output.claims == []
    assert output.overall_supported is False
    assert output.recommendation is OracleRecommendation.ESCALATE


@pytest.mark.parametrize(
    "claim",
    [
        "Refund investigation is completed within 7 business days.",
        "Premium customers are denied instant refunds up to 10000.",
        "Premium customers forfeit instant refunds up to 10000.",
        "Refunds without investigation for amounts above 50000.",
    ],
)
def test_material_qualifier_or_polarity_changes_are_rejected(claim: str) -> None:
    output = FactChecker().verify(claim, [REFUND_SOURCE])

    assert output.overall_supported is False
    assert output.unsupported_claims == [claim]
    assert output.claims[0].supported is False


def test_one_word_material_claim_is_not_dropped() -> None:
    output = FactChecker().verify(
        "Standard customers must wait 7 business days for refund investigation. "
        "Guaranteed.",
        [REFUND_SOURCE],
    )

    assert [claim.claim for claim in output.claims] == [
        "Standard customers must wait 7 business days for refund investigation.",
        "Guaranteed.",
    ]
    assert output.overall_supported is False
    assert output.unsupported_claims == ["Guaranteed."]
