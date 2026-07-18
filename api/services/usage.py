from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.models import (
    BillingAccount,
    BillingOutbox,
    Organization,
    UsageEvent,
    UsageReservation,
)
from api.errors import APIError
from api.saas_schemas import UsageSummary


ACTIVE_BILLING_STATES = {"ACTIVE", "AUTHENTICATED"}


def period_key(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    return value.strftime("%Y-%m")


def _lock_organization(session: Session, organization_id: str) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:organization_id))"),
            {"organization_id": organization_id},
        )


def usage_count(session: Session, organization_id: str, period: str) -> int:
    return int(
        session.scalar(
            select(func.coalesce(func.sum(UsageEvent.units), 0)).where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.period_key == period,
            )
        )
        or 0
    )


def reserve_usage(
    session: Session,
    settings: Settings,
    organization_id: str,
    workspace_id: str,
    idempotency_key: str,
) -> UsageReservation:
    _lock_organization(session, organization_id)
    existing = session.scalar(
        select(UsageReservation).where(
            UsageReservation.organization_id == organization_id,
            UsageReservation.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    period = period_key()
    completed = usage_count(session, organization_id, period)
    active_reservations = int(
        session.scalar(
            select(func.count(UsageReservation.id)).where(
                UsageReservation.organization_id == organization_id,
                UsageReservation.period_key == period,
                UsageReservation.status == "RESERVED",
                UsageReservation.expires_at > datetime.now(timezone.utc),
            )
        )
        or 0
    )
    billing = session.get(BillingAccount, organization_id)
    paid = bool(
        billing
        and billing.payment_method_present
        and billing.status in ACTIVE_BILLING_STATES
    )
    next_ordinal = completed + active_reservations + 1
    if (
        settings.provider_cost_cap_cents > 0
        and settings.estimated_cost_per_decision_millicents > 0
        and next_ordinal * settings.estimated_cost_per_decision_millicents
        > settings.provider_cost_cap_cents * 1000
    ):
        raise APIError(
            503,
            "provider_cost_circuit_open",
            "Decision processing is temporarily paused by the platform cost safeguard.",
        )
    if completed + active_reservations >= settings.free_decisions_per_month and not paid:
        raise APIError(
            402,
            "quota_exceeded",
            "A payment method is required to continue after the free monthly allowance.",
            details={
                "included": settings.free_decisions_per_month,
                "used": completed,
                "period": period,
            },
        )
    organization = session.get(Organization, organization_id)
    if (
        paid
        and organization
        and organization.spend_cap_paise is not None
        and settings.overage_unit_price_paise > 0
    ):
        projected_overage = max(
            0, next_ordinal - settings.free_decisions_per_month
        ) * settings.overage_unit_price_paise
        if projected_overage > organization.spend_cap_paise:
            raise APIError(
                402,
                "spend_cap_reached",
                "The organization monthly spend cap has been reached.",
                details={"spend_cap_paise": organization.spend_cap_paise},
            )
    reservation = UsageReservation(
        organization_id=organization_id,
        workspace_id=workspace_id,
        idempotency_key=idempotency_key,
        period_key=period,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    session.add(reservation)
    session.flush()
    return reservation


def finalize_usage(
    session: Session,
    settings: Settings,
    reservation: UsageReservation,
    decision_id: str,
) -> UsageEvent:
    _lock_organization(session, reservation.organization_id)
    existing = session.scalar(
        select(UsageEvent).where(UsageEvent.decision_id == decision_id)
    )
    if existing is not None:
        return existing
    ordinal = usage_count(
        session, reservation.organization_id, reservation.period_key
    ) + 1
    billable = 1 if ordinal > settings.free_decisions_per_month else 0
    usage = UsageEvent(
        organization_id=reservation.organization_id,
        workspace_id=reservation.workspace_id,
        decision_id=decision_id,
        period_key=reservation.period_key,
        units=1,
        billable_units=billable,
        razorpay_status="NOT_BILLABLE" if not billable else "PENDING",
    )
    session.add(usage)
    reservation.status = "FINALIZED"
    session.flush()
    if billable:
        billing = session.get(BillingAccount, reservation.organization_id)
        if not billing or not billing.razorpay_subscription_id:
            raise APIError(402, "billing_not_ready", "Billing is not ready for paid usage.")
        session.add(
            BillingOutbox(
                organization_id=reservation.organization_id,
                usage_event_id=usage.id,
                payload={
                    "razorpay_subscription_id": billing.razorpay_subscription_id,
                    "amount_paise": settings.overage_unit_price_paise,
                    "currency": "INR",
                    "value": 1,
                    "identifier": usage.id,
                },
            )
        )
    return usage


def release_usage(reservation: UsageReservation) -> None:
    reservation.status = "RELEASED"


def summary(
    session: Session, settings: Settings, organization_id: str
) -> UsageSummary:
    period = period_key()
    completed = usage_count(session, organization_id, period)
    billing = session.get(BillingAccount, organization_id)
    organization = session.get(Organization, organization_id)
    return UsageSummary(
        organization_id=organization_id,
        period=period,
        completed_decisions=completed,
        included_decisions=settings.free_decisions_per_month,
        overage_decisions=max(0, completed - settings.free_decisions_per_month),
        remaining_free_decisions=max(0, settings.free_decisions_per_month - completed),
        billing_status=billing.status if billing else "FREE",
        payment_method_present=bool(billing and billing.payment_method_present),
        spend_cap_paise=organization.spend_cap_paise if organization else None,
        projected_overage_paise=(
            max(0, completed - settings.free_decisions_per_month)
            * settings.overage_unit_price_paise
            if settings.overage_unit_price_paise > 0
            else None
        ),
    )


def update_spend_cap(
    session: Session, organization_id: str, spend_cap_paise: int | None
) -> None:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise APIError(404, "not_found", "Organization not found.")
    organization.spend_cap_paise = spend_cap_paise
    session.flush()
