from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request, Response
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import (
    InvitationCreate,
    InvitationView,
    MemberView,
    MemberUpdate,
    OnboardingResult,
    OrganizationCreate,
    OrganizationView,
    OwnershipTransfer,
    ProfileDraft,
    ProfileView,
    WorkspaceCreate,
    WorkspaceView,
)
from api.services import tenants as tenant_service
from api.tenancy import (
    get_db_session,
    organization_context,
    principal_dependency,
    workspace_context,
)


router = APIRouter(tags=["organizations"])


@router.get("/organizations", response_model=list[OrganizationView])
def organizations(
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(principal_dependency),
) -> list[OrganizationView]:
    return tenant_service.list_organizations(session, principal)


@router.post("/organizations", response_model=OnboardingResult, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(principal_dependency),
) -> OnboardingResult:
    organization, workspace = tenant_service.create_organization(
        session, principal, payload
    )
    return OnboardingResult(organization=organization, workspace=workspace)


@router.post("/invitations/accept", response_model=OrganizationView)
def accept_invitation(
    token: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(principal_dependency),
) -> OrganizationView:
    return tenant_service.accept_invitation(session, principal, token)


@router.get(
    "/organizations/{organization_id}/workspaces",
    response_model=list[WorkspaceView],
)
def workspaces(
    organization_id: str = Path(),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[WorkspaceView]:
    organization_context(
        organization_id, "organization:read", session, principal
    )
    return tenant_service.list_workspaces(session, organization_id)


@router.post(
    "/organizations/{organization_id}/workspaces",
    response_model=WorkspaceView,
    status_code=201,
)
def create_workspace(
    payload: WorkspaceCreate,
    organization_id: str = Path(),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> WorkspaceView:
    context = organization_context(
        organization_id, "workspace:manage", session, principal
    )
    return tenant_service.create_workspace(session, context, payload)


@router.get(
    "/organizations/{organization_id}/members",
    response_model=list[MemberView],
)
def members(
    organization_id: str = Path(),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[MemberView]:
    organization_context(organization_id, "organization:read", session, principal)
    return tenant_service.list_members(session, organization_id)


@router.patch(
    "/organizations/{organization_id}/members/{membership_id}",
    response_model=MemberView,
)
def update_member(
    payload: MemberUpdate,
    organization_id: str,
    membership_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> MemberView:
    context = organization_context(
        organization_id, "team:manage", session, principal
    )
    return tenant_service.update_member(session, context, membership_id, payload)


@router.post(
    "/organizations/{organization_id}/transfer-ownership",
    status_code=204,
    response_class=Response,
)
def transfer_ownership(
    payload: OwnershipTransfer,
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> Response:
    context = organization_context(
        organization_id, "organization:transfer", session, principal
    )
    tenant_service.transfer_ownership(session, context, payload)
    return Response(status_code=204)


@router.delete(
    "/organizations/{organization_id}", status_code=204, response_class=Response
)
def delete_organization(
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> Response:
    context = organization_context(
        organization_id, "organization:delete", session, principal
    )
    tenant_service.delete_organization(session, context)
    return Response(status_code=204)


@router.post(
    "/organizations/{organization_id}/invitations",
    response_model=InvitationView,
    status_code=201,
)
def invite_member(
    payload: InvitationCreate,
    request: Request,
    organization_id: str = Path(),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> InvitationView:
    context = organization_context(organization_id, "team:manage", session, principal)
    return tenant_service.create_invitation(
        session, request.app.state.settings, context, payload
    )


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/profiles",
    response_model=list[ProfileView],
)
def profiles(
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[ProfileView]:
    workspace_context(
        organization_id, workspace_id, "profile:read", session, principal
    )
    return [
        ProfileView.model_validate(profile)
        for profile in tenant_service.list_profiles(
            session, organization_id, workspace_id
        )
    ]


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/profiles",
    response_model=ProfileView,
    status_code=201,
)
def create_profile(
    payload: ProfileDraft,
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> ProfileView:
    context = workspace_context(
        organization_id, workspace_id, "profile:manage", session, principal
    )
    return ProfileView.model_validate(
        tenant_service.create_profile_draft(session, context, payload)
    )


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/profiles/{profile_id}/publish",
    response_model=ProfileView,
)
def publish_profile(
    organization_id: str,
    workspace_id: str,
    profile_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> ProfileView:
    context = workspace_context(
        organization_id, workspace_id, "profile:manage", session, principal
    )
    return ProfileView.model_validate(
        tenant_service.publish_profile(session, context, profile_id)
    )
