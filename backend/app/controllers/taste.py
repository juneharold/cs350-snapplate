from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.base import BaseResponse
from app.services.main.taste import TasteService


TasteProfileResponse = BaseResponse[dict]

api = APIRouter()


@api.get("/taste/profile", response_model=TasteProfileResponse)
async def get_profile(
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> TasteProfileResponse:
    payload = await TasteService(ctx).get_profile(user.user_id)
    return TasteProfileResponse(response=payload)


@api.post("/taste/refresh", response_model=TasteProfileResponse)
async def refresh(
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> TasteProfileResponse:
    payload = await TasteService(ctx).refresh(user.user_id)
    return TasteProfileResponse(response=payload)
