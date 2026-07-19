from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers or {}


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


def error_payload(
    request: Request, code: str, message: str, details: Any | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id(request),
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        error_payload(request, exc.code, exc.message, exc.details),
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "location": ".".join(str(part) for part in item.get("loc", [])),
            "message": item.get("msg", "Invalid value"),
            "type": item.get("type", "validation_error"),
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        error_payload(request, "validation_error", "Request validation failed.", details),
        status_code=422,
    )
