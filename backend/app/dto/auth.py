from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.dto.base import BaseRequest, BaseResponse, BaseResponseCore
from app.schemas.auth import AuthUserInfo


# ── Request DTOs ──────────────────────────────────────────────────────────────
class MagicLinkRequest(BaseRequest):
    email: str


class VerifyRequest(BaseRequest):
    token: str


class DeleteAccountRequest(BaseRequest):
    confirm_email: str


# ── Repo data schemas ─────────────────────────────────────────────────────────
class CreateUserData(BaseRequest):
    email: str


class UpdateUserData(BaseRequest):
    nickname: str | None = None
    is_onboarded: bool | None = None
    taste_type: str | None = None
    deleted_at: datetime | None = None


class CreateMagicLinkData(BaseRequest):
    token: str
    email: str
    expires_at: datetime


class UpdateMagicLinkData(BaseRequest):
    consumed_at: datetime | None = None


# ── Response Cores + aliases ──────────────────────────────────────────────────
class MagicLinkResponseCore(BaseResponseCore):
    sent: bool = True
    resend_available_at: str
    # DEV ONLY: the raw token, present only when no email provider is configured
    # (SMTP_URL empty) so the UI can simulate the link tap. None in prod.
    # Serializes as `_mock_link_token` to match the frontend mock contract
    # (email/page.tsx reads res._mock_link_token).
    mock_link_token: str | None = Field(default=None, serialization_alias="_mock_link_token")


class VerifyResponseCore(BaseResponseCore):
    access_token: str
    expires_in: int
    user: AuthUserInfo


MagicLinkResponse = BaseResponse[MagicLinkResponseCore]
VerifyResponse = BaseResponse[VerifyResponseCore]
