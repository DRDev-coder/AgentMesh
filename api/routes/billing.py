from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import BillingPortalResult, CheckoutResult
from api.services import billing
from api.tenancy import get_db_session, organization_context, set_platform_database_context


router = APIRouter(tags=["billing"])


@router.post(
    "/organizations/{organization_id}/billing/checkout",
    response_model=CheckoutResult,
)
def checkout(
    request: Request,
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> CheckoutResult:
    context = organization_context(
        organization_id, "billing:manage", session, principal
    )
    return CheckoutResult(
        url=billing.create_checkout(session, request.app.state.settings, context)
    )


@router.post(
    "/organizations/{organization_id}/billing/portal",
    response_model=BillingPortalResult,
)
def portal(
    request: Request,
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> BillingPortalResult:
    context = organization_context(
        organization_id, "billing:manage", session, principal
    )
    return BillingPortalResult(
        url=billing.create_portal(session, request.app.state.settings, context)
    )


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    session: Session = Depends(get_db_session),
) -> Response:
    set_platform_database_context(session, True)
    billing.process_stripe_webhook(
        session,
        request.app.state.settings,
        await request.body(),
        stripe_signature,
    )
    return Response(status_code=204)
