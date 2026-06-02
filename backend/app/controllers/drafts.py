from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.draft import (
    CreateDraftRequest,
    DraftDetailResponse,
    DraftListResponse,
    DraftListResponseCore,
    FinalizeDraftRequest,
    FinalizeDraftResponse,
    FinalizeDraftResponseCore,
    UpdateDraftRequest,
)
from app.services.main.draft import DraftService

api = APIRouter()


@api.post("/drafts", response_model=DraftDetailResponse, status_code=201)
async def create_draft(
    body: CreateDraftRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> DraftDetailResponse:
    draft = await DraftService(ctx).create(
        user.user_id,
        body.media_ids,
        body.cover_media_id,
        body.captured_at,
        body.lat,
        body.lng,
        body.restaurant_id,
        body.restaurant_suggested,
    )
    return DraftDetailResponse(response=draft)


@api.get("/drafts", response_model=DraftListResponse)
async def list_drafts(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, le=50),
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> DraftListResponse:
    items, total = await DraftService(ctx).list(user.user_id, status, limit)
    return DraftListResponse(
        response=DraftListResponseCore(items=items, next_cursor=None, total=total)
    )


@api.get("/drafts/{draft_id}", response_model=DraftDetailResponse)
async def get_draft(
    draft_id: str,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> DraftDetailResponse:
    draft = await DraftService(ctx).get(user.user_id, draft_id)
    return DraftDetailResponse(response=draft)


@api.patch("/drafts/{draft_id}", response_model=DraftDetailResponse)
async def update_draft(
    draft_id: str,
    body: UpdateDraftRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> DraftDetailResponse:
    draft = await DraftService(ctx).update(
        user.user_id, draft_id, body.restaurant_id, body.captured_at, body.cover_media_id
    )
    return DraftDetailResponse(response=draft)


@api.post("/drafts/{draft_id}/finalize", response_model=FinalizeDraftResponse, status_code=201)
async def finalize_draft(
    draft_id: str,
    body: FinalizeDraftRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> FinalizeDraftResponse:
    entry_id = await DraftService(ctx).finalize(
        user.user_id, draft_id, body.note, body.rating, body.restaurant_id
    )
    return FinalizeDraftResponse(
        response=FinalizeDraftResponseCore(entry_id=entry_id, draft_id=draft_id)
    )


@api.delete("/drafts/{draft_id}")
async def delete_draft(
    draft_id: str,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> Response:
    await DraftService(ctx).delete(user.user_id, draft_id)
    return Response(status_code=204)
