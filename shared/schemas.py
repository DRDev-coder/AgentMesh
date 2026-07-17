from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentState(str, Enum):
    AVAILABLE = "AVAILABLE"
    TIMEOUT = "TIMEOUT"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    MODEL_ERROR = "MODEL_ERROR"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"


class DecisionState(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_REWRITE = "APPROVED_WITH_REWRITE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    SYSTEM_UNAVAILABLE = "SYSTEM_UNAVAILABLE"


class GuardianStatus(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class GuardianAction(str, Enum):
    ALLOW = "allow"
    ESCALATE = "escalate"
    BLOCK = "block"


class OracleRecommendation(str, Enum):
    APPROVE = "APPROVE"
    CLARIFY = "CLARIFY"
    ESCALATE = "ESCALATE"


class EscalationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"


class AuditStatus(str, Enum):
    DISABLED = "DISABLED"
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class SourceRecord(StrictModel):
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance_or_similarity: float = Field(ge=0.0, le=1.0)


class SageOutput(StrictModel):
    answer: str
    confidence: float = Field(ge=0.0, le=100.0)
    citations: list[SourceRecord] = Field(default_factory=list)
    retrieval_quality: float = Field(ge=0.0, le=1.0)
    insufficient_data: bool
    generation_mode: Literal["deterministic", "groq", "deterministic_fallback"]
    warnings: list[str] = Field(default_factory=list)


class GuardianOutput(StrictModel):
    status: GuardianStatus
    violations: list[str] = Field(default_factory=list)
    action: GuardianAction
    reasoning: str
    confidence: float = Field(ge=0.0, le=100.0)
    blocking: bool
    deterministic_violations: list[str] = Field(default_factory=list)
    semantic_violations: list[str] = Field(default_factory=list)
    safe_guidance: str | None = None


class EmpathOutput(StrictModel):
    emotion: str
    urgency: int = Field(ge=0, le=10)
    sentiment_label: str
    sentiment_score: float = Field(ge=0.0, le=1.0)
    recommended_tone: str
    churn_risk: bool
    requires_urgent_review: bool = False


class ClaimVerification(StrictModel):
    claim: str
    supported: bool
    source_ids: list[str] = Field(default_factory=list)
    reason: str
    support_score: float = Field(ge=0.0, le=1.0)


class OracleOutput(StrictModel):
    claims: list[ClaimVerification] = Field(default_factory=list)
    overall_supported: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=100.0)
    recommendation: OracleRecommendation


class AgentFinding(StrictModel):
    state: AgentState
    output: dict[str, Any] | None = None
    error: str | None = None


class DecisionResult(StrictModel):
    state: DecisionState
    reason: str
    create_escalation: bool = False
    priority: EscalationPriority | None = None
    response_source: Literal["draft", "security", "clarification", "unavailable"]
    rewrite_tone: bool = False


class AuditOutcome(StrictModel):
    status: AuditStatus
    transaction_hash: str | None = None
    error: str | None = None
    network: str | None = None
    explorer_url: str | None = None


class AgentRequest(StrictModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)


class SageResponse(StrictModel):
    agent: Literal["sage"] = "sage"
    session_id: str
    state: AgentState
    output: SageOutput | None = None
    error: str | None = None


class GuardianRequest(AgentRequest):
    proposed_answer: str = Field(default="", max_length=12000)


class GuardianResponse(StrictModel):
    agent: Literal["guardian"] = "guardian"
    session_id: str
    state: AgentState
    output: GuardianOutput | None = None
    error: str | None = None


class EmpathResponse(StrictModel):
    agent: Literal["empath"] = "empath"
    session_id: str
    state: AgentState
    output: EmpathOutput | None = None
    error: str | None = None


class OracleRequest(AgentRequest):
    draft_answer: str = Field(max_length=12000)
    sources: list[SourceRecord] = Field(default_factory=list)


class OracleResponse(StrictModel):
    agent: Literal["oracle"] = "oracle"
    session_id: str
    state: AgentState
    output: OracleOutput | None = None
    error: str | None = None
