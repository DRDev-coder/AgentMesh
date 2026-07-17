from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from api.schemas import EscalationAction, EscalationRecord, EscalationUpdate
from shared.schemas import EscalationStatus


router = APIRouter(prefix="/escalations", tags=["prototype-review"])


async def require_review_key(x_review_api_key: str | None = Header(default=None)) -> None:
    configured = os.getenv("REVIEW_API_KEY", "").strip()
    if configured and x_review_api_key != configured:
        raise HTTPException(status_code=401, detail="Review API key required")


def _not_found(ticket_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Escalation {ticket_id} not found")


@router.get("", response_model=list[EscalationRecord], dependencies=[Depends(require_review_key)])
async def list_escalations(
    request: Request,
    status: EscalationStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EscalationRecord]:
    return await asyncio.to_thread(
        request.app.state.repository.list_escalations, status, limit
    )


@router.get("/{ticket_id}", response_model=EscalationRecord, dependencies=[Depends(require_review_key)])
async def get_escalation(ticket_id: str, request: Request) -> EscalationRecord:
    try:
        return await asyncio.to_thread(
            request.app.state.repository.get_escalation, ticket_id
        )
    except KeyError:
        raise _not_found(ticket_id) from None


@router.patch("/{ticket_id}", response_model=EscalationRecord, dependencies=[Depends(require_review_key)])
async def update_escalation(
    ticket_id: str, payload: EscalationUpdate, request: Request
) -> EscalationRecord:
    try:
        return await asyncio.to_thread(
            request.app.state.repository.update_escalation,
            ticket_id,
            **payload.model_dump(exclude_none=True),
        )
    except KeyError:
        raise _not_found(ticket_id) from None


@router.post("/{ticket_id}/approve", response_model=EscalationRecord, dependencies=[Depends(require_review_key)])
async def approve_escalation(
    ticket_id: str, request: Request, payload: EscalationAction | None = None
) -> EscalationRecord:
    return await _apply_action(
        ticket_id,
        request,
        EscalationStatus.APPROVED,
        payload,
        "Prototype reviewer approved the suggested answer.",
    )


@router.post("/{ticket_id}/reject", response_model=EscalationRecord, dependencies=[Depends(require_review_key)])
async def reject_escalation(
    ticket_id: str, request: Request, payload: EscalationAction | None = None
) -> EscalationRecord:
    return await _apply_action(
        ticket_id,
        request,
        EscalationStatus.REJECTED,
        payload,
        "Prototype reviewer rejected the suggested answer as unsafe or unsuitable.",
    )


@router.post("/{ticket_id}/resolve", response_model=EscalationRecord, dependencies=[Depends(require_review_key)])
async def resolve_escalation(
    ticket_id: str, request: Request, payload: EscalationAction | None = None
) -> EscalationRecord:
    return await _apply_action(
        ticket_id,
        request,
        EscalationStatus.RESOLVED,
        payload,
        "Prototype review completed.",
    )


async def _apply_action(
    ticket_id: str,
    request: Request,
    status: EscalationStatus,
    payload: EscalationAction | None,
    default_notes: str,
) -> EscalationRecord:
    values = payload or EscalationAction()
    notes = values.resolution_notes or values.reason or default_notes
    try:
        return await asyncio.to_thread(
            request.app.state.repository.update_escalation,
            ticket_id,
            draft_answer=values.answer,
            status=status,
            resolution_notes=notes,
        )
    except KeyError:
        raise _not_found(ticket_id) from None
