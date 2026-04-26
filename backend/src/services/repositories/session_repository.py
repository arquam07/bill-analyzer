import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import UserSession


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: uuid.UUID, token_hash: str) -> UserSession:
        row = UserSession(user_id=user_id, token_hash=token_hash)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_user_id_by_token_hash(self, token_hash: str) -> uuid.UUID | None:
        result = await self._session.execute(
            select(UserSession.user_id).where(UserSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def delete_by_token_hash(self, token_hash: str) -> int:
        result = await self._session.execute(
            delete(UserSession).where(UserSession.token_hash == token_hash)
        )
        return result.rowcount or 0
