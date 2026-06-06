from __future__ import annotations

from app.dto.base import BaseRequest, BaseResponse, BaseResponseCore
from app.schemas.user import MeInfo


class UpdateMeRequest(BaseRequest):
    nickname: str | None = None


class AvatarUploadResponseCore(BaseResponseCore):
    profile_image_url: str


AvatarUploadResponse = BaseResponse[AvatarUploadResponseCore]


# /me returns the user fields flat (no nesting), matching types.ts MeResponse:
# response IS the MeInfo itself ({id, email, nickname, ...}), not a {me: ...} wrapper.
MeResponse = BaseResponse[MeInfo]
