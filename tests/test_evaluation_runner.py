from __future__ import annotations

import asyncio
import json
from pathlib import Path

from evaluation.run_evaluation import run


ROOT = Path(__file__).resolve().parents[1]


def test_evaluation_runner_uses_all_cases_and_reports_real_denominators() -> None:
    report = asyncio.run(
        run(
            ROOT / "evaluation" / "cases.json",
            ROOT / "data" / "product_docs.json",
        )
    )

    assert report["execution_mode"] == "deterministic_local"
    assert report["external_services_used"] is False
    assert report["dataset"]["case_count"] == 65
    assert len(report["case_results"]) == 65
    assert report["metrics"]["grounded_answer_accuracy"]["denominator"] == 15
    assert report["metrics"]["unsupported_answer_rejection_rate"]["denominator"] == 10
    assert report["metrics"]["agent_failure_behavior"]["denominator"] == 4


def test_evaluation_runner_has_no_component_errors() -> None:
    report = asyncio.run(
        run(
            ROOT / "evaluation" / "cases.json",
            ROOT / "data" / "product_docs.json",
        )
    )
    error_metric = report["metrics"]["component_error_rate"]
    assert error_metric == {"value": 0.0, "numerator": 0, "denominator": 65}


def test_report_is_json_serializable() -> None:
    report = asyncio.run(
        run(
            ROOT / "evaluation" / "cases.json",
            ROOT / "data" / "product_docs.json",
        )
    )
    serialized = json.dumps(report)
    assert "grounded_answer_accuracy" in serialized
