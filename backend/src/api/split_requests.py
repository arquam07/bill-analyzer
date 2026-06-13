import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import (
    AssignmentItemsInvalid,
    BillHasNoTotal,
    BillNotFound,
    SettlementNotFound,
    SettlementNotPending,
    SettlementNotRecipient,
    SplitItemsInvalid,
    SplitRequestAlreadyExists,
    SplitRequestNotFound,
    SplitRequestNotPending,
    SplitRequestNotRecipient,
    SplitWithSelf,
    UserNotFound,
)
from src.models.user import User
from src.schemas.split_request import (
    BalancesResponse,
    SettleRequest,
    SettlementListResponse,
    SettlementResponse,
    SplitRequestCreate,
    SplitRequestListResponse,
    SplitRequestResponse,
    UserPublicResponse,
)
from src.services.split_request_service import SplitRequestService

router = APIRouter(tags=["split-requests"])


def _svc(db: AsyncSession) -> SplitRequestService:
    return SplitRequestService(db)


@router.get("/users/by-username/{username}", response_model=UserPublicResponse)
async def get_user_by_username(
    username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublicResponse:
    try:
        found = await _svc(db).get_user_by_username(username)
    except UserNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found") from exc
    return UserPublicResponse(id=found.id, username=found.username, name=found.name)


@router.post(
    "/bills/{bill_id}/split-requests",
    response_model=SplitRequestListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_split_requests(
    bill_id: uuid.UUID,
    body: SplitRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitRequestListResponse:
    try:
        return await _svc(db).create_split_requests(
            bill_id=bill_id,
            from_user=user,
            usernames=body.usernames,
            bill_item_ids=body.bill_item_ids,
            total_to_split=body.total_to_split,
            assignments=body.assignments,
            owner_item_ids=body.owner_item_ids,
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillHasNoTotal as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "bill has no total — extract it first"
        ) from exc
    except SplitItemsInvalid as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except AssignmentItemsInvalid as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except UserNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"user not found: {exc}") from exc
    except SplitWithSelf as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "cannot split a bill with yourself"
        ) from exc
    except SplitRequestAlreadyExists as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "a pending split request already exists for this bill and user"
        ) from exc


@router.get("/split-requests/incoming", response_model=SplitRequestListResponse)
async def list_incoming(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitRequestListResponse:
    return await _svc(db).list_incoming(user)


@router.get("/split-requests/outgoing", response_model=SplitRequestListResponse)
async def list_outgoing(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitRequestListResponse:
    return await _svc(db).list_outgoing(user)


@router.post("/split-requests/{sr_id}/accept", response_model=SplitRequestResponse)
async def accept_split_request(
    sr_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitRequestResponse:
    try:
        return await _svc(db).accept(sr_id=sr_id, user=user)
    except SplitRequestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "split request not found") from exc
    except SplitRequestNotRecipient as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not your split request") from exc
    except SplitRequestNotPending as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "split request is no longer pending"
        ) from exc


@router.post("/split-requests/{sr_id}/reject", response_model=SplitRequestResponse)
async def reject_split_request(
    sr_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitRequestResponse:
    try:
        return await _svc(db).reject(sr_id=sr_id, user=user)
    except SplitRequestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "split request not found") from exc
    except SplitRequestNotRecipient as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not your split request") from exc
    except SplitRequestNotPending as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "split request is no longer pending"
        ) from exc


@router.get("/balances", response_model=BalancesResponse)
async def get_balances(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BalancesResponse:
    return await _svc(db).get_balances(user)


@router.post(
    "/settlements",
    response_model=SettlementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_settlement(
    body: SettleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettlementResponse:
    try:
        return await _svc(db).settle(
            from_user=user,
            username=body.username,
            amount=body.amount,
            direction=body.direction,
            note=body.note,
        )
    except UserNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found") from exc
    except SplitWithSelf as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "cannot settle with yourself"
        ) from exc


@router.get("/settlements/incoming", response_model=SettlementListResponse)
async def list_incoming_settlements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettlementListResponse:
    return await _svc(db).list_incoming_settlements(user)


@router.get("/settlements/outgoing", response_model=SettlementListResponse)
async def list_outgoing_settlements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettlementListResponse:
    return await _svc(db).list_outgoing_settlements(user)


@router.post("/settlements/{settlement_id}/accept", response_model=SettlementResponse)
async def accept_settlement(
    settlement_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettlementResponse:
    try:
        return await _svc(db).accept_settlement(settlement_id=settlement_id, user=user)
    except SettlementNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "settlement not found") from exc
    except SettlementNotRecipient as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "not your settlement request to accept"
        ) from exc
    except SettlementNotPending as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "settlement is no longer pending"
        ) from exc


@router.post("/settlements/{settlement_id}/reject", response_model=SettlementResponse)
async def reject_settlement(
    settlement_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettlementResponse:
    try:
        return await _svc(db).reject_settlement(settlement_id=settlement_id, user=user)
    except SettlementNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "settlement not found") from exc
    except SettlementNotRecipient as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "not your settlement request to reject"
        ) from exc
    except SettlementNotPending as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "settlement is no longer pending"
        ) from exc
