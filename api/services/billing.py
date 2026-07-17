from __future__ import annotations

from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.base import Database
from api.db.models import (
    BillingAccount,
    BillingOutbox,
    Organization,
    StripeEvent,
    UsageEvent,
)
from api.errors import APIError
from api.services.audit import record_audit
from api.tenancy import (
    TenantContext,
    set_platform_database_context,
    set_tenant_database_context,
)


def _configure(settings: Settings) -> None:
    if not settings.stripe_secret_key:
        raise APIError(503, "billing_unavailable", "Billing is not configured.")
    stripe.api_key = settings.stripe_secret_key


def create_checkout(
    session: Session,
    settings: Settings,
    context: TenantContext,
) -> str:
    _configure(settings)
    if not settings.stripe_price_id:
        raise APIError(503, "billing_unavailable", "The metered price is not configured.")
    organization = session.get(Organization, context.organization_id)
    billing = session.get(BillingAccount, context.organization_id)
    if organization is None or billing is None:
        raise APIError(404, "not_found", "Organization not found.")
    if not billing.stripe_customer_id:
        customer = stripe.Customer.create(
            name=organization.name,
            email=organization.billing_email,
            metadata={"agentmesh_organization_id": organization.id},
        )
        billing.stripe_customer_id = customer.id
    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=billing.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id}],
        success_url=f"{settings.public_app_url}/billing?checkout=success",
        cancel_url=f"{settings.public_app_url}/billing?checkout=cancelled",
        client_reference_id=organization.id,
        metadata={"agentmesh_organization_id": organization.id},
        subscription_data={"metadata": {"agentmesh_organization_id": organization.id}},
        allow_promotion_codes=True,
    )
    record_audit(
        session,
        context,
        "billing.checkout_created",
        "billing_account",
        organization.id,
    )
    return checkout.url


def create_portal(
    session: Session,
    settings: Settings,
    context: TenantContext,
) -> str:
    _configure(settings)
    billing = session.get(BillingAccount, context.organization_id)
    if billing is None or not billing.stripe_customer_id:
        raise APIError(409, "billing_not_started", "Start billing before opening the portal.")
    portal = stripe.billing_portal.Session.create(
        customer=billing.stripe_customer_id,
        return_url=f"{settings.public_app_url}/billing",
    )
    return portal.url


def process_stripe_webhook(
    session: Session,
    settings: Settings,
    body: bytes,
    signature: str | None,
) -> None:
    if not settings.stripe_webhook_secret or not signature:
        raise APIError(503, "billing_unavailable", "Stripe webhook verification is unavailable.")
    try:
        event = stripe.Webhook.construct_event(
            body, signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise APIError(400, "invalid_webhook", "Stripe webhook signature is invalid.") from exc
    if session.get(StripeEvent, event["id"]):
        return
    event_type = event["type"]
    obj = event["data"]["object"]
    metadata = obj.get("metadata") or {}
    organization_id = metadata.get("agentmesh_organization_id")
    if not organization_id and event_type.startswith("invoice."):
        customer_id = obj.get("customer")
        account = session.scalar(
            select(BillingAccount).where(BillingAccount.stripe_customer_id == customer_id)
        )
        organization_id = account.organization_id if account else None
    session.add(
        StripeEvent(
            event_id=event["id"],
            event_type=event_type,
            payload=dict(event),
        )
    )
    if not organization_id:
        return
    set_tenant_database_context(session, organization_id)
    account = session.get(BillingAccount, organization_id)
    if account is None:
        return
    if event_type == "checkout.session.completed":
        account.stripe_customer_id = obj.get("customer") or account.stripe_customer_id
        account.stripe_subscription_id = obj.get("subscription")
        account.payment_method_present = True
        account.status = "ACTIVE"
    elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        account.stripe_subscription_id = obj.get("id")
        status = str(obj.get("status") or "").upper()
        account.status = status
        account.payment_method_present = status in {"ACTIVE", "TRIALING", "PAST_DUE"}
        timestamp = obj.get("current_period_end")
        if timestamp:
            account.current_period_end = datetime.fromtimestamp(timestamp, timezone.utc)
    elif event_type == "customer.subscription.deleted":
        account.status = "CANCELED"
        account.payment_method_present = False
    elif event_type == "invoice.payment_failed":
        account.status = "PAST_DUE"
    elif event_type == "invoice.paid" and account.stripe_subscription_id:
        account.status = "ACTIVE"
        account.payment_method_present = True
    context = TenantContext(
        organization_id=organization_id,
        workspace_id=None,
        actor_id="stripe",
        actor_type="SYSTEM",
        role="owner",
    )
    record_audit(
        session,
        context,
        "billing.stripe_event",
        "billing_account",
        organization_id,
        {"event_id": event["id"], "event_type": event_type, "status": account.status},
    )


def report_meter_events(
    database: Database, settings: Settings, limit: int = 100
) -> int:
    _configure(settings)
    sent = 0
    with database.session() as session:
        set_platform_database_context(session, True)
        entries = session.scalars(
            select(BillingOutbox)
            .where(
                BillingOutbox.status.in_(["PENDING", "RETRY"]),
                BillingOutbox.available_at <= datetime.now(timezone.utc),
            )
            .order_by(BillingOutbox.created_at)
            .limit(limit)
        ).all()
        for entry in entries:
            set_tenant_database_context(session, entry.organization_id)
            try:
                result = stripe.billing.MeterEvent.create(
                    event_name=entry.payload["event_name"],
                    payload={
                        "stripe_customer_id": entry.payload["stripe_customer_id"],
                        "value": str(entry.payload["value"]),
                    },
                    identifier=entry.payload["identifier"],
                )
                entry.status = "SENT"
                usage = session.get(UsageEvent, entry.usage_event_id)
                if usage:
                    usage.stripe_status = "SENT"
                    usage.stripe_event_id = result.identifier
                sent += 1
            except Exception as exc:
                entry.attempts += 1
                entry.last_error = str(exc)[:500]
                entry.status = "FAILED" if entry.attempts >= 8 else "RETRY"
                entry.available_at = datetime.now(timezone.utc) + timedelta(
                    minutes=min(60, 2 ** min(entry.attempts, 6))
                )
    return sent


def reconcile_meter_outbox(database: Database, settings: Settings) -> int:
    repaired = 0
    with database.session() as session:
        set_platform_database_context(session, True)
        usage_events = session.scalars(
            select(UsageEvent).where(
                UsageEvent.billable_units > 0,
                UsageEvent.stripe_status != "SENT",
            )
        ).all()
        for usage in usage_events:
            set_tenant_database_context(session, usage.organization_id)
            existing = session.scalar(
                select(BillingOutbox).where(
                    BillingOutbox.usage_event_id == usage.id
                )
            )
            billing = session.get(BillingAccount, usage.organization_id)
            if not billing or not billing.stripe_customer_id:
                continue
            if existing is None:
                session.add(
                    BillingOutbox(
                        organization_id=usage.organization_id,
                        usage_event_id=usage.id,
                        payload={
                            "event_name": settings.stripe_meter_event_name,
                            "stripe_customer_id": billing.stripe_customer_id,
                            "value": usage.billable_units,
                            "identifier": usage.id,
                        },
                    )
                )
                repaired += 1
            elif existing.status == "FAILED":
                existing.status = "RETRY"
                existing.attempts = 0
                existing.last_error = None
                repaired += 1
    return repaired
