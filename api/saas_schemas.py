from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from shared.schemas import AgentFinding, DecisionState, SourceRecord


class SaaSModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", from_attributes=True, protected_namespaces=()
    )


class OrganizationCreate(SaaSModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=80)
    workspace_name: str = Field(default="Support", min_length=2, max_length=160)
    workspace_slug: str | None = Field(default=None, min_length=2, max_length=80)
    industry_template: Literal["GENERAL", "FINANCE", "HEALTHCARE", "ECOMMERCE"] = "GENERAL"


class OrganizationView(SaaSModel):
    id: str
    name: str
    slug: str
    role: str
    status: str
    billing_email: str
    spend_cap_cents: int | None
    created_at: datetime


class WorkspaceCreate(SaaSModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=80)
    industry_template: Literal["GENERAL", "FINANCE", "HEALTHCARE", "ECOMMERCE"] = "GENERAL"


class WorkspaceView(SaaSModel):
    id: str
    organization_id: str
    name: str
    slug: str
    industry_template: str
    status: str
    active_profile_version_id: str | None
    active_knowledge_release_id: str | None
    created_at: datetime


class OnboardingResult(SaaSModel):
    organization: OrganizationView
    workspace: WorkspaceView


class MemberView(SaaSModel):
    id: str
    auth_user_id: str
    email: str
    role: str
    status: str
    created_at: datetime


class MemberUpdate(SaaSModel):
    role: Literal["admin", "developer", "reviewer", "viewer"]
    status: Literal["ACTIVE", "SUSPENDED"] = "ACTIVE"


class OwnershipTransfer(SaaSModel):
    auth_user_id: str = Field(min_length=1, max_length=128)


class InvitationCreate(SaaSModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["admin", "developer", "reviewer", "viewer"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must be valid")
        return value


class InvitationView(SaaSModel):
    id: str
    organization_id: str
    email: str
    role: str
    expires_at: datetime
    invite_url: str | None = None


class ProfileDraft(SaaSModel):
    template_key: Literal["GENERAL", "FINANCE", "HEALTHCARE", "ECOMMERCE"]
    tone: Literal["PROFESSIONAL", "FRIENDLY", "PATIENT", "EMPATHETIC"] = "PROFESSIONAL"
    response_length: Literal["CONCISE", "BALANCED", "DETAILED"] = "CONCISE"
    custom_instructions: str = Field(default="", max_length=2000)
    supported_topics: list[str] = Field(default_factory=list, max_length=50)
    enabled_rule_packs: list[str] = Field(default_factory=list, max_length=20)
    escalation_threshold: int = Field(default=7, ge=1, le=10)

    @field_validator("custom_instructions")
    @classmethod
    def reject_prompt_control(cls, value: str) -> str:
        lowered = value.lower()
        prohibited = (
            "ignore previous",
            "system prompt",
            "disable safety",
            "bypass guardian",
            "developer mode",
        )
        if any(term in lowered for term in prohibited):
            raise ValueError("custom instructions cannot alter platform safety controls")
        return value.strip()

    @model_validator(mode="after")
    def approved_rule_packs_only(self) -> "ProfileDraft":
        approved = {
            "GENERAL": {"GLOBAL_SAFETY"},
            "FINANCE": {"GLOBAL_SAFETY", "FINANCE_SUPPORT"},
            "HEALTHCARE": {"GLOBAL_SAFETY", "HEALTHCARE_INFORMATION"},
            "ECOMMERCE": {"GLOBAL_SAFETY", "ECOMMERCE_SUPPORT"},
        }[self.template_key]
        unsupported = set(self.enabled_rule_packs) - approved
        if unsupported:
            raise ValueError(
                f"unsupported rule packs for {self.template_key}: {sorted(unsupported)}"
            )
        return self


class ProfileView(ProfileDraft):
    id: str
    organization_id: str
    workspace_id: str
    version: int
    status: str
    published_at: datetime | None
    created_at: datetime


class DocumentView(SaaSModel):
    id: str
    organization_id: str
    workspace_id: str
    name: str
    status: str
    current_version: int
    filename: str | None = None
    media_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    extraction_error: str | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeReleaseView(SaaSModel):
    id: str
    organization_id: str
    workspace_id: str
    version: int
    status: str
    document_version_ids: list[str]
    published_at: datetime


class DocumentPreviewChunk(SaaSModel):
    chunk_index: int
    page_number: int | None
    text: str


class DocumentPreview(SaaSModel):
    document_id: str
    document_version_id: str
    version: int
    chunks: list[DocumentPreviewChunk]


class APIKeyCreate(SaaSModel):
    name: str = Field(min_length=2, max_length=120)
    environment: Literal["test", "live"] = "test"
    scopes: list[Literal["decisions:write", "decisions:read", "traces:read"]] = Field(
        default_factory=lambda: ["decisions:write"], max_length=3
    )
    expires_at: datetime | None = None


class APIKeyView(SaaSModel):
    id: str
    organization_id: str
    workspace_id: str
    name: str
    environment: str
    scopes: list[str]
    last_four: str
    status: str
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class APIKeyCreated(APIKeyView):
    secret: str


class PublicDecisionRequest(SaaSModel):
    input: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    end_user_id: str | None = Field(default=None, min_length=1, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("input")
    @classmethod
    def strip_input(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("input cannot be blank")
        return value

    @field_validator("metadata")
    @classmethod
    def constrain_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20:
            raise ValueError("metadata supports at most 20 keys")
        if len(str(value).encode("utf-8")) > 4096:
            raise ValueError("metadata must be at most 4 KB")
        return value


class DecisionTrace(SaaSModel):
    agent_findings: dict[str, AgentFinding]
    profile_version_id: str | None
    knowledge_release_id: str | None
    model_id: str


class PublicDecisionResponse(SaaSModel):
    id: str
    session_id: str
    answer: str
    decision_state: DecisionState
    decision_reason: str
    citations: list[SourceRecord]
    trace: DecisionTrace | None
    escalation_id: str | None
    usage_units: int
    created_at: datetime


class DecisionListItem(SaaSModel):
    id: str
    session_id: str
    state: str
    reason: str
    environment: str
    escalation_id: str | None
    usage_units: int
    created_at: datetime


class UsageSummary(SaaSModel):
    organization_id: str
    period: str
    completed_decisions: int
    included_decisions: int
    overage_decisions: int
    remaining_free_decisions: int
    billing_status: str
    payment_method_present: bool
    spend_cap_cents: int | None
    projected_overage_cents: int | None
    stripe_projection_is_async: bool = True


class SpendCapUpdate(SaaSModel):
    spend_cap_cents: int | None = Field(default=None, ge=0, le=100_000_000)


class CheckoutResult(SaaSModel):
    url: str


class BillingPortalResult(SaaSModel):
    url: str


class ReviewClaim(SaaSModel):
    answer: str | None = Field(default=None, max_length=12000)
    notes: str | None = Field(default=None, max_length=4000)
    expected_version: int = Field(ge=1)


class TenantEscalationView(SaaSModel):
    id: str
    organization_id: str
    workspace_id: str
    decision_id: str | None
    session_id: str
    query: str
    draft_answer: str
    reason: str
    priority: str
    agent_findings: dict[str, Any]
    status: str
    assigned_to: str | None
    resolution_notes: str | None
    lock_version: int
    created_at: datetime
    updated_at: datetime


class WebhookCreate(SaaSModel):
    url: HttpUrl
    event_types: list[
        Literal["escalation.created", "escalation.updated", "escalation.resolved"]
    ] = Field(min_length=1, max_length=3)


class WebhookView(SaaSModel):
    id: str
    organization_id: str
    workspace_id: str
    url: str
    event_types: list[str]
    status: str
    created_at: datetime


class WebhookCreated(WebhookView):
    signing_secret: str


class WebhookDeliveryView(SaaSModel):
    id: str
    endpoint_id: str
    event_type: str
    status: str
    attempts: int
    response_status: int | None
    last_error: str | None
    next_attempt_at: datetime
    created_at: datetime


class PlatformOrganizationView(SaaSModel):
    id: str
    name: str
    slug: str
    status: str
    billing_email: str
    created_at: datetime
