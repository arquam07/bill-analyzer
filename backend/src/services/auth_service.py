from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    EmailAlreadyExists,
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
from src.services.repositories.session_repository import SessionRepository
from src.services.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)

    async def register(
        self, *, email: str, username: str, password: str, name: str | None
    ) -> tuple[User, str]:
        normalized = email.lower()
        if await self._users.get_by_email(normalized) is not None:
            raise EmailAlreadyExists(normalized)
        if await self._users.get_by_username(username) is not None:
            raise UsernameAlreadyExists(username)
        user = await self._users.create(
            email=normalized, username=username, password_hash=hash_password(password), name=name
        )
        token = await self._issue_token(user)
        await self._session.commit()
        return user, token

    async def login(self, *, email: str, password: str) -> tuple[User, str]:
        normalized = email.lower()
        user = await self._users.get_by_email(normalized)
        if user is None or not verify_password(user.password_hash, password):
            raise InvalidCredentials()
        token = await self._issue_token(user)
        await self._session.commit()
        return user, token

    async def logout(self, token: str) -> None:
        await self._sessions.delete_by_token_hash(hash_session_token(token))
        await self._session.commit()

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
