import asyncio

from google.cloud import storage

from src.services.storage.base import StorageBackend


class GcsBackend(StorageBackend):
    def __init__(self, bucket_name: str) -> None:
        self._client = storage.Client()
        self._bucket_name = bucket_name

    def _blob(self, key: str) -> storage.Blob:
        return self._client.bucket(self._bucket_name).blob(key)

    async def write(self, key: str, data: bytes, content_type: str) -> None:
        blob = self._blob(key)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)

    async def read(self, key: str) -> bytes:
        blob = self._blob(key)
        return bytes(await asyncio.to_thread(blob.download_as_bytes))

    async def delete(self, key: str) -> None:
        blob = self._blob(key)
        # Match LocalDiskBackend's missing_ok semantics.
        try:
            await asyncio.to_thread(blob.delete)
        except Exception:  # noqa: BLE001
            pass

    async def exists(self, key: str) -> bool:
        blob = self._blob(key)
        result = await asyncio.to_thread(blob.exists)
        return bool(result)
