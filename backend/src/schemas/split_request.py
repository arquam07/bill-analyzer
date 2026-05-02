import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class SplitRequestCreate(BaseModel):
    usernames: list[str] = Field(min_length=1, max_length=10)
    bill_item_ids: list[uuid.UUID] | None = Field(default=None)
    total_to_split: float | None = Field(default=None, gt=0)


class BillSummary(BaseModel):
    merchant: str | None
    total: float | None
    billed_at: date | None


class SplitRequestResponse(BaseModel):
    id: uuid.UUID
    bill_id: uuid.UUID
    from_username: str
    to_username: str
    amount: float
    status: str
    note: str | None
    created_at: datetime
    responded_at: datetime | None
    bill: BillSummary


class SplitRequestListResponse(BaseModel):
    items: list[SplitRequestResponse]


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    username: str
    name: str | None


class BalanceRow(BaseModel):
    username: str
    user_id: uuid.UUID
    net: float


class BalancesResponse(BaseModel):
    balances: list[BalanceRow]


class SettleRequest(BaseModel):
    username: str
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=256)


class SettlementResponse(BaseModel):
    id: uuid.UUID
    from_username: str
    to_username: str
    amount: float
    note: str | None
    created_at: datetime
