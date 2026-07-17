from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from agents.empath.service import EmpathService
from agents.guardian.service import GuardianService
from agents.sage.service import SageService
from api.config import Settings
from api.db.base import Database
from api.db.models import (
    AbuseSignal,
    IdempotencyRecord,
    SaaSDecision,
    UsageReservation,
    Workspace,
    WorkspaceProfileVersion,
)
from api.errors import APIError
from api.saas_schemas import (
    DecisionTrace,
    PublicDecisionRequest,
    PublicDecisionResponse,
)
from api.services.api_keys import APIKeyPrincipal
from api.services.dlp import reject_sensitive_input
from api.services.knowledge import retrieve_sources
from api.services.orchestrator import AgentOrchestrator
from api.services.tenant_persistence import TenantDecisionPersistence
from api.services.usage import finalize_usage, release_usage, reserve_usage
from api.tenancy import TenantContext, set_tenant_database_context
from shared.schemas import DecisionState, SourceRecord


class RetrievedEvidenceEngine:
    def __init__(self, sources: list[SourceRecord]):
        self.sources = sources

    @property
    def ready(self) -> bool:
        return True

    def search(self, query: str, n_results: int = 3) -> list[SourceRecord]:
        del query
        return self.sources[:n_results]


def _request_digest(payload: PublicDecisionRequest) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _profile(
    session: Session, workspace: Workspace, environment: str
) -> WorkspaceProfileVersion | None:
    if environment == "test":
        draft = session.scalar(
            select(WorkspaceProfileVersion)
            .where(
                WorkspaceProfileVersion.workspace_id == workspace.id,
                WorkspaceProfileVersion.status == "DRAFT",
            )
            .order_by(WorkspaceProfileVersion.version.desc())
            .limit(1)
        )
        if draft:
            return draft
    return (
        session.get(WorkspaceProfileVersion, workspace.active_profile_version_id)
        if workspace.active_profile_version_id
        else None
    )


def _stored_response(record: IdempotencyRecord) -> PublicDecisionResponse:
    if not record.response_payload:
        raise APIError(409, "request_in_progress", "This idempotent request is still processing.")
    return PublicDecisionResponse.model_validate(record.response_payload)


async def create_decision(
    *,
    session: Session,
    database: Database,
    settings: Settings,
    orchestrator: AgentOrchestrator,
    key: APIKeyPrincipal,
    idempotency_key: str,
    payload: PublicDecisionRequest,
) -> PublicDecisionResponse:
    key.require("decisions:write")
    try:
        reject_sensitive_input(payload.input)
    except APIError:
        session.add(
            AbuseSignal(
                organization_id=key.organization_id,
                workspace_id=key.workspace_id,
                api_key_id=key.key_id,
                signal_type="SENSITIVE_DATA_BLOCKED",
                details={"environment": key.environment},
            )
        )
        session.commit()
        raise
    digest = _request_digest(payload)
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text(
                "SELECT pg_advisory_xact_lock(hashtext(:lock_key))"
            ),
            {"lock_key": f"idempotency:{key.organization_id}:{key.key_id}:{idempotency_key}"},
        )
    existing = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.organization_id == key.organization_id,
            IdempotencyRecord.api_key_id == key.key_id,
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing:
        if existing.request_digest != digest:
            raise APIError(
                409,
                "idempotency_conflict",
                "Idempotency-Key was already used with a different request.",
            )
        if existing.status == "COMPLETED":
            if not existing.response_payload:
                raise APIError(
                    409,
                    "idempotency_expired",
                    "The retained response for this idempotency key has expired.",
                )
            return _stored_response(existing)
        if existing.status == "EXPIRED":
            raise APIError(
                409,
                "idempotency_expired",
                "The retained response for this idempotency key has expired.",
            )
        if existing.status == "PROCESSING":
            created_at = existing.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at >= datetime.now(timezone.utc) - timedelta(minutes=10):
                raise APIError(409, "request_in_progress", "This request is already processing.")
        existing.status = "PROCESSING"
        existing.response_payload = None
        idempotency = existing
    else:
        idempotency = IdempotencyRecord(
            organization_id=key.organization_id,
            api_key_id=key.key_id,
            key=idempotency_key,
            request_digest=digest,
        )
        session.add(idempotency)
    reservation = reserve_usage(
        session,
        settings,
        key.organization_id,
        key.workspace_id,
        idempotency_key,
    )
    session.commit()
    reservation_id = reservation.id
    try:
        set_tenant_database_context(session, key.organization_id)
        workspace = session.scalar(
            select(Workspace).where(
                Workspace.id == key.workspace_id,
                Workspace.organization_id == key.organization_id,
                Workspace.status == "ACTIVE",
            )
        )
        if workspace is None:
            raise APIError(404, "workspace_not_found", "Workspace is unavailable.")
        profile = _profile(session, workspace, key.environment)
        sources, release_id = retrieve_sources(
            session,
            key.organization_id,
            key.workspace_id,
            key.environment,
            payload.input,
        )
        context = TenantContext(
            organization_id=key.organization_id,
            workspace_id=key.workspace_id,
            actor_id=key.key_id,
            actor_type="API_KEY",
            role="developer",
        )
        persistence = TenantDecisionPersistence(
            database,
            context,
            api_key_id=key.key_id,
            environment=key.environment,
            end_user_id=payload.end_user_id,
            metadata=payload.metadata,
            profile_version_id=profile.id if profile else None,
            knowledge_release_id=release_id,
            model_id=orchestrator.sage.model,
        )
        response = await orchestrator.process(
            payload.input,
            payload.session_id or str(uuid.uuid4()),
            sage=SageService(
                engine=RetrievedEvidenceEngine(sources),
                system_instructions=(
                    "Workspace template: "
                    f"{profile.template_key}. Supported topics: "
                    f"{', '.join(profile.supported_topics) or 'workspace knowledge only'}. "
                    f"Approved instructions: {profile.custom_instructions}"
                    if profile
                    else ""
                ),
                response_length=profile.response_length if profile else "CONCISE",
            ),
            guardian=GuardianService(
                rule_packs=profile.enabled_rule_packs if profile else ["GLOBAL_SAFETY"]
            ),
            empath=EmpathService(
                preferred_tone=profile.tone if profile else "PROFESSIONAL"
            ),
            repository=persistence,
            include_prototype_notice=False,
            escalation_threshold=profile.escalation_threshold if profile else None,
        )
        if persistence.last_decision_id is None or persistence.last_created_at is None:
            raise RuntimeError("Tenant decision was not persisted")
        set_tenant_database_context(session, key.organization_id)
        reservation = session.get(UsageReservation, reservation_id)
        if reservation is None:
            raise RuntimeError("Usage reservation disappeared")
        usage_units = 0
        if response.decision_state is DecisionState.SYSTEM_UNAVAILABLE:
            release_usage(reservation)
        else:
            finalize_usage(
                session, settings, reservation, persistence.last_decision_id
            )
            usage_units = 1
        decision = session.get(SaaSDecision, persistence.last_decision_id)
        if decision:
            decision.usage_units = usage_units
        trace = None
        if "traces:read" in key.scopes:
            trace = DecisionTrace(
                agent_findings=response.agent_findings,
                profile_version_id=profile.id if profile else None,
                knowledge_release_id=release_id,
                model_id=orchestrator.sage.model,
            )
        public = PublicDecisionResponse(
            id=persistence.last_decision_id,
            session_id=response.session_id,
            answer=response.final_answer,
            decision_state=response.decision_state,
            decision_reason=response.decision_reason,
            citations=response.citations,
            trace=trace,
            escalation_id=response.escalation_ticket_id,
            usage_units=usage_units,
            created_at=persistence.last_created_at,
        )
        idempotency = session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.id == idempotency.id)
        )
        if idempotency:
            idempotency.status = "COMPLETED"
            idempotency.decision_id = persistence.last_decision_id
            idempotency.response_payload = public.model_dump(mode="json")
        session.commit()
        return public
    except Exception:
        session.rollback()
        set_tenant_database_context(session, key.organization_id)
        failed_reservation = session.get(UsageReservation, reservation_id)
        if failed_reservation and failed_reservation.status == "RESERVED":
            release_usage(failed_reservation)
        failed_idempotency = session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.organization_id == key.organization_id,
                IdempotencyRecord.api_key_id == key.key_id,
                IdempotencyRecord.key == idempotency_key,
            )
        )
        if failed_idempotency:
            failed_idempotency.status = "FAILED"
        session.commit()
        raise


def decision_response(
    decision: SaaSDecision, include_trace: bool
) -> PublicDecisionResponse:
    return PublicDecisionResponse(
        id=decision.id,
        session_id=decision.session_id,
        answer=decision.answer,
        decision_state=DecisionState(decision.state),
        decision_reason=decision.reason,
        citations=[SourceRecord.model_validate(value) for value in decision.citations],
        trace=(
            DecisionTrace(
                agent_findings=decision.agent_findings,
                profile_version_id=decision.profile_version_id,
                knowledge_release_id=decision.knowledge_release_id,
                model_id=decision.model_id,
            )
            if include_trace
            else None
        ),
        escalation_id=decision.escalation_id,
        usage_units=decision.usage_units,
        created_at=decision.created_at,
    )
