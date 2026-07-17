from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from api.db.base import Database
from api.db.models import (
    AgentFindingRecord,
    DecisionCitation,
    DecisionSession,
    SaaSDecision,
    TenantEscalation,
)
from api.services.audit import record_audit
from api.services.email import queue_review_notifications
from api.services.webhooks import queue_event
from api.tenancy import TenantContext, set_tenant_database_context


@dataclass(frozen=True, slots=True)
class CreatedTenantTicket:
    ticket_id: str


class TenantDecisionPersistence:
    """Request-bound persistence adapter consumed by the proven orchestrator."""

    def __init__(
        self,
        database: Database,
        context: TenantContext,
        *,
        api_key_id: str,
        environment: str,
        end_user_id: str | None,
        metadata: dict,
        profile_version_id: str | None,
        knowledge_release_id: str | None,
        model_id: str,
    ):
        self.database = database
        self.context = context
        self.api_key_id = api_key_id
        self.environment = environment
        self.end_user_id = end_user_id
        self.metadata = metadata
        self.profile_version_id = profile_version_id
        self.knowledge_release_id = knowledge_release_id
        self.model_id = model_id
        self.last_decision_id: str | None = None
        self.last_created_at: datetime | None = None

    def create_escalation(
        self,
        *,
        session_id: str,
        query: str,
        draft_answer: str,
        reason: str,
        priority,
        agent_findings: dict,
    ) -> CreatedTenantTicket:
        with self.database.session() as session:
            set_tenant_database_context(session, self.context.organization_id)
            value = TenantEscalation(
                organization_id=self.context.organization_id,
                workspace_id=self.context.workspace_id,
                session_id=session_id,
                query=query,
                draft_answer=draft_answer,
                reason=reason,
                priority=getattr(priority, "value", str(priority)),
                agent_findings=agent_findings,
            )
            session.add(value)
            session.flush()
            record_audit(
                session,
                self.context,
                "escalation.created",
                "escalation",
                value.id,
                {"priority": value.priority},
            )
            queue_event(
                session,
                self.context.organization_id,
                self.context.workspace_id,
                "escalation.created",
                {
                    "id": value.id,
                    "type": "escalation.created",
                    "workspace_id": self.context.workspace_id,
                    "data": {
                        "escalation_id": value.id,
                        "session_id": session_id,
                        "status": value.status,
                        "priority": value.priority,
                    },
                },
            )
            queue_review_notifications(
                session,
                self.context.organization_id,
                self.context.workspace_id,
                value.id,
                value.priority,
            )
            return CreatedTenantTicket(ticket_id=value.id)

    def create_decision(
        self,
        *,
        session_id: str,
        query: str,
        factual_answer: str,
        final_answer: str,
        decision_state: str,
        decision_reason: str,
        agent_findings: dict,
        citations: list[dict],
        audit: dict,
        escalation_ticket_id: str | None,
    ) -> str:
        del audit
        with self.database.session() as session:
            set_tenant_database_context(session, self.context.organization_id)
            value = SaaSDecision(
                organization_id=self.context.organization_id,
                workspace_id=self.context.workspace_id,
                api_key_id=self.api_key_id,
                environment=self.environment,
                session_id=session_id,
                end_user_id=self.end_user_id,
                input=query,
                answer=final_answer,
                factual_answer=factual_answer,
                state=decision_state,
                reason=decision_reason,
                citations=citations,
                agent_findings=agent_findings,
                request_metadata=self.metadata,
                profile_version_id=self.profile_version_id,
                knowledge_release_id=self.knowledge_release_id,
                model_id=self.model_id,
                escalation_id=escalation_ticket_id,
            )
            session.add(value)
            session.flush()
            runtime_session = session.scalar(
                select(DecisionSession).where(
                    DecisionSession.organization_id == self.context.organization_id,
                    DecisionSession.workspace_id == self.context.workspace_id,
                    DecisionSession.environment == self.environment,
                    DecisionSession.session_id == session_id,
                )
            )
            if runtime_session is None:
                runtime_session = DecisionSession(
                    organization_id=self.context.organization_id,
                    workspace_id=self.context.workspace_id,
                    environment=self.environment,
                    session_id=session_id,
                    end_user_id=self.end_user_id,
                )
                session.add(runtime_session)
            else:
                runtime_session.last_activity_at = datetime.now(timezone.utc)
            for position, citation in enumerate(citations):
                session.add(
                    DecisionCitation(
                        organization_id=self.context.organization_id,
                        workspace_id=self.context.workspace_id,
                        decision_id=value.id,
                        position=position,
                        document_id=str(citation.get("document_id", "")),
                        chunk_id=str(citation.get("chunk_id", "")),
                        text=str(citation.get("text", "")),
                        source_metadata=dict(citation.get("metadata") or {}),
                        similarity=float(
                            citation.get("distance_or_similarity", 0)
                        ),
                    )
                )
            for agent_name, finding in agent_findings.items():
                session.add(
                    AgentFindingRecord(
                        organization_id=self.context.organization_id,
                        workspace_id=self.context.workspace_id,
                        decision_id=value.id,
                        agent_name=agent_name,
                        state=str(finding.get("state", "UNKNOWN")),
                        output=finding.get("output"),
                        error=finding.get("error"),
                    )
                )
            if escalation_ticket_id:
                escalation = session.get(TenantEscalation, escalation_ticket_id)
                if escalation:
                    escalation.decision_id = value.id
            self.last_decision_id = value.id
            self.last_created_at = value.created_at
            return value.id

    def update_decision_audit(self, decision_id: str, audit: dict) -> None:
        del decision_id, audit
        # PostgreSQL is authoritative for SaaS requests; optional blockchain data is
        # deliberately excluded from the tenant decision record.
