import logging
from abc import ABC, abstractmethod
from pathlib import Path

from call_analyzer.config import settings

logger = logging.getLogger(__name__)


class StorageClient(ABC):
    @abstractmethod
    async def upload(self, data: bytes, key: str) -> str:
        """Upload data and return the storage path/URL."""
        ...

    @abstractmethod
    async def fetch(self, key: str) -> bytes:
        """Fetch data by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data by key."""
        ...


class LocalStorageClient(StorageClient):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, data: bytes, key: str) -> str:
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def fetch(self, key: str) -> bytes:
        path = self.base_dir / key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self.base_dir / key
        if path.exists():
            path.unlink()


class S3StorageClient(StorageClient):
    def __init__(self, bucket: str, prefix: str, region: str, endpoint_url: str = ""):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self.endpoint_url = endpoint_url or None

    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}" if self.prefix else key

    async def upload(self, data: bytes, key: str) -> str:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "s3", region_name=self.region, endpoint_url=self.endpoint_url
        ) as s3:
            full_key = self._key(key)
            await s3.put_object(Bucket=self.bucket, Key=full_key, Body=data)
            return f"s3://{self.bucket}/{full_key}"

    async def fetch(self, key: str) -> bytes:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "s3", region_name=self.region, endpoint_url=self.endpoint_url
        ) as s3:
            resp = await s3.get_object(Bucket=self.bucket, Key=self._key(key))
            return await resp["Body"].read()

    async def delete(self, key: str) -> None:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "s3", region_name=self.region, endpoint_url=self.endpoint_url
        ) as s3:
            await s3.delete_object(Bucket=self.bucket, Key=self._key(key))


def get_storage_client() -> StorageClient:
    if settings.storage_type == "s3":
        return S3StorageClient(
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
        )
    return LocalStorageClient(settings.upload_dir)
