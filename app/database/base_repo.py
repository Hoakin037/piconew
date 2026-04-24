from typing import TypeVar, Generic, Sequence, Literal
from uuid import UUID
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption
from app.database.tables import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    async def create(self, session: AsyncSession, obj: ModelType) -> ModelType:
        session.add(obj)
        return obj

    async def get_by_sid(
        self,
        session: AsyncSession,
        model: type[ModelType],
        sid: UUID,
        custom_options: tuple[ExecutableOption, ...] = None,
    ) -> ModelType | None:
        query = select(model).where(model.sid == sid)
        if custom_options:
            query = query.options(*custom_options)

        result = await session.execute(query)
        return result.scalars().first()

    async def get_all(
        self,
        session: AsyncSession,
        model: type[ModelType],
            custom_options: tuple[ExecutableOption, ...] = None,
    ) -> Sequence[ModelType]:
        query = select(model)

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

    def _validate_sort_field(self, model: type[ModelType], field_name: str):
        if field_name not in model.__table__.columns:
            raise ValueError(
                f"Поле '{field_name}' не найдено в модели {model.__name__}."
            )
        return getattr(model, field_name)

    def _apply_sorts(
        self,
        query: Select,
        model: type[ModelType],
        sort_by: str | None = None,
        sort_direction: Literal["asc", "desc"] = "asc",
    ) -> Select:
        if sort_by:
            column = self._validate_sort_field(model, sort_by)
            query = query.order_by(
                column.desc() if sort_direction.lower() == "desc" else column.asc()
            )
        return query

    async def _apply_pagination(
        self, query: Select, session: AsyncSession, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[ModelType], int]:
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0

        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        items = result.scalars().all()
        return items, total
