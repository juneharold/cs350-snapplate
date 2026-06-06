from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.config.auth import UserContext, get_user_context
from app.config.http_errors import NotFoundError
from app.config.lifespan import Context, get_context
from app.dto.taste import (
    TasteJobResponse,
    TasteJobResponseCore,
    TasteProfileResponse,
    TasteProfileResponseCore,
    TasteRefreshResponse,
    TasteRefreshResponseCore,
)
from app.models.taste_job import taste_job_state
from app.repositories.taste_job import TasteJobRepository
from app.services.algorithm.taste_jobs import refresh_taste_for_user
from app.services.main.taste import TasteService

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
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> TasteRefreshResponse:
    job, newly_queued = await TasteJobRepository(ctx.db_session).get_or_create_for_user(
        user.user_id
    )
    if newly_queued:
        background_tasks.add_task(
            refresh_taste_for_user,
            request.state.context,
            user.user_id,
            job.id,
        )
    return TasteRefreshResponse(
        response=TasteRefreshResponseCore(job_id=job.id, status=taste_job_state(job.state)),
    )


@api.get("/taste/jobs/{job_id}", response_model=TasteJobResponse)
async def get_refresh_job(
    job_id: str,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> TasteJobResponse:
    job = await TasteJobRepository(ctx.db_session).find_for_user(job_id, user.user_id)
    if job is None:
        raise NotFoundError("Taste job not found")
    return TasteJobResponse(
        response=TasteJobResponseCore(
            job_id=job.id,
            status=taste_job_state(job.state),
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=job.error,
        ),
    )
