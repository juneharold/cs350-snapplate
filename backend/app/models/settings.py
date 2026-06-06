from __future__ import annotations

from sqlmodel import Field

from app.models.base import ForeignKeyField, SQLModelBase
from app.types.settings import AppearancePref


class SettingsModel(SQLModelBase, table=True):
    __tablename__ = "settings"

    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE", primary_key=True)
    notif_meal_reminders: bool = Field(default=True, nullable=False)
    notif_taste_analysis_complete: bool = Field(default=True, nullable=False)
    notif_weekly_picks: bool = Field(default=False, nullable=False)
    appearance: AppearancePref = AppearancePref.db_field(default=AppearancePref.LIGHT)
