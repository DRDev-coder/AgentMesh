from __future__ import annotations

import re

from shared.schemas import (
    ClaimVerification,
    OracleOutput,
    OracleRecommendation,
    SourceRecord,
)


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "help", "in", "is", "it", "of", "on", "or", "please", "policy", "support",
    "that", "the", "this", "to", "user", "users", "will", "with", "you", "your",
}

_MATERIAL_MARKERS = {
    "above",
    "all",
    "always",
    "below",
    "cannot",
    "complete",
    "completed",
    "denied",
    "deny",
    "every",
    "free",
    "guarantee",
    "guaranteed",
    "immediately",
    "instant",
    "maximum",
    "minimum",
    "must",
    "never",
    "no",
    "not",
    "only",
    "required",
    "requires",
    "should",
    "up",
    "within",
    "without",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    aliases = {
        "apps": "app",
        "canceled": "cancel",
        "cancelled": "cancel",
        "canceling": "cancel",
        "cancelling": "cancel",
        "cancellation": "cancel",
        "cancellations": "cancel",
        "charged": "charge",
        "charges": "charge",
        "closes": "close",
        "details": "detail",
        "items": "item",
        "payments": "payment",
        "purchases": "purchase",
        "refunded": "refund",
        "refundable": "refund",
        "refunds": "refund",
        "subscriptions": "subscription",
    }
    return {
        aliases.get(word, word)
        for word in words
        if word not in _STOP_WORDS and len(word) > 1
    }


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _material_markers(text: str) -> set[str]:
    aliases = {
        "above": "LIMIT_ABOVE",
        "all": "UNIVERSAL",
        "always": "UNIVERSAL",
        "below": "LIMIT_BELOW",
        "cannot": "NEGATION",
        "complete": "COMPLETION",
        "completed": "COMPLETION",
        "denied": "NEGATION",
        "deny": "NEGATION",
        "every": "UNIVERSAL",
        "free": "FREE",
        "guarantee": "GUARANTEE",
        "guaranteed": "GUARANTEE",
        "immediately": "IMMEDIATE",
        "instant": "IMMEDIATE",
        "maximum": "MAXIMUM",
        "minimum": "MINIMUM",
        "must": "REQUIREMENT",
        "never": "NEGATION",
        "no": "NEGATION",
        "not": "NEGATION",
        "only": "REQUIREMENT",
        "required": "REQUIREMENT",
        "requires": "REQUIREMENT",
        "should": "RECOMMENDATION",
        "up": "LIMIT_UP_TO",
        "within": "WITHIN",
        "without": "NEGATION",
    }
    markers = set(re.findall(r"[a-z0-9]+", text.lower())) & _MATERIAL_MARKERS
    return {aliases[marker] for marker in markers}


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]


def _strip_citation_markers(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", "", text).strip()
    return re.sub(r"\s+([.!?])", r"\1", text)


class FactChecker:
    """Verifies extracted draft claims against application-controlled evidence.

    This deliberately uses transparent lexical/numeric support checks. It does
    not present semantic similarity as proof of truth.
    """

    support_threshold = 0.62

    def verify(self, answer: str, sources: list[SourceRecord]) -> OracleOutput:
        claims = self.extract_claims(answer)
        verified = [self.verify_claim(claim, sources) for claim in claims]
        unsupported = [item.claim for item in verified if not item.supported]
        overall_supported = bool(verified) and not unsupported

        if overall_supported:
            recommendation = OracleRecommendation.APPROVE
        elif not sources:
            recommendation = OracleRecommendation.CLARIFY
        else:
            recommendation = OracleRecommendation.ESCALATE

        confidence = (
            sum(item.support_score for item in verified) / len(verified) * 100
            if verified
            else 0.0
        )
        return OracleOutput(
            claims=verified,
            overall_supported=overall_supported,
            unsupported_claims=unsupported,
            confidence=round(confidence, 1),
            recommendation=recommendation,
        )

    def extract_claims(self, answer: str) -> list[str]:
        claims: list[str] = []
        for line in answer.splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.lower().startswith("according to the approved policy"):
                continue
            cleaned = re.sub(r"^[-*]\s*", "", cleaned)
            cleaned = re.sub(r"^\[[^\]]+\]\s*", "", cleaned)
            for sentence in re.split(r"(?<=[.!?])\s+", cleaned):
                sentence = _strip_citation_markers(sentence)
                # Short claims such as "Guaranteed." are still material. Dropping
                # them would let a model append an unsupported qualifier to an
                # otherwise supported answer.
                if _tokens(sentence):
                    claims.append(sentence)
        return claims

    def verify_claim(
        self, claim: str, sources: list[SourceRecord]
    ) -> ClaimVerification:
        if not sources:
            return ClaimVerification(
                claim=claim,
                supported=False,
                source_ids=[],
                reason="No approved evidence was retrieved.",
                support_score=0,
            )

        claim_tokens = _tokens(claim)
        claim_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", claim))
        scored: list[tuple[float, SourceRecord]] = []
        normalized_claim = _normalized(claim)
        claim_markers = _material_markers(claim)

        for source in sources:
            best_sentence_score = 0.0
            for evidence_sentence in _sentences(source.text):
                source_tokens = _tokens(evidence_sentence)
                normalized_source = _normalized(evidence_sentence)
                if normalized_claim and normalized_claim == normalized_source:
                    score = 1.0
                else:
                    coverage = len(claim_tokens & source_tokens) / max(len(claim_tokens), 1)
                    lexical_content_supported = claim_tokens <= source_tokens
                    source_numbers = set(
                        re.findall(r"\b\d+(?:[.,]\d+)?\b", evidence_sentence)
                    )
                    numbers_supported = not claim_numbers or claim_numbers <= source_numbers
                    markers_supported = claim_markers == _material_markers(evidence_sentence)
                    score = coverage
                    if not lexical_content_supported:
                        score *= 0.5
                    if not numbers_supported:
                        score *= 0.35
                    if not markers_supported:
                        score *= 0.25
                best_sentence_score = max(best_sentence_score, min(1.0, score))
            scored.append((best_sentence_score, source))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score = scored[0][0]
        supporting = [
            source.document_id
            for score, source in scored
            if score >= self.support_threshold
        ]
        supported = best_score >= self.support_threshold
        reason = (
            "Claim is supported by retrieved approved policy evidence."
            if supported
            else (
                "No retrieved policy sentence provides sufficient lexical, numeric, "
                "and material-qualifier support."
            )
        )
        return ClaimVerification(
            claim=claim,
            supported=supported,
            source_ids=supporting,
            reason=reason,
            support_score=round(best_score, 4),
        )

    def compare_answers(self, answer1: str, answer2: str) -> float:
        first = _tokens(answer1)
        second = _tokens(answer2)
        return len(first & second) / max(len(first | second), 1)

    def check_against_context(self, answer: str, context: str) -> float:
        return self.compare_answers(answer, context)
