# pyright: reportArgumentType=false, reportAssignmentType=false
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from app.models.base import OptionalTimestampField, SQLModelBase


class MagicLinkModel(SQLModelBase, table=True):
    __tablename__ = "magic_links"

    # PK is the token hash (sha256 hex), not the raw token.
    token: str = Field(primary_key=True)
    email: str = Field(index=True, nullable=False)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    consumed_at: datetime | None = OptionalTimestampField()
