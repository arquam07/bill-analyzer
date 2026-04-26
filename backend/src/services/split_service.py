import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    BillItemNotFound,
    BillNotEditable,
    BillNotFound,
    SplitParticipantConflict,
    SplitParticipantNotFound,
)
from src.models.bill import Bill, BillItem
from src.models.split import Split, SplitItemShare, SplitParticipant
from src.models.user import User
from src.schemas.split import (
    ItemShareResponse,
    ParticipantResponse,
    ParticipantTotal,
    SplitResponse,
    round_money,
)
from src.services.bill_service import STATUS_REVIEWED
from src.services.repositories.bill_repository import BillRepository
from src.services.repositories.split_repository import SplitRepository
from src.services.repositories.user_repository import UserRepository


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SplitService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._bills = BillRepository(session)
        self._splits = SplitRepository(session)
        self._users = UserRepository(session)

    async def _owned_bill(self, *, bill_id: uuid.UUID, user: User) -> Bill:
        bill = await self._bills.get_with_items(bill_id)
        if bill is None or bill.user_id != user.id:
            raise BillNotFound(str(bill_id))
        return bill

    async def _editable_bill(self, *, bill_id: uuid.UUID, user: User) -> Bill:
        bill = await self._owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))
        return bill

    async def _ensure_split(self, *, bill: Bill, user: User) -> Split:
        existing = await self._splits.get_by_bill_id(bill.id)
        if existing is not None:
            return existing
        split = Split(bill_id=bill.id, created_by_user_id=user.id)
        self._session.add(split)
        await self._session.flush()
        # Re-fetch with relationships eager-loaded
        loaded = await self._splits.get_by_id(split.id)
        if loaded is None:
            raise RuntimeError("split disappeared after insert")
        return loaded

    async def get_or_create(self, *, bill_id: uuid.UUID, user: User) -> SplitResponse:
        bill = await self._owned_bill(bill_id=bill_id, user=user)
        existing = await self._splits.get_by_bill_id(bill.id)
        if existing is None:
            if bill.status == STATUS_REVIEWED:
                # Reading a non-existent split on a finalized bill — return an empty
                # structure rather than creating one.
                return self._render(bill=bill, split=None)
            existing = await self._ensure_split(bill=bill, user=user)
            await self._session.commit()
            existing = await self._splits.get_by_bill_id(bill.id)
        return self._render(bill=bill, split=existing)

    async def get(self, *, bill_id: uuid.UUID, user: User) -> SplitResponse:
        bill = await self._owned_bill(bill_id=bill_id, user=user)
        split = await self._splits.get_by_bill_id(bill.id)
        return self._render(bill=bill, split=split)

    async def add_participant(
        self,
        *,
        bill_id: uuid.UUID,
        user: User,
        display_name: str,
        user_email: str | None,
    ) -> SplitResponse:
        bill = await self._editable_bill(bill_id=bill_id, user=user)
        split = await self._ensure_split(bill=bill, user=user)

        # uniqueness check on display_name within split
        if any(p.display_name == display_name for p in split.participants):
            raise SplitParticipantConflict(
                f"participant with name '{display_name}' already exists"
            )

        linked_user_id: uuid.UUID | None = None
        if user_email is not None:
            linked = await self._users.get_by_email(user_email.lower())
            if linked is not None:
                linked_user_id = linked.id

        participant = SplitParticipant(
            display_name=display_name,
            user_id=linked_user_id,
        )
        split.participants.append(participant)
        await self._session.commit()
        return await self.get(bill_id=bill_id, user=user)

    async def remove_participant(
        self, *, bill_id: uuid.UUID, user: User, participant_id: uuid.UUID
    ) -> SplitResponse:
        bill = await self._editable_bill(bill_id=bill_id, user=user)
        split = await self._splits.get_by_bill_id(bill.id)
        if split is None:
            raise SplitParticipantNotFound(str(participant_id))

        target = next((p for p in split.participants if p.id == participant_id), None)
        if target is None:
            raise SplitParticipantNotFound(str(participant_id))

        split.participants.remove(target)
        await self._session.commit()
        return await self.get(bill_id=bill_id, user=user)

    async def set_item_participants(
        self,
        *,
        bill_id: uuid.UUID,
        user: User,
        bill_item_id: uuid.UUID,
        participant_ids: list[uuid.UUID],
    ) -> SplitResponse:
        bill = await self._editable_bill(bill_id=bill_id, user=user)
        split = await self._ensure_split(bill=bill, user=user)

        # Validate the bill_item belongs to this bill
        item = next((i for i in bill.items if i.id == bill_item_id), None)
        if item is None:
            raise BillItemNotFound(str(bill_item_id))

        # Validate every participant_id belongs to this split
        valid_pids = {p.id for p in split.participants}
        for pid in participant_ids:
            if pid not in valid_pids:
                raise SplitParticipantNotFound(str(pid))

        # Replace existing shares for this item — drop from relationship so
        # cascade=delete-orphan removes them, and the in-memory collection stays
        # consistent (we use expire_on_commit=False).
        existing = [s for s in split.item_shares if s.bill_item_id == bill_item_id]
        for share in existing:
            split.item_shares.remove(share)
        await self._session.flush()

        for pid in dict.fromkeys(participant_ids):
            split.item_shares.append(
                SplitItemShare(
                    bill_item_id=bill_item_id,
                    participant_id=pid,
                    weight=Decimal("1.000"),
                )
            )
        await self._session.commit()
        return await self.get(bill_id=bill_id, user=user)

    async def settle_participant(
        self,
        *,
        bill_id: uuid.UUID,
        user: User,
        participant_id: uuid.UUID,
        settled: bool,
    ) -> SplitResponse:
        bill = await self._owned_bill(bill_id=bill_id, user=user)
        # Settlement is allowed even after the bill is reviewed — settling a debt
        # doesn't mutate the split structure, just records that money changed hands.
        split = await self._splits.get_by_bill_id(bill.id)
        if split is None:
            raise SplitParticipantNotFound(str(participant_id))
        target = next((p for p in split.participants if p.id == participant_id), None)
        if target is None:
            raise SplitParticipantNotFound(str(participant_id))
        target.settled_at = _utcnow() if settled else None
        await self._session.commit()
        return await self.get(bill_id=bill_id, user=user)

    def _render(self, *, bill: Bill, split: Split | None) -> SplitResponse:
        items: list[BillItem] = bill.items or []
        bill_total = sum((i.total_price or Decimal("0") for i in items), Decimal("0"))

        if split is None:
            return SplitResponse(
                id=uuid.UUID(int=0),
                bill_id=bill.id,
                created_by_user_id=bill.user_id,
                created_at=bill.created_at,
                participants=[],
                item_assignments=[],
                participant_totals=[],
                unassigned_total=round_money(bill_total),
                bill_total=round_money(bill_total),
                bill_locked=bill.status == STATUS_REVIEWED,
            )

        # Group shares by item
        shares_by_item: dict[uuid.UUID, list[SplitItemShare]] = defaultdict(list)
        for s in split.item_shares:
            shares_by_item[s.bill_item_id].append(s)

        # Compute participant totals + unassigned
        totals: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        unassigned = Decimal("0")
        for item in items:
            item_total = item.total_price or Decimal("0")
            shares = shares_by_item.get(item.id, [])
            if not shares:
                unassigned += item_total
                continue
            weight_sum = sum((s.weight for s in shares), Decimal("0"))
            if weight_sum == 0:
                unassigned += item_total
                continue
            for share in shares:
                totals[share.participant_id] += item_total * share.weight / weight_sum

        participant_responses = [
            ParticipantResponse.model_validate(p) for p in split.participants
        ]
        item_assignments = [
            ItemShareResponse(
                bill_item_id=item_id,
                participant_ids=[s.participant_id for s in shares],
            )
            for item_id, shares in shares_by_item.items()
        ]
        participant_totals = [
            ParticipantTotal(
                participant_id=p.id,
                display_name=p.display_name,
                total=round_money(totals.get(p.id, Decimal("0"))),
                settled_at=p.settled_at,
            )
            for p in split.participants
        ]
        return SplitResponse(
            id=split.id,
            bill_id=bill.id,
            created_by_user_id=split.created_by_user_id,
            created_at=split.created_at,
            participants=participant_responses,
            item_assignments=item_assignments,
            participant_totals=participant_totals,
            unassigned_total=round_money(unassigned),
            bill_total=round_money(bill_total),
            bill_locked=bill.status == STATUS_REVIEWED,
        )
