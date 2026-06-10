import json
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Annotated

import aioboto3
from aiobotocore.client import AioBaseClient
from botocore.client import Config
from fastapi import Depends

from app.common.core.s3_settings import S3Settings, get_s3_settings


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
                signature_version="s3v4",
            ),
            region_name="us-east-1",
        )

    async def init_buckets(self):
        async with self._get_client() as client:
            await self._create_bucket(client, self._settings.S3_BUCKET_NAME)
            await self._make_bucket_public(client, self._settings.S3_BUCKET_NAME)

            await self._create_bucket(client, "temp")
            await self._make_bucket_public(client, "temp")
            await self._set_temp_lifecycle(client, "temp")

    async def _create_bucket(self, client, bucket_name: str):
        try:
            await client.create_bucket(Bucket=bucket_name)

        except Exception:
            raise

    async def _make_bucket_public(self, client, bucket_name: str):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                }
            ],
        }

        try:
            await client.put_bucket_policy(
                Bucket=bucket_name, Policy=json.dumps(policy)
            )
        except Exception:
            raise

    async def _set_temp_lifecycle(self, client, bucket_name: str):
        lifecycle = {
            "Rules": [
                {
                    "ID": "ExpireTempFiles",
                    "Status": "Enabled",
                    "Filter": {"Prefix": ""},
                    "Expiration": {"Days": 1},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                }
            ]
        }

        try:
            await client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name, LifecycleConfiguration=lifecycle
            )
        except Exception:
            raise

    async def get_connect(self) -> AbstractAsyncContextManager:
        return self._get_client()


async def get_s3_client(
    settings: Annotated[S3Settings, Depends(get_s3_settings)],
) -> S3Connect:
    return S3Connect(settings=settings)


class S3SessionProvider:
    def __init__(self, s3_client: S3Connect):
        self._s3_client = s3_client

    @asynccontextmanager
    async def get_session(self):
        cm = await self._s3_client.get_connect()
        async with cm as client:
            yield client


async def get_s3_session_provider(
    s3_client: Annotated[S3Connect, Depends(get_s3_client)],
) -> S3SessionProvider:
    return S3SessionProvider(s3_client=s3_client)
