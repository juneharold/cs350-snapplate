from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.config.env import Env

ALGORITHM = "HS256"


def _secret() -> str:
    return Env.get(Env.JWT_SECRET_KEY)


def _expiry_hours() -> int:
    return int(Env.get(Env.JWT_EXPIRATION_HOURS))


def issue_token(user_id: str) -> tuple[str, int]:
    """Return (jwt, expires_in_seconds). sub = user_id."""
    expires_in = _expiry_hours() * 3600
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, _secret(), algorithm=ALGORITHM)
    return token, expires_in


def verify_token(token: str) -> str | None:
    """Return user_id (sub) if valid, else None."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return sub if isinstance(sub, str) else None
    except jwt.PyJWTError:
        return None
