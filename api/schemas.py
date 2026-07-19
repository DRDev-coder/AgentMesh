from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.schemas import (
    AgentFinding,
    AuditOutcome,
    DecisionState,
    EscalationPriority,
    EscalationStatus,
    SourceRecord,
)


QUERY_MAX_LENGTH = int(os.getenv("QUERY_MAX_LENGTH", "4000"))


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatRequest(APIModel):
    query: str = Field(min_length=1, max_length=QUERY_MAX_LENGTH)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class ChatResponse(APIModel):
    session_id: str
    query: str
    final_answer: str
    factual_answer: str
    decision_state: DecisionState
    decision_reason: str
    citations: list[SourceRecord]
    agent_findings: dict[str, AgentFinding]
    completed_agents: list[str]
    escalation_ticket_id: str | None = None
    audit: AuditOutcome
    # Compatibility fields retained while clients migrate from the prototype API.
    consensus_status: str
    consensus_reason: str
    agent_votes: dict[str, Any]
    escalate: bool
    blockchain_tx: str | None = None
    primary_agent: str | None = None
    confidence: float | None = None


class EscalationRecord(APIModel):
    ticket_id: str
    session_id: str
    query: str
    draft_answer: str
    reason: str
    priority: EscalationPriority
    agent_findings: dict[str, Any]
    status: EscalationStatus
    created_at: str
    updated_at: str
    resolution_notes: str | None = None


class EscalationUpdate(APIModel):
    draft_answer: str | None = Field(default=None, max_length=12000)
    priority: EscalationPriority | None = None
    status: EscalationStatus | None = None
    resolution_notes: str | None = Field(default=None, max_length=4000)


class EscalationAction(APIModel):
    answer: str | None = Field(default=None, max_length=12000)
    reason: str | None = Field(default=None, max_length=4000)
    resolution_notes: str | None = Field(default=None, max_length=4000)
