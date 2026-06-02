from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.settings import (
    GetSettingsResponse,
    UpdateSettingsRequest,
)
from app.services.main.settings import SettingsService

api = APIRouter()


@api.get("/settings", response_model=GetSettingsResponse)
async def get_settings(
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> GetSettingsResponse:
    settings = await SettingsService(ctx).get_settings(user.user_id)
    return GetSettingsResponse(response=settings)


@api.patch("/settings", response_model=GetSettingsResponse)
async def update_settings(
    body: UpdateSettingsRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> GetSettingsResponse:
    # Convert the API request DTO to its domain form HERE; the service never
    # sees the request DTO (convention: request DTO stays client↔controller).
    settings = await SettingsService(ctx).update_settings(user.user_id, body.to_data())
    return GetSettingsResponse(response=settings)
