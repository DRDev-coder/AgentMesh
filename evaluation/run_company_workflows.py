from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import select


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "evaluation" / "manifest.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _headers(user_id: str) -> dict[str, str]:
    return {
        "X-Dev-User": user_id,
        "X-Dev-Email": f"{user_id}@evaluation.local",
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _trace_value(response: dict[str, Any], agent: str, field: str) -> Any:
    trace = response.get("trace") or {}
    finding = (trace.get("agent_findings") or {}).get(agent) or {}
    output = finding.get("output") or {}
    return output.get(field)


def _public_response(response) -> dict[str, Any]:
    payload = response.json()
    return {
        "http_status": response.status_code,
        "decision_id": payload.get("id"),
        "decision_state": payload.get("decision_state"),
        "answer": payload.get("answer"),
        "decision_reason": payload.get("decision_reason"),
        "citations": payload.get("citations", []),
        "generation_mode": _trace_value(payload, "sage", "generation_mode"),
        "sage_warnings": _trace_value(payload, "sage", "warnings") or [],
        "oracle_supported": _trace_value(payload, "oracle", "overall_supported"),
        "usage_units": payload.get("usage_units"),
    }


def _case_pass(case: dict[str, Any], result: dict[str, Any]) -> bool:
    if result["http_status"] != 200:
        return False
    if case["type"] == "isolation":
        return (
            result["decision_state"] == "NEEDS_CLARIFICATION"
            and not result["citations"]
        )
    approved = result["decision_state"] in {"APPROVED", "APPROVED_WITH_REWRITE"}
    answer = (result.get("answer") or "").lower()
    expected = all(term.lower() in answer for term in case.get("expected_terms", []))
    return approved and bool(result["citations"]) and expected and result["oracle_supported"] is True


def _create_key(
    client: TestClient,
    organization_id: str,
    workspace_id: str,
    headers: dict[str, str],
) -> str:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/api-keys",
        headers=headers,
        json={
            "name": "Company evaluation live key",
            "environment": "live",
            "scopes": ["decisions:write", "decisions:read", "traces:read"],
        },
    )
    if response.status_code != 201:
        raise RuntimeError(f"API key creation failed: {response.text}")
    return response.json()["secret"]


def run_company_evaluation(*, use_groq: bool = False) -> dict[str, Any]:
    if use_groq:
        load_dotenv(ROOT / ".env", override=False)
        if not os.getenv("GROQ_API_KEY", "").strip():
            raise RuntimeError("--groq requested but GROQ_API_KEY is not configured")
    else:
        os.environ["GROQ_API_KEY"] = ""

    # Import after the model mode has been selected so every service sees the
    # intended environment.
    from api.config import get_settings
    from api.db.base import Database
    from api.db.models import BackgroundJob, DocumentChunk, DocumentVersion
    from api.main import create_app

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="agentmesh-company-eval-") as temp_dir:
        temp_path = Path(temp_dir)
        get_settings.cache_clear()
        settings = replace(
            get_settings(),
            environment="test",
            auth_mode="development",
            database_url=f"sqlite+pysqlite:///{(temp_path / 'company-evaluation.db').as_posix()}",
            object_storage_backend="local",
            object_storage_path=temp_path / "documents",
            saas_enabled=True,
            tasks_eager=True,
            free_decisions_per_month=500,
        )
        database = Database(settings)
        application = create_app(settings=settings, database=database, enable_saas=True)
        company_results: list[dict[str, Any]] = []

        with TestClient(application) as client:
            for company_index, company in enumerate(manifest["companies"]):
                user_id = f"eval-{company['company_id']}-owner"
                headers = _headers(user_id)
                onboard = client.post(
                    "/api/v1/organizations",
                    headers=headers,
                    json={
                        "name": f"{company['company_name']} Evaluation",
                        "workspace_name": "Customer Support",
                        "industry_template": "GENERAL",
                    },
                )
                if onboard.status_code != 201:
                    raise RuntimeError(f"Onboarding failed for {company['company_name']}: {onboard.text}")
                organization_id = onboard.json()["organization"]["id"]
                workspace_id = onboard.json()["workspace"]["id"]

                uploads: list[dict[str, Any]] = []
                for document in company["documents"]:
                    file_path = MANIFEST_PATH.parent / document["filename"]
                    content = file_path.read_text(encoding="utf-8").strip()
                    uploaded = client.post(
                        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents",
                        headers=headers,
                        files={"file": (file_path.name, content.encode("utf-8"), "text/plain")},
                    )
                    upload_payload = uploaded.json()
                    if uploaded.status_code != 201:
                        raise RuntimeError(f"Upload failed for {company['company_name']}: {uploaded.text}")
                    preview = client.get(
                        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents/{upload_payload['id']}/preview",
                        headers=headers,
                    )
                    with database.session() as session:
                        version = session.scalar(
                            select(DocumentVersion).where(DocumentVersion.document_id == upload_payload["id"])
                        )
                        chunks = session.scalars(
                            select(DocumentChunk).where(DocumentChunk.document_id == upload_payload["id"])
                        ).all()
                        jobs = session.scalars(
                            select(BackgroundJob).where(
                                BackgroundJob.organization_id == organization_id,
                                BackgroundJob.job_type == "INGEST_DOCUMENT",
                            )
                        ).all()
                        matching_job = next(
                            (
                                job
                                for job in jobs
                                if version and job.payload.get("document_version_id") == version.id
                            ),
                            None,
                        )
                        job_result = {
                            "status": matching_job.status if matching_job else None,
                            "attempts": matching_job.attempts if matching_job else None,
                            "error": matching_job.error if matching_job else None,
                        }
                        version_result = {
                            "status": version.status if version else None,
                            "extraction_error": version.extraction_error if version else None,
                            "page_count": version.page_count if version else None,
                            "chunk_count": len(chunks),
                        }
                    uploads.append(
                        {
                            "document_id": upload_payload["id"],
                            "document_name": document["title"],
                            "filename": file_path.name,
                            "source_url": document["source_url"],
                            "uploaded_text": content,
                            "upload_status": upload_payload["status"],
                            "version": version_result,
                            "background_job": job_result,
                            "preview": preview.json() if preview.status_code == 200 else {"error": preview.text},
                        }
                    )

                release = client.post(
                    f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases",
                    headers=headers,
                )
                if release.status_code != 201:
                    raise RuntimeError(f"Publishing failed for {company['company_name']}: {release.text}")
                key = _create_key(client, organization_id, workspace_id, headers)

                cases: list[dict[str, Any]] = []
                grounded_index = 0
                evaluation_cases = (
                    company["tests"][:1] if use_groq else company["tests"]
                )
                for case_index, case in enumerate(evaluation_cases):
                    playground = client.post(
                        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/playground/decisions",
                        headers={**headers, "Idempotency-Key": f"pg-{company_index:02d}-{case_index:02d}-workflow"},
                        json={"input": case["query"]},
                    )
                    playground_result = _public_response(playground)
                    playground_result["passed"] = _case_pass(case, playground_result) and (
                        not use_groq or playground_result["generation_mode"] == "groq"
                    )

                    api_result = None
                    if case["type"] == "grounded" and grounded_index == 0:
                        api_response = client.post(
                            "/api/v1/decisions",
                            headers={
                                "Authorization": f"Bearer {key}",
                                "Idempotency-Key": f"api-{company_index:02d}-{case_index:02d}-workflow",
                            },
                            json={"input": case["query"]},
                        )
                        api_result = _public_response(api_response)
                        api_result["passed"] = _case_pass(case, api_result) and (
                            not use_groq or api_result["generation_mode"] == "groq"
                        )
                    if case["type"] == "grounded":
                        grounded_index += 1
                    cases.append({**case, "playground": playground_result, "api_key": api_result})

                company_results.append(
                    {
                        "company_id": company["company_id"],
                        "company_name": company["company_name"],
                        "organization_id": organization_id,
                        "workspace_id": workspace_id,
                        "uploads": uploads,
                        "release": {
                            "http_status": release.status_code,
                            "id": release.json()["id"],
                            "version": release.json()["version"],
                            "document_version_ids": release.json()["document_version_ids"],
                        },
                        "cases": cases,
                    }
                )

        database.dispose()

    checks = []
    for company in company_results:
        checks.extend(
            upload["upload_status"] == "READY_FOR_REVIEW"
            and upload["version"]["status"] == "READY_FOR_REVIEW"
            and upload["version"]["extraction_error"] is None
            and upload["version"]["chunk_count"] > 0
            and upload["background_job"]["status"] == "COMPLETED"
            for upload in company["uploads"]
        )
        for case in company["cases"]:
            checks.append(case["playground"]["passed"])
            if case["api_key"] is not None:
                checks.append(case["api_key"]["passed"])

    return {
        "metadata": {
            "evaluation_date": manifest["evaluation_date"],
            "git_commit": _git_commit(),
            "company_count": len(company_results),
            "model_mode_requested": "groq" if use_groq else "deterministic",
            "method": manifest["method"],
        },
        "summary": {
            "checks": len(checks),
            "passed": sum(bool(check) for check in checks),
            "failed": sum(not bool(check) for check in checks),
            "pass_rate": round(sum(bool(check) for check in checks) / max(len(checks), 1), 4),
        },
        "companies": company_results,
    }


def render_markdown(result: dict[str, Any]) -> str:
    metadata = result["metadata"]
    summary = result["summary"]
    lines = [
        "# AgentMesh 10-company workflow evaluation",
        "",
        f"- Date: {metadata['evaluation_date']}",
        f"- Commit: `{metadata['git_commit']}`",
        f"- Requested model mode: `{metadata['model_mode_requested']}`",
        f"- Result: {summary['passed']}/{summary['checks']} checks passed ({summary['pass_rate']:.1%})",
        "- Method: " + metadata["method"],
        "",
        "| Company | Ingestion | Release | Grounded prompts | Isolation | API key |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for company in result["companies"]:
        ingestion = all(upload["background_job"]["status"] == "COMPLETED" for upload in company["uploads"])
        grounded = [case for case in company["cases"] if case["type"] == "grounded"]
        isolation = [case for case in company["cases"] if case["type"] == "isolation"]
        api_cases = [case for case in company["cases"] if case["api_key"] is not None]
        lines.append(
            f"| {company['company_name']} | {'PASS' if ingestion else 'FAIL'} | "
            f"v{company['release']['version']} | "
            f"{sum(case['playground']['passed'] for case in grounded)}/{len(grounded)} | "
            f"{sum(case['playground']['passed'] for case in isolation)}/{len(isolation)} | "
            f"{sum(case['api_key']['passed'] for case in api_cases)}/{len(api_cases)} |"
        )

    for company in result["companies"]:
        lines.extend(["", f"## {company['company_name']}", ""])
        for upload in company["uploads"]:
            lines.extend(
                [
                    f"Document: `{upload['filename']}` — {upload['document_name']}",
                    "",
                    f"Official source: {upload['source_url']}",
                    "",
                    f"Ingestion: upload `{upload['upload_status']}`, job `{upload['background_job']['status']}`, "
                    f"version `{upload['version']['status']}`, chunks `{upload['version']['chunk_count']}`, "
                    f"extraction error `{upload['version']['extraction_error']}`.",
                    "",
                    "Uploaded text:",
                    "",
                    "> " + upload["uploaded_text"].replace("\n", "\n> "),
                    "",
                ]
            )
        for case in company["cases"]:
            pg = case["playground"]
            lines.extend(
                [
                    f"### {case['id']}",
                    "",
                    f"Customer query: {case['query']}",
                    "",
                    f"Playground: `{pg['decision_state']}` — {'PASS' if pg['passed'] else 'FAIL'}; "
                    f"mode `{pg['generation_mode']}`; citations `{len(pg['citations'])}`; "
                    f"Oracle supported `{pg['oracle_supported']}`.",
                    "",
                    f"Answer: {pg['answer']}",
                    "",
                ]
            )
            if case["api_key"] is not None:
                api = case["api_key"]
                lines.extend(
                    [
                        f"API key: `{api['decision_state']}` — {'PASS' if api['passed'] else 'FAIL'}; "
                        f"mode `{api['generation_mode']}`; citations `{len(api['citations'])}`; "
                        f"Oracle supported `{api['oracle_supported']}`.",
                        "",
                        f"API answer: {api['answer']}",
                        "",
                    ]
                )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 10-company AgentMesh workflow tests")
    parser.add_argument("--groq", action="store_true", help="Load .env and exercise Groq generation")
    parser.add_argument("--no-write", action="store_true", help="Print summary without writing reports")
    args = parser.parse_args()
    result = run_company_evaluation(use_groq=args.groq)
    print(json.dumps(result["summary"], indent=2))
    if not args.no_write:
        suffix = "groq" if args.groq else "deterministic"
        json_path = ROOT / "evaluation" / f"company_workflow_report_{suffix}.json"
        markdown_path = ROOT / "evaluation" / f"company_workflow_report_{suffix}.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        markdown_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"Wrote {json_path.relative_to(ROOT)}")
        print(f"Wrote {markdown_path.relative_to(ROOT)}")
    return 0 if result["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
