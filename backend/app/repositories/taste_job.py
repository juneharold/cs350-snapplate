from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.taste_job import ACTIVE_TASTE_JOB_STATES, TasteJobModel
from app.utils.time import utcnow


class TasteJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_for_user(self, user_id: str) -> tuple[TasteJobModel, bool]:
        try:
            return await self._get_or_create_for_user(user_id)
        except IntegrityError:
            await self.db.rollback()
            return await self._reuse_after_insert_conflict(user_id)
        except Exception:
            await self.db.rollback()
            raise

    async def find_for_user(self, job_id: str, user_id: str) -> TasteJobModel | None:
        return await self._find_job_for_user(job_id, user_id, lock=False)

    async def mark_running(self, job_id: str, user_id: str) -> TasteJobModel:
        job = await self._require_job_for_user(job_id, user_id)
        job.state = "running"
        job.started_at = utcnow()
        job.finished_at = None
        job.error = None
        await self._commit_and_refresh(job)
        return job

    async def mark_done(self, job_id: str, user_id: str) -> TasteJobModel:
        job = await self._require_job_for_user(job_id, user_id)
        now = utcnow()
        job.state = "done"
        if job.started_at is None:
            job.started_at = now
        job.finished_at = now
        job.error = None
        await self._commit_and_refresh(job)
        return job

    async def mark_failed(self, job_id: str, user_id: str, error: str) -> TasteJobModel:
        job = await self._require_job_for_user(job_id, user_id)
        now = utcnow()
        job.state = "failed"
        if job.started_at is None:
            job.started_at = now
        job.finished_at = now
        job.error = error
        await self._commit_and_refresh(job)
        return job

    async def _get_or_create_for_user(self, user_id: str) -> tuple[TasteJobModel, bool]:
        job = await self._find_active_user_job_for_update(user_id)
        if job is not None:
            await self.db.commit()
            return job, False
        job = TasteJobModel(user_id=user_id, state="queued")
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job, True

    async def _reuse_after_insert_conflict(
        self,
        user_id: str,
    ) -> tuple[TasteJobModel, bool]:
        try:
            job = await self._find_active_user_job_for_update(user_id)
            if job is None:
                raise RuntimeError(
                    f"taste job insert conflict without active row for user {user_id}"
                )
            await self.db.commit()
            return job, False
        except Exception:
            await self.db.rollback()
            raise

    async def _find_active_user_job_for_update(self, user_id: str) -> TasteJobModel | None:
        stmt = (
            select(TasteJobModel)
            .where(TasteJobModel.user_id == user_id)
            .where(TasteJobModel.state.in_(ACTIVE_TASTE_JOB_STATES))  # type: ignore[attr-defined]
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_job_for_user(
        self,
        job_id: str,
        user_id: str,
        *,
        lock: bool,
    ) -> TasteJobModel | None:
        stmt = select(TasteJobModel).where(
            TasteJobModel.id == job_id,
            TasteJobModel.user_id == user_id,
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _require_job_for_user(self, job_id: str, user_id: str) -> TasteJobModel:
        job = await self._find_job_for_user(job_id, user_id, lock=True)
        if job is None:
            raise ValueError(f"taste job {job_id} not found for user {user_id}")
        return job

    async def _commit_and_refresh(self, job: TasteJobModel) -> None:
        self.db.add(job)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(job)
