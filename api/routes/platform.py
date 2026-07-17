from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal, require_platform_admin, sync_user_profile
from api.db.models import (
    BackgroundJob,
    AbuseSignal,
    BillingOutbox,
    EmailOutbox,
    Organization,
    IndustryTemplate,
    UsageEvent,
    WebhookDelivery,
)
from api.saas_schemas import PlatformOrganizationView
from api.tenancy import get_db_session, set_platform_database_context


router = APIRouter(prefix="/platform", tags=["platform-administration"])


def _authorize(session: Session, principal: Principal) -> None:
    sync_user_profile(session, principal)
    require_platform_admin(session, principal)
    set_platform_database_context(session, True)


@router.get("/organizations", response_model=list[PlatformOrganizationView])
def organizations(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[PlatformOrganizationView]:
    _authorize(session, principal)
    values = session.scalars(
        select(Organization).order_by(Organization.created_at.desc()).limit(200)
    ).all()
    return [PlatformOrganizationView.model_validate(value) for value in values]


@router.get("/metrics")
def platform_metrics(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> dict:
    _authorize(session, principal)
    return {
        "organizations": session.scalar(select(func.count(Organization.id))) or 0,
        "decisions": session.scalar(select(func.coalesce(func.sum(UsageEvent.units), 0))) or 0,
        "failed_billing_events": session.scalar(
            select(func.count(BillingOutbox.id)).where(BillingOutbox.status == "FAILED")
        ) or 0,
        "failed_jobs": session.scalar(
            select(func.count(BackgroundJob.id)).where(BackgroundJob.status == "FAILED")
        ) or 0,
        "failed_webhooks": session.scalar(
            select(func.count(WebhookDelivery.id)).where(WebhookDelivery.status == "FAILED")
        ) or 0,
        "failed_emails": session.scalar(
            select(func.count(EmailOutbox.id)).where(EmailOutbox.status == "FAILED")
        ) or 0,
    }


@router.get("/jobs")
def jobs(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[dict]:
    _authorize(session, principal)
    values = session.scalars(
        select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(100)
    ).all()
    return [
        {
            "id": value.id,
            "type": value.job_type,
            "status": value.status,
            "attempts": value.attempts,
            "error": value.error,
            "created_at": value.created_at,
        }
        for value in values
    ]


@router.get("/templates")
def templates(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[dict]:
    _authorize(session, principal)
    values = session.scalars(
        select(IndustryTemplate).order_by(
            IndustryTemplate.key, IndustryTemplate.version.desc()
        )
    ).all()
    return [
        {
            "id": value.id,
            "key": value.key,
            "version": value.version,
            "name": value.name,
            "enabled": value.enabled,
            "mandatory_rule_keys": value.mandatory_rule_keys,
        }
        for value in values
    ]


@router.get("/rule-packs")
def rule_packs(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[dict]:
    _authorize(session, principal)
    return [
        {"key": "GLOBAL_SAFETY", "mandatory": True},
        {"key": "FINANCE_SUPPORT", "mandatory": False},
        {"key": "HEALTHCARE_INFORMATION", "mandatory": False},
        {"key": "ECOMMERCE_SUPPORT", "mandatory": False},
    ]


@router.get("/abuse-signals")
def abuse_signals(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[dict]:
    _authorize(session, principal)
    values = session.scalars(
        select(AbuseSignal).order_by(AbuseSignal.created_at.desc()).limit(200)
    ).all()
    return [
        {
            "id": value.id,
            "organization_id": value.organization_id,
            "workspace_id": value.workspace_id,
            "signal_type": value.signal_type,
            "details": value.details,
            "created_at": value.created_at,
        }
        for value in values
    ]


@router.get("/billing-reconciliation")
def billing_reconciliation(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> dict:
    _authorize(session, principal)
    rows = session.execute(
        select(BillingOutbox.status, func.count(BillingOutbox.id)).group_by(
            BillingOutbox.status
        )
    ).all()
    return {"outbox": {status: count for status, count in rows}}


@router.get("/service-health")
def service_health(
    request: Request,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> dict:
    _authorize(session, principal)
    try:
        redis_ready = bool(request.app.state.rate_limiter.client.ping())
    except Exception:
        redis_ready = False
    return {
        "postgresql": request.app.state.database.health(),
        "redis": redis_ready,
        "pending_jobs": session.scalar(
            select(func.count(BackgroundJob.id)).where(
                BackgroundJob.status.in_(["PENDING", "RETRY"])
            )
        )
        or 0,
        "pending_billing_events": session.scalar(
            select(func.count(BillingOutbox.id)).where(
                BillingOutbox.status.in_(["PENDING", "RETRY"])
            )
        )
        or 0,
    }
