from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from api.db.base import Database
from api.db.models import (
    AgentFindingRecord,
    DecisionCitation,
    DecisionSession,
    IdempotencyRecord,
    Organization,
    ReviewAction,
    SaaSDecision,
    TenantEscalation,
)
from api.services.audit import record_audit
from api.tenancy import TenantContext, set_tenant_database_context


REDACTED = "[REDACTED BY RETENTION POLICY]"


def redact_expired_content(database: Database) -> int:
    redacted = 0
    with database.session() as session:
        organizations = session.scalars(select(Organization)).all()
        now = datetime.now(timezone.utc)
        for organization in organizations:
            set_tenant_database_context(session, organization.id)
            cutoff = now - timedelta(days=organization.raw_content_retention_days)
            decisions = session.scalars(
                select(SaaSDecision).where(
                    SaaSDecision.organization_id == organization.id,
                    SaaSDecision.created_at < cutoff,
                    SaaSDecision.content_redacted_at.is_(None),
                )
            ).all()
            escalations = session.scalars(
                select(TenantEscalation).where(
                    TenantEscalation.organization_id == organization.id,
                    TenantEscalation.created_at < cutoff,
                    TenantEscalation.content_redacted_at.is_(None),
                )
            ).all()
            for decision in decisions:
                decision.input = REDACTED
                decision.answer = REDACTED
                decision.factual_answer = REDACTED
                decision.reason = REDACTED
                decision.citations = []
                decision.agent_findings = {}
                decision.request_metadata = {}
                decision.content_redacted_at = now
                redacted += 1
            decision_ids = [decision.id for decision in decisions]
            if decision_ids:
                for citation in session.scalars(
                    select(DecisionCitation).where(
                        DecisionCitation.decision_id.in_(decision_ids)
                    )
                ).all():
                    citation.text = REDACTED
                    citation.source_metadata = {}
                for finding in session.scalars(
                    select(AgentFindingRecord).where(
                        AgentFindingRecord.decision_id.in_(decision_ids)
                    )
                ).all():
                    finding.output = None
                    finding.error = None
                for idempotency in session.scalars(
                    select(IdempotencyRecord).where(
                        IdempotencyRecord.decision_id.in_(decision_ids)
                    )
                ).all():
                    idempotency.response_payload = None
                    idempotency.status = "EXPIRED"
            for escalation in escalations:
                escalation.query = REDACTED
                escalation.draft_answer = REDACTED
                escalation.reason = REDACTED
                escalation.agent_findings = {}
                escalation.resolution_notes = REDACTED if escalation.resolution_notes else None
                escalation.content_redacted_at = now
                redacted += 1
            escalation_ids = [escalation.id for escalation in escalations]
            if escalation_ids:
                for action in session.scalars(
                    select(ReviewAction).where(
                        ReviewAction.escalation_id.in_(escalation_ids)
                    )
                ).all():
                    action.notes = REDACTED if action.notes else None
            for runtime_session in session.scalars(
                select(DecisionSession).where(
                    DecisionSession.organization_id == organization.id,
                    DecisionSession.last_activity_at < cutoff,
                    DecisionSession.end_user_id.is_not(None),
                )
            ).all():
                runtime_session.end_user_id = None
            if decisions or escalations:
                record_audit(
                    session,
                    TenantContext(
                        organization_id=organization.id,
                        workspace_id=None,
                        actor_id="retention-worker",
                        actor_type="SYSTEM",
                        role="platform",
                    ),
                    "retention.content_redacted",
                    "organization",
                    organization.id,
                    {"decisions": len(decisions), "escalations": len(escalations)},
                )
    return redacted
