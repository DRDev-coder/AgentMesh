from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.db.models import SaaSDecision
from api.errors import APIError
from api.saas_schemas import (
    DecisionListItem,
    PublicDecisionRequest,
    PublicDecisionResponse,
)
from api.services import decisions as decision_service
from api.services.api_keys import authenticate_key, get_or_create_playground_principal
from api.tenancy import get_db_session, set_tenant_database_context, workspace_context


router = APIRouter(tags=["decisions"])


@router.post("/decisions", response_model=PublicDecisionResponse)
async def create_decision(
    payload: PublicDecisionRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    idempotency_key: str = Header(
        min_length=8, max_length=128, alias="Idempotency-Key"
    ),
    session: Session = Depends(get_db_session),
) -> PublicDecisionResponse:
    key = authenticate_key(
        session, request.app.state.settings, authorization
    )
    client_ip = request.client.host if request.client else "unknown"
    limit = request.app.state.settings.public_rate_limit_per_minute
    request.app.state.rate_limiter.check(f"ip:{client_ip}", limit * 2)
    request.app.state.rate_limiter.check(f"org:{key.organization_id}", limit)
    request.app.state.rate_limiter.check(f"workspace:{key.workspace_id}", limit)
    request.app.state.rate_limiter.check(f"key:{key.key_id}", limit)
    return await decision_service.create_decision(
        session=session,
        database=request.app.state.database,
        settings=request.app.state.settings,
        orchestrator=request.app.state.orchestrator,
        key=key,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/playground/decisions",
    response_model=PublicDecisionResponse,
)
async def create_playground_decision(
    organization_id: str,
    workspace_id: str,
    payload: PublicDecisionRequest,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
        min_length=8,
        max_length=128,
        alias="Idempotency-Key",
    ),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> PublicDecisionResponse:
    context = workspace_context(
        organization_id, workspace_id, "playground:use", session, principal
    )
    key = get_or_create_playground_principal(
        session, request.app.state.settings, context
    )
    return await decision_service.create_decision(
        session=session,
        database=request.app.state.database,
        settings=request.app.state.settings,
        orchestrator=request.app.state.orchestrator,
        key=key,
        idempotency_key=idempotency_key or f"playground-{uuid.uuid4()}",
        payload=payload,
    )


@router.get("/decisions/{decision_id}", response_model=PublicDecisionResponse)
def get_public_decision(
    decision_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db_session),
) -> PublicDecisionResponse:
    key = authenticate_key(session, request.app.state.settings, authorization)
    key.require("decisions:read")
    decision = session.scalar(
        select(SaaSDecision).where(
            SaaSDecision.id == decision_id,
            SaaSDecision.organization_id == key.organization_id,
            SaaSDecision.workspace_id == key.workspace_id,
        )
    )
    if decision is None:
        raise APIError(404, "not_found", "Decision not found.")
    return decision_service.decision_response(
        decision, "traces:read" in key.scopes
    )


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/decisions",
    response_model=list[DecisionListItem],
)
def list_dashboard_decisions(
    organization_id: str,
    workspace_id: str,
    limit: int = 50,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[DecisionListItem]:
    workspace_context(
        organization_id, workspace_id, "decisions:read", session, principal
    )
    limit = max(1, min(limit, 100))
    values = session.scalars(
        select(SaaSDecision)
        .where(
            SaaSDecision.organization_id == organization_id,
            SaaSDecision.workspace_id == workspace_id,
        )
        .order_by(SaaSDecision.created_at.desc())
        .limit(limit)
    ).all()
    return [DecisionListItem.model_validate(value) for value in values]


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/decisions/{decision_id}",
    response_model=PublicDecisionResponse,
)
def get_dashboard_decision(
    organization_id: str,
    workspace_id: str,
    decision_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> PublicDecisionResponse:
    workspace_context(
        organization_id, workspace_id, "decisions:read", session, principal
    )
    set_tenant_database_context(session, organization_id)
    decision = session.scalar(
        select(SaaSDecision).where(
            SaaSDecision.id == decision_id,
            SaaSDecision.organization_id == organization_id,
            SaaSDecision.workspace_id == workspace_id,
        )
    )
    if decision is None:
        raise APIError(404, "not_found", "Decision not found.")
    return decision_service.decision_response(decision, True)
