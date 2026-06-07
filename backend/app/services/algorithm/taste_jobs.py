from __future__ import annotations

from app.config.lifespan import Context, InternalContext
from app.config.logger import create_logger
from app.repositories.taste_job import TasteJobRepository
from app.services.main.taste import TasteService

logger = create_logger(__name__)


async def refresh_taste_for_user(
    internal: InternalContext,
    user_id: str,
    job_id: str,
) -> None:
    async with internal.db_sessionmaker() as db:
        ctx = Context(
            db_session=db,
            http_client=internal.http_client,
            s3=internal.s3,
            algorithm_service=internal.algorithm_service,
        )
        jobs = TasteJobRepository(db)
        try:
            await jobs.mark_running(job_id, user_id)
            await TasteService(ctx).recompute_and_store(user_id)
            await jobs.mark_done(job_id, user_id)
        except Exception as exc:
            await db.rollback()
            try:
                await jobs.mark_failed(job_id, user_id, str(exc))
            except Exception as mark_exc:
                logger.error(
                    f"taste refresh failed to mark job {job_id} failed for {user_id}: {mark_exc}",
                    exc_info=mark_exc,
                )
            logger.error(
                f"taste refresh job {job_id} failed for {user_id}: {exc}",
                exc_info=exc,
            )
            raise
