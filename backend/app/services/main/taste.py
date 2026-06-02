from __future__ import annotations

from algorithm import generate_taste_report
from algorithm.version import ALGORITHM_VERSION
from sqlalchemy import desc, select

from app.config.lifespan import Context
from app.dto.auth import UpdateUserData
from app.models.taste_report import TasteReportModel
from app.repositories.user import UserRepository
from app.services.main.diary_inputs import DiaryInputService

_MIN_ENTRIES = 10


class TasteService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.users = UserRepository(self.db)

    async def get_profile(self, user_id: str) -> dict:
        """Return the latest stored TasteProfileResponse payload (dict). If none
        stored yet, compute the insufficient-data shape on the fly."""
        stmt = (
            select(TasteReportModel)
            .where(TasteReportModel.user_id == user_id)
            .order_by(desc(TasteReportModel.generated_at))
            .limit(1)
        )
        latest = (await self.db.execute(stmt)).scalars().first()
        if latest is not None:
            return latest.payload_json
        # Nothing stored → compute current shape (likely insufficient).
        return await self._compute_payload(user_id)

    async def refresh(self, user_id: str) -> dict:
        """Recompute inline + persist, return the fresh payload."""
        return await self.recompute_and_store(user_id)

    async def recompute_and_store(self, user_id: str) -> dict:
        entries = await DiaryInputService(self.ctx).for_user(user_id)
        try:
            report = generate_taste_report(
                user_id, entries, min_entries_required=_MIN_ENTRIES
            )
        except Exception:
            # Preserve prior report on failure — just don't insert.
            return await self.get_profile(user_id)

        payload = report.model_dump(mode="json")
        self.db.add(
            TasteReportModel(
                user_id=user_id,
                payload_json=payload,
                has_enough_data=bool(report.has_enough_data),
                source_entry_count=len(entries),
                algorithm_version=ALGORITHM_VERSION,
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
        report = generate_taste_report(user_id, entries, min_entries_required=_MIN_ENTRIES)
        return report.model_dump(mode="json")
