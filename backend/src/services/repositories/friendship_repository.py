import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.friendship import (
    STATUS_ACCEPTED,
    STATUS_PENDING,
    Friendship,
    DeferredSplitRequest,
)


class FriendshipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_between(self, user_a: uuid.UUID, user_b: uuid.UUID) -> Friendship | None:
        result = await self._session.execute(
            select(Friendship)
            .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
            .where(
                or_(
                    (Friendship.requester_id == user_a) & (Friendship.addressee_id == user_b),
                    (Friendship.requester_id == user_b) & (Friendship.addressee_id == user_a),
                )
            )
        )
        return result.scalar_one_or_none()

    async def are_friends(self, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
        f = await self.get_between(user_a, user_b)
        return f is not None and f.status == STATUS_ACCEPTED

    async def create(self, requester_id: uuid.UUID, addressee_id: uuid.UUID) -> Friendship:
        fr = Friendship(requester_id=requester_id, addressee_id=addressee_id, status=STATUS_PENDING)
        self._session.add(fr)
        await self._session.flush()
        await self._session.refresh(fr, attribute_names=["requester", "addressee"])
        return fr

    async def get_by_id(self, fr_id: uuid.UUID) -> Friendship | None:
        result = await self._session.execute(
            select(Friendship)
            .options(
                selectinload(Friendship.requester),
                selectinload(Friendship.addressee),
                selectinload(Friendship.deferred_splits),
            )
            .where(Friendship.id == fr_id)
        )
        return result.scalar_one_or_none()

    async def list_incoming(self, user_id: uuid.UUID) -> list[Friendship]:
        result = await self._session.execute(
            select(Friendship)
            .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
            .where(Friendship.addressee_id == user_id, Friendship.status == STATUS_PENDING)
            .order_by(Friendship.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_outgoing(self, user_id: uuid.UUID) -> list[Friendship]:
        result = await self._session.execute(
            select(Friendship)
            .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
            .where(Friendship.requester_id == user_id, Friendship.status == STATUS_PENDING)
            .order_by(Friendship.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_accepted(self, user_id: uuid.UUID) -> list[Friendship]:
        result = await self._session.execute(
            select(Friendship)
            .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
            .where(
                or_(
                    Friendship.requester_id == user_id,
                    Friendship.addressee_id == user_id,
                ),
                Friendship.status == STATUS_ACCEPTED,
            )
            .order_by(Friendship.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_status(self, fr: Friendship, status: str) -> Friendship:
        fr.status = status
        fr.responded_at = datetime.now(UTC)
        await self._session.flush()
        return fr

    async def add_deferred_split(
        self,
        *,
        friendship_id: uuid.UUID,
        bill_id: uuid.UUID,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        amount: Decimal,
        note: str | None,
        bill_item_ids: list[str] | None,
    ) -> DeferredSplitRequest:
        ds = DeferredSplitRequest(
            friendship_id=friendship_id,
            bill_id=bill_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            note=note,
            bill_item_ids=bill_item_ids,
        )
        self._session.add(ds)
        await self._session.flush()
        return ds
