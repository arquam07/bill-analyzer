import contextlib
import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    BillItemNotFound,
    BillNotEditable,
    BillNotExtracted,
    BillNotFound,
)
from src.models.bill import Bill, BillItem
from src.models.user import User
from src.schemas.bill import (
    BillItemCreateRequest,
    BillItemUpdateRequest,
    BillManualCreateRequest,
    BillUpdateRequest,
)
from src.schemas.extraction import RawBillExtraction
from src.services.image_processing import process_image
from src.services.repositories.bill_repository import BillRepository
from src.services.storage.base import StorageBackend
from src.services.vision_service import VisionService

_EXTENSION_FOR_FORMAT = {"JPEG": "jpg", "PNG": "png"}

STATUS_UPLOADED = "uploaded"
STATUS_EXTRACTED = "extracted"
STATUS_REVIEWED = "reviewed"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _to_decimal(value: float | int | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _recompute_total(bill: Bill) -> None:
    """Sync bill.total to the sum of item totals after a user edit.

    Why: dashboard reads bill.total, bill detail UI shows items — they must agree.
    Extract-time totals are preserved (VLM may report tax/fees separately); we only
    re-sum on user-driven item add/update/delete so the contract is "edits keep
    bill.total consistent with what the user sees."
    """
    totals = [it.total_price for it in bill.items if it.total_price is not None]
    bill.total = sum(totals, Decimal(0)) if totals else None


class BillService:
    def __init__(self, session: AsyncSession, storage: StorageBackend) -> None:
        self._session = session
        self._storage = storage
        self._bills = BillRepository(session)

    async def upload_bill(self, *, user: User, raw_bytes: bytes) -> Bill:
        processed_bytes, mime_type, fmt = process_image(raw_bytes)
        content_hash = hashlib.sha256(processed_bytes).hexdigest()
        ext = _EXTENSION_FOR_FORMAT[fmt]
        bill_id = uuid.uuid4()
        image_path = f"users/{user.id}/bills/{bill_id}.{ext}"

        # Write file first; if the DB commit later fails we delete the orphan.
        # Files-without-rows are recoverable; rows-without-files cause 500s on read.
        await self._storage.write(image_path, processed_bytes, mime_type)
        try:
            await self._bills.create(
                bill_id=bill_id,
                user_id=user.id,
                image_path=image_path,
                content_hash=content_hash,
                mime_type=mime_type,
                byte_size=len(processed_bytes),
                status=STATUS_UPLOADED,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            with contextlib.suppress(Exception):
                await self._storage.delete(image_path)
            raise
        loaded = await self._bills.get_with_items(bill_id)
        if loaded is None:
            raise RuntimeError("bill disappeared after commit")
        return loaded

    async def create_manual_bill(
        self, *, user: User, fields: BillManualCreateRequest
    ) -> Bill:
        """Create a bill from scratch — no image, no VLM. Lands in 'extracted' state
        so the user can review/edit/finalize through the existing UI.
        """
        bill_id = uuid.uuid4()
        await self._bills.create(
            bill_id=bill_id,
            user_id=user.id,
            image_path="",
            content_hash="",
            mime_type="",
            byte_size=0,
            status=STATUS_EXTRACTED,
        )
        bill = await self._bills.get_with_items(bill_id)
        if bill is None:
            raise RuntimeError("bill disappeared after create")
        bill.merchant = fields.merchant
        bill.total = _to_decimal(fields.total)
        bill.currency = fields.currency
        bill.billed_at = fields.billed_at
        bill.category = fields.category
        bill.extracted_at = _utcnow()
        await self._session.commit()
        loaded = await self._bills.get_with_items(bill_id)
        if loaded is None:
            raise RuntimeError("bill disappeared after commit")
        return loaded

    async def _get_owned_bill(self, *, bill_id: uuid.UUID, user: User) -> Bill:
        bill = await self._bills.get_with_items(bill_id)
        if bill is None or bill.user_id != user.id:
            raise BillNotFound(str(bill_id))
        return bill

    async def get_bill(self, *, bill_id: uuid.UUID, user: User) -> Bill:
        return await self._get_owned_bill(bill_id=bill_id, user=user)

    async def list_bills(
        self, *, user: User, limit: int, offset: int
    ) -> tuple[list[Bill], int]:
        bills = await self._bills.list_for_user(user.id, limit=limit, offset=offset)
        total = await self._bills.count_for_user(user.id)
        return bills, total

    async def extract_bill(
        self, *, bill_id: uuid.UUID, user: User, vision: VisionService
    ) -> Bill:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))

        image_bytes = await self._storage.read(bill.image_path)
        extraction: RawBillExtraction = await vision.extract_bill(
            image_bytes, language=user.preferred_language
        )

        bill.merchant = extraction.merchant
        bill.total = _to_decimal(extraction.total)
        bill.currency = extraction.currency
        bill.billed_at = extraction.billed_at
        bill.category = extraction.category
        bill.raw_ocr_text = extraction.raw_text
        bill.status = STATUS_EXTRACTED
        bill.extracted_at = _utcnow()

        bill.items.clear()
        await self._session.flush()
        for index, item in enumerate(extraction.items):
            bill.items.append(
                BillItem(
                    position=index,
                    name=item.name,
                    quantity=_to_decimal(item.quantity),
                    unit_price=_to_decimal(item.unit_price),
                    total_price=_to_decimal(item.total_price),
                    category=item.category,
                )
            )

        await self._session.commit()
        return await self._get_owned_bill(bill_id=bill.id, user=user)

    async def update_bill(
        self, *, bill_id: uuid.UUID, user: User, fields: BillUpdateRequest
    ) -> Bill:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))

        data = fields.model_dump(exclude_unset=True)
        if "merchant" in data:
            bill.merchant = data["merchant"]
        if "total" in data:
            bill.total = _to_decimal(data["total"])
        if "currency" in data:
            bill.currency = data["currency"]
        if "billed_at" in data:
            bill.billed_at = data["billed_at"]
        if "category" in data:
            bill.category = data["category"]

        await self._session.commit()
        return await self._get_owned_bill(bill_id=bill.id, user=user)

    async def add_item(
        self, *, bill_id: uuid.UUID, user: User, item: BillItemCreateRequest
    ) -> Bill:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))

        next_position = await self._bills.max_item_position(bill.id) + 1
        bill.items.append(
            BillItem(
                position=next_position,
                name=item.name,
                quantity=_to_decimal(item.quantity),
                unit_price=_to_decimal(item.unit_price),
                total_price=_to_decimal(item.total_price),
                category=item.category,
            )
        )
        _recompute_total(bill)
        await self._session.commit()
        return await self._get_owned_bill(bill_id=bill.id, user=user)

    async def update_item(
        self,
        *,
        bill_id: uuid.UUID,
        item_id: uuid.UUID,
        user: User,
        fields: BillItemUpdateRequest,
    ) -> Bill:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))

        item = await self._bills.get_item(item_id)
        if item is None or item.bill_id != bill.id:
            raise BillItemNotFound(str(item_id))

        data = fields.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            item.name = data["name"]
        if "quantity" in data:
            item.quantity = _to_decimal(data["quantity"])
        if "unit_price" in data:
            item.unit_price = _to_decimal(data["unit_price"])
        if "total_price" in data:
            item.total_price = _to_decimal(data["total_price"])
        if "category" in data:
            item.category = data["category"]

        _recompute_total(bill)
        await self._session.commit()
        return await self._get_owned_bill(bill_id=bill.id, user=user)

    async def delete_item(
        self, *, bill_id: uuid.UUID, item_id: uuid.UUID, user: User
    ) -> Bill:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))

        target = next((i for i in bill.items if i.id == item_id), None)
        if target is None:
            raise BillItemNotFound(str(item_id))

        bill.items.remove(target)
        _recompute_total(bill)
        await self._session.commit()
        return await self._get_owned_bill(bill_id=bill.id, user=user)

    async def delete_bill(self, *, bill_id: uuid.UUID, user: User) -> None:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        image_path = bill.image_path
        await self._session.delete(bill)
        await self._session.commit()
        if image_path:
            with contextlib.suppress(Exception):
                await self._storage.delete(image_path)

    async def finalize(self, *, bill_id: uuid.UUID, user: User) -> Bill:
        bill = await self._get_owned_bill(bill_id=bill_id, user=user)
        if bill.status == STATUS_REVIEWED:
            raise BillNotEditable(str(bill_id))
        if bill.status != STATUS_EXTRACTED:
            raise BillNotExtracted(str(bill_id))

        bill.status = STATUS_REVIEWED
        bill.reviewed_at = _utcnow()
        await self._session.commit()
        return await self._get_owned_bill(bill_id=bill.id, user=user)
