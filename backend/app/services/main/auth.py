from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from app.config.http_errors import AppError
from app.config.jwt import issue_token
from app.config.lifespan import Context
from app.dto.auth import (
    CreateMagicLinkData,
    CreateUserData,
    UpdateMagicLinkData,
    UpdateUserData,
)
from app.repositories.magic_link import MagicLinkRepository
from app.repositories.user import UserRepository
from app.schemas.auth import AuthUserInfo
from app.services.email.sender import EmailService
from app.services.s3.storage import StorageService
from app.utils.time import as_utc, utcnow


class AuthService:
    LINK_TTL_MIN = 15
    RESEND_COOLDOWN_SEC = 60
    RESTORE_GRACE_DAYS = 30

    def __init__(self, ctx: Context):
        self.users = UserRepository(ctx.db_session)
        self.links = MagicLinkRepository(ctx.db_session)
        self.email = EmailService()
        self.storage = StorageService(ctx.s3)

    async def request_magic_link(self, email: str) -> tuple[str, str | None]:
        """Issue a single-use token, store its hash, send the link.

        Returns (resend_available_at_iso, dev_token). dev_token is the raw token,
        included ONLY when no email provider is configured (dev: SMTP_URL empty) so
        the UI can simulate tapping the link — never returned once email actually
        sends. In prod (SMTP_URL set) dev_token is None and the token only travels
        in the email.
        """
        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise AppError(400, "invalid_email", "That doesn't look like a valid email.", "email")

        raw_token = secrets.token_urlsafe(32)
        await self.links.create(
            CreateMagicLinkData(
                token=self._hash(raw_token),
                email=email,
                expires_at=utcnow() + timedelta(minutes=self.LINK_TTL_MIN),
            )
        )
        await self.email.send_magic_link(email, raw_token)
        dev_token = raw_token if not self.email.is_real_provider else None
        resend_at = (utcnow() + timedelta(seconds=self.RESEND_COOLDOWN_SEC)).isoformat()
        return resend_at, dev_token

    async def verify(self, raw_token: str) -> tuple[str, int, AuthUserInfo]:
        """Validate the token (unconsumed + unexpired), mark consumed, create or
        restore the user, issue a JWT. Returns (jwt, expires_in, AuthUserInfo)."""
        link = await self.links.find_by_token(self._hash(raw_token))
        if link is None:
            raise AppError(401, "invalid_token", "This sign-in link is invalid.")
        if link.consumed_at is not None:
            raise AppError(401, "expired_token", "This link has already been used.")
        if as_utc(link.expires_at) < utcnow():
            raise AppError(401, "expired_token", "This sign-in link has expired.")

        # Single-use: consume now.
        await self.links.update(link, UpdateMagicLinkData(consumed_at=utcnow()))

        user = await self.users.find_by_email(link.email)
        is_new = False
        if user is None:
            user = await self.users.create(CreateUserData(email=link.email))
            is_new = True
        elif user.deleted_at is not None:
            # Soft-delete restore within the grace window.
            if as_utc(user.deleted_at) > utcnow() - timedelta(days=self.RESTORE_GRACE_DAYS):
                user = await self.users.update(user, UpdateUserData(deleted_at=None))
            else:
                raise AppError(401, "invalid_token", "This account is no longer available.")

        token, expires_in = issue_token(user.id)
        profile_image_url = None
        if user.profile_image_url:
            profile_image_url = await self.storage.signed_url(user.profile_image_url)
        return (
            token,
            expires_in,
            AuthUserInfo.from_model(user, is_new=is_new, profile_image_url=profile_image_url),
        )

    async def logout(self, user_id: str) -> None:
        """v1: client-discards the JWT (stateless). No server-side denylist — the
        token stays valid until expiry. Documented limitation (CONVENTIONS §7)."""
        return None

    async def soft_delete_account(self, user_id: str, confirm_email: str) -> None:
        user = await self.users.find(user_id)
        if user is None:
            raise AppError(404, "not_found", "Account not found.")
        if user.email.strip().lower() != confirm_email.strip().lower():
            raise AppError(
                400, "email_mismatch", "Email does not match this account.", "confirm_email"
            )
        await self.users.update(user, UpdateUserData(deleted_at=utcnow()))

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
