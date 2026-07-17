from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import SpendCapUpdate, UsageSummary
from api.services.audit import record_audit
from api.services.usage import summary
from api.services import usage as usage_service
from api.tenancy import get_db_session, organization_context


router = APIRouter(tags=["usage"])


@router.get(
    "/organizations/{organization_id}/usage",
    response_model=UsageSummary,
)
def organization_usage(
    request: Request,
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> UsageSummary:
    organization_context(organization_id, "usage:read", session, principal)
    return summary(session, request.app.state.settings, organization_id)


@router.patch(
    "/organizations/{organization_id}/usage/spend-cap",
    response_model=UsageSummary,
)
def set_spend_cap(
    payload: SpendCapUpdate,
    request: Request,
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> UsageSummary:
    context = organization_context(
        organization_id, "billing:manage", session, principal
    )
    usage_service.update_spend_cap(
        session, organization_id, payload.spend_cap_cents
    )
    record_audit(
        session,
        context,
        "billing.spend_cap_updated",
        "organization",
        organization_id,
        {"spend_cap_cents": payload.spend_cap_cents},
    )
    return summary(session, request.app.state.settings, organization_id)
