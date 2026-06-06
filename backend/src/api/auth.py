from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import bearer_scheme, get_db
from src.core.config import get_settings
from src.core.exceptions import (
    EmailAlreadyExists,
    GoogleAccountAlreadyExists,
    GoogleTokenInvalid,
    InvalidCredentials,
    UsernameAlreadyExists,
)
from src.schemas.auth import (
    GoogleAuthRequest,
    GoogleAuthResponse,
    GoogleCompleteRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        user, token = await AuthService(db).register(
            email=payload.email,
            username=payload.username,
            password=payload.password,
            name=payload.name,
            preferred_language=payload.preferred_language,
        )
    except EmailAlreadyExists as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "email already registered"
        ) from exc
    except UsernameAlreadyExists as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "username already taken"
        ) from exc
    return TokenResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        user, token = await AuthService(db).login(
            email=payload.email, password=payload.password
        )
    except InvalidCredentials as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials") from exc
    return TokenResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(
    payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
) -> GoogleAuthResponse:
    try:
        return await AuthService(db).google_auth(
            id_token=payload.id_token,
            client_id=get_settings().google_client_id,
        )
    except GoogleTokenInvalid as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"invalid Google token: {exc}",
        ) from exc


@router.post("/google/complete", response_model=TokenResponse)
async def google_complete(
    payload: GoogleCompleteRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        user, token = await AuthService(db).google_complete(
            id_token=payload.id_token,
            client_id=get_settings().google_client_id,
            username=payload.username,
            preferred_language=payload.preferred_language,
        )
    except GoogleTokenInvalid as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid Google token") from exc
    except GoogleAccountAlreadyExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "account already exists") from exc
    except UsernameAlreadyExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "username already taken") from exc
    except EmailAlreadyExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered") from exc
    return TokenResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> None:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    await AuthService(db).logout(credentials.credentials)
