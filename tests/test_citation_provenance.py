from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agents.sage.rag_engine import RAGEngine
from agents.sage.service import SageService


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data" / "product_docs.json"


def _policies() -> dict[str, str]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item["text"] for item in payload}


def test_retrieval_returns_application_controlled_source_records() -> None:
    engine = RAGEngine(POLICY_PATH)
    sources = engine.search("standard refund investigation seven business days")

    assert sources
    policies = _policies()
    for source in sources:
        assert source.document_id in policies
        assert source.text == policies[source.document_id]
        assert source.chunk_id == f"{source.document_id}:0"
        assert source.metadata == {"source": "product_docs.json", "approved": True}
        assert 0 <= source.distance_or_similarity <= 1


def test_sage_citations_are_structured_retrieval_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    engine = RAGEngine(POLICY_PATH)
    service = SageService(engine)
    service.api_key = ""

    output = asyncio.run(service.analyze("How long does a standard refund take?"))

    assert output.insufficient_data is False
    assert output.citations
    assert {item.document_id for item in output.citations} <= set(_policies())
    for citation in output.citations:
        assert f"[{citation.document_id}]" in output.answer


def test_model_text_cannot_replace_structured_citation_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = RAGEngine(POLICY_PATH)
    service = SageService(engine)
    service.api_key = "test-key"

    async def untrusted_model_text(*_args: object) -> str:
        return "Invented claim [not_a_real_policy]"

    monkeypatch.setattr(service, "_generate_with_groq", untrusted_model_text)
    output = asyncio.run(service.analyze("How long does a standard refund take?"))

    assert "not_a_real_policy" not in {item.document_id for item in output.citations}
    assert {item.document_id for item in output.citations} <= set(_policies())


def test_unsupported_query_has_no_fabricated_citations() -> None:
    service = SageService(RAGEngine(POLICY_PATH))
    service.api_key = ""

    output = asyncio.run(service.analyze("Will Bitcoin double next month?"))

    assert output.insufficient_data is True
    assert output.citations == []
    assert output.retrieval_quality == 0


def test_generic_temporal_overlap_does_not_create_irrelevant_policy_evidence() -> None:
    service = SageService(RAGEngine(POLICY_PATH))
    service.api_key = ""

    output = asyncio.run(service.analyze("What will the weather be in 7 days?"))

    assert output.insufficient_data is True
    assert output.citations == []


def test_generic_account_words_do_not_select_premium_policy() -> None:
    engine = RAGEngine(POLICY_PATH)

    assert engine.search("Can you help with my account?") == []


def test_missing_policy_file_is_reported_as_dependency_failure(tmp_path: Path) -> None:
    engine = RAGEngine(tmp_path / "missing.json")
    assert engine.ready is False
    assert engine.error is not None
    with pytest.raises(RuntimeError):
        engine.search("refund")
