from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager

from app.common.core import get_database_settings, DatabaseSettings
from .tables import Base


class DatabaseManager:
    def __init__(self, settings: DatabaseSettings):
        self._engine = None
        self._async_session_maker = None
        self._settings = settings

    async def database_init(self):
        if self._engine:
            return

        self._engine = create_async_engine(
            url=self._settings.get_database_url, pool_pre_ping=True, echo=False
        )

        self._async_session_maker = async_sessionmaker(
            bind=self._engine, expire_on_commit=False, class_=AsyncSession
        )

    async def close(self):
        if self._engine:
            await self._engine.dispose()
            self._engine = None

    @asynccontextmanager
    async def session_scope(self):
        if not self._async_session_maker:
            raise Exception("База данных не инициализирована.")

        async with self._async_session_maker() as session:
            try:
                yield session

            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()


db_manager = DatabaseManager(get_database_settings())


async def get_session():
    async with db_manager.session_scope() as session:
        yield session
