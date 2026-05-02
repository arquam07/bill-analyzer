from datetime import date

from pydantic import BaseModel, Field, field_validator

from src.core.constants import BILL_CATEGORIES


class LineItem(BaseModel):
    name: str
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None
    category: str | None = None


class RawBillExtraction(BaseModel):
    merchant: str | None = None
    total: float | None = None
    currency: str | None = None
    billed_at: date | None = None
    category: str | None = None
    items: list[LineItem] = Field(default_factory=list)
    raw_text: str | None = None

    @field_validator("category")
    @classmethod
    def category_supported(cls, v: str | None) -> str | None:
        # VLM may emit a value not in our enum — treat as null rather than fail extraction.
        if v is None or v not in BILL_CATEGORIES:
            return None
        return v
