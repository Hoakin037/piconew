from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import (
    DecodeError,
    ExpiredSignatureError,
    InvalidSignatureError,
    decode,
    encode,
)

from app.common.core.jwt.jwt_config import JWTConfig, get_jwt_config

security = HTTPBearer()


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
            expires_delta = timedelta(seconds=3600)
        expire = datetime.now(UTC) + expires_delta
        payload_copy.update(
            {
                "type": token_type,
                "exp": expire.timestamp(),  # Срок действия
                "iat": datetime.now(UTC).timestamp(),  # Время выпуска
            }
        )
        return encode(
            payload_copy,
            self.config.JWT_SECRET_KEY,
            algorithm=self.config.JWT_ALGORITHM,
        )

    async def decode_token(self, token: str) -> UUID:
        """
        Returns user_sid from token
        """
        try:
            payload = decode(
                token, self.config.JWT_SECRET_KEY, self.config.JWT_ALGORITHM
            )
            user_sid = payload.get("sub")
            return user_sid
        except (ExpiredSignatureError, InvalidSignatureError, DecodeError):
            raise HTTPException(status_code=401, detail="Ошибка валидации jwt токена.")

    @property
    def get_refresh_token_ttl_seconds(self) -> int:
        return self.config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def get_jwt_manager(config: Annotated[JWTConfig, Depends(get_jwt_config)]):
    return JWTManager(config)


async def get_current_user(
    jwt_manager: Annotated[JWTManager, Depends(get_jwt_manager)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UUID:
    if credentials:
        access_token = credentials.credentials
        user_sid = await jwt_manager.decode_token(access_token)

        return user_sid

    raise HTTPException(status_code=401, detail="Токен некорректный или отсутсвует")
