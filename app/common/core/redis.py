from uuid import UUID

from redis import RedisError
from redis.asyncio import Redis
from fastapi import Request
import json
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class RedisConfig(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_DECODE_RESPONSES: bool
    REDIS_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        arbitrary_types_allowed=True,
    )


@lru_cache
def get_redis_config():
    return RedisConfig()


class RedisManager:
    def __init__(self, client: Redis):
        self.client = client

    def _get_token_key(self, token: str) -> str:
        return f"refresh:{token}"

    def _get_user_sessions_key(self, user_sid: str) -> str:
        return f"user_sessions:{user_sid}"

    async def create_session(self, user_sid: str, token: str, ttl_seconds: int) -> bool:

        token_key = self._get_token_key(token)
        user_sessions_key = self._get_user_sessions_key(user_sid)

        session_data = json.dumps(
            {
                "user_sid": user_sid,
                # **device_info пока что без
            }
        )

        try:
            async with self.client.pipeline(transaction=True) as pipe:
                await pipe.setex(token_key, ttl_seconds, session_data)
                await pipe.sadd(user_sessions_key, token)
                await pipe.expire(user_sessions_key, ttl_seconds + 60)
                await pipe.execute()
            return True
        except RedisError as e:
            raise Exception(f"{e}")

    async def get_session(self, token: str) -> dict:
        token_key = self._get_token_key(token)
        try:
            user_data = await self.client.get(token_key)
            if not user_data:
                return None
            return json.loads(user_data)
        except RedisError as e:
            raise Exception(f"{e}")
        except json.JSONDecodeError as e:
            raise Exception(f"{e}")

    async def revoke_session(self, token: str) -> bool:
        token_key = self._get_token_key(token)
        try:
            data = await self.client.get(token_key)
            if data:
                session_data = json.loads(data)
                user_id = session_data.get("user_id")

                async with self.client.pipeline(transaction=True) as pipe:
                    await pipe.delete(token_key)
                    if user_id:
                        await pipe.srem(self._get_user_sessions_key(user_id), token)
                    await pipe.execute()
            else:
                await self.client.delete(token_key)

            return True
        except Exception:
            return False

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        user_sessions_key = self._get_user_sessions_key(user_id)
        try:
            tokens = await self.client.smembers(user_sessions_key)
            if not tokens:
                return 0

            async with self.client.pipeline(transaction=True) as pipe:
                for token in tokens:
                    await pipe.delete(self._get_token_key(token))
                await pipe.delete(user_sessions_key)
                await pipe.execute()

            return len(tokens)
        except RedisError as e:
            raise Exception(f"{e}")

    def close(self):
        self.client.close()


def init_redis_client(config: RedisConfig) -> Redis:
    redis_client = Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD,
        decode_responses=config.REDIS_DECODE_RESPONSES,
        socket_connect_timeout=5,
        socket_timeout=5,
        max_connections=50,
    )
    return redis_client


async def get_redis_manager(request: Request) -> RedisManager:
    redis_client: Redis = request.app.state.redis_client
    return RedisManager(redis_client)
