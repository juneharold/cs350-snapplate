from __future__ import annotations

from app.types.base import BaseStrEnum


class DraftStatus(BaseStrEnum):
    WAITING = "waiting"
    REMINDED = "reminded"
    NEEDS_PLACE = "needs_place"
    FINALIZING = "finalizing"
