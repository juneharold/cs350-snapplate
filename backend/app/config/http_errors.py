from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _trace_id() -> str:
    return uuid.uuid4().hex


def error_body(code: str, message: str, field: str | None = None) -> dict:
    err: dict[str, str] = {"code": code, "message": message, "trace_id": _trace_id()}
    if field is not None:
        err["field"] = field
    return {"error": err}


class AppError(Exception):
    """Domain error that maps to the contract envelope."""

    def __init__(self, status: int, code: str, message: str, field: str | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(404, "not_found", message)


class OwnershipError(NotFoundError):
    """Cross-user access. Returns 404 (not 403) so we don't leak which ids exist
    (REQ-SEC-004 / plan §5.3)."""


def init_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=error_body(exc.code, exc.message, exc.field),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(f"http_{exc.status_code}", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = first.get("loc", [])
        field = ".".join(str(p) for p in loc[1:]) or None  # drop "body"/"query" prefix
        message = first.get("msg", "Validation error")
        return JSONResponse(
            status_code=422,
            content=error_body("validation_error", message, field),
        )
