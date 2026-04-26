from datetime import date

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    name: str
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None


class RawBillExtraction(BaseModel):
    merchant: str | None = None
    total: float | None = None
    currency: str | None = None
    billed_at: date | None = None
    items: list[LineItem] = Field(default_factory=list)
    raw_text: str | None = None
