from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import Principal, sync_user_profile
from api.config import Settings
from api.db.models import (
    BillingAccount,
    IndustryTemplate,
    Invitation,
    Membership,
    Organization,
    UserProfile,
    Workspace,
    WorkspaceProfileVersion,
)
from api.errors import APIError
from api.saas_schemas import (
    InvitationCreate,
    InvitationView,
    MemberView,
    MemberUpdate,
    OwnershipTransfer,
    OrganizationCreate,
    OrganizationView,
    ProfileDraft,
    WorkspaceCreate,
    WorkspaceView,
)
from api.services.audit import record_audit
from api.services.email import queue_email
from api.tenancy import TenantContext


TEMPLATE_DEFAULTS: dict[str, dict] = {
    "GENERAL": {
        "name": "General support",
        "description": "Evidence-grounded support for general business questions.",
        "tone": "PROFESSIONAL",
        "rule_packs": ["GLOBAL_SAFETY"],
        "topics": [],
    },
    "FINANCE": {
        "name": "Financial support",
        "description": "Informational financial-support workflows without account data.",
        "tone": "PROFESSIONAL",
        "rule_packs": ["GLOBAL_SAFETY", "FINANCE_SUPPORT"],
        "topics": ["policies", "refunds", "fraud reporting", "card support"],
    },
    "HEALTHCARE": {
        "name": "Healthcare information",
        "description": "Public healthcare information; no diagnosis or patient records.",
        "tone": "EMPATHETIC",
        "rule_packs": ["GLOBAL_SAFETY", "HEALTHCARE_INFORMATION"],
        "topics": ["public information", "coverage", "appointments"],
    },
    "ECOMMERCE": {
        "name": "E-commerce support",
        "description": "Product, shipping, return, and marketplace support.",
        "tone": "FRIENDLY",
        "rule_packs": ["GLOBAL_SAFETY", "ECOMMERCE_SUPPORT"],
        "topics": ["products", "shipping", "returns", "orders"],
    },
}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if len(value) < 2:
        raise APIError(422, "invalid_slug", "Use at least two letters or numbers.")
    return value[:80]


def seed_industry_templates(session: Session) -> None:
    for key, values in TEMPLATE_DEFAULTS.items():
        existing = session.scalar(
            select(IndustryTemplate).where(
                IndustryTemplate.key == key,
                IndustryTemplate.version == 1,
            )
        )
        if existing is None:
            session.add(
                IndustryTemplate(
                    key=key,
                    version=1,
                    name=values["name"],
                    description=values["description"],
                    default_profile={
                        "tone": values["tone"],
                        "response_length": "CONCISE",
                        "supported_topics": values["topics"],
                        "enabled_rule_packs": values["rule_packs"],
                        "escalation_threshold": 7,
                    },
                    mandatory_rule_keys=["GLOBAL_SAFETY"],
                )
            )


def _organization_view(organization: Organization, role: str) -> OrganizationView:
    return OrganizationView(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        role=role,
        status=organization.status,
        billing_email=organization.billing_email,
        spend_cap_paise=organization.spend_cap_paise,
        created_at=organization.created_at,
    )


def _workspace_view(workspace: Workspace) -> WorkspaceView:
    return WorkspaceView.model_validate(workspace)


def create_organization(
    session: Session,
    principal: Principal,
    payload: OrganizationCreate,
) -> tuple[OrganizationView, WorkspaceView]:
    profile = sync_user_profile(session, principal)
    if profile.created_free_organization:
        raise APIError(
            409,
            "free_organization_limit",
            "This identity has already created its free organization.",
        )
    organization_slug = slugify(payload.slug or payload.name)
    if session.scalar(select(Organization.id).where(Organization.slug == organization_slug)):
        organization_slug = f"{organization_slug[:70]}-{secrets.token_hex(3)}"
    organization = Organization(
        name=payload.name.strip(),
        slug=organization_slug,
        billing_email=principal.email,
    )
    session.add(organization)
    session.flush()
    membership = Membership(
        organization_id=organization.id,
        auth_user_id=principal.user_id,
        role="owner",
    )
    session.add(membership)
    session.add(BillingAccount(organization_id=organization.id))
    profile.created_free_organization = True
    workspace = _create_workspace_record(
        session,
        organization.id,
        principal.user_id,
        WorkspaceCreate(
            name=payload.workspace_name,
            slug=payload.workspace_slug,
            industry_template=payload.industry_template,
        ),
    )
    context = TenantContext(
        organization_id=organization.id,
        workspace_id=workspace.id,
        actor_id=principal.user_id,
        actor_type="USER",
        role="owner",
    )
    record_audit(
        session,
        context,
        "organization.created",
        "organization",
        organization.id,
        {"workspace_id": workspace.id, "template": payload.industry_template},
    )
    session.flush()
    return _organization_view(organization, "owner"), _workspace_view(workspace)


def list_organizations(
    session: Session, principal: Principal
) -> list[OrganizationView]:
    sync_user_profile(session, principal)
    rows = session.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(
            Membership.auth_user_id == principal.user_id,
            Membership.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
        .order_by(Organization.name)
    ).all()
    return [_organization_view(organization, role) for organization, role in rows]


def _create_workspace_record(
    session: Session,
    organization_id: str,
    actor_id: str,
    payload: WorkspaceCreate,
) -> Workspace:
    workspace_slug = slugify(payload.slug or payload.name)
    if session.scalar(
        select(Workspace.id).where(
            Workspace.organization_id == organization_id,
            Workspace.slug == workspace_slug,
        )
    ):
        raise APIError(409, "workspace_slug_exists", "That workspace slug is already used.")
    workspace = Workspace(
        organization_id=organization_id,
        name=payload.name.strip(),
        slug=workspace_slug,
        industry_template=payload.industry_template,
    )
    session.add(workspace)
    session.flush()
    template = TEMPLATE_DEFAULTS[payload.industry_template]
    profile = WorkspaceProfileVersion(
        organization_id=organization_id,
        workspace_id=workspace.id,
        version=1,
        status="PUBLISHED",
        template_key=payload.industry_template,
        tone=template["tone"],
        response_length="CONCISE",
        supported_topics=template["topics"],
        enabled_rule_packs=template["rule_packs"],
        escalation_threshold=7,
        published_at=datetime.now(timezone.utc),
        created_by=actor_id,
    )
    session.add(profile)
    session.flush()
    workspace.active_profile_version_id = profile.id
    return workspace


def create_workspace(
    session: Session,
    context: TenantContext,
    payload: WorkspaceCreate,
) -> WorkspaceView:
    workspace = _create_workspace_record(
        session, context.organization_id, context.actor_id, payload
    )
    record_audit(
        session,
        TenantContext(
            organization_id=context.organization_id,
            workspace_id=workspace.id,
            actor_id=context.actor_id,
            actor_type=context.actor_type,
            role=context.role,
        ),
        "workspace.created",
        "workspace",
        workspace.id,
        {"template": payload.industry_template},
    )
    session.flush()
    return _workspace_view(workspace)


def list_workspaces(session: Session, organization_id: str) -> list[WorkspaceView]:
    values = session.scalars(
        select(Workspace)
        .where(Workspace.organization_id == organization_id, Workspace.status == "ACTIVE")
        .order_by(Workspace.name)
    ).all()
    return [_workspace_view(value) for value in values]


def create_invitation(
    session: Session,
    settings: Settings,
    context: TenantContext,
    payload: InvitationCreate,
) -> InvitationView:
    existing_user = session.scalar(
        select(UserProfile).where(func.lower(UserProfile.email) == payload.email)
    )
    if existing_user and session.scalar(
        select(Membership.id).where(
            Membership.organization_id == context.organization_id,
            Membership.auth_user_id == existing_user.auth_user_id,
            Membership.status == "ACTIVE",
        )
    ):
        raise APIError(409, "already_a_member", "This user is already a member.")
    raw_token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = Invitation(
        organization_id=context.organization_id,
        email=payload.email,
        role=payload.role,
        token_digest=digest,
        invited_by=context.actor_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(invitation)
    session.flush()
    record_audit(
        session,
        context,
        "team.invited",
        "invitation",
        invitation.id,
        {"email": payload.email, "role": payload.role},
    )
    invite_url = f"{settings.public_app_url}/accept-invite?token={raw_token}"
    queue_email(
        session,
        context.organization_id,
        payload.email,
        "team_invitation",
        {"invite_url": invite_url, "role": payload.role},
    )
    return InvitationView(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        role=invitation.role,
        expires_at=invitation.expires_at,
        invite_url=invite_url,
    )


def accept_invitation(
    session: Session, principal: Principal, token: str
) -> OrganizationView:
    sync_user_profile(session, principal)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = session.scalar(
        select(Invitation).where(Invitation.token_digest == digest)
    )
    now = datetime.now(timezone.utc)
    expires_at = invitation.expires_at if invitation else now
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        invitation is None
        or invitation.accepted_at is not None
        or expires_at < now
        or invitation.email.lower() != principal.email.lower()
    ):
        raise APIError(404, "invalid_invitation", "Invitation is invalid or expired.")
    membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == invitation.organization_id,
            Membership.auth_user_id == principal.user_id,
        )
    )
    if membership is None:
        membership = Membership(
            organization_id=invitation.organization_id,
            auth_user_id=principal.user_id,
            role=invitation.role,
        )
        session.add(membership)
    else:
        membership.role = invitation.role
        membership.status = "ACTIVE"
    invitation.accepted_at = now
    organization = session.get(Organization, invitation.organization_id)
    if organization is None:
        raise APIError(404, "invalid_invitation", "Invitation is invalid or expired.")
    context = TenantContext(
        organization_id=organization.id,
        workspace_id=None,
        actor_id=principal.user_id,
        actor_type="USER",
        role=invitation.role,
    )
    record_audit(
        session,
        context,
        "team.invitation_accepted",
        "membership",
        membership.id,
        {"role": invitation.role},
    )
    return _organization_view(organization, invitation.role)


def list_members(session: Session, organization_id: str) -> list[MemberView]:
    rows = session.execute(
        select(Membership, UserProfile.email)
        .join(UserProfile, UserProfile.auth_user_id == Membership.auth_user_id)
        .where(Membership.organization_id == organization_id)
        .order_by(UserProfile.email)
    ).all()
    return [
        MemberView(
            id=membership.id,
            auth_user_id=membership.auth_user_id,
            email=email,
            role=membership.role,
            status=membership.status,
            created_at=membership.created_at,
        )
        for membership, email in rows
    ]


def update_member(
    session: Session,
    context: TenantContext,
    membership_id: str,
    payload: MemberUpdate,
) -> MemberView:
    membership = session.scalar(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.organization_id == context.organization_id,
        )
    )
    if membership is None:
        raise APIError(404, "not_found", "Member not found.")
    if membership.role == "owner":
        raise APIError(
            409,
            "owner_role_protected",
            "Transfer ownership before changing the owner membership.",
        )
    membership.role = payload.role
    membership.status = payload.status
    email = session.scalar(
        select(UserProfile.email).where(
            UserProfile.auth_user_id == membership.auth_user_id
        )
    ) or ""
    record_audit(
        session,
        context,
        "team.member_updated",
        "membership",
        membership.id,
        {"role": payload.role, "status": payload.status},
    )
    return MemberView(
        id=membership.id,
        auth_user_id=membership.auth_user_id,
        email=email,
        role=membership.role,
        status=membership.status,
        created_at=membership.created_at,
    )


def transfer_ownership(
    session: Session,
    context: TenantContext,
    payload: OwnershipTransfer,
) -> None:
    current = session.scalar(
        select(Membership).where(
            Membership.organization_id == context.organization_id,
            Membership.auth_user_id == context.actor_id,
            Membership.role == "owner",
            Membership.status == "ACTIVE",
        )
    )
    target = session.scalar(
        select(Membership).where(
            Membership.organization_id == context.organization_id,
            Membership.auth_user_id == payload.auth_user_id,
            Membership.status == "ACTIVE",
        )
    )
    if current is None or target is None or current.id == target.id:
        raise APIError(409, "invalid_ownership_transfer", "Select another active member.")
    current.role = "admin"
    target.role = "owner"
    record_audit(
        session,
        context,
        "organization.ownership_transferred",
        "organization",
        context.organization_id,
        {"previous_owner": current.auth_user_id, "new_owner": target.auth_user_id},
    )


def delete_organization(session: Session, context: TenantContext) -> None:
    organization = session.get(Organization, context.organization_id)
    if organization is None:
        raise APIError(404, "not_found", "Organization not found.")
    organization.status = "DELETED"
    for workspace in session.scalars(
        select(Workspace).where(Workspace.organization_id == organization.id)
    ).all():
        workspace.status = "ARCHIVED"
    record_audit(
        session,
        context,
        "organization.deleted",
        "organization",
        organization.id,
    )


def create_profile_draft(
    session: Session,
    context: TenantContext,
    payload: ProfileDraft,
) -> WorkspaceProfileVersion:
    latest = session.scalar(
        select(func.max(WorkspaceProfileVersion.version)).where(
            WorkspaceProfileVersion.workspace_id == context.workspace_id
        )
    ) or 0
    profile = WorkspaceProfileVersion(
        organization_id=context.organization_id,
        workspace_id=context.workspace_id,
        version=latest + 1,
        status="DRAFT",
        template_key=payload.template_key,
        tone=payload.tone,
        response_length=payload.response_length,
        custom_instructions=payload.custom_instructions,
        supported_topics=payload.supported_topics,
        enabled_rule_packs=sorted(set(["GLOBAL_SAFETY", *payload.enabled_rule_packs])),
        escalation_threshold=payload.escalation_threshold,
        created_by=context.actor_id,
    )
    session.add(profile)
    session.flush()
    record_audit(
        session,
        context,
        "profile.draft_created",
        "profile_version",
        profile.id,
        {"version": profile.version, "template": profile.template_key},
    )
    return profile


def publish_profile(
    session: Session, context: TenantContext, profile_id: str
) -> WorkspaceProfileVersion:
    profile = session.scalar(
        select(WorkspaceProfileVersion).where(
            WorkspaceProfileVersion.id == profile_id,
            WorkspaceProfileVersion.organization_id == context.organization_id,
            WorkspaceProfileVersion.workspace_id == context.workspace_id,
        )
    )
    if profile is None:
        raise APIError(404, "not_found", "Profile version not found.")
    profile.status = "PUBLISHED"
    profile.published_at = datetime.now(timezone.utc)
    workspace = session.get(Workspace, context.workspace_id)
    if workspace is None:
        raise APIError(404, "not_found", "Workspace not found.")
    workspace.active_profile_version_id = profile.id
    workspace.industry_template = profile.template_key
    record_audit(
        session,
        context,
        "profile.published",
        "profile_version",
        profile.id,
        {"version": profile.version},
    )
    return profile


def list_profiles(
    session: Session, organization_id: str, workspace_id: str
) -> list[WorkspaceProfileVersion]:
    return list(
        session.scalars(
            select(WorkspaceProfileVersion)
            .where(
                WorkspaceProfileVersion.organization_id == organization_id,
                WorkspaceProfileVersion.workspace_id == workspace_id,
            )
            .order_by(WorkspaceProfileVersion.version.desc())
        ).all()
    )
