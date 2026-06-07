from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from sqlmodel import Field

from app.models.base import ForeignKeyField, OptionalTimestampField, SQLModelBase
from app.utils.ids import taste_job_id

TasteJobState = Literal["queued", "running", "done", "failed"]
ACTIVE_TASTE_JOB_STATES: tuple[TasteJobState, TasteJobState] = ("queued", "running")
_TASTE_JOB_STATES: tuple[TasteJobState, ...] = (
    *ACTIVE_TASTE_JOB_STATES,
    "done",
    "failed",
)


def taste_job_state(state: str) -> TasteJobState:
    if state not in _TASTE_JOB_STATES:
        raise ValueError(f"unknown taste job state: {state}")
    return cast(TasteJobState, state)


class TasteJobModel(SQLModelBase, table=True):
    __tablename__ = "taste_jobs"  # type: ignore[reportAssignmentType]

    id: str = Field(default_factory=taste_job_id, primary_key=True)
    # The active-job partial unique index covers user_id for the lookup path.
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE", index=False)
    state: str = Field(nullable=False)
    started_at: datetime | None = OptionalTimestampField()
    finished_at: datetime | None = OptionalTimestampField()
    error: str | None = Field(default=None)
