from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.base import Database
from api.db.models import WebhookDelivery, WebhookEndpoint
from api.errors import APIError
from api.saas_schemas import (
    WebhookCreate,
    WebhookCreated,
    WebhookDeliveryView,
    WebhookView,
)
from api.services.audit import record_audit
from api.tenancy import (
    TenantContext,
    set_platform_database_context,
    set_tenant_database_context,
)


def _encryption_key(settings: Settings) -> bytes:
    return hashlib.sha256(settings.webhook_encryption_key.encode("utf-8")).digest()


def _encrypt(settings: Settings, value: str) -> bytes:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_encryption_key(settings)).encrypt(
        nonce, value.encode("utf-8"), b"agentmesh-webhook"
    )
    return nonce + ciphertext


def _decrypt(settings: Settings, value: bytes) -> str:
    nonce, ciphertext = value[:12], value[12:]
    return AESGCM(_encryption_key(settings)).decrypt(
        nonce, ciphertext, b"agentmesh-webhook"
    ).decode("utf-8")


def create_endpoint(
    session: Session,
    settings: Settings,
    context: TenantContext,
    payload: WebhookCreate,
) -> WebhookCreated:
    url = str(payload.url)
    if not url.startswith("https://") and settings.environment != "development":
        raise APIError(422, "invalid_webhook_url", "Webhook URLs must use HTTPS.")
    secret = secrets.token_urlsafe(32)
    endpoint = WebhookEndpoint(
        organization_id=context.organization_id,
        workspace_id=context.workspace_id,
        url=url,
        event_types=sorted(set(payload.event_types)),
        secret_ciphertext=_encrypt(settings, secret),
        created_by=context.actor_id,
    )
    session.add(endpoint)
    session.flush()
    record_audit(
        session,
        context,
        "webhook.created",
        "webhook_endpoint",
        endpoint.id,
        {"url": endpoint.url, "event_types": endpoint.event_types},
    )
    return WebhookCreated(
        **WebhookView.model_validate(endpoint).model_dump(), signing_secret=secret
    )


def list_endpoints(
    session: Session, organization_id: str, workspace_id: str
) -> list[WebhookView]:
    values = session.scalars(
        select(WebhookEndpoint)
        .where(
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.workspace_id == workspace_id,
        )
        .order_by(WebhookEndpoint.created_at.desc())
    ).all()
    return [WebhookView.model_validate(value) for value in values]


def disable_endpoint(
    session: Session, context: TenantContext, endpoint_id: str
) -> WebhookView:
    endpoint = session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.organization_id == context.organization_id,
            WebhookEndpoint.workspace_id == context.workspace_id,
        )
    )
    if endpoint is None:
        raise APIError(404, "not_found", "Webhook endpoint not found.")
    endpoint.status = "DISABLED"
    record_audit(
        session,
        context,
        "webhook.disabled",
        "webhook_endpoint",
        endpoint.id,
    )
    return WebhookView.model_validate(endpoint)


def list_deliveries(
    session: Session,
    organization_id: str,
    workspace_id: str,
    endpoint_id: str | None = None,
) -> list[WebhookDeliveryView]:
    query = select(WebhookDelivery).where(
        WebhookDelivery.organization_id == organization_id,
        WebhookDelivery.workspace_id == workspace_id,
    )
    if endpoint_id:
        query = query.where(WebhookDelivery.endpoint_id == endpoint_id)
    values = session.scalars(
        query.order_by(WebhookDelivery.created_at.desc()).limit(200)
    ).all()
    return [WebhookDeliveryView.model_validate(value) for value in values]


def queue_event(
    session: Session,
    organization_id: str,
    workspace_id: str,
    event_type: str,
    payload: dict,
) -> None:
    endpoints = session.scalars(
        select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.workspace_id == workspace_id,
            WebhookEndpoint.status == "ACTIVE",
        )
    ).all()
    for endpoint in endpoints:
        if event_type in endpoint.event_types:
            session.add(
                WebhookDelivery(
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    endpoint_id=endpoint.id,
                    event_type=event_type,
                    payload=payload,
                )
            )


def deliver_pending(database: Database, settings: Settings, limit: int = 50) -> int:
    delivered = 0
    with database.session() as session:
        set_platform_database_context(session, True)
        values = session.scalars(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.status.in_(["PENDING", "RETRY"]),
                WebhookDelivery.next_attempt_at <= datetime.now(timezone.utc),
            )
            .order_by(WebhookDelivery.created_at)
            .limit(limit)
        ).all()
        for delivery in values:
            set_tenant_database_context(session, delivery.organization_id)
            endpoint = session.get(WebhookEndpoint, delivery.endpoint_id)
            if endpoint is None or endpoint.status != "ACTIVE":
                delivery.status = "DISABLED"
                continue
            body = json.dumps(delivery.payload, sort_keys=True, separators=(",", ":"))
            timestamp = str(int(time.time()))
            secret = _decrypt(settings, endpoint.secret_ciphertext)
            signature = hmac.new(
                secret.encode("utf-8"),
                f"{timestamp}.{body}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            try:
                response = httpx.post(
                    endpoint.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "AgentMesh-Webhooks/1.0",
                        "X-AgentMesh-Timestamp": timestamp,
                        "X-AgentMesh-Signature": f"v1={signature}",
                    },
                    timeout=10.0,
                )
                delivery.response_status = response.status_code
                if 200 <= response.status_code < 300:
                    delivery.status = "DELIVERED"
                    delivery.last_error = None
                    delivered += 1
                else:
                    raise RuntimeError(f"HTTP {response.status_code}")
            except Exception as exc:
                delivery.attempts += 1
                delivery.last_error = str(exc)[:500]
                if delivery.attempts >= 8:
                    delivery.status = "FAILED"
                else:
                    delivery.status = "RETRY"
                    minutes = min(60, 2 ** min(delivery.attempts, 6))
                    delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                        minutes=minutes
                    )
    return delivered
