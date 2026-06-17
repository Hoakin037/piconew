from collections.abc import Sequence
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from app.database.tables import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def create(self, session: AsyncSession, obj: ModelType) -> ModelType:
        session.add(obj)
        return obj

    async def get_by_sid(
        self,
        session: AsyncSession,
        sid: UUID,
        custom_options: tuple[ExecutableOption, ...] = None,
    ) -> ModelType | None:
        query = select(self.model).where(self.model.sid == sid)
        if custom_options:
            query = query.options(*custom_options)

        await session.flush()
        result = await session.execute(query)
        return result.scalars().first()

    async def get_all(
        self,
        session: AsyncSession,
        custom_options: tuple[ExecutableOption, ...] = None,
    ) -> Sequence[ModelType]:
        query = select(self.model)
        if custom_options:
            query = query.options(*custom_options)

        result = await session.execute(query)
        return result.scalars().all()

    async def update(
        self, session: AsyncSession, obj: ModelType, update_data: dict
    ) -> ModelType:
        for key, value in update_data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await session.flush()
        return obj

    async def delete(self, session: AsyncSession, obj: ModelType) -> None:
        await session.delete(obj)
        await session.flush()

    def _apply_options(
        self, query: Select, options: tuple[ExecutableOption, ...] | None = None
    ) -> Select:
        return query.options(*options) if options else query

    async def _apply_pagination(
        self, query: Select, session: AsyncSession, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[ModelType], int]:
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0

        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        items = result.scalars().all()
        return items, total
