from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.entry import (
    EntryDetailResponse,
    EntryListResponse,
    EntryListResponseCore,
    UpdateEntryRequest,
)
from app.services.main.entry import EntryService

api = APIRouter()


@api.get("/entries", response_model=EntryListResponse)
async def list_entries(
    sort: str = Query(default="recency"),
    q: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, le=50),
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> EntryListResponse:
    items, stats = await EntryService(ctx).list(
        user.user_id, sort, q, date_from, date_to, limit
    )
    return EntryListResponse(
        response=EntryListResponseCore(
            items=items, next_cursor=None, has_more=False, total=stats.entries_total, stats=stats
        )
    )


@api.get("/entries/{entry_id}", response_model=EntryDetailResponse)
async def get_entry(
    entry_id: str,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> EntryDetailResponse:
    entry = await EntryService(ctx).get(user.user_id, entry_id)
    return EntryDetailResponse(response=entry)


@api.patch("/entries/{entry_id}", response_model=EntryDetailResponse)
async def update_entry(
    entry_id: str,
    body: UpdateEntryRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> EntryDetailResponse:
    entry = await EntryService(ctx).update(user.user_id, entry_id, body.rating, body.note)
    return EntryDetailResponse(response=entry)


@api.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> Response:
    await EntryService(ctx).delete(user.user_id, entry_id)
    return Response(status_code=204)
