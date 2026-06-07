from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict

from app.dto.base import BaseResponse, BaseResponseCore
from app.models.taste_job import TasteJobState

TasteJobStatus = TasteJobState


class TasteProfileResponseCore(BaseResponseCore):
    model_config = ConfigDict(extra="allow")


class TasteRefreshResponseCore(BaseResponseCore):
    job_id: str
    status: TasteJobStatus


class TasteJobResponseCore(BaseResponseCore):
    job_id: str
    status: TasteJobStatus
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


TasteProfileResponse = BaseResponse[TasteProfileResponseCore]
TasteRefreshResponse = BaseResponse[TasteRefreshResponseCore]
TasteJobResponse = BaseResponse[TasteJobResponseCore]
