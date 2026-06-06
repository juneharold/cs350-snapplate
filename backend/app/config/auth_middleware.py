from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config.auth import UserContext
from app.config.jwt import verify_token

# Paths that never require a principal (auth endpoints + liveness + docs).
_PUBLIC_PREFIXES = ("/health", "/v1/auth", "/docs", "/openapi.json", "/redoc")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not self._is_public(request.url.path):
            user_ctx = self._resolve(request)
            if user_ctx is not None:
                request.state.user_ctx = user_ctx
        return await call_next(request)

    @staticmethod
    def _is_public(path: str) -> bool:
        return any(path.startswith(p) for p in _PUBLIC_PREFIXES)

    @staticmethod
    def _resolve(request: Request) -> UserContext | None:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.removeprefix("Bearer ").strip()
        user_id = verify_token(token)
        return UserContext(user_id=user_id) if user_id else None
