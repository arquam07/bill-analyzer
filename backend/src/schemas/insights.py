from datetime import date
from typing import Literal

from pydantic import BaseModel

Granularity = Literal["day", "week", "month"]
Dimension = Literal["category", "merchant"]
ItemOrderBy = Literal["spend", "frequency"]


class InsightsOverviewResponse(BaseModel):
    range_from: date
    range_to: date
    total_spend: float
    bill_count: int
    avg_bill: float
    top_category: str | None = None
    top_merchant: str | None = None
    prev_total_spend: float
    spend_delta_pct: float | None = None
    bills_missing_date: int = 0


class TimeseriesPoint(BaseModel):
    period: date
    total: float
    count: int


class InsightsTimeseriesResponse(BaseModel):
    range_from: date
    range_to: date
    granularity: Granularity
    points: list[TimeseriesPoint]


class BreakdownRow(BaseModel):
    label: str
    total: float
    count: int


class InsightsBreakdownResponse(BaseModel):
    range_from: date
    range_to: date
    dimension: Dimension
    rows: list[BreakdownRow]


class TopItem(BaseModel):
    name: str
    normalized_name: str
    total_spend: float
    purchase_count: int
    last_purchased: date | None = None


class InsightsTopItemsResponse(BaseModel):
    range_from: date
    range_to: date
    order_by: ItemOrderBy
    rows: list[TopItem]


class ItemTimeseriesPoint(BaseModel):
    period: date
    total: float
    count: int


class ItemTimeseriesResponse(BaseModel):
    normalized_name: str
    range_from: date
    range_to: date
    granularity: Granularity
    total_spend: float
    purchase_count: int
    points: list[ItemTimeseriesPoint]
