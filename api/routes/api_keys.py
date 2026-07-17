from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import APIKeyCreate, APIKeyCreated, APIKeyView
from api.services import api_keys as key_service
from api.tenancy import get_db_session, workspace_context


router = APIRouter(tags=["api-keys"])


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/api-keys",
    response_model=list[APIKeyView],
)
def api_keys(
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[APIKeyView]:
    workspace_context(organization_id, workspace_id, "keys:manage", session, principal)
    return key_service.list_keys(session, organization_id, workspace_id)


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/api-keys",
    response_model=APIKeyCreated,
    status_code=201,
)
def create_api_key(
    payload: APIKeyCreate,
    request: Request,
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> APIKeyCreated:
    context = workspace_context(
        organization_id, workspace_id, "keys:manage", session, principal
    )
    return key_service.create_key(session, request.app.state.settings, context, payload)


@router.delete(
    "/organizations/{organization_id}/workspaces/{workspace_id}/api-keys/{key_id}",
    response_model=APIKeyView,
)
def revoke_api_key(
    organization_id: str,
    workspace_id: str,
    key_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> APIKeyView:
    context = workspace_context(
        organization_id, workspace_id, "keys:manage", session, principal
    )
    return key_service.revoke_key(session, context, key_id)
