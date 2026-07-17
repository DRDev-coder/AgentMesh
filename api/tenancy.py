from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal, require_verified_principal, sync_user_profile
from api.db.models import Membership, Organization, Workspace
from api.errors import APIError


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset({"*"}),
    "admin": frozenset(
        {
            "organization:read",
            "team:manage",
            "workspace:read",
            "workspace:manage",
            "knowledge:read",
            "knowledge:manage",
            "profile:read",
            "profile:manage",
            "decisions:read",
            "reviews:read",
            "reviews:manage",
            "usage:read",
            "keys:manage",
            "webhooks:manage",
            "playground:use",
        }
    ),
    "developer": frozenset(
        {
            "organization:read",
            "workspace:read",
            "knowledge:read",
            "profile:read",
            "decisions:read",
            "usage:read",
            "keys:manage",
            "webhooks:manage",
            "playground:use",
        }
    ),
    "reviewer": frozenset(
        {
            "organization:read",
            "workspace:read",
            "knowledge:read",
            "profile:read",
            "decisions:read",
            "reviews:read",
            "reviews:manage",
        }
    ),
    "viewer": frozenset(
        {
            "organization:read",
            "workspace:read",
            "knowledge:read",
            "profile:read",
            "decisions:read",
            "usage:read",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class TenantContext:
    organization_id: str | None
    workspace_id: str | None
    actor_id: str
    actor_type: str
    role: str

    def can(self, permission: str) -> bool:
        permissions = ROLE_PERMISSIONS.get(self.role, frozenset())
        return "*" in permissions or permission in permissions


def get_db_session(request: Request) -> Iterator[Session]:
    with request.app.state.database.session() as session:
        yield session


def set_tenant_database_context(session: Session, organization_id: str) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.organization_id', :organization_id, true)"),
            {"organization_id": organization_id},
        )
        session.execute(text("SELECT set_config('app.platform_access', 'false', true)"))


def set_platform_database_context(session: Session, enabled: bool = True) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.platform_access', :enabled, true)"),
            {"enabled": "true" if enabled else "false"},
        )


def organization_context(
    organization_id: str,
    permission: str,
    session: Session,
    principal: Principal,
) -> TenantContext:
    require_verified_principal(principal)
    sync_user_profile(session, principal)
    membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.auth_user_id == principal.user_id,
            Membership.status == "ACTIVE",
        )
    )
    if membership is None:
        raise APIError(404, "not_found", "Organization not found.")
    context = TenantContext(
        organization_id=organization_id,
        workspace_id=None,
        actor_id=principal.user_id,
        actor_type="USER",
        role=membership.role,
    )
    if not context.can(permission):
        raise APIError(403, "permission_denied", "You do not have permission for this action.")
    set_tenant_database_context(session, organization_id)
    organization = session.get(Organization, organization_id)
    if organization is None or organization.status != "ACTIVE":
        raise APIError(404, "not_found", "Organization not found.")
    return context


def workspace_context(
    organization_id: str,
    workspace_id: str,
    permission: str,
    session: Session,
    principal: Principal,
) -> TenantContext:
    base = organization_context(organization_id, permission, session, principal)
    workspace = session.scalar(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.organization_id == organization_id,
            Workspace.status == "ACTIVE",
        )
    )
    if workspace is None:
        raise APIError(404, "not_found", "Workspace not found.")
    return TenantContext(
        organization_id=base.organization_id,
        workspace_id=workspace_id,
        actor_id=base.actor_id,
        actor_type=base.actor_type,
        role=base.role,
    )


def principal_dependency(principal: Principal = Depends(get_principal)) -> Principal:
    return require_verified_principal(principal)
