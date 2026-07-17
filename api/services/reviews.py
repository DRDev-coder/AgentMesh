from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.guardian.service import GuardianService
from agents.oracle.service import OracleService
from api.db.models import (
    ReviewAction,
    SaaSDecision,
    TenantEscalation,
    Workspace,
    WorkspaceProfileVersion,
)
from api.errors import APIError
from api.saas_schemas import ReviewClaim
from api.services.audit import record_audit
from api.services.webhooks import queue_event
from api.tenancy import TenantContext
from shared.schemas import GuardianStatus, SourceRecord


FINAL_STATES = {"APPROVED", "REJECTED", "RESOLVED"}


def list_escalations(
    session: Session,
    organization_id: str,
    workspace_id: str,
    status: str | None = None,
) -> list[TenantEscalation]:
    query = select(TenantEscalation).where(
        TenantEscalation.organization_id == organization_id,
        TenantEscalation.workspace_id == workspace_id,
    )
    if status:
        query = query.where(TenantEscalation.status == status)
    return list(
        session.scalars(query.order_by(TenantEscalation.created_at.desc())).all()
    )


def get_escalation(
    session: Session, context: TenantContext, escalation_id: str, *, lock: bool = False
) -> TenantEscalation:
    query = select(TenantEscalation).where(
        TenantEscalation.id == escalation_id,
        TenantEscalation.organization_id == context.organization_id,
        TenantEscalation.workspace_id == context.workspace_id,
    )
    if lock:
        query = query.with_for_update()
    value = session.scalar(query)
    if value is None:
        raise APIError(404, "not_found", "Escalation not found.")
    return value


def _check_version(value: TenantEscalation, expected: int) -> None:
    if value.lock_version != expected:
        raise APIError(
            409,
            "review_conflict",
            "The escalation changed. Refresh it before taking another action.",
            details={"current_version": value.lock_version},
        )


def _record_transition(
    session: Session,
    context: TenantContext,
    value: TenantEscalation,
    prior_status: str,
    new_status: str,
    action: str,
    notes: str | None,
) -> None:
    session.add(
        ReviewAction(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            escalation_id=value.id,
            actor_id=context.actor_id,
            action=action,
            prior_status=prior_status,
            new_status=new_status,
            notes=notes,
        )
    )
    record_audit(
        session,
        context,
        f"review.{action.lower()}",
        "escalation",
        value.id,
        {"from": prior_status, "to": new_status, "lock_version": value.lock_version},
    )
    event_type = (
        "escalation.resolved" if new_status in FINAL_STATES else "escalation.updated"
    )
    queue_event(
        session,
        context.organization_id,
        context.workspace_id,
        event_type,
        {
            "id": value.id,
            "type": event_type,
            "data": {
                "escalation_id": value.id,
                "decision_id": value.decision_id,
                "status": new_status,
                "priority": value.priority,
                "workspace_id": value.workspace_id,
            },
        },
    )


def claim_escalation(
    session: Session,
    context: TenantContext,
    escalation_id: str,
    payload: ReviewClaim,
) -> TenantEscalation:
    value = get_escalation(session, context, escalation_id, lock=True)
    _check_version(value, payload.expected_version)
    if value.status != "OPEN":
        raise APIError(409, "invalid_review_transition", "Only open escalations can be claimed.")
    prior = value.status
    value.status = "IN_REVIEW"
    value.assigned_to = context.actor_id
    value.lock_version += 1
    _record_transition(session, context, value, prior, value.status, "CLAIMED", payload.notes)
    return value


async def transition_escalation(
    session: Session,
    context: TenantContext,
    escalation_id: str,
    target_status: str,
    payload: ReviewClaim,
) -> TenantEscalation:
    if target_status not in FINAL_STATES:
        raise APIError(422, "invalid_review_transition", "Unsupported review status.")
    value = get_escalation(session, context, escalation_id, lock=True)
    _check_version(value, payload.expected_version)
    if value.status != "IN_REVIEW" or value.assigned_to != context.actor_id:
        raise APIError(
            409,
            "invalid_review_transition",
            "Claim the open escalation before completing review.",
        )
    answer = (payload.answer or value.draft_answer).strip()
    if target_status == "APPROVED":
        decision = session.get(SaaSDecision, value.decision_id) if value.decision_id else None
        sources = [
            SourceRecord.model_validate(item) for item in (decision.citations if decision else [])
        ]
        workspace = session.get(Workspace, context.workspace_id)
        profile = (
            session.get(WorkspaceProfileVersion, workspace.active_profile_version_id)
            if workspace and workspace.active_profile_version_id
            else None
        )
        guardian = await GuardianService(
            rule_packs=profile.enabled_rule_packs if profile else ["GLOBAL_SAFETY"]
        ).analyze(value.query, answer)
        oracle = OracleService().analyze(answer, sources)
        if guardian.status is GuardianStatus.CRITICAL or not oracle.overall_supported:
            raise APIError(
                409,
                "review_validation_failed",
                "The edited answer failed safety or evidence verification.",
                details={
                    "guardian_status": guardian.status.value,
                    "guardian_violations": guardian.violations,
                    "unsupported_claims": oracle.unsupported_claims,
                },
            )
        value.draft_answer = answer
        if decision:
            decision.answer = answer
    prior = value.status
    value.status = target_status
    value.resolution_notes = payload.notes
    value.lock_version += 1
    _record_transition(
        session,
        context,
        value,
        prior,
        target_status,
        target_status,
        payload.notes,
    )
    return value
