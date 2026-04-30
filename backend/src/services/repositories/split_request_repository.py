import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from src.models.split_request import (
    STATUS_ACCEPTED,
    STATUS_PENDING,
    STATUS_REJECTED,
    SplitRequest,
    SplitSettlement,
)


class SplitRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _with_relations(self) -> list[ExecutableOption]:
        return [
            selectinload(SplitRequest.from_user),
            selectinload(SplitRequest.to_user),
            selectinload(SplitRequest.bill),
        ]

    async def create(
        self,
        *,
        bill_id: uuid.UUID,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        amount: Decimal,
        note: str | None,
    ) -> SplitRequest:
        sr = SplitRequest(
            bill_id=bill_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            status=STATUS_PENDING,
            note=note,
        )
        self._session.add(sr)
        await self._session.flush()
        await self._session.refresh(sr, attribute_names=["from_user", "to_user", "bill"])
        return sr

    async def get_by_id(self, sr_id: uuid.UUID) -> SplitRequest | None:
        result = await self._session.execute(
            select(SplitRequest)
            .options(*self._with_relations())
            .where(SplitRequest.id == sr_id)
        )
        return result.scalar_one_or_none()

    async def pending_exists(
        self, bill_id: uuid.UUID, from_user_id: uuid.UUID, to_user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(SplitRequest.id).where(
                SplitRequest.bill_id == bill_id,
                SplitRequest.from_user_id == from_user_id,
                SplitRequest.to_user_id == to_user_id,
                SplitRequest.status == STATUS_PENDING,
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_incoming(self, user_id: uuid.UUID) -> list[SplitRequest]:
        result = await self._session.execute(
            select(SplitRequest)
            .options(*self._with_relations())
            .where(
                SplitRequest.to_user_id == user_id,
                SplitRequest.status == STATUS_PENDING,
            )
            .order_by(SplitRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_outgoing(self, user_id: uuid.UUID) -> list[SplitRequest]:
        result = await self._session.execute(
            select(SplitRequest)
            .options(*self._with_relations())
            .where(SplitRequest.from_user_id == user_id)
            .order_by(SplitRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_status(
        self, sr: SplitRequest, status: str
    ) -> SplitRequest:
        sr.status = status
        sr.responded_at = datetime.now(UTC)
        await self._session.flush()
        return sr

    async def create_settlement(
        self,
        *,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        amount: Decimal,
        note: str | None,
    ) -> SplitSettlement:
        s = SplitSettlement(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            note=note,
        )
        self._session.add(s)
        await self._session.flush()
        await self._session.refresh(s, attribute_names=["from_user", "to_user"])
        return s

    async def get_balances_data(
        self, user_id: uuid.UUID
    ) -> tuple[list[SplitRequest], list[SplitSettlement]]:
        splits_result = await self._session.execute(
            select(SplitRequest)
            .options(selectinload(SplitRequest.from_user), selectinload(SplitRequest.to_user))
            .where(
                SplitRequest.status == STATUS_ACCEPTED,
                or_(
                    SplitRequest.from_user_id == user_id,
                    SplitRequest.to_user_id == user_id,
                ),
            )
        )
        settlements_result = await self._session.execute(
            select(SplitSettlement)
            .options(
                selectinload(SplitSettlement.from_user),
                selectinload(SplitSettlement.to_user),
            )
            .where(
                or_(
                    SplitSettlement.from_user_id == user_id,
                    SplitSettlement.to_user_id == user_id,
                )
            )
        )
        return list(splits_result.scalars().all()), list(settlements_result.scalars().all())
