import json
import os
import re
from pathlib import Path

from shared.schemas import SourceRecord


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "for", "from",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "should",
    "that", "the", "this", "to", "was", "what", "when", "will", "with", "you",
    "your", "account", "accounts", "bank", "business", "customer", "customers",
    "day", "days", "policy", "rules", "support",
}

_DOMAIN_SIGNALS = {
    "refund_policy_1": {"refund", "reimbursement", "chargeback"},
    "security_policy_1": {"otp", "password", "passcode", "pin", "cvv", "credential"},
    "card_block_1": {"stolen", "lost", "replacement"},
    "fraud_report_1": {"fraud", "fraudulent", "scam", "scammer", "unauthorized", "fir"},
    "premium_benefits_1": {"premium", "lounge", "forex"},
}


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return {token for token in normalized.split() if len(token) > 1 and token not in _STOP_WORDS}


def _has_domain_signal(document_id: str, query_tokens: set[str]) -> bool:
    if query_tokens & _DOMAIN_SIGNALS.get(document_id, set()):
        return True
    if document_id == "card_block_1":
        return bool(
            {"card", "block"} <= query_tokens
            or {"card", "blocked"} <= query_tokens
        )
    return False


class RAGEngine:
    """Small deterministic retriever over the approved, versioned policy file.

    The original Chroma client made the critical path depend on an unpinned server
    and hid source provenance. For the hackathon data size, loading the approved
    JSON policy file is faster, reproducible, and keeps exact evidence available
    for claim verification.
    """

    def __init__(self, knowledge_base_path: str | Path | None = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "product_docs.json"
        self.path = Path(
            knowledge_base_path or os.getenv("KNOWLEDGE_BASE_PATH", str(default_path))
        )
        self.documents: list[dict] = []
        self.error: str | None = None
        self.reload()

    @property
    def ready(self) -> bool:
        return bool(self.documents) and self.error is None

    def reload(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not payload:
                raise ValueError("knowledge base must be a non-empty JSON list")
            validated = []
            for item in payload:
                if not isinstance(item, dict) or not item.get("id") or not item.get("text"):
                    raise ValueError("each knowledge-base item needs id and text")
                validated.append({"id": str(item["id"]), "text": str(item["text"])})
            self.documents = validated
            self.error = None
        except Exception as exc:
            self.documents = []
            self.error = f"knowledge base unavailable: {type(exc).__name__}"

    def search(self, query: str, n_results: int = 3) -> list[SourceRecord]:
        if not self.ready:
            raise RuntimeError(self.error or "knowledge base unavailable")

        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        minimum_score = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.18"))
        ranked: list[tuple[float, dict]] = []
        for document in self.documents:
            document_tokens = _tokens(document["text"])
            overlap = query_tokens & document_tokens
            domain_signal = _has_domain_signal(document["id"], query_tokens)
            # One generic shared word (for example "days" or "account") is not
            # enough to establish that a query belongs to a policy domain.
            if not domain_signal and len(overlap) < 2:
                continue
            query_coverage = len(overlap) / len(query_tokens)
            evidence_density = len(overlap) / max(len(document_tokens), 1)
            score = min(1.0, (0.8 * query_coverage) + (0.2 * evidence_density))
            if domain_signal:
                score = max(score, 0.35)
            if score >= minimum_score:
                ranked.append((score, document))

        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [
            SourceRecord(
                document_id=document["id"],
                chunk_id=f"{document['id']}:0",
                text=document["text"],
                metadata={"source": self.path.name, "approved": True},
                distance_or_similarity=round(score, 4),
            )
            for score, document in ranked[:n_results]
        ]

    def add_documents(self, docs: list, ids: list) -> None:
        raise NotImplementedError("approved policy data is updated through the versioned JSON file")
