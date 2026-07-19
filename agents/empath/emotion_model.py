from __future__ import annotations

import re

from shared.schemas import EmpathOutput


class EmotionAnalyzer:
    """Transparent lexicon-based analysis suitable for deterministic demos."""

    _frustrated = {
        "angry", "furious", "frustrated", "terrible", "worst", "scam", "cheat",
        "lawsuit", "called four times", "still blocked", "no one helped", "asked twice",
        "ridiculous", "tired of", "useless", "nobody", "waited on hold forever",
        "canned replies", "extremely annoyed", "maddening", "fed up", "conflicting answers",
    }
    _urgent = {
        "urgent", "asap", "emergency", "hospital", "medical",
        "stolen", "hacked", "fraud", "unauthorized", "cannot access", "blocked",
        "immediate action",
    }
    _positive = {"happy", "thanks", "thank you", "great", "excellent", "love"}
    _confused = {"confused", "don't understand", "do not understand", "help", "how do i"}
    _high_risk = {"hospital", "emergency", "stolen", "hacked", "fraud", "unauthorized", "scam"}

    def analyze(self, text: str) -> EmpathOutput:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        frustration_hits = self._matches(normalized, self._frustrated)
        urgency_hits = self._matches(normalized, self._urgent)
        immediate_request = bool(
            re.search(
                r"\b(?:i need|please|act|help|block (?:it|this|the\s+\w+))\b"
                r".{0,80}\bimmediately\b",
                normalized,
            )
        )
        if immediate_request:
            urgency_hits.append("immediately")
        positive_hits = self._matches(normalized, self._positive)
        confused_hits = self._matches(normalized, self._confused)

        if frustration_hits:
            emotion = "FRUSTRATED"
        elif confused_hits:
            emotion = "CONFUSED"
        elif positive_hits:
            emotion = "SATISFIED"
        elif urgency_hits:
            emotion = "ANXIOUS"
        else:
            emotion = "NEUTRAL"

        if immediate_request or any(term in normalized for term in {"emergency", "hospital"}):
            urgency = 10
        elif urgency_hits:
            urgency = 9
        elif frustration_hits:
            urgency = 8
        elif confused_hits:
            urgency = 5
        elif positive_hits:
            urgency = 2
        else:
            urgency = 4

        negative_weight = len(frustration_hits) + len(urgency_hits)
        if negative_weight:
            sentiment_label = "NEGATIVE"
            sentiment_score = min(0.99, 0.65 + (negative_weight * 0.08))
        elif positive_hits:
            sentiment_label = "POSITIVE"
            sentiment_score = min(0.99, 0.7 + (len(positive_hits) * 0.08))
        else:
            sentiment_label = "NEUTRAL"
            sentiment_score = 0.5

        if urgency >= 9:
            tone = "EMPATHETIC_URGENT"
        elif emotion == "FRUSTRATED":
            tone = "APOLOGETIC"
        elif emotion == "CONFUSED":
            tone = "PATIENT"
        elif emotion == "SATISFIED":
            tone = "FRIENDLY"
        else:
            tone = "PROFESSIONAL"

        requires_urgent_review = urgency >= 9 and any(
            term in normalized for term in self._high_risk
        )
        return EmpathOutput(
            emotion=emotion,
            urgency=urgency,
            sentiment_label=sentiment_label,
            sentiment_score=round(sentiment_score, 3),
            recommended_tone=tone,
            churn_risk=emotion == "FRUSTRATED" and urgency >= 8,
            requires_urgent_review=requires_urgent_review,
        )

    @staticmethod
    def _matches(text: str, terms: set[str]) -> list[str]:
        return sorted(term for term in terms if term in text)
