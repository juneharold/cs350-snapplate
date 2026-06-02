from __future__ import annotations

from app.config.env import Env
from app.config.logger import create_logger

logger = create_logger(__name__)


class EmailService:
    @property
    def is_real_provider(self) -> bool:
        """True when an email provider is configured (SMTP_URL set). When False we're
        in dev/no-email mode and the magic-link token is surfaced for testing."""
        return bool(Env.get(Env.SMTP_URL))

    async def send_magic_link(self, email: str, token: str) -> None:
        link = f"snapplate://auth/verify?token={token}"
        if not self.is_real_provider:
            # Dev: no provider → log the link so it can be consumed/tested.
            logger.info(f"[magic-link][dev] to={email} link={link} token={token}")
            return
        # TODO: real provider send when SMTP_URL is configured.
        logger.info(f"[magic-link] sending to {email} via configured provider")
