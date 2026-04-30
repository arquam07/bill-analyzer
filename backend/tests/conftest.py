from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import src.models  # noqa: F401  -- registers ORM tables on Base.metadata
from src.core.exceptions import OllamaUnavailable
from src.db.base import Base
from src.services.storage.local import LocalDiskBackend


class _NullVisionService:
    """Default stand-in: tests that exercise extraction must override the dep."""

    async def extract_bill(self, image_bytes: bytes) -> object:
        raise OllamaUnavailable("vision service not configured in tests")


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


@pytest.fixture
async def client(postgres_url: str, storage_root: Path) -> AsyncIterator[AsyncClient]:
    from src.main import app

    engine = create_async_engine(postgres_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if Base.metadata.tables:
            await conn.execute(
                text(
                    "TRUNCATE TABLE "
                    + ", ".join(Base.metadata.tables.keys())
                    + " RESTART IDENTITY CASCADE"
                )
            )

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.storage = LocalDiskBackend(storage_root)
    app.state.vision_service = _NullVisionService()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.fixture
async def auth(client: AsyncClient) -> dict[str, object]:
    r = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "passw0rd!", "username": "testuser", "name": "User"},
    )
    body = r.json()
    return {
        "headers": {"Authorization": f"Bearer {body['token']}"},
        "user_id": body["user"]["id"],
    }
