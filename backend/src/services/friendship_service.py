import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    AlreadyFriends,
    FriendRequestAlreadyExists,
    FriendRequestNotFound,
    FriendRequestNotPending,
    FriendRequestNotRecipient,
    UserNotFound,
)
from src.models.friendship import STATUS_ACCEPTED, STATUS_PENDING, Friendship
from src.models.user import User
from src.schemas.friendship import (
    DeferredSplitInfo,
    FriendListResponse,
    FriendRequestListResponse,
    FriendRequestResponse,
    FriendResponse,
)
from src.services.repositories.friendship_repository import FriendshipRepository
from src.services.repositories.split_request_repository import SplitRequestRepository
from src.services.repositories.user_repository import UserRepository


def _fr_to_response(fr: Friendship) -> FriendRequestResponse:
    return FriendRequestResponse(
        id=fr.id,
        requester_username=fr.requester.username,
        addressee_username=fr.addressee.username,
        status=fr.status,
        created_at=fr.created_at,
        responded_at=fr.responded_at,
    )


class FriendshipService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = FriendshipRepository(session)
        self._users = UserRepository(session)
        self._sr_repo = SplitRequestRepository(session)

    async def send_request(
        self,
        *,
        from_user: User,
        to_username: str,
        deferred_split: DeferredSplitInfo | None = None,
    ) -> FriendRequestResponse:
        to_user = await self._users.get_by_username(to_username)
        if to_user is None:
            raise UserNotFound(to_username)

        existing = await self._repo.get_between(from_user.id, to_user.id)
        if existing is not None:
            if existing.status == STATUS_ACCEPTED:
                raise AlreadyFriends()
            if existing.status == STATUS_PENDING:
                raise FriendRequestAlreadyExists()
            # Rejected — allow re-request
            existing.status = STATUS_PENDING
            existing.responded_at = None
            await self._session.flush()
            fr = existing
        else:
            fr = await self._repo.create(from_user.id, to_user.id)

        if deferred_split is not None:
            await self._repo.add_deferred_split(
                friendship_id=fr.id,
                bill_id=deferred_split.bill_id,
                from_user_id=from_user.id,
                to_user_id=to_user.id,
                amount=Decimal(str(deferred_split.amount)),
                note=None,
                bill_item_ids=[str(i) for i in deferred_split.bill_item_ids]
                if deferred_split.bill_item_ids
                else None,
            )

        await self._session.commit()
        return _fr_to_response(fr)

    async def accept(self, *, fr_id: uuid.UUID, user: User) -> FriendRequestResponse:
        fr = await self._repo.get_by_id(fr_id)
        if fr is None:
            raise FriendRequestNotFound()
        if fr.addressee_id != user.id:
            raise FriendRequestNotRecipient()
        if fr.status != STATUS_PENDING:
            raise FriendRequestNotPending()

        fr = await self._repo.set_status(fr, STATUS_ACCEPTED)

        # Promote any deferred split requests to real split requests
        for ds in fr.deferred_splits:
            already = await self._sr_repo.pending_exists(ds.bill_id, ds.from_user_id, ds.to_user_id)
            if not already:
                await self._sr_repo.create(
                    bill_id=ds.bill_id,
                    from_user_id=ds.from_user_id,
                    to_user_id=ds.to_user_id,
                    amount=ds.amount,
                    note=ds.note,
                )

        await self._session.commit()
        return _fr_to_response(fr)

    async def reject(self, *, fr_id: uuid.UUID, user: User) -> FriendRequestResponse:
        fr = await self._repo.get_by_id(fr_id)
        if fr is None:
            raise FriendRequestNotFound()
        if fr.addressee_id != user.id:
            raise FriendRequestNotRecipient()
        if fr.status != STATUS_PENDING:
            raise FriendRequestNotPending()
        fr = await self._repo.set_status(fr, "rejected")
        await self._session.commit()
        return _fr_to_response(fr)

    async def list_incoming(self, user: User) -> FriendRequestListResponse:
        items = await self._repo.list_incoming(user.id)
        return FriendRequestListResponse(items=[_fr_to_response(fr) for fr in items])

    async def list_outgoing(self, user: User) -> FriendRequestListResponse:
        items = await self._repo.list_outgoing(user.id)
        return FriendRequestListResponse(items=[_fr_to_response(fr) for fr in items])

    async def list_friends(self, user: User) -> FriendListResponse:
        friendships = await self._repo.list_accepted(user.id)
        friends = []
        for fr in friendships:
            other = fr.addressee if fr.requester_id == user.id else fr.requester
            friends.append(
                FriendResponse(user_id=other.id, username=other.username, name=other.name)
            )
        return FriendListResponse(friends=sorted(friends, key=lambda f: f.username))
