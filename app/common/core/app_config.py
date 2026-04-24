from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.common.errors import BackendException
from .router import router
from .redis import init_redis_client, get_redis_config
from app.database import db_manager
from .middleware_settings import (
    backend_exception_handler,
    global_exception_handler,
    validation_exception_handler,
    ExceptionMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_config = get_redis_config()
    redis_client = init_redis_client(redis_config)
    try:
        await redis_client.ping()
        app.state.redis_client = redis_client
        print("Успешное подключение к Redis.")
    except ConnectionError as e:
        print(f"Ошибка подключения к Redis: {e}")
        raise RuntimeError("Не удалось подключиться к Redis при запуске.") from e

    await db_manager.database_init()
    print("Успешное поддключение к базе данных.")

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
