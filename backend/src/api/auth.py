from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import bearer_scheme, get_db
from src.core.exceptions import EmailAlreadyExists, InvalidCredentials, UsernameAlreadyExists
from src.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> None:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    await AuthService(db).logout(credentials.credentials)
