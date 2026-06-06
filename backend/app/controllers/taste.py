from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.taste import (
    TasteProfileResponse,
    TasteProfileResponseCore,
    TasteRefreshResponse,
    TasteRefreshResponseCore,
)
from app.services.algorithm.taste_jobs import refresh_taste_for_user
from app.services.main.taste import TasteService
from app.utils.ids import make_id

api = APIRouter()


@api.get("/taste/profile", response_model=TasteProfileResponse)
async def get_profile(
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> TasteProfileResponse:
    payload = await TasteService(ctx).get_profile(user.user_id)
    return TasteProfileResponse(response=TasteProfileResponseCore.model_validate(payload))


@api.post("/taste/refresh", response_model=TasteRefreshResponse, status_code=202)
async def refresh(
    background_tasks: BackgroundTasks,
    request: Request,
    user: UserContext = Depends(get_user_context),
) -> TasteRefreshResponse:
    job_id = make_id("tj")
    background_tasks.add_task(refresh_taste_for_user, request.state.context, user.user_id)
    return TasteRefreshResponse(
        response=TasteRefreshResponseCore(job_id=job_id),
    )
