import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import (
    BillItemNotFound,
    BillNotEditable,
    BillNotFound,
    SplitParticipantConflict,
    SplitParticipantNotFound,
)
from src.models.user import User
from src.schemas.split import (
    ParticipantCreateRequest,
    SetItemParticipantsRequest,
    SplitResponse,
)
from src.services.split_service import SplitService

router = APIRouter(prefix="/bills/{bill_id}/split", tags=["splits"])


def _service(db: AsyncSession) -> SplitService:
    return SplitService(db)


def _bill_404_or_409(exc: Exception) -> HTTPException:
    if isinstance(exc, BillNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "bill not found")
    if isinstance(exc, BillNotEditable):
        return HTTPException(
            status.HTTP_409_CONFLICT, "bill is finalized and cannot be edited"
        )
    raise exc  # unreachable


@router.get("", response_model=SplitResponse)
async def get_split(
    bill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    try:
        return await _service(db).get_or_create(bill_id=bill_id, user=user)
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc


@router.post(
    "/participants",
    response_model=SplitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    bill_id: uuid.UUID,
    body: ParticipantCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    try:
        return await _service(db).add_participant(
            bill_id=bill_id,
            user=user,
            display_name=body.display_name,
            user_email=body.user_email,
        )
    except (BillNotFound, BillNotEditable) as exc:
        raise _bill_404_or_409(exc) from exc
    except SplitParticipantConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.delete("/participants/{participant_id}", response_model=SplitResponse)
async def remove_participant(
    bill_id: uuid.UUID,
    participant_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    try:
        return await _service(db).remove_participant(
            bill_id=bill_id, user=user, participant_id=participant_id
        )
    except (BillNotFound, BillNotEditable) as exc:
        raise _bill_404_or_409(exc) from exc
    except SplitParticipantNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "participant not found") from exc


@router.put(
    "/items/{bill_item_id}/participants",
    response_model=SplitResponse,
)
async def set_item_participants(
    bill_id: uuid.UUID,
    bill_item_id: uuid.UUID,
    body: SetItemParticipantsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    try:
        return await _service(db).set_item_participants(
            bill_id=bill_id,
            user=user,
            bill_item_id=bill_item_id,
            participant_ids=body.participant_ids,
        )
    except (BillNotFound, BillNotEditable) as exc:
        raise _bill_404_or_409(exc) from exc
    except BillItemNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not found") from exc
    except SplitParticipantNotFound as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "unknown participant id"
        ) from exc


@router.post(
    "/participants/{participant_id}/settle",
    response_model=SplitResponse,
)
async def settle_participant(
    bill_id: uuid.UUID,
    participant_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    try:
        return await _service(db).settle_participant(
            bill_id=bill_id,
            user=user,
            participant_id=participant_id,
            settled=True,
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except SplitParticipantNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "participant not found") from exc


@router.delete(
    "/participants/{participant_id}/settle",
    response_model=SplitResponse,
)
async def unsettle_participant(
    bill_id: uuid.UUID,
    participant_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SplitResponse:
    try:
        return await _service(db).settle_participant(
            bill_id=bill_id,
            user=user,
            participant_id=participant_id,
            settled=False,
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except SplitParticipantNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "participant not found") from exc
