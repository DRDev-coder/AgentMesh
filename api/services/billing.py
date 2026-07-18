from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.base import Database
from api.db.models import (
    BillingAccount,
    BillingOutbox,
    Organization,
    RazorpayEvent,
    UsageEvent,
)
from api.errors import APIError
from api.services.audit import record_audit
from api.tenancy import (
    TenantContext,
    set_platform_database_context,
    set_tenant_database_context,
)


class RazorpayRequestError(RuntimeError):
    def __init__(self, message: str, *, delivery_uncertain: bool = False):
        super().__init__(message)
        self.delivery_uncertain = delivery_uncertain


def _require_configured(settings: Settings) -> None:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise APIError(503, "billing_unavailable", "Razorpay billing is not configured.")


def _request(
    settings: Settings,
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    _require_configured(settings)
    try:
        response = httpx.request(
            method,
            f"{settings.razorpay_base_url}{path}",
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            headers={"Accept": "application/json"},
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        uncertain = exc.response.status_code == 429 or exc.response.status_code >= 500
        raise RazorpayRequestError(
            f"Razorpay returned HTTP {exc.response.status_code}: {detail}",
            delivery_uncertain=uncertain,
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise RazorpayRequestError(
            "Razorpay did not return a valid response.", delivery_uncertain=True
        ) from exc
    if not isinstance(result, dict):
        raise RazorpayRequestError(
            "Razorpay returned an unexpected response.", delivery_uncertain=True
        )
    return result


def create_subscription(
    session: Session,
    settings: Settings,
    context: TenantContext,
) -> str:
    _require_configured(settings)
    if not settings.razorpay_plan_id:
        raise APIError(503, "billing_unavailable", "The Razorpay plan is not configured.")
    organization = session.get(Organization, context.organization_id)
    account = session.get(BillingAccount, context.organization_id)
    if organization is None or account is None:
        raise APIError(404, "not_found", "Organization not found.")
    if account.razorpay_subscription_url and account.status not in {
        "CANCELLED",
        "COMPLETED",
        "EXPIRED",
    }:
        return account.razorpay_subscription_url
    try:
        subscription = _request(
            settings,
            "POST",
            "/subscriptions",
            {
                "plan_id": settings.razorpay_plan_id,
                "total_count": settings.razorpay_subscription_total_count,
                "quantity": 1,
                "customer_notify": True,
                "notes": {
                    "agentmesh_organization_id": organization.id,
                    "agentmesh_organization_name": organization.name[:200],
                    "agentmesh_billing_email": organization.billing_email[:200],
                },
            },
        )
    except RazorpayRequestError as exc:
        raise APIError(
            502,
            "billing_provider_error",
            "Razorpay could not create the subscription.",
        ) from exc
    subscription_id = str(subscription.get("id") or "")
    short_url = str(subscription.get("short_url") or "")
    if not subscription_id or not short_url:
        raise APIError(
            502,
            "billing_provider_error",
            "Razorpay did not return a subscription link.",
        )
    account.razorpay_subscription_id = subscription_id
    account.razorpay_subscription_url = short_url
    account.status = str(subscription.get("status") or "CREATED").upper()
    record_audit(
        session,
        context,
        "billing.razorpay_subscription_created",
        "billing_account",
        organization.id,
        {"subscription_id": subscription_id},
    )
    return short_url


def _verify_webhook_signature(
    settings: Settings, body: bytes, signature: str | None
) -> None:
    if not settings.razorpay_webhook_secret or not signature:
        raise APIError(
            503,
            "billing_unavailable",
            "Razorpay webhook verification is unavailable.",
        )
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature.strip().lower()):
        raise APIError(
            400,
            "invalid_webhook",
            "Razorpay webhook signature is invalid.",
        )


def _subscription_entity(event: dict) -> dict:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return {}
    subscription = payload.get("subscription")
    if not isinstance(subscription, dict):
        return {}
    entity = subscription.get("entity")
    return entity if isinstance(entity, dict) else {}


def process_razorpay_webhook(
    session: Session,
    settings: Settings,
    body: bytes,
    signature: str | None,
    delivery_id: str | None,
) -> None:
    _verify_webhook_signature(settings, body, signature)
    try:
        event = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise APIError(400, "invalid_webhook", "Razorpay webhook JSON is invalid.") from exc
    if not isinstance(event, dict):
        raise APIError(400, "invalid_webhook", "Razorpay webhook payload is invalid.")
    event_id = (delivery_id or "").strip() or hashlib.sha256(body).hexdigest()
    if session.get(RazorpayEvent, event_id):
        return
    event_type = str(event.get("event") or "unknown")
    subscription = _subscription_entity(event)
    subscription_id = str(subscription.get("id") or "")
    customer_id = str(subscription.get("customer_id") or "")
    notes = subscription.get("notes")
    organization_id = ""
    if isinstance(notes, dict):
        organization_id = str(notes.get("agentmesh_organization_id") or "")
    account: BillingAccount | None = None
    if organization_id:
        account = session.get(BillingAccount, organization_id)
    elif subscription_id:
        account = session.scalar(
            select(BillingAccount).where(
                BillingAccount.razorpay_subscription_id == subscription_id
            )
        )
        organization_id = account.organization_id if account else ""
    elif customer_id:
        account = session.scalar(
            select(BillingAccount).where(
                BillingAccount.razorpay_customer_id == customer_id
            )
        )
        organization_id = account.organization_id if account else ""
    if (
        account is not None
        and account.razorpay_subscription_id
        and subscription_id
        and account.razorpay_subscription_id != subscription_id
    ):
        session.add(
            RazorpayEvent(
                event_id=event_id,
                event_type=event_type,
                payload={
                    "event": event_type,
                    "subscription_id": subscription_id,
                    "ignored_as_stale": True,
                },
            )
        )
        return
    session.add(
        RazorpayEvent(
            event_id=event_id,
            event_type=event_type,
            payload={
                "event": event_type,
                "subscription_id": subscription_id or None,
                "customer_id": customer_id or None,
                "contains": event.get("contains")
                if isinstance(event.get("contains"), list)
                else [],
            },
        )
    )
    if not organization_id or account is None:
        return
    set_tenant_database_context(session, organization_id)
    account.razorpay_subscription_id = (
        subscription_id or account.razorpay_subscription_id
    )
    account.razorpay_customer_id = customer_id or account.razorpay_customer_id
    account.razorpay_subscription_url = (
        str(subscription.get("short_url") or "")
        or account.razorpay_subscription_url
    )
    provider_status = str(subscription.get("status") or "").upper()
    status_by_event = {
        "subscription.authenticated": "AUTHENTICATED",
        "subscription.activated": "ACTIVE",
        "subscription.charged": "ACTIVE",
        "subscription.resumed": "ACTIVE",
        "subscription.pending": "PENDING",
        "subscription.halted": "HALTED",
        "subscription.cancelled": "CANCELLED",
        "subscription.completed": "COMPLETED",
        "subscription.expired": "EXPIRED",
        "subscription.paused": "PAUSED",
    }
    status = status_by_event.get(event_type, provider_status or account.status)
    account.status = status
    account.payment_method_present = status in {"ACTIVE", "AUTHENTICATED"}
    current_end = subscription.get("current_end")
    if isinstance(current_end, (int, float)) and current_end > 0:
        account.current_period_end = datetime.fromtimestamp(current_end, timezone.utc)
    context = TenantContext(
        organization_id=organization_id,
        workspace_id=None,
        actor_id="razorpay",
        actor_type="SYSTEM",
        role="owner",
    )
    record_audit(
        session,
        context,
        "billing.razorpay_event",
        "billing_account",
        organization_id,
        {"event_id": event_id, "event_type": event_type, "status": account.status},
    )


def report_usage_addons(
    database: Database, settings: Settings, limit: int = 100
) -> int:
    _require_configured(settings)
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
                subscription_id = str(entry.payload["razorpay_subscription_id"])
                result = _request(
                    settings,
                    "POST",
                    f"/subscriptions/{quote(subscription_id, safe='')}/addons",
                    {
                        "item": {
                            "name": "AgentMesh decision usage",
                            "description": f"Usage event {entry.payload['identifier']}",
                            "amount": int(entry.payload["amount_paise"]),
                            "currency": str(entry.payload.get("currency") or "INR"),
                        },
                        "quantity": int(entry.payload["value"]),
                    },
                )
                addon_id = str(result.get("id") or "")
                if not addon_id:
                    raise RazorpayRequestError(
                        "Razorpay did not return an add-on identifier.",
                        delivery_uncertain=True,
                    )
                entry.status = "SENT"
                usage = session.get(UsageEvent, entry.usage_event_id)
                if usage:
                    usage.razorpay_status = "SENT"
                    usage.razorpay_addon_id = addon_id
                sent += 1
            except RazorpayRequestError as exc:
                entry.attempts += 1
                entry.last_error = str(exc)[:500]
                # Razorpay add-on creation has no idempotency key. An ambiguous
                # timeout or 5xx must not be retried automatically or it could
                # charge the customer twice.
                entry.status = "REVIEW" if exc.delivery_uncertain else "FAILED"
    return sent


def reconcile_billing_outbox(database: Database, settings: Settings) -> int:
    repaired = 0
    with database.session() as session:
        set_platform_database_context(session, True)
        usage_events = session.scalars(
            select(UsageEvent).where(
                UsageEvent.billable_units > 0,
                UsageEvent.razorpay_status != "SENT",
            )
        ).all()
        for usage in usage_events:
            set_tenant_database_context(session, usage.organization_id)
            existing = session.scalar(
                select(BillingOutbox).where(BillingOutbox.usage_event_id == usage.id)
            )
            account = session.get(BillingAccount, usage.organization_id)
            if not account or not account.razorpay_subscription_id:
                continue
            if existing is None:
                session.add(
                    BillingOutbox(
                        organization_id=usage.organization_id,
                        usage_event_id=usage.id,
                        payload={
                            "razorpay_subscription_id": account.razorpay_subscription_id,
                            "amount_paise": settings.overage_unit_price_paise,
                            "currency": "INR",
                            "value": usage.billable_units,
                            "identifier": usage.id,
                        },
                    )
                )
                repaired += 1
    return repaired
