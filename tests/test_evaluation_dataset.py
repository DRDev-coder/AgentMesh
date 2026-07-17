from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evaluation" / "cases.json"
POLICY_PATH = ROOT / "data" / "product_docs.json"

MINIMUMS = {
    "safe_grounded": 15,
    "unsupported": 10,
    "credential_phishing": 10,
    "frustrated": 10,
    "urgent_fraud": 10,
    "prompt_injection": 10,
}
ALLOWED_DECISIONS = {
    "APPROVED",
    "APPROVED_WITH_REWRITE",
    "NEEDS_CLARIFICATION",
    "BLOCKED",
    "ESCALATED",
    "SYSTEM_UNAVAILABLE",
}


def _dataset() -> dict:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def test_dataset_meets_required_category_minimums() -> None:
    cases = _dataset()["cases"]
    counts = Counter(case["category"] for case in cases)

    assert len(cases) >= 65
    for category, minimum in MINIMUMS.items():
        assert counts[category] >= minimum


def test_dataset_ids_are_unique_and_labels_are_complete() -> None:
    cases = _dataset()["cases"]
    ids = [case["id"] for case in cases]
    required_labels = {
        "grounded",
        "unsupported",
        "critical_risk",
        "frustrated",
        "urgent",
        "should_escalate",
        "expected_doc_ids",
        "expected_decisions",
    }

    assert len(ids) == len(set(ids))
    for case in cases:
        assert case["query"].strip()
        assert required_labels <= set(case["labels"])
        assert set(case["labels"]["expected_decisions"]) <= ALLOWED_DECISIONS


def test_all_expected_document_ids_exist_in_approved_policy_corpus() -> None:
    policy_ids = {
        item["id"]
        for item in json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    }
    for case in _dataset()["cases"]:
        assert set(case["labels"]["expected_doc_ids"]) <= policy_ids


def test_category_labels_are_consistent() -> None:
    cases = _dataset()["cases"]
    for case in cases:
        labels = case["labels"]
        if case["category"] == "unsupported":
            assert labels["unsupported"] is True
            assert labels["grounded"] is False
        elif case["category"] in {"credential_phishing", "prompt_injection"}:
            assert labels["critical_risk"] is True
            assert labels["should_escalate"] is True
        elif case["category"] == "frustrated":
            assert labels["frustrated"] is True
        elif case["category"] == "urgent_fraud":
            assert labels["urgent"] is True
            assert labels["should_escalate"] is True
