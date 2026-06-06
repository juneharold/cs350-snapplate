from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from app.dto.base import BaseResponse, BaseResponseCore


class TasteProfileResponseCore(BaseResponseCore):
    model_config = ConfigDict(extra="allow")


class TasteRefreshResponseCore(BaseResponseCore):
    job_id: str
    status: Literal["queued"] = "queued"


TasteProfileResponse = BaseResponse[TasteProfileResponseCore]
TasteRefreshResponse = BaseResponse[TasteRefreshResponseCore]
