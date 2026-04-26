import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.split import Split, SplitItemShare, SplitParticipant


class SplitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_bill_id(self, bill_id: uuid.UUID) -> Split | None:
        stmt = (
            select(Split)
            .where(Split.bill_id == bill_id)
            .options(
                selectinload(Split.participants),
                selectinload(Split.item_shares),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, split_id: uuid.UUID) -> Split | None:
        stmt = (
            select(Split)
            .where(Split.id == split_id)
            .options(
                selectinload(Split.participants),
                selectinload(Split.item_shares),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_participant(self, participant_id: uuid.UUID) -> SplitParticipant | None:
        return await self._session.get(SplitParticipant, participant_id)

    async def shares_for_item(self, bill_item_id: uuid.UUID) -> list[SplitItemShare]:
        stmt = select(SplitItemShare).where(
            SplitItemShare.bill_item_id == bill_item_id
        )
        return list((await self._session.execute(stmt)).scalars().all())
