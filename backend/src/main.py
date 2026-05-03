from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.api.auth import router as auth_router
from src.api.bills import router as bills_router
from src.api.friends import router as friends_router
from src.api.health import router as health_router
from src.api.insights import router as insights_router
from src.api.me import router as me_router
from src.api.split_requests import router as split_requests_router
from src.api.splits import router as splits_router
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.db.session import make_engine, make_sessionmaker
from src.services.storage.base import StorageBackend
from src.services.storage.gcs import GcsBackend
from src.services.storage.local import LocalDiskBackend
from src.services.vision_service import VisionService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    storage: StorageBackend = (
        GcsBackend(settings.gcs_bucket)
        if settings.gcs_bucket
        else LocalDiskBackend(Path(settings.storage_root))
    )
    app.state.storage = storage
    app.state.vision_service = VisionService(
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        api_key=settings.ollama_api_key,
    )
    try:
        yield
    finally:
        await app.state.vision_service.aclose()
        await engine.dispose()


app = FastAPI(title="Bill Analyzer", lifespan=lifespan)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(bills_router)
app.include_router(splits_router)
app.include_router(split_requests_router)
app.include_router(friends_router)
app.include_router(insights_router)
