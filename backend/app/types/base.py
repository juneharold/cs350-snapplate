from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeVar

from sqlalchemy import Column
from sqlalchemy import Enum as SQLEnum
from sqlmodel import Field

T = TypeVar("T", bound="BaseStrEnum")


class BaseStrEnum(StrEnum):
    """String enum with database integration."""

    @classmethod
    def db_field(
        cls: type[T], nullable: bool = False, default: T | None = None, **kwargs: Any
    ):
        return Field(
            sa_column=Column(
                SQLEnum(
                    cls,
                    native_enum=False,
                    values_callable=lambda e: [str(x.value) for x in e],
                ),
                nullable=nullable,
            ),
            default=default,
            **kwargs,
        )
