from __future__ import annotations

import hashlib
import json

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.db.models import AuditEvent
from api.tenancy import TenantContext


def record_audit(
    session: Session,
    context: TenantContext,
    action: str,
    resource_type: str,
    resource_id: str | None,
    details: dict | None = None,
) -> AuditEvent:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:audit_chain))"),
            {"audit_chain": f"audit:{context.organization_id or 'platform'}"},
        )
    prior = session.scalar(
        select(AuditEvent)
        .where(AuditEvent.organization_id == context.organization_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(1)
    )
    prior_hash = prior.event_hash if prior else None
    canonical = json.dumps(
        {
            "organization_id": context.organization_id,
            "workspace_id": context.workspace_id,
            "actor_type": context.actor_type,
            "actor_id": context.actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "prior_hash": prior_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    event = AuditEvent(
        organization_id=context.organization_id,
        workspace_id=context.workspace_id,
        actor_type=context.actor_type,
        actor_id=context.actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        prior_hash=prior_hash,
        event_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
    session.add(event)
    return event
