from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import UniqueConstraint
from sqlmodel import JSON as SAJSON
from sqlmodel import BigInteger, Column, Field

from app.config.algorithm import EMBEDDING_DIMENSIONS
from app.models.base import ForeignKeyField, SQLModelBase, TimestampField


class EntryProfileArtifactModel(SQLModelBase, table=True):
    __tablename__ = "entry_profile_artifacts"  # type: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("entry_id", name="uq_entry_profile_artifacts_entry_id"),)

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    entry_id: str = ForeignKeyField("entries.id", ondelete="CASCADE", index=False)
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)


class UserProfileArtifactModel(SQLModelBase, table=True):
    __tablename__ = "user_profile_artifacts"  # type: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_profile_artifacts_user_id"),)

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE", index=False)
    source_entry_count: int = Field(nullable=False)
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    long_term_embedding: Any = Field(
        sa_type=VECTOR(EMBEDDING_DIMENSIONS),  # type: ignore[reportArgumentType]
        nullable=False,
    )
    short_term_embedding: Any = Field(
        sa_type=VECTOR(EMBEDDING_DIMENSIONS),  # type: ignore[reportArgumentType]
        nullable=False,
    )
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)


class RestaurantProfileArtifactModel(SQLModelBase, table=True):
    __tablename__ = "restaurant_profile_artifacts"  # type: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("restaurant_id", name="uq_restaurant_profile_artifacts_restaurant_id"),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    restaurant_id: str = ForeignKeyField("restaurants.id", ondelete="CASCADE", index=False)
    payload_json: dict = Field(sa_column=Column(SAJSON, nullable=False))
    embedding: Any = Field(
        sa_type=VECTOR(EMBEDDING_DIMENSIONS),  # type: ignore[reportArgumentType]
        nullable=False,
    )
    algorithm_version: str = Field(nullable=False)
    generated_at: datetime = TimestampField(index=True)
