import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, get_storage, get_vision_service
from src.core.constants import MAX_UPLOAD_BYTES
from src.core.exceptions import (
    BillItemNotFound,
    BillNotEditable,
    BillNotExtracted,
    BillNotFound,
    OllamaResponseError,
    OllamaUnavailable,
    UnsupportedImageFormat,
    VLMResponseInvalid,
)
from src.models.user import User
from src.schemas.bill import (
    BillItemCreateRequest,
    BillItemUpdateRequest,
    BillListResponse,
    BillResponse,
    BillSummaryResponse,
    BillUpdateRequest,
)
from src.services.bill_service import BillService
from src.services.storage.base import StorageBackend
from src.services.vision_service import VisionService

router = APIRouter(prefix="/bills", tags=["bills"])


def _service(db: AsyncSession, storage: StorageBackend) -> BillService:
    return BillService(db, storage)


@router.post("", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
async def upload_bill(
    image: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    data = await image.read()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty upload")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "image too large")
    try:
        bill = await _service(db, storage).upload_bill(user=user, raw_bytes=data)
    except UnsupportedImageFormat as exc:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported image format"
        ) from exc
    return BillResponse.model_validate(bill)


@router.get("", response_model=BillListResponse)
async def list_bills(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> BillListResponse:
    bills, total = await _service(db, storage).list_bills(
        user=user, limit=limit, offset=offset
    )
    return BillListResponse(
        items=[BillSummaryResponse.model_validate(b) for b in bills],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
    bill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    try:
        bill = await _service(db, storage).get_bill(bill_id=bill_id, user=user)
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    return BillResponse.model_validate(bill)


@router.patch("/{bill_id}", response_model=BillResponse)
async def update_bill(
    bill_id: uuid.UUID,
    body: BillUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    try:
        bill = await _service(db, storage).update_bill(
            bill_id=bill_id, user=user, fields=body
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillNotEditable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "bill is finalized and cannot be edited"
        ) from exc
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/extract", response_model=BillResponse)
async def extract_bill(
    bill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    vision: VisionService = Depends(get_vision_service),
) -> BillResponse:
    try:
        bill = await _service(db, storage).extract_bill(
            bill_id=bill_id, user=user, vision=vision
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillNotEditable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "bill is finalized and cannot be re-extracted"
        ) from exc
    except OllamaUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"vision service unavailable: {exc}"
        ) from exc
    except (OllamaResponseError, VLMResponseInvalid) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"vision extraction failed: {exc}"
        ) from exc
    return BillResponse.model_validate(bill)


@router.post(
    "/{bill_id}/items",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    bill_id: uuid.UUID,
    body: BillItemCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    try:
        bill = await _service(db, storage).add_item(
            bill_id=bill_id, user=user, item=body
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillNotEditable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "bill is finalized and cannot be edited"
        ) from exc
    return BillResponse.model_validate(bill)


@router.patch("/{bill_id}/items/{item_id}", response_model=BillResponse)
async def update_item(
    bill_id: uuid.UUID,
    item_id: uuid.UUID,
    body: BillItemUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    try:
        bill = await _service(db, storage).update_item(
            bill_id=bill_id, item_id=item_id, user=user, fields=body
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillItemNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not found") from exc
    except BillNotEditable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "bill is finalized and cannot be edited"
        ) from exc
    return BillResponse.model_validate(bill)


@router.delete("/{bill_id}/items/{item_id}", response_model=BillResponse)
async def delete_item(
    bill_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    try:
        bill = await _service(db, storage).delete_item(
            bill_id=bill_id, item_id=item_id, user=user
        )
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillItemNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not found") from exc
    except BillNotEditable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "bill is finalized and cannot be edited"
        ) from exc
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/finalize", response_model=BillResponse)
async def finalize_bill(
    bill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> BillResponse:
    try:
        bill = await _service(db, storage).finalize(bill_id=bill_id, user=user)
    except BillNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bill not found") from exc
    except BillNotEditable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "bill is already finalized"
        ) from exc
    except BillNotExtracted as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "bill must be extracted before it can be finalized",
        ) from exc
    return BillResponse.model_validate(bill)
