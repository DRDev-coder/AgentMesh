"""Exercise the deployed HTTP workflow with a real, separate Celery worker.

This intentionally does not import application internals.  A successful run proves
that the gateway, Redis queue, worker, database, and shared object storage cooperate.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

import httpx


DEFAULT_DOCUMENT = Path("data/evaluation/documents/github-plan-billing.txt")


def require(response: httpx.Response, expected: int) -> dict:
    if response.status_code != expected:
        raise RuntimeError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}: {response.text}"
        )
    return response.json()


def run(base_url: str, document_path: Path, timeout_seconds: float) -> dict:
    run_id = uuid.uuid4().hex[:10]
    dashboard_headers = {
        "X-Dev-User": f"async-smoke-{run_id}",
        "X-Dev-Email": f"async-smoke-{run_id}@example.test",
    }

    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        onboarding = require(
            client.post(
                "/api/v1/organizations",
                headers=dashboard_headers,
                json={
                    "name": f"Async Worker Smoke {run_id}",
                    "workspace_name": "GitHub Support",
                    "industry_template": "GENERAL",
                },
            ),
            201,
        )
        organization_id = onboarding["organization"]["id"]
        workspace_id = onboarding["workspace"]["id"]
        prefix = f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}"

        uploaded = require(
            client.post(
                f"{prefix}/documents",
                headers=dashboard_headers,
                files={
                    "file": (
                        document_path.name,
                        document_path.read_bytes(),
                        "text/plain",
                    )
                },
            ),
            201,
        )
        document_id = uploaded["id"]

        status_history = [uploaded["status"]]
        deadline = time.monotonic() + timeout_seconds
        document = uploaded
        while time.monotonic() < deadline:
            documents = require(
                client.get(f"{prefix}/documents", headers=dashboard_headers), 200
            )
            document = next(item for item in documents if item["id"] == document_id)
            if document["status"] != status_history[-1]:
                status_history.append(document["status"])
            if document["status"] in {"READY_FOR_REVIEW", "FAILED"}:
                break
            time.sleep(0.5)

        if document["status"] != "READY_FOR_REVIEW":
            raise RuntimeError(
                f"Document did not reach READY_FOR_REVIEW: {document} "
                f"(history={status_history})"
            )

        preview = require(
            client.get(
                f"{prefix}/documents/{document_id}/preview",
                headers=dashboard_headers,
            ),
            200,
        )
        if not preview["chunks"]:
            raise RuntimeError("Worker completed without producing document chunks")

        release = require(
            client.post(f"{prefix}/knowledge-releases", headers=dashboard_headers),
            201,
        )
        query = "If I cancel a paid GitHub plan, when does it take effect?"
        playground = require(
            client.post(
                f"{prefix}/playground/decisions",
                headers={**dashboard_headers, "Idempotency-Key": f"play-{run_id}"},
                json={"input": query, "session_id": f"play-{run_id}"},
            ),
            200,
        )

        key = require(
            client.post(
                f"{prefix}/api-keys",
                headers=dashboard_headers,
                json={
                    "name": "Async smoke key",
                    "environment": "test",
                    "scopes": ["decisions:write", "decisions:read", "traces:read"],
                },
            ),
            201,
        )
        api_decision = require(
            client.post(
                "/api/v1/decisions",
                headers={
                    "Authorization": f"Bearer {key['secret']}",
                    "Idempotency-Key": f"api-{run_id}",
                },
                json={"input": query, "session_id": f"api-{run_id}"},
            ),
            200,
        )

    result = {
        "passed": True,
        "base_url": base_url,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "document": {
            "id": document_id,
            "filename": document["filename"],
            "status_history": status_history,
            "final_status": document["status"],
            "extraction_error": document["extraction_error"],
            "chunks": len(preview["chunks"]),
        },
        "release": {"id": release["id"], "status": release["status"]},
        "query": query,
        "playground": {
            "answer": playground["answer"],
            "decision_state": playground["decision_state"],
            "citations": len(playground["citations"]),
        },
        "api_key": {
            "id": key["id"],
            "last_four": key["last_four"],
            "secret_persisted": False,
        },
        "api_decision": {
            "answer": api_decision["answer"],
            "decision_state": api_decision["decision_state"],
            "citations": len(api_decision["citations"]),
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--document", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/async_ingestion_smoke_report.json"),
    )
    args = parser.parse_args()

    result = run(args.base_url.rstrip("/"), args.document, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
