from __future__ import annotations

import pytest

from agents.empath.emotion_model import EmotionAnalyzer
from api.services.tone_adapter import ToneAdapter
from shared.schemas import EmpathOutput


FACTUAL_ANSWER = (
    "Standard customers must wait 7 business days for refund investigation "
    "[refund_policy_1]."
)


@pytest.mark.parametrize(
    ("message", "expected_emotion", "expected_tone"),
    [
        (
            "I called four times and no one helped with my refund.",
            "FRUSTRATED",
            "APOLOGETIC",
        ),
        (
            "My stolen card is being used immediately.",
            "ANXIOUS",
            "EMPATHETIC_URGENT",
        ),
        ("I do not understand how to block my card.", "CONFUSED", "PATIENT"),
    ],
)
def test_emotion_analysis_selects_response_strategy(
    message: str, expected_emotion: str, expected_tone: str
) -> None:
    output = EmotionAnalyzer().analyze(message)
    assert output.emotion == expected_emotion
    assert output.recommended_tone == expected_tone


def test_tone_adaptation_preserves_verified_body_byte_for_byte() -> None:
    empath = EmotionAnalyzer().analyze(
        "I called four times and no one helped with my refund."
    )
    adapted = ToneAdapter().adapt(FACTUAL_ANSWER, empath)

    assert adapted.endswith(FACTUAL_ANSWER)
    assert adapted.count(FACTUAL_ANSWER) == 1
    assert "7 business days" in adapted
    assert "[refund_policy_1]" in adapted
    assert ToneAdapter.preserves_facts(FACTUAL_ANSWER, adapted) is True


def test_neutral_tone_does_not_modify_answer() -> None:
    empath = EmotionAnalyzer().analyze("What is the refund timeline?")
    adapted = ToneAdapter().adapt(FACTUAL_ANSWER, empath)
    assert adapted == FACTUAL_ANSWER


def test_missing_empath_output_uses_neutral_fallback() -> None:
    assert ToneAdapter().adapt(FACTUAL_ANSWER, None) == FACTUAL_ANSWER


def test_preserves_facts_rejects_rewritten_or_removed_body() -> None:
    altered = "All refunds are instant [refund_policy_1]."
    assert ToneAdapter.preserves_facts(FACTUAL_ANSWER, altered) is False


def test_adapter_only_uses_declared_presentation_prefix() -> None:
    empath = EmpathOutput(
        emotion="FRUSTRATED",
        urgency=8,
        sentiment_label="NEGATIVE",
        sentiment_score=0.9,
        recommended_tone="APOLOGETIC",
        churn_risk=True,
    )
    adapted = ToneAdapter().adapt(FACTUAL_ANSWER, empath)
    prefix, body = adapted.split("\n\n", 1)
    assert prefix == "I'm sorry this situation has been frustrating."
    assert body == FACTUAL_ANSWER
