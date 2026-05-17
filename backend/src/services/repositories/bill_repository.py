import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.bill import Bill, BillItem


class BillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        image_path: str,
        content_hash: str,
        mime_type: str,
        byte_size: int,
        status: str,
    ) -> Bill:
        bill = Bill(
            id=bill_id,
            user_id=user_id,
            image_path=image_path,
            content_hash=content_hash,
            mime_type=mime_type,
            byte_size=byte_size,
            status=status,
        )
        self._session.add(bill)
        await self._session.flush()
        return bill

    async def get_by_id(self, bill_id: uuid.UUID) -> Bill | None:
        return await self._session.get(Bill, bill_id)

    async def get_with_items(self, bill_id: uuid.UUID) -> Bill | None:
        stmt = (
            select(Bill).where(Bill.id == bill_id).options(selectinload(Bill.items))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[Bill]:
        stmt = (
            select(Bill)
            .where(Bill.user_id == user_id)
            .order_by(Bill.billed_at.desc().nullslast(), Bill.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Bill).where(Bill.user_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def delete_items(self, bill_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(BillItem).where(BillItem.bill_id == bill_id)
        )

    async def get_item(self, item_id: uuid.UUID) -> BillItem | None:
        return await self._session.get(BillItem, item_id)

    async def max_item_position(self, bill_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(BillItem.position), -1)).where(
            BillItem.bill_id == bill_id
        )
        return int((await self._session.execute(stmt)).scalar_one())
