from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.base import Database
from api.db.models import EmailOutbox, Membership, UserProfile
from api.tenancy import set_platform_database_context, set_tenant_database_context


def queue_email(
    session: Session,
    organization_id: str,
    recipient: str,
    template_key: str,
    template_data: dict,
    *,
    workspace_id: str | None = None,
) -> None:
    session.add(
        EmailOutbox(
            organization_id=organization_id,
            workspace_id=workspace_id,
            recipient=recipient.strip().lower(),
            template_key=template_key,
            template_data=template_data,
        )
    )


def queue_review_notifications(
    session: Session,
    organization_id: str,
    workspace_id: str,
    escalation_id: str,
    priority: str,
) -> None:
    recipients = session.scalars(
        select(UserProfile.email)
        .join(Membership, Membership.auth_user_id == UserProfile.auth_user_id)
        .where(
            Membership.organization_id == organization_id,
            Membership.status == "ACTIVE",
            Membership.role.in_(["owner", "admin", "reviewer"]),
        )
    ).all()
    for recipient in sorted(set(recipients)):
        queue_email(
            session,
            organization_id,
            recipient,
            "review_required",
            {"escalation_id": escalation_id, "priority": priority},
            workspace_id=workspace_id,
        )


def deliver_pending(database: Database, settings: Settings, limit: int = 50) -> int:
    delivered = 0
    with database.session() as session:
        set_platform_database_context(session, True)
        values = session.scalars(
            select(EmailOutbox)
            .where(
                EmailOutbox.status.in_(["PENDING", "RETRY"]),
                EmailOutbox.available_at <= datetime.now(timezone.utc),
            )
            .order_by(EmailOutbox.created_at)
            .limit(limit)
        ).all()
        for value in values:
            set_tenant_database_context(session, value.organization_id)
            if not settings.email_provider_url:
                value.status = "SKIPPED"
                continue
            try:
                response = httpx.post(
                    settings.email_provider_url,
                    headers={
                        "Authorization": f"Bearer {settings.email_provider_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": settings.email_from,
                        "to": value.recipient,
                        "template": value.template_key,
                        "data": value.template_data,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                payload = response.json() if response.content else {}
                value.provider_message_id = str(payload.get("id", ""))[:128] or None
                value.status = "DELIVERED"
                value.last_error = None
                delivered += 1
            except Exception as exc:
                value.attempts += 1
                value.last_error = str(exc)[:500]
                if value.attempts >= 8:
                    value.status = "FAILED"
                else:
                    value.status = "RETRY"
                    value.available_at = datetime.now(timezone.utc) + timedelta(
                        minutes=min(60, 2 ** min(value.attempts, 6))
                    )
    return delivered
