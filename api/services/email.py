from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json
from urllib.parse import urlparse

import resend
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.base import Database
from api.db.models import EmailOutbox, Membership, UserProfile
from api.tenancy import set_platform_database_context, set_tenant_database_context


def _safe_link(value: object) -> str | None:
    link = str(value or "").strip()
    parsed = urlparse(link)
    return link if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _render_email(template_key: str, template_data: dict) -> tuple[str, str, str]:
    if template_key == "team_invitation":
        role = str(template_data.get("role") or "member").strip().title()
        invite_url = _safe_link(template_data.get("invite_url"))
        subject = "You're invited to AgentMesh"
        action_html = (
            f'<p><a href="{escape(invite_url, quote=True)}">Accept invitation</a></p>'
            if invite_url
            else "<p>Open AgentMesh to accept your invitation.</p>"
        )
        html = (
            "<p>You have been invited to join an AgentMesh organization as "
            f"<strong>{escape(role)}</strong>.</p>{action_html}"
        )
        text = (
            f"You have been invited to join an AgentMesh organization as {role}."
            + (f"\n\nAccept invitation: {invite_url}" if invite_url else "")
        )
        return subject, html, text

    if template_key == "review_required":
        escalation_id = str(template_data.get("escalation_id") or "unknown")
        priority = str(template_data.get("priority") or "unspecified").upper()
        subject = f"AgentMesh review required: {priority}"
        html = (
            "<p>A decision requires human review.</p>"
            f"<p><strong>Priority:</strong> {escape(priority)}<br>"
            f"<strong>Escalation:</strong> {escape(escalation_id)}</p>"
        )
        text = (
            "A decision requires human review.\n\n"
            f"Priority: {priority}\nEscalation: {escalation_id}"
        )
        return subject, html, text

    details = json.dumps(template_data, sort_keys=True, default=str)
    subject = "AgentMesh notification"
    html = (
        f"<p>{escape(template_key.replace('_', ' ').title())}</p>"
        f"<pre>{escape(details)}</pre>"
    )
    return subject, html, f"{template_key}\n\n{details}"


def _send_with_resend(
    settings: Settings,
    recipient: str,
    template_key: str,
    template_data: dict,
) -> str | None:
    subject, html, text = _render_email(template_key, template_data)
    resend.api_key = settings.resend_api_key
    response = resend.Emails.send(
        {
            "from": settings.resend_from,
            "to": [recipient],
            "subject": subject,
            "html": html,
            "text": text,
        }
    )
    if isinstance(response, dict):
        message_id = response.get("id")
    else:
        message_id = getattr(response, "id", None)
    return str(message_id)[:128] if message_id else None


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
            if not settings.resend_api_key:
                value.status = "SKIPPED"
                continue
            try:
                value.provider_message_id = _send_with_resend(
                    settings,
                    value.recipient,
                    value.template_key,
                    value.template_data,
                )
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
