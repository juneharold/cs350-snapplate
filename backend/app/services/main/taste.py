from __future__ import annotations

from sqlalchemy import desc, select

from app.config.lifespan import Context
from app.config.logger import create_logger
from app.dto.auth import UpdateUserData
from app.models.taste_report import TasteReportModel
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.repositories.user import UserRepository
from app.services.main.diary_inputs import DiaryInputService
from app.utils.time import utcnow

logger = create_logger(__name__)

_MIN_ENTRIES = 10


class TasteService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.users = UserRepository(self.db)
        self.algorithm = ctx.algorithm_service

    async def get_profile(self, user_id: str) -> dict:
        """Return the taste profile reflecting the user's *current* diary.

        Serve the latest stored report only while it still matches the live
        entry count; otherwise recompute on the fly. The previous behaviour
        returned the cached report unconditionally, so entries added or removed
        through any path other than draft finalisation (the only recompute
        trigger) stayed invisible until the next finalise.
        """
        latest = await self._latest_report(user_id)
        if latest is not None and latest.source_entry_count == await self._live_entry_count(user_id):
            return latest.payload_json
        # Stale (entries changed) or nothing stored → reflect the live diary.
        return await self._compute_payload(user_id)

    async def _latest_report(self, user_id: str) -> TasteReportModel | None:
        stmt = (
            select(TasteReportModel)
            .where(TasteReportModel.user_id == user_id)  # type: ignore[reportArgumentType]
            .order_by(desc(TasteReportModel.generated_at))  # type: ignore[reportArgumentType]
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _live_entry_count(self, user_id: str) -> int:
        """Count the entries that actually feed the report. Goes through the
        same `for_user` path the report is built from (so rows skipped for an
        unsupported category are excluded here too), but without image fetches,
        so `source_entry_count` and this value compare apples to apples.
        """
        return len(await DiaryInputService(self.ctx).for_user(user_id))

    async def refresh(self, user_id: str) -> dict:
        return await self.recompute_and_store(user_id)

    async def recompute_and_store(self, user_id: str) -> dict:
        entries = await DiaryInputService(self.ctx).for_user(
            user_id,
            include_image_references=True,
        )
        generated_at = utcnow()
        try:
            artifacts = self.algorithm.build_taste_refresh_artifacts(
                user_id,
                entries,
                generated_at=generated_at,
                min_entries_required=_MIN_ENTRIES,
            )
        except Exception:
            # A recompute failure (e.g. the OpenAI call) must not 500 the caller
            # or wipe the profile. Log it, then keep serving the genuinely-prior
            # stored report. Return its payload directly rather than calling
            # get_profile — get_profile would re-run this same compute on a stale
            # cache and re-raise. Fall through to the insufficient-data shape
            # only when there's no prior report at all.
            logger.exception("taste recompute failed for user %s", user_id)
            prior = await self._latest_report(user_id)
            if prior is not None:
                return prior.payload_json
            return await self._compute_payload(user_id)
        report = artifacts.report
        artifact_repo = AlgorithmArtifactRepository(self.db)

        payload = report.model_dump(mode="json")
        for profile in artifacts.entry_profiles:
            profile_payload = profile.model_dump(mode="json")
            await artifact_repo.add_entry_profile(
                entry_id=profile.entry_id,
                user_id=profile.user_id,
                payload_json=profile_payload,
                algorithm_version=profile_payload["algorithm_version"],
                generated_at=generated_at,
                commit=False,
            )
        if artifacts.user_profile is not None:
            user_profile_payload = artifacts.user_profile.model_dump(mode="json")
            await artifact_repo.add_user_profile(
                user_id=user_id,
                source_entry_count=artifacts.user_profile.source_entry_count,
                payload_json=user_profile_payload,
                long_term_embedding=user_profile_payload["long_term_embedding"],
                short_term_embedding=user_profile_payload["short_term_embedding"],
                algorithm_version=user_profile_payload["algorithm_version"],
                generated_at=generated_at,
                commit=False,
            )
        self.db.add(
            TasteReportModel(
                user_id=user_id,
                payload_json=payload,
                has_enough_data=bool(report.has_enough_data),
                source_entry_count=len(entries),
                algorithm_version=report.algorithm_version,
                generated_at=generated_at,
            )
        )
        await self.db.commit()

        # Update the denormalized taste_type cache when there's a real type label.
        if report.has_enough_data:
            label = payload.get("type", {}).get("label")
            if label:
                user = await self.users.find(user_id)
                if user is not None:
                    await self.users.update(user, UpdateUserData(taste_type=label))
        return payload

    async def _compute_payload(self, user_id: str) -> dict:
        entries = await DiaryInputService(self.ctx).for_user(
            user_id,
            include_image_references=True,
        )
        report = self.algorithm.generate_taste_report(
            user_id,
            entries,
            min_entries_required=_MIN_ENTRIES,
        )
        return report.model_dump(mode="json")
