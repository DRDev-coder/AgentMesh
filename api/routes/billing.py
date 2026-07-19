from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.saas_schemas import CheckoutResult
from api.services import billing
from api.tenancy import get_db_session, organization_context, set_platform_database_context


router = APIRouter(tags=["billing"])


@router.post(
    "/organizations/{organization_id}/billing/subscription",
    response_model=CheckoutResult,
)
def create_subscription(
    request: Request,
    organization_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> CheckoutResult:
    context = organization_context(
        organization_id, "billing:manage", session, principal
    )
    return CheckoutResult(
        url=billing.create_subscription(session, request.app.state.settings, context)
    )


@router.post("/webhooks/razorpay", include_in_schema=False)
async def razorpay_webhook(
    request: Request,
    razorpay_signature: str | None = Header(
        default=None, alias="X-Razorpay-Signature"
    ),
    razorpay_event_id: str | None = Header(
        default=None, alias="X-Razorpay-Event-Id"
    ),
    session: Session = Depends(get_db_session),
) -> Response:
    set_platform_database_context(session, True)
    billing.process_razorpay_webhook(
        session,
        request.app.state.settings,
        await request.body(),
        razorpay_signature,
        razorpay_event_id,
    )
    return Response(status_code=204)
