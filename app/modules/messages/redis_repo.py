import json
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis

from app.common.core import (
    RedisConfig,
    get_redis_config,
    init_redis_client,
)


class MessagesRedisRepository:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def cache_message(self, chat_sid: UUID, message_dict: dict):
        key = f"chat:{chat_sid}:history"
        score = datetime.fromisoformat(message_dict["created_at"]).timestamp()
        data = json.dumps(message_dict, default=str)

        async with self.redis.pipeline() as pipe:
            await pipe.zadd(key, {data: score})
            await pipe.zremrangebyrank(key, 0, -101)  # Храним 100 последних
            await pipe.execute()


async def get_redis_repo(
    redis_config: Annotated[RedisConfig, Depends(get_redis_config)],
):
    redis_client = init_redis_client(redis_config)
    return MessagesRedisRepository(redis_client)
