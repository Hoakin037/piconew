import socketio

from app.common.core.redis import get_redis_config

redis_config = get_redis_config()
manager = socketio.AsyncRedisManager(
    f"redis://{redis_config.REDIS_PASSWORD}@{redis_config.REDIS_HOST}:{redis_config.REDIS_PORT}/{redis_config.REDIS_DB}"
)

sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins="*", client_manager=manager
)


def get_sio_server() -> socketio.AsyncServer:
    return sio
