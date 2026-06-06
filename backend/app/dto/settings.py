from __future__ import annotations

from app.dto.base import BaseRequest, BaseResponse
from app.schemas.settings import SettingsInfo
from app.types.settings import AppearancePref


# ── Request DTOs ──────────────────────────────────────────────────────────────
class NotificationPatch(BaseRequest):
    meal_reminders: bool | None = None
    taste_analysis_complete: bool | None = None
    weekly_picks: bool | None = None


class UpdateSettingsRequest(BaseRequest):
    notifications: NotificationPatch | None = None
    appearance: AppearancePref | None = None

    def to_data(self) -> UpdateSettingsData:
        """Convert this nested API DTO into the flat domain update schema.

        Lives on the DTO (not the service) so the request shape never crosses
        into the service layer — only its flattened domain form does. Carries
        only the fields the client actually sent (exclude_unset semantics).
        """
        fields: dict[str, object] = {}
        if self.notifications is not None:
            n = self.notifications
            if n.meal_reminders is not None:
                fields["notif_meal_reminders"] = n.meal_reminders
            if n.taste_analysis_complete is not None:
                fields["notif_taste_analysis_complete"] = n.taste_analysis_complete
            if n.weekly_picks is not None:
                fields["notif_weekly_picks"] = n.weekly_picks
        if self.appearance is not None:
            fields["appearance"] = self.appearance
        return UpdateSettingsData(**fields)


# ── Repository data schemas (flat, map 1:1 to columns) ────────────────────────
class CreateSettingsData(BaseRequest):
    user_id: str


class UpdateSettingsData(BaseRequest):
    notif_meal_reminders: bool | None = None
    notif_taste_analysis_complete: bool | None = None
    notif_weekly_picks: bool | None = None
    appearance: AppearancePref | None = None


# ── Response aliases ──────────────────────────────────────────────────────────
GetSettingsResponse = BaseResponse[SettingsInfo]
UpdateSettingsResponse = BaseResponse[SettingsInfo]
