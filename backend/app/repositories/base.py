from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import delete as sa_delete
from sqlmodel import func, select

from app.config.logger import create_logger
from app.models.base import SQLModelBase

ModelType = TypeVar("ModelType", bound=SQLModelBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

logger = create_logger(__name__)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    db: AsyncSession
    model: type[ModelType]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find(self, model_id: Any) -> ModelType | None:
        try:
            stmt = select(self.model).where(self.model.id == model_id)  # type: ignore[attr-defined]
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"find {self.model.__name__} {model_id}: {e}", exc_info=e)
            await self.db.rollback()
            raise

    async def find_by(self, **kwargs: Any) -> ModelType | None:
        try:
            filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
            result = await self.db.execute(select(self.model).where(*filters))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"find_by {self.model.__name__} {kwargs}: {e}", exc_info=e)
            await self.db.rollback()
            raise

    async def find_all(
        self,
        where: dict[str, Any] | None = None,
        order_by: ColumnElement | None = None,
    ) -> Sequence[ModelType]:
        try:
            filters = [getattr(self.model, k) == v for k, v in (where or {}).items()]
            stmt = select(self.model).where(*filters)
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"find_all {self.model.__name__} {where}: {e}", exc_info=e)
            await self.db.rollback()
            raise

    async def total_count(self, where: dict[str, Any] | None = None) -> int:
        try:
            filters = [getattr(self.model, k) == v for k, v in (where or {}).items()]
            stmt = select(func.count()).select_from(self.model).where(*filters)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"total_count {self.model.__name__} {where}: {e}", exc_info=e)
            await self.db.rollback()
            raise

    async def create(self, data: CreateSchemaType) -> ModelType:
        instance = self.model(**data.model_dump(exclude_unset=True))
        self.db.add(instance)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, data: UpdateSchemaType) -> ModelType:
        for key, value in data.model_dump(exclude_unset=True).items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.add(instance)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(instance)
        return instance

    async def delete(self, model_id: Any) -> bool:
        try:
            await self.db.execute(
                sa_delete(self.model).where(self.model.id == model_id)  # type: ignore[attr-defined]
            )
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            raise

    async def batch_upsert(
        self,
        items: list[CreateSchemaType],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> list[ModelType]:
        """PostgreSQL INSERT ... ON CONFLICT DO UPDATE (oscre pattern).

        The Kakao restaurant cache relies on this: upsert dedupe on `kakao_id`.
        """
        from sqlalchemy.dialects.postgresql import insert

        if not items:
            return []
        try:
            values = [item.model_dump() for item in items]
            stmt = insert(self.model).values(values)
            if update_columns is None:
                cols = [c.name for c in self.model.__table__.columns]  # type: ignore[attr-defined]
                update_columns = [c for c in cols if c not in conflict_columns and c != "id"]
            set_ = {c: getattr(stmt.excluded, c) for c in update_columns}
            stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_=set_).returning(
                self.model
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"batch_upsert {self.model.__name__}: {e}", exc_info=e)
            await self.db.rollback()
            raise
