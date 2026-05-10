import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.constants import BILL_CATEGORIES


class BillItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bill_id: uuid.UUID
    position: int
    name: str
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    category: str | None = None


class BillSummaryResponse(BaseModel):
    """List view — no items, no raw_ocr_text."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    image_path: str
    mime_type: str
    byte_size: int
    status: str
    merchant: str | None = None
    total: float | None = None
    currency: str | None = None
    billed_at: date | None = None
    category: str | None = None
    extracted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class BillResponse(BillSummaryResponse):
    """Detail view — includes items and raw OCR text."""

    content_hash: str
    raw_ocr_text: str | None = None
    items: list[BillItemResponse] = Field(default_factory=list)


class BillListResponse(BaseModel):
    items: list[BillSummaryResponse]
    limit: int
    offset: int
    total: int


def _validate_optional_category(v: str | None) -> str | None:
    if v is None:
        return None
    if v not in BILL_CATEGORIES:
        raise ValueError(f"category must be one of {BILL_CATEGORIES}")
    return v


class BillUpdateRequest(BaseModel):
    merchant: str | None = None
    total: float | None = None
    currency: str | None = None
    billed_at: date | None = None
    category: str | None = None

    @field_validator("category")
    @classmethod
    def category_supported(cls, v: str | None) -> str | None:
        return _validate_optional_category(v)


class BillManualCreateRequest(BaseModel):
    merchant: str | None = Field(default=None, max_length=256)
    total: float | None = None
    currency: str | None = Field(default=None, max_length=8)
    billed_at: date | None = None
    category: str | None = None

    @field_validator("category")
    @classmethod
    def category_supported(cls, v: str | None) -> str | None:
        return _validate_optional_category(v)


class BillItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = Field(default=None, ge=0, le=1)
    category: str | None = Field(default=None, max_length=64)


class BillItemUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = Field(default=None, ge=0, le=1)
    category: str | None = Field(default=None, max_length=64)
