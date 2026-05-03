import uuid
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    BillHasNoTotal,
    BillNotFound,
    SplitItemsInvalid,
    SplitRequestAlreadyExists,
    SplitRequestNotFound,
    SplitRequestNotPending,
    SplitRequestNotRecipient,
    SplitWithSelf,
    UserNotFound,
)
from src.models.split_request import (
    STATUS_ACCEPTED,
    STATUS_PENDING,
    STATUS_REJECTED,
    SplitRequest,
    SplitSettlement,
)
from src.models.user import User
from src.schemas.split_request import (
    BalanceRow,
    BalancesResponse,
    BillSummary,
    NonFriendInfo,
    SettlementResponse,
    SplitRequestListResponse,
    SplitRequestResponse,
)
from src.services.repositories.bill_repository import BillRepository
from src.services.repositories.friendship_repository import FriendshipRepository
from src.services.repositories.split_request_repository import SplitRequestRepository
from src.services.repositories.user_repository import UserRepository


def _to_float(d: Decimal) -> float:
    return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _sr_to_response(sr: SplitRequest) -> SplitRequestResponse:
    return SplitRequestResponse(
        id=sr.id,
        bill_id=sr.bill_id,
        from_username=sr.from_user.username,
        to_username=sr.to_user.username,
        amount=_to_float(sr.amount),
        status=sr.status,
        note=sr.note,
        created_at=sr.created_at,
        responded_at=sr.responded_at,
        bill=BillSummary(
            merchant=sr.bill.merchant,
            total=float(sr.bill.total) if sr.bill.total is not None else None,
            billed_at=sr.bill.billed_at,
        ),
    )


class SplitRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SplitRequestRepository(session)
        self._bills = BillRepository(session)
        self._users = UserRepository(session)
        self._friends = FriendshipRepository(session)

    async def get_user_by_username(self, username: str) -> User:
        user = await self._users.get_by_username(username)
        if user is None:
            raise UserNotFound(username)
        return user

    async def create_split_requests(
        self,
        *,
        bill_id: uuid.UUID,
        from_user: User,
        usernames: list[str],
        bill_item_ids: list[uuid.UUID] | None,
        total_to_split: float | None,
    ) -> SplitRequestListResponse:
        bill = await self._bills.get_with_items(bill_id)
        if bill is None or bill.user_id != from_user.id:
            raise BillNotFound(str(bill_id))

        # Resolve which items are part of the split (if any).
        selected_priced: list[tuple[uuid.UUID, Decimal]] = []
        if bill_item_ids:
            ids_set = set(bill_item_ids)
            picked = [it for it in bill.items if it.id in ids_set]
            if len(picked) != len(ids_set):
                raise SplitItemsInvalid("one or more bill_item_ids do not belong to this bill")
            for it in picked:
                if it.total_price is None:
                    raise SplitItemsInvalid(f"item {it.id} has no price")
                selected_priced.append((it.id, it.total_price))

        if selected_priced:
            split_base = sum((p for _, p in selected_priced), Decimal("0"))
        elif total_to_split is not None:
            split_base = Decimal(str(total_to_split))
        elif bill.total is not None:
            split_base = bill.total
        else:
            raise BillHasNoTotal()

        # Resolve usernames to users
        recipients: list[User] = []
        for uname in usernames:
            user = await self._users.get_by_username(uname)
            if user is None:
                raise UserNotFound(uname)
            if user.id == from_user.id:
                raise SplitWithSelf()
            recipients.append(user)

        # Equal shares: each person (owner + recipients) pays 1/(n+1) of split_base
        n = len(recipients) + 1

        # Per-item recipient share = item.total_price / n
        item_shares: list[tuple[uuid.UUID, Decimal]] = []
        if selected_priced:
            for item_id, price in selected_priced:
                share = (price / Decimal(n)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                item_shares.append((item_id, share))
            sr_amount = sum((s for _, s in item_shares), Decimal("0"))
        else:
            sr_amount = (split_base / Decimal(n)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        note = bill.merchant if bill.merchant else None

        created: list[SplitRequest] = []
        non_friends: list[NonFriendInfo] = []
        for recipient in recipients:
            is_friend = await self._friends.are_friends(from_user.id, recipient.id)
            if not is_friend:
                non_friends.append(
                    NonFriendInfo(
                        username=recipient.username,
                        amount=float(sr_amount),
                        bill_item_ids=[iid for iid, _ in item_shares] if item_shares else None,
                    )
                )
                continue
            if await self._repo.pending_exists(bill_id, from_user.id, recipient.id):
                raise SplitRequestAlreadyExists()
            sr = await self._repo.create(
                bill_id=bill_id,
                from_user_id=from_user.id,
                to_user_id=recipient.id,
                amount=sr_amount,
                note=note,
                item_shares=item_shares if item_shares else None,
            )
            created.append(sr)

        await self._session.commit()
        return SplitRequestListResponse(
            items=[_sr_to_response(sr) for sr in created],
            non_friends=non_friends,
        )

    async def list_incoming(self, user: User) -> SplitRequestListResponse:
        items = await self._repo.list_incoming(user.id)
        return SplitRequestListResponse(items=[_sr_to_response(sr) for sr in items])

    async def list_outgoing(self, user: User) -> SplitRequestListResponse:
        items = await self._repo.list_outgoing(user.id)
        return SplitRequestListResponse(items=[_sr_to_response(sr) for sr in items])

    async def accept(self, *, sr_id: uuid.UUID, user: User) -> SplitRequestResponse:
        sr = await self._repo.get_by_id(sr_id)
        if sr is None:
            raise SplitRequestNotFound(str(sr_id))
        if sr.to_user_id != user.id:
            raise SplitRequestNotRecipient()
        if sr.status != STATUS_PENDING:
            raise SplitRequestNotPending()
        sr = await self._repo.set_status(sr, STATUS_ACCEPTED)
        await self._session.commit()
        return _sr_to_response(sr)

    async def reject(self, *, sr_id: uuid.UUID, user: User) -> SplitRequestResponse:
        sr = await self._repo.get_by_id(sr_id)
        if sr is None:
            raise SplitRequestNotFound(str(sr_id))
        if sr.to_user_id != user.id:
            raise SplitRequestNotRecipient()
        if sr.status != STATUS_PENDING:
            raise SplitRequestNotPending()
        sr = await self._repo.set_status(sr, STATUS_REJECTED)
        await self._session.commit()
        return _sr_to_response(sr)

    async def get_balances(self, user: User) -> BalancesResponse:
        splits, settlements = await self._repo.get_balances_data(user.id)

        # net[counterparty_id] = positive → they owe me; negative → I owe them
        net: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        counterparty_info: dict[uuid.UUID, tuple[str, uuid.UUID]] = {}

        for sr in splits:
            if sr.from_user_id == user.id:
                cid = sr.to_user_id
                net[cid] += sr.amount
                counterparty_info[cid] = (sr.to_user.username, cid)
            else:
                cid = sr.from_user_id
                net[cid] -= sr.amount
                counterparty_info[cid] = (sr.from_user.username, cid)

        for s in settlements:
            if s.from_user_id == user.id:
                cid = s.to_user_id
                net[cid] += s.amount
                counterparty_info[cid] = (s.to_user.username, cid)
            else:
                cid = s.from_user_id
                net[cid] -= s.amount
                counterparty_info[cid] = (s.from_user.username, cid)

        balances = [
            BalanceRow(
                username=counterparty_info[cid][0],
                user_id=cid,
                net=_to_float(amount),
            )
            for cid, amount in net.items()
            if amount != Decimal("0")
        ]
        return BalancesResponse(balances=sorted(balances, key=lambda b: b.username))

    async def settle(
        self, *, from_user: User, username: str, amount: float, note: str | None
    ) -> SettlementResponse:
        to_user = await self._users.get_by_username(username)
        if to_user is None:
            raise UserNotFound(username)
        if to_user.id == from_user.id:
            raise SplitWithSelf()

        s = await self._repo.create_settlement(
            from_user_id=from_user.id,
            to_user_id=to_user.id,
            amount=Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            note=note,
        )
        await self._session.commit()
        return SettlementResponse(
            id=s.id,
            from_username=s.from_user.username,
            to_username=s.to_user.username,
            amount=_to_float(s.amount),
            note=s.note,
            created_at=s.created_at,
        )
