from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from api.services.storage import SQLiteRepository
from shared.schemas import EscalationPriority, EscalationStatus


def _create(repository: SQLiteRepository, *, session_id: str = "session-1"):
    return repository.create_escalation(
        session_id=session_id,
        query="I see an unauthorized transfer.",
        draft_answer="Use the approved fraud reporting process.",
        reason="Urgent fraud report requires prototype review.",
        priority=EscalationPriority.HIGH,
        agent_findings={"guardian": {"status": "WARNING"}},
    )


def test_sqlite_escalation_create_and_retrieve(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")
    record = _create(repository)

    assert record.ticket_id.startswith("AM-")
    assert record.session_id == "session-1"
    assert record.status is EscalationStatus.OPEN
    assert record.priority is EscalationPriority.HIGH
    assert record.agent_findings == {"guardian": {"status": "WARNING"}}
    assert repository.get_escalation(record.ticket_id) == record


def test_sqlite_escalation_list_and_status_filter(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")
    first = _create(repository, session_id="one")
    second = _create(repository, session_id="two")
    repository.update_escalation(
        second.ticket_id,
        status=EscalationStatus.RESOLVED,
        resolution_notes="Reviewed in the prototype queue.",
    )

    assert {item.ticket_id for item in repository.list_escalations()} == {
        first.ticket_id,
        second.ticket_id,
    }
    assert [
        item.ticket_id
        for item in repository.list_escalations(EscalationStatus.RESOLVED)
    ] == [second.ticket_id]
    assert [
        item.ticket_id for item in repository.list_escalations(EscalationStatus.OPEN)
    ] == [first.ticket_id]


def test_sqlite_escalation_update_edit_and_resolve(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")
    record = _create(repository)

    updated = repository.update_escalation(
        record.ticket_id,
        draft_answer="Edited response grounded in policy.",
        priority=EscalationPriority.CRITICAL,
        status=EscalationStatus.RESOLVED,
        resolution_notes="Reviewer completed the prototype workflow.",
    )

    assert updated.draft_answer == "Edited response grounded in policy."
    assert updated.priority is EscalationPriority.CRITICAL
    assert updated.status is EscalationStatus.RESOLVED
    assert updated.resolution_notes == "Reviewer completed the prototype workflow."
    assert updated.updated_at >= updated.created_at


def test_missing_escalation_raises_key_error(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")
    with pytest.raises(KeyError):
        repository.get_escalation("AM-NOT-FOUND")
    with pytest.raises(KeyError):
        repository.update_escalation(
            "AM-NOT-FOUND", status=EscalationStatus.REJECTED
        )


def test_repository_health_checks_a_real_sqlite_write(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")

    assert repository.health() is True
    with sqlite3.connect(repository.path) as connection:
        checked_at = connection.execute(
            "SELECT checked_at FROM readiness_probe WHERE singleton = 1"
        ).fetchone()[0]
    assert checked_at


def test_decision_audit_can_reference_escalation(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")
    escalation = _create(repository)
    decision_id = repository.create_decision(
        session_id=escalation.session_id,
        query=escalation.query,
        factual_answer=escalation.draft_answer,
        final_answer="Sent to prototype review.",
        decision_state="ESCALATED",
        decision_reason=escalation.reason,
        agent_findings=escalation.agent_findings,
        citations=[],
        audit={"status": "DISABLED"},
        escalation_ticket_id=escalation.ticket_id,
    )

    with sqlite3.connect(repository.path) as connection:
        row = connection.execute(
            "SELECT decision_state, escalation_ticket_id FROM decision_log "
            "WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    assert row == ("ESCALATED", escalation.ticket_id)


def test_optional_audit_outcome_updates_existing_local_decision(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "review.db")
    decision_id = repository.create_decision(
        session_id="session-audit",
        query="Refund policy",
        factual_answer="Approved policy draft",
        final_answer="Approved policy draft",
        decision_state="APPROVED",
        decision_reason="Grounded and safe",
        agent_findings={},
        citations=[],
        audit={"status": "PENDING"},
        escalation_ticket_id=None,
    )

    repository.update_decision_audit(
        decision_id,
        {"status": "CONFIRMED", "transaction_hash": "0xabc"},
    )

    with sqlite3.connect(repository.path) as connection:
        stored = connection.execute(
            "SELECT audit FROM decision_log WHERE decision_id = ?", (decision_id,)
        ).fetchone()[0]
    assert json.loads(stored) == {
        "status": "CONFIRMED",
        "transaction_hash": "0xabc",
    }
