#!/usr/bin/env python3
"""Run AgentMesh's deterministic local evaluation and write an honest JSON report.

The runner deliberately disables external model access. It exercises the actual
local retriever, SAGE fallback, deterministic GUARDIAN scanner, EMPATH analyzer,
ORACLE verifier, and risk decision engine. Metric values are calculated from
evaluation/cases.json; no expected score is embedded in this program.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Evaluation is explicitly local. Never inherit a developer's real model key.
os.environ["GROQ_API_KEY"] = ""

from agents.empath.emotion_model import EmotionAnalyzer  # noqa: E402
from agents.guardian.service import GuardianService  # noqa: E402
from agents.oracle.fact_checker import FactChecker  # noqa: E402
from agents.sage.rag_engine import RAGEngine  # noqa: E402
from agents.sage.service import SageService  # noqa: E402
from consensus.risk_engine import RiskAwareDecisionEngine  # noqa: E402
from shared.schemas import (  # noqa: E402
    AgentState,
    DecisionState,
    GuardianStatus,
    SageOutput,
    SourceRecord,
)


REQUIRED_CATEGORY_COUNTS = {
    "safe_grounded": 15,
    "unsupported": 10,
    "credential_phishing": 10,
    "frustrated": 10,
    "urgent_fraud": 10,
    "prompt_injection": 10,
}


def _ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "value": round(numerator / denominator, 4) if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
    }


def _report_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _validate_dataset(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("dataset must contain a cases list")

    ids: set[str] = set()
    counts: Counter[str] = Counter()
    for position, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"case {position} must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"case {position} has no non-empty id")
        if case_id in ids:
            raise ValueError(f"duplicate case id: {case_id}")
        ids.add(case_id)
        category = case.get("category")
        if category not in REQUIRED_CATEGORY_COUNTS:
            raise ValueError(f"case {case_id} has unknown category: {category}")
        counts[category] += 1
        if not isinstance(case.get("query"), str) or not case["query"].strip():
            raise ValueError(f"case {case_id} has no query")
        if not isinstance(case.get("labels"), dict):
            raise ValueError(f"case {case_id} has no labels object")

    for category, minimum in REQUIRED_CATEGORY_COUNTS.items():
        if counts[category] < minimum:
            raise ValueError(
                f"category {category} has {counts[category]} cases; requires {minimum}"
            )
    return cases


async def _evaluate_case(
    case: dict[str, Any],
    *,
    sage_service: SageService,
    guardian_service: GuardianService,
    empath_analyzer: EmotionAnalyzer,
    fact_checker: FactChecker,
    decision_engine: RiskAwareDecisionEngine,
) -> dict[str, Any]:
    started = perf_counter()
    query = case["query"]
    labels = case["labels"]
    try:
        sage = await sage_service.analyze(query)
        guardian = await guardian_service.analyze(query, sage.answer)
        empath = empath_analyzer.analyze(query)
        oracle = fact_checker.verify(sage.answer, sage.citations)
        states = {
            name: AgentState.AVAILABLE
            for name in ("sage", "guardian", "empath", "oracle")
        }
        decision = decision_engine.decide(
            states=states,
            sage=sage,
            guardian=guardian,
            empath=empath,
            oracle=oracle,
        )
        error = None
    except Exception as exc:  # Report component failures; do not convert them into passes.
        latency_ms = round((perf_counter() - started) * 1000, 3)
        return {
            "id": case["id"],
            "category": case["category"],
            "latency_ms": latency_ms,
            "component_error": f"{type(exc).__name__}: {exc}",
        }

    retrieved_ids = [source.document_id for source in sage.citations]
    expected_ids = labels["expected_doc_ids"]
    retrieval_hit = bool(set(retrieved_ids) & set(expected_ids)) if expected_ids else None
    predicted_escalation = decision.create_escalation or decision.state in {
        DecisionState.BLOCKED,
        DecisionState.ESCALATED,
        DecisionState.SYSTEM_UNAVAILABLE,
    }
    safe_grounded_correct = (
        not sage.insufficient_data
        and bool(sage.citations)
        and oracle.overall_supported
        and retrieval_hit is True
    )
    unsupported_rejected = sage.insufficient_data or decision.state in {
        DecisionState.NEEDS_CLARIFICATION,
        DecisionState.ESCALATED,
        DecisionState.BLOCKED,
    }
    critical_detected = guardian.status is GuardianStatus.CRITICAL and guardian.blocking
    frustration_detected = empath.emotion == "FRUSTRATED"
    urgency_detected = empath.urgency >= 9 or empath.requires_urgent_review

    return {
        "id": case["id"],
        "category": case["category"],
        "latency_ms": round((perf_counter() - started) * 1000, 3),
        "component_error": error,
        "retrieved_doc_ids": retrieved_ids,
        "retrieval_hit": retrieval_hit,
        "sage_insufficient_data": sage.insufficient_data,
        "guardian_status": guardian.status.value,
        "guardian_blocking": guardian.blocking,
        "guardian_violations": guardian.violations,
        "emotion": empath.emotion,
        "urgency": empath.urgency,
        "requires_urgent_review": empath.requires_urgent_review,
        "oracle_overall_supported": oracle.overall_supported,
        "unsupported_claim_count": len(oracle.unsupported_claims),
        "decision": decision.state.value,
        "predicted_escalation": predicted_escalation,
        "expected_escalation": labels["should_escalate"],
        "safe_grounded_correct": safe_grounded_correct,
        "unsupported_rejected": unsupported_rejected,
        "critical_detected": critical_detected,
        "frustration_detected": frustration_detected,
        "urgency_detected": urgency_detected,
    }


def _failure_policy_checks(
    baseline: dict[str, Any],
    *,
    decision_engine: RiskAwareDecisionEngine,
) -> list[dict[str, Any]]:
    sage = baseline["sage"]
    guardian = baseline["guardian"]
    empath = baseline["empath"]
    oracle = baseline["oracle"]
    available = {
        name: AgentState.AVAILABLE
        for name in ("sage", "guardian", "empath", "oracle")
    }
    scenarios = [
        ("sage_dependency_unavailable", "sage", AgentState.DEPENDENCY_UNAVAILABLE, DecisionState.SYSTEM_UNAVAILABLE),
        ("guardian_timeout", "guardian", AgentState.TIMEOUT, DecisionState.ESCALATED),
        ("oracle_invalid_output", "oracle", AgentState.INVALID_OUTPUT, DecisionState.ESCALATED),
        ("empath_model_error", "empath", AgentState.MODEL_ERROR, DecisionState.APPROVED),
    ]
    results = []
    for name, agent, unavailable_state, expected in scenarios:
        states = dict(available)
        states[agent] = unavailable_state
        decision = decision_engine.decide(
            states=states,
            sage=sage,
            guardian=guardian,
            empath=empath,
            oracle=oracle,
        )
        results.append(
            {
                "scenario": name,
                "expected_decision": expected.value,
                "actual_decision": decision.state.value,
                "passed": decision.state is expected,
            }
        )
    return results


async def run(dataset_path: Path, policy_path: Path) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = _validate_dataset(dataset)

    rag_engine = RAGEngine(policy_path)
    if not rag_engine.ready:
        raise RuntimeError(rag_engine.error or "policy retriever is not ready")
    sage_service = SageService(rag_engine)
    sage_service.api_key = ""
    guardian_service = GuardianService()
    guardian_service.api_key = ""
    empath_analyzer = EmotionAnalyzer()
    fact_checker = FactChecker()
    decision_engine = RiskAwareDecisionEngine()

    results = []
    for case in cases:
        results.append(
            await _evaluate_case(
                case,
                sage_service=sage_service,
                guardian_service=guardian_service,
                empath_analyzer=empath_analyzer,
                fact_checker=fact_checker,
                decision_engine=decision_engine,
            )
        )

    completed = [result for result in results if not result["component_error"]]
    by_id = {case["id"]: case for case in cases}

    safe = [item for item in completed if item["category"] == "safe_grounded"]
    unsupported = [item for item in completed if item["category"] == "unsupported"]
    expected_critical = [
        item for item in completed if by_id[item["id"]]["labels"]["critical_risk"]
    ]
    expected_noncritical = [
        item for item in completed if not by_id[item["id"]]["labels"]["critical_risk"]
    ]
    predicted_escalations = [
        item for item in completed if item["predicted_escalation"]
    ]
    retrieval_cases = [
        item
        for item in completed
        if by_id[item["id"]]["labels"]["expected_doc_ids"]
    ]
    frustrated = [item for item in completed if item["category"] == "frustrated"]
    urgent = [item for item in completed if item["category"] == "urgent_fraud"]

    # Use a neutral typed baseline so each failure scenario changes exactly one
    # agent state. Retrieved policy prose can itself contain credential warnings,
    # which would confound a degradation-policy measurement.
    baseline_query = "What approved support is available?"
    baseline_source = SourceRecord(
        document_id="failure_policy_fixture",
        chunk_id="failure_policy_fixture:0",
        text="Approved support is available.",
        metadata={"approved": True, "evaluation_fixture": True},
        distance_or_similarity=1.0,
    )
    baseline_sage = SageOutput(
        answer=baseline_source.text,
        confidence=100,
        citations=[baseline_source],
        retrieval_quality=1.0,
        insufficient_data=False,
        generation_mode="deterministic",
    )
    baseline_guardian = await guardian_service.analyze(
        baseline_query, baseline_sage.answer
    )
    baseline_empath = empath_analyzer.analyze(baseline_query)
    baseline_oracle = fact_checker.verify(
        baseline_sage.answer, baseline_sage.citations
    )
    failure_checks = _failure_policy_checks(
        {
            "sage": baseline_sage,
            "guardian": baseline_guardian,
            "empath": baseline_empath,
            "oracle": baseline_oracle,
        },
        decision_engine=decision_engine,
    )

    metrics = {
        "grounded_answer_accuracy": _ratio(
            sum(item["safe_grounded_correct"] for item in safe), len(safe)
        ),
        "unsupported_answer_rejection_rate": _ratio(
            sum(item["unsupported_rejected"] for item in unsupported),
            len(unsupported),
        ),
        "critical_risk_recall": _ratio(
            sum(item["critical_detected"] for item in expected_critical),
            len(expected_critical),
        ),
        "critical_risk_false_positive_rate": _ratio(
            sum(item["guardian_status"] == GuardianStatus.CRITICAL.value for item in expected_noncritical),
            len(expected_noncritical),
        ),
        "escalation_precision": _ratio(
            sum(item["expected_escalation"] for item in predicted_escalations),
            len(predicted_escalations),
        ),
        "retrieval_hit_rate": _ratio(
            sum(item["retrieval_hit"] is True for item in retrieval_cases),
            len(retrieval_cases),
        ),
        "frustration_recall": _ratio(
            sum(item["frustration_detected"] for item in frustrated), len(frustrated)
        ),
        "urgent_fraud_recall": _ratio(
            sum(item["urgency_detected"] for item in urgent), len(urgent)
        ),
        "agent_failure_behavior": _ratio(
            sum(item["passed"] for item in failure_checks), len(failure_checks)
        ),
        "average_response_latency_ms": {
            "value": round(fmean(item["latency_ms"] for item in completed), 3)
            if completed
            else None,
            "sample_count": len(completed),
        },
        "component_error_rate": _ratio(len(results) - len(completed), len(results)),
    }

    return {
        "report_schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "deterministic_local",
        "external_services_used": False,
        "dataset": {
            "path": _report_path(dataset_path),
            "schema_version": dataset.get("schema_version"),
            "case_count": len(cases),
            "category_counts": dict(sorted(Counter(case["category"] for case in cases).items())),
        },
        "policy_corpus": {
            "path": _report_path(policy_path),
            "document_count": len(rag_engine.documents),
        },
        "metric_definitions": {
            "grounded_answer_accuracy": "Safe-grounded cases with retrieved expected evidence and claim-level supported output.",
            "unsupported_answer_rejection_rate": "Unsupported cases producing insufficient-data or a non-approval routing decision.",
            "critical_risk_recall": "Labelled critical-risk cases blocked by GUARDIAN's CRITICAL deterministic result.",
            "critical_risk_false_positive_rate": "Labelled non-critical cases incorrectly marked CRITICAL by GUARDIAN.",
            "escalation_precision": "Predicted escalations whose labels require escalation.",
            "retrieval_hit_rate": "Cases with expected evidence where at least one expected document was retrieved.",
            "frustration_recall": "Frustrated-category cases classified with FRUSTRATED emotion.",
            "urgent_fraud_recall": "Urgent-fraud cases assigned urgency at least 9 or urgent review.",
            "agent_failure_behavior": "Synthetic unavailable-agent scenarios routed to their documented safe degradation decision.",
            "average_response_latency_ms": "Mean local end-to-end component latency per successfully evaluated case.",
            "component_error_rate": "Cases that raised an exception in any evaluated local component.",
        },
        "metrics": metrics,
        "failure_policy_scenarios": failure_checks,
        "case_results": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "evaluation" / "cases.json",
        help="labelled evaluation JSON (default: evaluation/cases.json)",
    )
    parser.add_argument(
        "--policies",
        type=Path,
        default=ROOT / "data" / "product_docs.json",
        help="approved policy corpus (default: data/product_docs.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evaluation" / "report.json",
        help="report output path (default: evaluation/report.json)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="print the report without writing the output file",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = asyncio.run(run(args.dataset, args.policies))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"evaluation failed: {exc}", file=sys.stderr)
        return 1

    serialized = json.dumps(report, indent=2, sort_keys=True)
    if not args.no_write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    print(json.dumps(report["metrics"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
