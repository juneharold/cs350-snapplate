from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
 
from app.config.auth import UserContext, get_user_context
from app.config.http_errors import AppError
from app.config.lifespan import Context, get_context
from app.dto.user import MeResponse, UpdateMeRequest, AvatarUploadResponse, AvatarUploadResponseCore
from app.repositories.user import UserRepository
from app.services.main.user import UserService
from app.services.s3.storage import StorageService
from app.utils.ids import make_id
 
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


@api.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> AvatarUploadResponse:
    allowed_types = {"image/jpeg", "image/png", "image/jpg"}
    content_type = file.content_type
    if not content_type:
        filename = file.filename or ""
        if filename.lower().endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif filename.lower().endswith(".png"):
            content_type = "image/png"
        else:
            raise AppError(400, "unsupported_format", "Unsupported file format.")
            
    if content_type not in allowed_types:
        raise AppError(400, "unsupported_format", f"{content_type} not supported.")
        
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise AppError(400, "file_too_large", "Avatar file size exceeds 10MB limit.")
        
    suffix = make_id("av")
    key = f"avatars/{user.user_id}/{suffix}.jpg"
    await StorageService(ctx.s3).put(key, data, content_type=content_type)
    
    db = ctx.db_session
    db_user = await UserRepository(db).find(user.user_id)
    if db_user is None:
        raise AppError(404, "not_found", "User not found.")
        
    db_user.profile_image_url = key
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    signed = await StorageService(ctx.s3).signed_url(key)
    return AvatarUploadResponse(response=AvatarUploadResponseCore(profile_image_url=signed))
