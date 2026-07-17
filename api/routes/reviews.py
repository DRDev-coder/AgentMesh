from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import ReviewClaim, TenantEscalationView
from api.services import reviews
from api.tenancy import get_db_session, workspace_context


router = APIRouter(tags=["reviews"])


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/reviews",
    response_model=list[TenantEscalationView],
)
def review_queue(
    organization_id: str,
    workspace_id: str,
    status: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[TenantEscalationView]:
    workspace_context(
        organization_id, workspace_id, "reviews:read", session, principal
    )
    return [
        TenantEscalationView.model_validate(value)
        for value in reviews.list_escalations(
            session, organization_id, workspace_id, status
        )
    ]


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{escalation_id}",
    response_model=TenantEscalationView,
)
def review_detail(
    organization_id: str,
    workspace_id: str,
    escalation_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> TenantEscalationView:
    context = workspace_context(
        organization_id, workspace_id, "reviews:read", session, principal
    )
    return TenantEscalationView.model_validate(
        reviews.get_escalation(session, context, escalation_id)
    )


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{escalation_id}/claim",
    response_model=TenantEscalationView,
)
def claim_review(
    payload: ReviewClaim,
    organization_id: str,
    workspace_id: str,
    escalation_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> TenantEscalationView:
    context = workspace_context(
        organization_id, workspace_id, "reviews:manage", session, principal
    )
    return TenantEscalationView.model_validate(
        reviews.claim_escalation(session, context, escalation_id, payload)
    )


def _transition_route(target_status: str):
    async def transition(
        payload: ReviewClaim,
        organization_id: str,
        workspace_id: str,
        escalation_id: str,
        session: Session = Depends(get_db_session),
        principal: Principal = Depends(get_principal),
    ) -> TenantEscalationView:
        context = workspace_context(
            organization_id, workspace_id, "reviews:manage", session, principal
        )
        value = await reviews.transition_escalation(
            session, context, escalation_id, target_status, payload
        )
        return TenantEscalationView.model_validate(value)

    return transition


router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{escalation_id}/approve",
    response_model=TenantEscalationView,
)(_transition_route("APPROVED"))
router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{escalation_id}/reject",
    response_model=TenantEscalationView,
)(_transition_route("REJECTED"))
router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{escalation_id}/resolve",
    response_model=TenantEscalationView,
)(_transition_route("RESOLVED"))
