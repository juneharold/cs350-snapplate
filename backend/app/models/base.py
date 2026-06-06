from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from sqlalchemy import DateTime, text
from sqlalchemy import ForeignKey as SAForeignKey
from sqlmodel import Field, SQLModel

from app.utils.time import utcnow

_TZ = cast(type[Any], DateTime(timezone=True))


def TimestampField(*, server_default: bool = False, onupdate: bool = False, **kwargs: Any):
    """A non-null timestamptz column defaulting to utcnow()."""
    col_kwargs: dict[str, Any] = {}
    if server_default:
        col_kwargs["server_default"] = text("current_timestamp(0)")
    if onupdate:
        col_kwargs["onupdate"] = text("current_timestamp(0)")
    if col_kwargs:
        kwargs["sa_column_kwargs"] = col_kwargs
    return Field(default_factory=utcnow, sa_type=_TZ, **kwargs)


def OptionalTimestampField(**kwargs: Any):
    """A nullable timestamptz column (default None)."""
    return Field(default=None, sa_type=_TZ, **kwargs)


class SQLModelBase(SQLModel):
    """created_at / updated_at, timezone-aware, server-defaulted."""

    created_at: datetime = TimestampField(server_default=True)
    updated_at: datetime = TimestampField(server_default=True, onupdate=True)


def ForeignKeyField(
    foreign_key: str,
    *,
    ondelete: Literal["CASCADE", "SET NULL", "RESTRICT", "NO ACTION"] | None = None,
    nullable: bool = False,
    index: bool = True,
    **kwargs,
):
    """FK with explicit ondelete semantics (oscre pattern)."""
    if ondelete:
        return Field(
            sa_column_args=[SAForeignKey(foreign_key, ondelete=ondelete)],
            nullable=nullable,
            index=index,
            **kwargs,
        )
    return Field(foreign_key=foreign_key, nullable=nullable, index=index, **kwargs)
