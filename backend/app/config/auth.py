from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from app.config.http_errors import AppError
from app.config.lifespan import Context, get_context
from app.repositories.user import UserRepository


@dataclass
class UserContext:
    user_id: str


async def get_user_context(
    request: Request,
    ctx: Context = Depends(get_context),
) -> UserContext:
    """Required-auth dependency. 401 if the middleware didn't attach a principal.

    Also confirms the user still exists and isn't soft-deleted. The JWT is
    stateless (signature + expiry only), so without this check a deleted
    account's token would keep working until it expires; we reject it now
    (REQ-4.1-008).
    """
    user_ctx = getattr(request.state, "user_ctx", None)
    if user_ctx is None:
        raise AppError(401, "unauthorized", "Sign in to continue.")
    user = await UserRepository(ctx.db_session).find(user_ctx.user_id)
    if user is None or user.deleted_at is not None:
        raise AppError(401, "unauthorized", "Sign in to continue.")
    return user_ctx


def get_optional_user_context(request: Request) -> UserContext | None:
    """Auth-optional dependency (e.g. /restaurants/* — a token enables
    is_bookmarked + personalization, but anonymous access is allowed)."""
    return getattr(request.state, "user_ctx", None)
