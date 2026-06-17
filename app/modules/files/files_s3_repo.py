from typing import Annotated

from fastapi import Depends

from app.client import S3SessionProvider, get_s3_session_provider


class FilesS3Repository:
    def __init__(self, s3_session_provider: S3SessionProvider):
        self.s3_session_provider = s3_session_provider
        self.bucket_name = "files"
        self.temp_bucket_name = "temp"

    async def put_temp_object(self, data: bytes, url: str) -> str:
        async with self.s3_session_provider.get_session() as s3_client:
            await s3_client.put_object(Body=data, Bucket=self.temp_bucket_name, Key=url)

        return f"{self.temp_bucket_name}/{url}"

    async def put_object(self, data: bytes, url: str) -> str:
        async with self.s3_session_provider.get_session() as s3_client:
            await s3_client.put_object(Body=data, Bucket=self.bucket_name, Key=url)

        return f"{self.bucket_name}/{url}"

    async def get_object(self, url: str) -> bytes:
        file_url = url.split("/", 1)[1]
        async with self.s3_session_provider.get_session() as s3_client:
            return await s3_client.get_object(Bucket=self.bucket_name, Key=file_url)

    async def delete_object(self, url: str) -> None:
        async with self.s3_session_provider.get_session() as s3_client:
            await s3_client.delete_object(Bucket=self.bucket_name, Key=url)

    async def copy_object(self, source_url: str, new_url: str) -> str:
        file_url = source_url.split("/", 1)[1]
        async with self.s3_session_provider.get_session() as s3_client:
            await s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={
                    "Bucket": self.temp_bucket_name,
                    "Key": file_url,
                },
                Key=new_url,
            )

        return f"{self.bucket_name}/{new_url}"


async def get_files_s3_repo(
    s3_session_provider: Annotated[S3SessionProvider, Depends(get_s3_session_provider)],
):
    return FilesS3Repository(s3_session_provider)
