from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.schemas import EscalationRecord
from shared.schemas import EscalationPriority, EscalationStatus


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteRepository:
    """Persistent prototype audit and human-review queue."""

    def __init__(self, database_path: str | Path | None = None):
        default = Path(tempfile.gettempdir()) / "agentmesh" / "agentmesh.db"
        self.path = Path(database_path or os.getenv("DATABASE_PATH", str(default)))
        self._lock = threading.RLock()
        self._initialized = False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS escalations (
                        ticket_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        query TEXT NOT NULL,
                        draft_answer TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        agent_findings TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        resolution_notes TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_escalations_status_created
                    ON escalations(status, created_at DESC);

                    CREATE TABLE IF NOT EXISTS decision_log (
                        decision_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        query TEXT NOT NULL,
                        factual_answer TEXT NOT NULL,
                        final_answer TEXT NOT NULL,
                        decision_state TEXT NOT NULL,
                        decision_reason TEXT NOT NULL,
                        agent_findings TEXT NOT NULL,
                        citations TEXT NOT NULL,
                        audit TEXT NOT NULL,
                        escalation_ticket_id TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(escalation_ticket_id) REFERENCES escalations(ticket_id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_decision_session_created
                    ON decision_log(session_id, created_at DESC);

                    CREATE TABLE IF NOT EXISTS readiness_probe (
                        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                        checked_at TEXT NOT NULL
                    );
                    """
                )
            self._initialized = True

    def health(self) -> bool:
        try:
            self._ensure_initialized()
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO readiness_probe(singleton, checked_at)
                    VALUES (1, ?)
                    ON CONFLICT(singleton) DO UPDATE SET checked_at = excluded.checked_at
                    """,
                    (_utc_now(),),
                )
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except Exception:
            return False

    def create_escalation(
        self,
        *,
        session_id: str,
        query: str,
        draft_answer: str,
        reason: str,
        priority: EscalationPriority,
        agent_findings: dict[str, Any],
    ) -> EscalationRecord:
        self._ensure_initialized()
        now = _utc_now()
        ticket_id = f"AM-{uuid.uuid4().hex[:10].upper()}"
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO escalations (
                    ticket_id, session_id, query, draft_answer, reason, priority,
                    agent_findings, status, created_at, updated_at, resolution_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    ticket_id,
                    session_id,
                    query,
                    draft_answer,
                    reason,
                    priority.value,
                    json.dumps(agent_findings, sort_keys=True),
                    EscalationStatus.OPEN.value,
                    now,
                    now,
                ),
            )
        return self.get_escalation(ticket_id)

    def list_escalations(
        self, status: EscalationStatus | None = None, limit: int = 100
    ) -> list[EscalationRecord]:
        self._ensure_initialized()
        query = "SELECT * FROM escalations"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_escalation(row) for row in rows]

    def get_escalation(self, ticket_id: str) -> EscalationRecord:
        self._ensure_initialized()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM escalations WHERE ticket_id = ?", (ticket_id,)
            ).fetchone()
        if row is None:
            raise KeyError(ticket_id)
        return self._row_to_escalation(row)

    def update_escalation(
        self,
        ticket_id: str,
        *,
        draft_answer: str | None = None,
        priority: EscalationPriority | None = None,
        status: EscalationStatus | None = None,
        resolution_notes: str | None = None,
    ) -> EscalationRecord:
        self._ensure_initialized()
        updates: dict[str, Any] = {"updated_at": _utc_now()}
        if draft_answer is not None:
            updates["draft_answer"] = draft_answer
        if priority is not None:
            updates["priority"] = priority.value
        if status is not None:
            updates["status"] = status.value
        if resolution_notes is not None:
            updates["resolution_notes"] = resolution_notes
        assignments = ", ".join(f"{column} = ?" for column in updates)
        values = [*updates.values(), ticket_id]
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE escalations SET {assignments} WHERE ticket_id = ?", values
            )
            if cursor.rowcount == 0:
                raise KeyError(ticket_id)
        return self.get_escalation(ticket_id)

    def create_decision(
        self,
        *,
        session_id: str,
        query: str,
        factual_answer: str,
        final_answer: str,
        decision_state: str,
        decision_reason: str,
        agent_findings: dict[str, Any],
        citations: list[dict[str, Any]],
        audit: dict[str, Any],
        escalation_ticket_id: str | None,
    ) -> str:
        self._ensure_initialized()
        decision_id = str(uuid.uuid4())
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO decision_log (
                    decision_id, session_id, query, factual_answer, final_answer,
                    decision_state, decision_reason, agent_findings, citations,
                    audit, escalation_ticket_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    session_id,
                    query,
                    factual_answer,
                    final_answer,
                    decision_state,
                    decision_reason,
                    json.dumps(agent_findings, sort_keys=True),
                    json.dumps(citations, sort_keys=True),
                    json.dumps(audit, sort_keys=True),
                    escalation_ticket_id,
                    _utc_now(),
                ),
            )
        return decision_id

    def update_decision_audit(
        self, decision_id: str, audit: dict[str, Any]
    ) -> None:
        """Persist the optional audit-sink outcome after the local record exists."""
        self._ensure_initialized()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE decision_log SET audit = ? WHERE decision_id = ?",
                (json.dumps(audit, sort_keys=True), decision_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(decision_id)

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    @staticmethod
    def _row_to_escalation(row: sqlite3.Row) -> EscalationRecord:
        return EscalationRecord(
            ticket_id=row["ticket_id"],
            session_id=row["session_id"],
            query=row["query"],
            draft_answer=row["draft_answer"],
            reason=row["reason"],
            priority=EscalationPriority(row["priority"]),
            agent_findings=json.loads(row["agent_findings"]),
            status=EscalationStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolution_notes=row["resolution_notes"],
        )
