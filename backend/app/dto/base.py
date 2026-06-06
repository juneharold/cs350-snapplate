from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas.base import BaseSchema


class BaseRequest(BaseSchema):
    pass


class BaseResponseCore(BaseSchema):
    """Base for multi-field response payloads (lists, paginated results)."""


# `response` can be any schema (an Info directly, or a multi-field Core).
T = TypeVar("T", bound=BaseSchema)


class BaseResponse(BaseSchema, Generic[T]):
    code: int = 0
    success: bool = True
    message: str = "success"
    response: T | None = None

    def render_json(self, status_code: int = 200) -> JSONResponse:
        return JSONResponse(content=jsonable_encoder(self), status_code=status_code)


class BaseStreamingResponse(StreamingResponse):
    """SSE responses (taste/refresh polling is sync in v1, but kept for parity)."""

    def __init__(self, content: AsyncGenerator[str, None]) -> None:
        super().__init__(
            content=content,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
