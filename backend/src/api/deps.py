from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import InvalidSessionToken
from src.models.user import User
from src.services.auth_service import AuthService
from src.services.normalization_service import NormalizationService
from src.services.storage.base import StorageBackend
from src.services.vision_service import VisionService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session


def get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage  # type: ignore[no-any-return]


def get_vision_service(request: Request) -> VisionService:
    return request.app.state.vision_service  # type: ignore[no-any-return]


def get_normalization_service(request: Request) -> NormalizationService:
    return request.app.state.normalization_service  # type: ignore[no-any-return]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        return await AuthService(db).authenticate_token(credentials.credentials)
    except InvalidSessionToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
