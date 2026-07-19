from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.schemas import ChatResponse
from api.services.orchestrator import AgentOrchestrator
from api.services.storage import SQLiteRepository
from shared.schemas import (
    AgentFinding,
    AgentState,
    AuditOutcome,
    AuditStatus,
    DecisionState,
    EscalationPriority,
)


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def process(self, query: str, session_id: str) -> ChatResponse:
        self.calls.append((query, session_id))
        findings = {
            name: AgentFinding(state=AgentState.AVAILABLE, output={"mocked": True})
            for name in ("sage", "guardian", "empath", "oracle")
        }
        return ChatResponse(
            session_id=session_id,
            query=query,
            final_answer="Mocked approved policy answer.",
            factual_answer="Mocked approved policy answer.",
            decision_state=DecisionState.APPROVED,
            decision_reason="Mocked local integration decision.",
            citations=[],
            agent_findings=findings,
            completed_agents=list(findings),
            audit=AuditOutcome(status=AuditStatus.DISABLED),
            consensus_status="APPROVED",
            consensus_reason="Mocked local integration decision.",
            agent_votes={name: finding.output for name, finding in findings.items()},
            escalate=False,
            primary_agent="sage",
            confidence=90,
        )

    def readiness(self):
        return True, {
            "mocked_pipeline": {"ready": True},
            "external_llm": {"ready": False, "required": False},
        }


class DisabledBlockchain:
    def __init__(self) -> None:
        self.enabled = False
        self.configured = False

    def log_decision(self, **_kwargs) -> AuditOutcome:
        return AuditOutcome(status=AuditStatus.DISABLED)


def _client(
    tmp_path: Path,
    *,
    orchestrator=None,
) -> tuple[TestClient, SQLiteRepository]:
    repository = SQLiteRepository(tmp_path / "agentmesh-test.db")
    application = create_app(
        repository=repository,
        orchestrator=orchestrator or FakeOrchestrator(),
    )
    return TestClient(application), repository


def test_chat_api_uses_in_process_mock_without_docker_or_network(tmp_path: Path) -> None:
    orchestrator = FakeOrchestrator()
    client, _ = _client(tmp_path, orchestrator=orchestrator)

    with client:
        response = client.post(
            "/api/v1/chat", json={"query": "What is the refund timeline?"}
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision_state"] == "APPROVED"
    assert payload["final_answer"] == "Mocked approved policy answer."
    assert len(payload["session_id"]) > 10
    assert orchestrator.calls == [
        ("What is the refund timeline?", payload["session_id"])
    ]


def test_chat_api_reuses_supplied_session_and_rejects_invalid_input(
    tmp_path: Path,
) -> None:
    client, _ = _client(tmp_path)
    with client:
        valid = client.post(
            "/api/v1/chat",
            json={"query": "Refund policy", "session_id": "existing-session"},
        )
        blank = client.post("/api/v1/chat", json={"query": "   "})
        extra = client.post(
            "/api/v1/chat", json={"query": "Refund policy", "unexpected": True}
        )

    assert valid.status_code == 200
    assert valid.json()["session_id"] == "existing-session"
    assert blank.status_code == 422
    assert extra.status_code == 422


def test_health_api_reflects_mocked_readiness(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        live = client.get("/api/v1/healthz")
        ready = client.get("/api/v1/readyz")

    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_review_queue_crud_endpoints_use_temporary_sqlite(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("REVIEW_API_KEY", "test-review-key")
    client, repository = _client(tmp_path)
    record = repository.create_escalation(
        session_id="session-review",
        query="Unauthorized transfer",
        draft_answer="Initial draft",
        reason="Fraud review",
        priority=EscalationPriority.HIGH,
        agent_findings={"guardian": {"status": "WARNING"}},
    )
    headers = {"X-Review-API-Key": "test-review-key"}

    with client:
        unauthorized = client.get("/api/v1/escalations")
        listed = client.get("/api/v1/escalations", headers=headers)
        retrieved = client.get(
            f"/api/v1/escalations/{record.ticket_id}", headers=headers
        )
        edited = client.patch(
            f"/api/v1/escalations/{record.ticket_id}",
            headers=headers,
            json={"draft_answer": "Reviewer-edited answer", "priority": "CRITICAL"},
        )
        approved = client.post(
            f"/api/v1/escalations/{record.ticket_id}/approve",
            headers=headers,
            json={
                "answer": "Approved reviewer answer",
                "resolution_notes": "Reviewed in prototype queue",
            },
        )
        resolved = client.post(
            f"/api/v1/escalations/{record.ticket_id}/resolve",
            headers=headers,
            json={"resolution_notes": "Prototype workflow completed"},
        )

    assert unauthorized.status_code == 401
    assert listed.status_code == 200
    assert [item["ticket_id"] for item in listed.json()] == [record.ticket_id]
    assert retrieved.json()["status"] == "OPEN"
    assert edited.json()["draft_answer"] == "Reviewer-edited answer"
    assert edited.json()["priority"] == "CRITICAL"
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["draft_answer"] == "Approved reviewer answer"
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolution_notes"] == "Prototype workflow completed"


def test_review_queue_reject_action_and_missing_ticket(tmp_path: Path) -> None:
    client, repository = _client(tmp_path)
    record = repository.create_escalation(
        session_id="session-reject",
        query="Unsafe request",
        draft_answer="Unsafe draft",
        reason="Credential risk",
        priority=EscalationPriority.CRITICAL,
        agent_findings={},
    )

    with client:
        rejected = client.post(
            f"/api/v1/escalations/{record.ticket_id}/reject",
            json={"reason": "Unsafe answer"},
        )
        missing = client.get("/api/v1/escalations/AM-MISSING")

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["resolution_notes"] == "Unsafe answer"
    assert missing.status_code == 404


def test_actual_local_pipeline_creates_escalation_without_external_services(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(tmp_path / "local-pipeline.db")
    orchestrator = AgentOrchestrator(
        repository=repository,
        blockchain=DisabledBlockchain(),
    )
    application = create_app(repository=repository, orchestrator=orchestrator)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/chat",
            json={"query": "Can you guarantee that Bitcoin will double next month?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision_state"] in {"NEEDS_CLARIFICATION", "ESCALATED"}
    assert payload["escalation_ticket_id"].startswith("AM-")
    assert payload["audit"]["status"] == "DISABLED"
    assert set(payload["completed_agents"]) == {"sage", "guardian", "empath", "oracle"}
    assert len(repository.list_escalations()) == 1
