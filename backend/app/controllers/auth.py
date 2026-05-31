from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.auth import (
    DeleteAccountRequest,
    MagicLinkRequest,
    MagicLinkResponse,
    MagicLinkResponseCore,
    VerifyRequest,
    VerifyResponse,
    VerifyResponseCore,
)
from app.services.main.auth import AuthService

api = APIRouter()


@api.post("/auth/magic-link", response_model=MagicLinkResponse, response_model_by_alias=True)
async def magic_link(
    body: MagicLinkRequest,
    ctx: Context = Depends(get_context),
) -> MagicLinkResponse:
    # dev_token is non-None only when no email provider is configured (SMTP_URL empty);
    # it serializes as `_mock_link_token` so the UI can simulate the link tap.
    resend_at, dev_token = await AuthService(ctx).request_magic_link(body.email)
    return MagicLinkResponse(
        response=MagicLinkResponseCore(
            sent=True, resend_available_at=resend_at, mock_link_token=dev_token
        )
    )


@api.post("/auth/verify", response_model=VerifyResponse)
async def verify(
    body: VerifyRequest,
    ctx: Context = Depends(get_context),
) -> VerifyResponse:
    token, expires_in, user = await AuthService(ctx).verify(body.token)
    return VerifyResponse(
        response=VerifyResponseCore(access_token=token, expires_in=expires_in, user=user)
    )


@api.post("/auth/logout")
async def logout(
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> Response:
    await AuthService(ctx).logout(user.user_id)
    return Response(status_code=204)


@api.delete("/account")
async def delete_account(
    body: DeleteAccountRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> Response:
    await AuthService(ctx).soft_delete_account(user.user_id, body.confirm_email)
    return Response(status_code=204)
