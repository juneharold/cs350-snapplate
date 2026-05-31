from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.media import MediaUploadResponse, MediaUploadResponseCore
from app.services.main.media import MediaService

api = APIRouter()


@api.post("/media/upload", response_model=MediaUploadResponse)
async def upload(
    files: list[UploadFile] = File(...),
    extract_exif: bool = Form(default=True),
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> MediaUploadResponse:
    payload = [
        (f.filename or "photo.jpg", f.content_type or "image/jpeg", await f.read())
        for f in files
    ]
    uploads = await MediaService(ctx).upload(user.user_id, payload, extract_exif)
    return MediaUploadResponse(response=MediaUploadResponseCore(uploads=uploads))
