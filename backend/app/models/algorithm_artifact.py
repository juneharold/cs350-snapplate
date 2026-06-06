from __future__ import annotations

from datetime import datetime

from sqlmodel import JSON as SAJSON
from sqlmodel import BigInteger, Column, Field

from app.models.base import ForeignKeyField, SQLModelBase, TimestampField


class EntryProfileArtifactModel(SQLModelBase, table=True):
    __tablename__ = "entry_profile_artifacts"  # type: ignore[reportAssignmentType]

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    entry_id: str = ForeignKeyField("entries.id", ondelete="CASCADE")
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)


class UserProfileArtifactModel(SQLModelBase, table=True):
    __tablename__ = "user_profile_artifacts"  # type: ignore[reportAssignmentType]

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    source_entry_count: int = Field(nullable=False)
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)


class RestaurantProfileArtifactModel(SQLModelBase, table=True):
    __tablename__ = "restaurant_profile_artifacts"  # type: ignore[reportAssignmentType]

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    restaurant_id: str = ForeignKeyField("restaurants.id", ondelete="CASCADE")
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)
