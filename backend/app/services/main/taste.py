from __future__ import annotations

from sqlalchemy import desc, select

from app.config.lifespan import Context
from app.dto.auth import UpdateUserData
from app.models.taste_report import TasteReportModel
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.repositories.user import UserRepository
from app.services.algorithm import generate_taste_report
from app.services.algorithm.taste import build_taste_refresh_artifacts
from app.services.main.diary_inputs import DiaryInputService
from app.utils.time import utcnow

_MIN_ENTRIES = 10


class TasteService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.users = UserRepository(self.db)

    async def get_profile(self, user_id: str) -> dict:
        """Return the latest stored TasteProfileResponse payload, or compute it."""
        stmt = (
            select(TasteReportModel)
            .where(TasteReportModel.user_id == user_id)  # type: ignore[reportArgumentType]
            .order_by(desc(TasteReportModel.generated_at))  # type: ignore[reportArgumentType]
            .limit(1)
        )
        latest = (await self.db.execute(stmt)).scalars().first()
        if latest is not None:
            return latest.payload_json
        return await self._compute_payload(user_id)

    async def refresh(self, user_id: str) -> dict:
        return await self.recompute_and_store(user_id)

    async def recompute_and_store(self, user_id: str) -> dict:
        entries = await DiaryInputService(self.ctx).for_user(user_id)
        generated_at = utcnow()
        artifacts = build_taste_refresh_artifacts(
            user_id,
            entries,
            generated_at=generated_at,
            profile_provider=self.ctx.profile_provider,
            min_entries_required=_MIN_ENTRIES,
        )
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
                algorithm_version=artifacts.user_profile.algorithm_version,
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
        entries = await DiaryInputService(self.ctx).for_user(user_id)
        report = generate_taste_report(
            user_id,
            entries,
            profile_provider=self.ctx.profile_provider,
            min_entries_required=_MIN_ENTRIES,
        )
        return report.model_dump(mode="json")
