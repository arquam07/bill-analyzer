import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class RecipientAssignment(BaseModel):
    username: str
    bill_item_ids: list[uuid.UUID] = Field(min_length=1)


class SplitRequestCreate(BaseModel):
    usernames: list[str] = Field(default=[], max_length=10)
    bill_item_ids: list[uuid.UUID] | None = Field(default=None)
    total_to_split: float | None = Field(default=None, gt=0)
    assignments: list[RecipientAssignment] | None = Field(default=None, max_length=10)
    owner_item_ids: list[uuid.UUID] | None = Field(default=None)

    @model_validator(mode="after")
    def validate_mode(self) -> "SplitRequestCreate":
        has_assignments = bool(self.assignments)
        has_usernames = bool(self.usernames)
        if not has_assignments and not has_usernames:
            raise ValueError("either usernames or assignments must be provided")
        if has_assignments and (self.bill_item_ids is not None or self.total_to_split is not None):
            raise ValueError("assignments cannot be combined with bill_item_ids or total_to_split")
        return self


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


class NonFriendInfo(BaseModel):
    username: str
    amount: float
    bill_item_ids: list[uuid.UUID] | None = None


class SplitRequestListResponse(BaseModel):
    items: list[SplitRequestResponse]
    non_friends: list[NonFriendInfo] = []


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
