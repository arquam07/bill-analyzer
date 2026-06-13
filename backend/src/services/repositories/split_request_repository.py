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
    SplitRequestItem,
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
        item_shares: list[tuple[uuid.UUID, Decimal]] | None = None,
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
        if item_shares:
            for bill_item_id, share in item_shares:
                self._session.add(
                    SplitRequestItem(
                        split_request_id=sr.id,
                        bill_item_id=bill_item_id,
                        share_amount=share,
                    )
                )
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

    async def request_exists(
        self, bill_id: uuid.UUID, from_user_id: uuid.UUID, to_user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(SplitRequest.id).where(
                SplitRequest.bill_id == bill_id,
                SplitRequest.from_user_id == from_user_id,
                SplitRequest.to_user_id == to_user_id,
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

    def _settlement_relations(self) -> list[ExecutableOption]:
        return [
            selectinload(SplitSettlement.from_user),
            selectinload(SplitSettlement.to_user),
            selectinload(SplitSettlement.initiated_by),
        ]

    async def create_settlement(
        self,
        *,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        initiated_by_user_id: uuid.UUID,
        amount: Decimal,
        note: str | None,
        status: str = STATUS_PENDING,
    ) -> SplitSettlement:
        s = SplitSettlement(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            initiated_by_user_id=initiated_by_user_id,
            amount=amount,
            note=note,
            status=status,
        )
        self._session.add(s)
        await self._session.flush()
        await self._session.refresh(
            s, attribute_names=["from_user", "to_user", "initiated_by"]
        )
        return s

    async def get_settlement_by_id(self, settlement_id: uuid.UUID) -> SplitSettlement | None:
        result = await self._session.execute(
            select(SplitSettlement)
            .options(*self._settlement_relations())
            .where(SplitSettlement.id == settlement_id)
        )
        return result.scalar_one_or_none()

    async def set_settlement_status(
        self, settlement: SplitSettlement, status: str
    ) -> SplitSettlement:
        settlement.status = status
        settlement.responded_at = datetime.now(UTC)
        await self._session.flush()
        return settlement

    async def list_incoming_settlements(self, user_id: uuid.UUID) -> list[SplitSettlement]:
        """Settlement requests addressed to this user (initiated by counterparty)."""
        result = await self._session.execute(
            select(SplitSettlement)
            .options(*self._settlement_relations())
            .where(
                SplitSettlement.status == STATUS_PENDING,
                SplitSettlement.initiated_by_user_id != user_id,
                or_(
                    SplitSettlement.from_user_id == user_id,
                    SplitSettlement.to_user_id == user_id,
                ),
            )
            .order_by(SplitSettlement.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_outgoing_settlements(self, user_id: uuid.UUID) -> list[SplitSettlement]:
        """Settlement requests this user initiated."""
        result = await self._session.execute(
            select(SplitSettlement)
            .options(*self._settlement_relations())
            .where(SplitSettlement.initiated_by_user_id == user_id)
            .order_by(SplitSettlement.created_at.desc())
        )
        return list(result.scalars().all())

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
                SplitSettlement.status == STATUS_ACCEPTED,
                or_(
                    SplitSettlement.from_user_id == user_id,
                    SplitSettlement.to_user_id == user_id,
                ),
            )
        )
        return list(splits_result.scalars().all()), list(settlements_result.scalars().all())
