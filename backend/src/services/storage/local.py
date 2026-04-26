import asyncio
from pathlib import Path, PurePosixPath

from src.services.storage.base import StorageBackend


class LocalDiskBackend(StorageBackend):
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        pure = PurePosixPath(key)
        if pure.is_absolute() or any(part == ".." for part in pure.parts):
            raise ValueError(f"invalid storage key: {key}")
        path = (self._root / Path(*pure.parts)).resolve()
        if self._root not in path.parents and path != self._root:
            raise ValueError(f"resolved path escapes root: {key}")
        return path

    async def write(self, key: str, data: bytes, content_type: str) -> None:
        path = self._full_path(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)

    async def read(self, key: str) -> bytes:
        path = self._full_path(key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    async def exists(self, key: str) -> bool:
        path = self._full_path(key)
        return await asyncio.to_thread(path.exists)
