from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def write(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def read(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...
