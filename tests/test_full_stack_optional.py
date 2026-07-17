from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

import pytest


pytestmark = [
    pytest.mark.full_stack,
    pytest.mark.skipif(
        os.getenv("RUN_FULL_STACK_TESTS") != "1",
        reason="set RUN_FULL_STACK_TESTS=1 after starting the complete stack",
    ),
]


def _request(path: str, *, payload: dict | None = None) -> tuple[int, dict]:
    base_url = os.getenv("AGENTMESH_GATEWAY_URL", "http://127.0.0.1:8000").rstrip("/")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=data,
        method="POST" if payload is not None else "GET",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - opt-in local test
        return response.status, json.loads(response.read().decode("utf-8"))


def test_complete_started_stack_health_and_chat() -> None:
    health_status, health = _request("/api/v1/readyz")
    assert health_status == 200
    assert health["status"] == "ready"

    chat_status, chat = _request(
        "/api/v1/chat",
        payload={"query": "How long does a standard refund investigation take?"},
    )
    assert chat_status == 200
    assert chat["session_id"]
    assert chat["decision_state"] in {
        "APPROVED",
        "APPROVED_WITH_REWRITE",
        "NEEDS_CLARIFICATION",
        "BLOCKED",
        "ESCALATED",
        "SYSTEM_UNAVAILABLE",
    }
    assert set(chat["agent_findings"]) == {"sage", "guardian", "empath", "oracle"}
