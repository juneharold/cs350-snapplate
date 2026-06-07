from __future__ import annotations

from app.models.settings import SettingsModel
from app.schemas.base import BaseSchema
from app.types.settings import AppearancePref


class NotificationInfo(BaseSchema):
    meal_reminders: bool
    taste_analysis_complete: bool
    weekly_picks: bool


class SettingsInfo(BaseSchema):
    notifications: NotificationInfo
    appearance: AppearancePref

    @classmethod
    def from_model(cls, m: SettingsModel) -> SettingsInfo:
        return cls(
            notifications=NotificationInfo(
                meal_reminders=m.notif_meal_reminders,
                taste_analysis_complete=m.notif_taste_analysis_complete,
                weekly_picks=m.notif_weekly_picks,
            ),
            appearance=m.appearance,
        )
