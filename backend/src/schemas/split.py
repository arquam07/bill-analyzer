import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    display_name: str
    settled_at: datetime | None = None


class ParticipantCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)
    user_email: EmailStr | None = None


class ItemShareResponse(BaseModel):
    """Per-item assignment list."""

    bill_item_id: uuid.UUID
    participant_ids: list[uuid.UUID]


class SetItemParticipantsRequest(BaseModel):
    participant_ids: list[uuid.UUID]


class ParticipantTotal(BaseModel):
    """Computed: how much one participant owes."""

    participant_id: uuid.UUID
    display_name: str
    total: float
    settled_at: datetime | None = None


class SplitResponse(BaseModel):
    id: uuid.UUID
    bill_id: uuid.UUID
    created_by_user_id: uuid.UUID
    created_at: datetime
    participants: list[ParticipantResponse]
    item_assignments: list[ItemShareResponse]
    participant_totals: list[ParticipantTotal]
    unassigned_total: float
    bill_total: float
    bill_locked: bool


def round_money(value: Decimal) -> float:
    """Round to two decimals using banker's rounding via Decimal then float-cast."""
    return float(value.quantize(Decimal("0.01")))
