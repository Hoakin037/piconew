from jwt import (
    encode,
    decode,
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError,
)
from fastapi import HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Literal

from app.core import JWTConfig, get_jwt_config


class JWTManager:
    def __init__(self, config: JWTConfig):
        self.config = config

    async def create_token(
        self, payload: dict, token_type: Literal["refresh", "access"]
    ):
        payload_copy = payload.copy()
        if token_type == "refresh":
            # для теста
            expires_delta = timedelta(hours=1)
            # expires_delta = timedelta(minutes=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            # expires_delta = timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MIN)
            expires_delta = timedelta(seconds=60)
        expire = datetime.now(timezone.utc) + expires_delta
        payload_copy.update(
            {
                "type": token_type,
                "exp": expire.timestamp(),  # Срок действия
                "iat": datetime.now(timezone.utc).timestamp(),  # Время выпуска
            }
        )
        return encode(
            payload_copy,
            self.config.JWT_SECRET_KEY,
            algorithm=self.config.JWT_ALGORITHM,
        )

    async def decode_token(self, token: str) -> int:
        """
        Returns user_id from token
        """
        try:
            payload = decode(
                token, self.config.JWT_SECRET_KEY, self.config.JWT_ALGORITHM
            )
            user_id = payload.get("sub")
            return int(user_id)
        except (ExpiredSignatureError, InvalidSignatureError, DecodeError):
            raise HTTPException(status_code=401, detail="Ошибка валидации jwt токена.")

    @property
    def get_refresh_token_ttl_seconds(self) -> int:
        return self._jwt_manager.config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def get_jwt_manager(config: JWTConfig = Depends(get_jwt_config)):
    return JWTManager(config)
