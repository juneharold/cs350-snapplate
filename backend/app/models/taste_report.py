from __future__ import annotations

from datetime import datetime

from sqlmodel import JSON as SAJSON
from sqlmodel import BigInteger, Column, Field

from app.models.base import ForeignKeyField, SQLModelBase, TimestampField


class TasteReportModel(SQLModelBase, table=True):
    __tablename__ = "taste_reports"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    has_enough_data: bool = Field(nullable=False)
    source_entry_count: int = Field(default=0, nullable=False)
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)
