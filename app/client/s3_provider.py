from contextlib import AbstractAsyncContextManager, asynccontextmanager

import aioboto3
from aiobotocore.client import AioBaseClient
from botocore.client import Config

from app.common.core.s3_settings import S3Settings


class S3Connect:
    def __init__(self, settings: S3Settings):
        self._settings = settings

    def _get_client(self) -> AioBaseClient:
        return aioboto3.Session().client(
            service_name="s3",
            endpoint_url=self._settings.S3_ENDPOINT_URL,
            aws_access_key_id=self._settings.S3_ACCESS_KEY,
            aws_secret_access_key=self._settings.S3_SECRET_KEY,
            config=Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    async def get_connect(self) -> AbstractAsyncContextManager:
        return self._get_client()


class S3SessionProvider:
    def __init__(self, s3_client: S3Connect):
        self._s3_client = s3_client

    @asynccontextmanager
    async def get_session(self):
        cm = await self._s3_client.get_connect()
        async with cm as client:
            yield client
