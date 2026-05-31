from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.config.http_errors import AppError


@dataclass
class UserContext:
    user_id: str


def get_user_context(request: Request) -> UserContext:
    """Required-auth dependency. 401 if the middleware didn't attach a principal."""
    user_ctx = getattr(request.state, "user_ctx", None)
    if user_ctx is None:
        raise AppError(401, "unauthorized", "Sign in to continue.")
    return user_ctx


def get_optional_user_context(request: Request) -> UserContext | None:
    """Auth-optional dependency (e.g. /restaurants/* — a token enables
    is_bookmarked + personalization, but anonymous access is allowed)."""
    return getattr(request.state, "user_ctx", None)
