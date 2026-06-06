import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    EmailAlreadyExists,
    GoogleAccountAlreadyExists,
    GoogleTokenInvalid,
    InvalidCredentials,
    InvalidSessionToken,
    UsernameAlreadyExists,
)
from src.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from src.models.user import User
from src.schemas.auth import GoogleAuthResponse, UserResponse
from src.services.repositories.session_repository import SessionRepository
from src.services.repositories.user_repository import UserRepository


_log = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)

    async def register(
        self,
        *,
        email: str,
        username: str,
        password: str,
        name: str | None,
        preferred_language: str,
    ) -> tuple[User, str]:
        normalized = email.lower()
        if await self._users.get_by_email(normalized) is not None:
            raise EmailAlreadyExists(normalized)
        if await self._users.get_by_username(username) is not None:
            raise UsernameAlreadyExists(username)
        user = await self._users.create(
            email=normalized,
            username=username,
            password_hash=hash_password(password),
            name=name,
            preferred_language=preferred_language,
        )
        token = await self._issue_token(user)
        await self._session.commit()
        return user, token

    async def login(self, *, email: str, password: str) -> tuple[User, str]:
        normalized = email.lower()
        user = await self._users.get_by_email(normalized)
        if user is None or user.password_hash is None or not verify_password(user.password_hash, password):
            raise InvalidCredentials()
        token = await self._issue_token(user)
        await self._session.commit()
        return user, token

    async def logout(self, token: str) -> None:
        await self._sessions.delete_by_token_hash(hash_session_token(token))
        await self._session.commit()

    def _verify_google_token(self, id_token: str, client_id: str) -> dict[str, str]:
        if not client_id:
            raise GoogleTokenInvalid("GOOGLE_CLIENT_ID is not configured on the server")
        try:
            return google_id_token.verify_oauth2_token(  # type: ignore[no-any-return,no-untyped-call]
                id_token, google_requests.Request(), client_id
            )
        except Exception as exc:
            _log.error("Google token verification failed: %s", exc)
            raise GoogleTokenInvalid(str(exc)) from exc

    async def google_auth(self, *, id_token: str, client_id: str) -> GoogleAuthResponse:
        info = self._verify_google_token(id_token, client_id)
        google_id: str = info["sub"]
        email: str = info["email"].lower()
        name: str | None = info.get("name")

        user = await self._users.get_by_google_id(google_id)
        if user is None:
            user = await self._users.get_by_email(email)
            if user is not None:
                user.google_id = google_id  # link existing password account

        if user is not None:
            token = await self._issue_token(user)
            await self._session.commit()
            return GoogleAuthResponse(
                needs_onboarding=False,
                user=UserResponse.model_validate(user),
                token=token,
            )

        return GoogleAuthResponse(needs_onboarding=True, email=email, name=name)

    async def google_complete(
        self,
        *,
        id_token: str,
        client_id: str,
        username: str,
        preferred_language: str,
    ) -> tuple[User, str]:
        info = self._verify_google_token(id_token, client_id)
        google_id: str = info["sub"]
        email: str = info["email"].lower()
        name: str | None = info.get("name")

        if await self._users.get_by_google_id(google_id) is not None:
            raise GoogleAccountAlreadyExists()
        if await self._users.get_by_username(username) is not None:
            raise UsernameAlreadyExists(username)
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyExists(email)

        user = await self._users.create(
            email=email,
            username=username,
            password_hash=None,
            name=name,
            preferred_language=preferred_language,
            google_id=google_id,
        )
        token = await self._issue_token(user)
        await self._session.commit()
        return user, token

    async def authenticate_token(self, token: str) -> User:
        user_id = await self._sessions.get_user_id_by_token_hash(hash_session_token(token))
        if user_id is None:
            raise InvalidSessionToken()
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise InvalidSessionToken()
        return user

    async def _issue_token(self, user: User) -> str:
        token = generate_session_token()
        await self._sessions.create(user_id=user.id, token_hash=hash_session_token(token))
        return token
