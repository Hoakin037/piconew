from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.client.s3_provider import (
    S3Connect,  # ← добавь импорт
)
from app.common import setup_logging
from app.common.core.s3_settings import get_s3_settings
from app.common.errors import BackendException
from app.database import db_manager

from .middleware_settings import (
    ExceptionMiddleware,
    backend_exception_handler,
    global_exception_handler,
    validation_exception_handler,
)
from .redis import get_redis_config, init_redis_client
from .router import router

logger = setup_logging(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_config = get_redis_config()
    redis_client = init_redis_client(redis_config)
    try:
        await redis_client.ping()
        app.state.redis_client = redis_client
        logger.info("Успешное подключение к Redis.")
    except ConnectionError as e:
        logger.critical(f"Ошибка подключения к Redis: {e}")
        raise RuntimeError("Не удалось подключиться к Redis при запуске.") from e

    await db_manager.database_init()
    logger.info("Успешное подключение к базе данных.")

    try:
        settings = get_s3_settings()
        s3_connect = S3Connect(settings=settings)  # ← Прямое создание
        await s3_connect.init_buckets()
        logger.info("S3 бакеты инициализированы (files, temp)")
    except Exception as e:
        logger.error(f" Ошибка инициализации S3 бакетов: {e}")

    yield

    await redis_client.close()
    await redis_client.connection_pool.disconnect()


def app_fabric() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        exception_handlers={
            BackendException: backend_exception_handler,
            RequestValidationError: validation_exception_handler,
            Exception: global_exception_handler,
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:5173",
            "http://192.168.0.109",
            "http://192.168.0.109:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.middleware("http")(ExceptionMiddleware())
    app.include_router(router)

    return app
