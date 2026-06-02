from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.user import MeResponse, UpdateMeRequest
from app.services.main.user import UserService

api = APIRouter()


@api.get("/me", response_model=MeResponse)
async def get_me(
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> MeResponse:
    me = await UserService(ctx).get_me(user.user_id)
    return MeResponse(response=me)


@api.patch("/me", response_model=MeResponse)
async def update_me(
    body: UpdateMeRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> MeResponse:
    me = await UserService(ctx).update_me(user.user_id, body.nickname)
    return MeResponse(response=me)
