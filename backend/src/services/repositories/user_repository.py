import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
        name: str | None,
        preferred_language: str,
    ) -> User:
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            name=name,
            preferred_language=preferred_language,
        )
        self._session.add(user)
        await self._session.flush()
        return user
