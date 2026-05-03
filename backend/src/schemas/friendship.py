import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeferredSplitInfo(BaseModel):
    bill_id: uuid.UUID
    amount: float = Field(gt=0)
    bill_item_ids: list[uuid.UUID] | None = None


class FriendRequestCreate(BaseModel):
    username: str
    deferred_split: DeferredSplitInfo | None = None


class FriendRequestResponse(BaseModel):
    id: uuid.UUID
    requester_username: str
    addressee_username: str
    status: str
    created_at: datetime
    responded_at: datetime | None


class FriendRequestListResponse(BaseModel):
    items: list[FriendRequestResponse]


class FriendResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    name: str | None


class FriendListResponse(BaseModel):
    friends: list[FriendResponse]
