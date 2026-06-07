from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.config.auth import UserContext, get_user_context
from app.config.http_errors import AppError
from app.config.lifespan import Context, get_context
from app.dto.user import AvatarUploadResponse, AvatarUploadResponseCore, MeResponse, UpdateMeRequest
from app.repositories.user import UserRepository
from app.services.document.image import ImageService
from app.services.main.media import MediaService
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
    """Upload a profile picture.

    Validates the *actual* image bytes (not just the client-supplied MIME),
    re-encodes through ImageService to strip EXIF and normalise orientation,
    then stores the S3 key on the user. Reuses MediaService's allowed-types
    and per-file size limit so the two upload paths can't drift apart.
    """
    content_type = file.content_type
    if not content_type:
        filename = (file.filename or "").lower()
        if filename.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif filename.endswith(".png"):
            content_type = "image/png"
        else:
            raise AppError(400, "unsupported_format", "Unsupported file format.")

    if content_type not in MediaService.ALLOWED:
        raise AppError(400, "unsupported_format", f"{content_type} not supported.")

    # Reject oversize before buffering the whole body when the multipart
    # parser reports a size; re-check after read as a backstop.
    if file.size is not None and file.size > MediaService.MAX_PER_FILE:
        raise AppError(400, "file_too_large", "Avatar file size exceeds 10MB limit.")

    data = await file.read()
    if len(data) > MediaService.MAX_PER_FILE:
        raise AppError(400, "file_too_large", "Avatar file size exceeds 10MB limit.")

    # A client can label arbitrary bytes as image/jpeg, so decode+re-encode
    # through PIL. Invalid bytes raise here and surface as a clean 400 instead
    # of being written to S3.
    try:
        processed = ImageService().process(data)
    except Exception as exc:
        raise AppError(400, "unsupported_format", "File is not a valid image.") from exc

    key = f"avatars/{user.user_id}/{make_id('av')}.jpg"
    await StorageService(ctx.s3).put(key, processed.original, content_type="image/jpeg")

    db = ctx.db_session
    db_user = await UserRepository(db).find(user.user_id)
    if db_user is None:
        raise AppError(404, "not_found", "User not found.")

    db_user.profile_image_url = key
    db.add(db_user)
    await db.commit()

    signed = await StorageService(ctx.s3).signed_url(key)
    return AvatarUploadResponse(response=AvatarUploadResponseCore(profile_image_url=signed))
