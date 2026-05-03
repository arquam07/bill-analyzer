import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import (
    AlreadyFriends,
    FriendRequestAlreadyExists,
    FriendRequestNotFound,
    FriendRequestNotPending,
    FriendRequestNotRecipient,
    UserNotFound,
)
from src.models.user import User
from src.schemas.friendship import (
    FriendListResponse,
    FriendRequestCreate,
    FriendRequestListResponse,
    FriendRequestResponse,
)
from src.services.friendship_service import FriendshipService

router = APIRouter(prefix="/friends", tags=["friends"])


def _svc(db: AsyncSession) -> FriendshipService:
    return FriendshipService(db)


@router.post("/requests", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    body: FriendRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendRequestResponse:
    try:
        return await _svc(db).send_request(
            from_user=user,
            to_username=body.username,
            deferred_split=body.deferred_split,
        )
    except UserNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"user not found: {exc}") from exc
    except AlreadyFriends as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "already friends") from exc
    except FriendRequestAlreadyExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "friend request already pending") from exc


@router.get("/requests/incoming", response_model=FriendRequestListResponse)
async def list_incoming_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendRequestListResponse:
    return await _svc(db).list_incoming(user)


@router.get("/requests/outgoing", response_model=FriendRequestListResponse)
async def list_outgoing_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendRequestListResponse:
    return await _svc(db).list_outgoing(user)


@router.post("/requests/{fr_id}/accept", response_model=FriendRequestResponse)
async def accept_friend_request(
    fr_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendRequestResponse:
    try:
        return await _svc(db).accept(fr_id=fr_id, user=user)
    except FriendRequestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "friend request not found") from exc
    except FriendRequestNotRecipient as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not your friend request") from exc
    except FriendRequestNotPending as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "friend request is no longer pending"
        ) from exc


@router.post("/requests/{fr_id}/reject", response_model=FriendRequestResponse)
async def reject_friend_request(
    fr_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendRequestResponse:
    try:
        return await _svc(db).reject(fr_id=fr_id, user=user)
    except FriendRequestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "friend request not found") from exc
    except FriendRequestNotRecipient as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not your friend request") from exc
    except FriendRequestNotPending as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "friend request is no longer pending"
        ) from exc


@router.get("", response_model=FriendListResponse)
async def list_friends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendListResponse:
    return await _svc(db).list_friends(user)
