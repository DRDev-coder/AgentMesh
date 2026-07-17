from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings
from api.db.models import APIKey
from api.errors import APIError
from api.saas_schemas import APIKeyCreate, APIKeyCreated, APIKeyView
from api.services.audit import record_audit
from api.tenancy import (
    TenantContext,
    set_platform_database_context,
    set_tenant_database_context,
)


_KEY_PATTERN = re.compile(
    r"^am_(?P<environment>test|live)_(?P<public_id>[A-Za-z0-9_-]{12})\.(?P<secret>[A-Za-z0-9_-]{32,})$"
)


@dataclass(frozen=True, slots=True)
class APIKeyPrincipal:
    key_id: str
    organization_id: str
    workspace_id: str
    environment: str
    scopes: frozenset[str]

    def require(self, scope: str) -> None:
        if scope not in self.scopes:
            raise APIError(403, "insufficient_scope", f"API key requires {scope} scope.")


def _digest(settings: Settings, secret: str) -> str:
    return hmac.new(
        settings.api_key_pepper.encode("utf-8"),
        secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_key(
    session: Session,
    settings: Settings,
    context: TenantContext,
    payload: APIKeyCreate,
) -> APIKeyCreated:
    if payload.expires_at and payload.expires_at <= datetime.now(timezone.utc):
        raise APIError(422, "invalid_expiry", "API key expiry must be in the future.")
    public_id = secrets.token_urlsafe(9)[:12]
    secret = secrets.token_urlsafe(32)
    full_secret = f"am_{payload.environment}_{public_id}.{secret}"
    record = APIKey(
        organization_id=context.organization_id,
        workspace_id=context.workspace_id,
        public_id=public_id,
        secret_digest=_digest(settings, secret),
        name=payload.name.strip(),
        environment=payload.environment,
        scopes=sorted(set(payload.scopes)),
        last_four=secret[-4:],
        expires_at=payload.expires_at,
        created_by=context.actor_id,
    )
    session.add(record)
    session.flush()
    record_audit(
        session,
        context,
        "api_key.created",
        "api_key",
        record.id,
        {"name": record.name, "environment": record.environment, "scopes": record.scopes},
    )
    return APIKeyCreated(
        **APIKeyView.model_validate(record).model_dump(), secret=full_secret
    )


def list_keys(
    session: Session, organization_id: str, workspace_id: str
) -> list[APIKeyView]:
    values = session.scalars(
        select(APIKey)
        .where(
            APIKey.organization_id == organization_id,
            APIKey.workspace_id == workspace_id,
        )
        .order_by(APIKey.created_at.desc())
    ).all()
    return [APIKeyView.model_validate(value) for value in values]


def revoke_key(
    session: Session,
    context: TenantContext,
    key_id: str,
) -> APIKeyView:
    key = session.scalar(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == context.organization_id,
            APIKey.workspace_id == context.workspace_id,
        )
    )
    if key is None:
        raise APIError(404, "not_found", "API key not found.")
    key.status = "REVOKED"
    record_audit(
        session,
        context,
        "api_key.revoked",
        "api_key",
        key.id,
        {"name": key.name},
    )
    return APIKeyView.model_validate(key)


def authenticate_key(
    session: Session,
    settings: Settings,
    authorization: str | None,
) -> APIKeyPrincipal:
    if not authorization:
        raise APIError(401, "api_key_required", "Provide an AgentMesh API key.")
    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw:
        raise APIError(401, "api_key_required", "Provide an AgentMesh API key.")
    parsed = _KEY_PATTERN.fullmatch(raw.strip())
    if parsed is None:
        raise APIError(401, "invalid_api_key", "API key is invalid.")
    set_platform_database_context(session, True)
    key = session.scalar(
        select(APIKey).where(APIKey.public_id == parsed.group("public_id"))
    )
    if key is None:
        raise APIError(401, "invalid_api_key", "API key is invalid.")
    set_tenant_database_context(session, key.organization_id)
    expected = _digest(settings, parsed.group("secret"))
    now = datetime.now(timezone.utc)
    expires_at = key.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        not hmac.compare_digest(expected, key.secret_digest)
        or key.environment != parsed.group("environment")
        or key.status != "ACTIVE"
        or (expires_at is not None and expires_at <= now)
    ):
        raise APIError(401, "invalid_api_key", "API key is invalid.")
    key.last_used_at = now
    return APIKeyPrincipal(
        key_id=key.id,
        organization_id=key.organization_id,
        workspace_id=key.workspace_id,
        environment=key.environment,
        scopes=frozenset(key.scopes),
    )
