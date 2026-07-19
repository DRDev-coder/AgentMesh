from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import (
    WebhookCreate,
    WebhookCreated,
    WebhookDeliveryView,
    WebhookView,
)
from api.services import webhooks
from api.tenancy import get_db_session, workspace_context


router = APIRouter(tags=["webhooks"])


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/webhooks",
    response_model=list[WebhookView],
)
def list_webhooks(
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[WebhookView]:
    workspace_context(
        organization_id, workspace_id, "webhooks:manage", session, principal
    )
    return webhooks.list_endpoints(session, organization_id, workspace_id)


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/webhooks",
    response_model=WebhookCreated,
    status_code=201,
)
def create_webhook(
    payload: WebhookCreate,
    request: Request,
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> WebhookCreated:
    context = workspace_context(
        organization_id, workspace_id, "webhooks:manage", session, principal
    )
    return webhooks.create_endpoint(
        session, request.app.state.settings, context, payload
    )


@router.delete(
    "/organizations/{organization_id}/workspaces/{workspace_id}/webhooks/{endpoint_id}",
    response_model=WebhookView,
)
def disable_webhook(
    organization_id: str,
    workspace_id: str,
    endpoint_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> WebhookView:
    context = workspace_context(
        organization_id, workspace_id, "webhooks:manage", session, principal
    )
    return webhooks.disable_endpoint(session, context, endpoint_id)


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/webhook-deliveries",
    response_model=list[WebhookDeliveryView],
)
def webhook_deliveries(
    organization_id: str,
    workspace_id: str,
    endpoint_id: str | None = None,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[WebhookDeliveryView]:
    workspace_context(
        organization_id, workspace_id, "webhooks:manage", session, principal
    )
    return webhooks.list_deliveries(
        session, organization_id, workspace_id, endpoint_id
    )
