import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Split(Base):
    __tablename__ = "splits"
    __table_args__ = (UniqueConstraint("bill_id", name="uq_splits_bill_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    participants: Mapped[list["SplitParticipant"]] = relationship(
        "SplitParticipant",
        back_populates="split",
        cascade="all, delete-orphan",
        order_by="SplitParticipant.created_at",
    )
    item_shares: Mapped[list["SplitItemShare"]] = relationship(
        "SplitItemShare",
        back_populates="split",
        cascade="all, delete-orphan",
    )


class SplitParticipant(Base):
    __tablename__ = "split_participants"
    __table_args__ = (
        UniqueConstraint("split_id", "display_name", name="uq_participant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    split_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("splits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    split: Mapped[Split] = relationship("Split", back_populates="participants")


class SplitItemShare(Base):
    __tablename__ = "split_item_shares"
    __table_args__ = (
        UniqueConstraint(
            "bill_item_id", "participant_id", name="uq_item_participant"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    split_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("splits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bill_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bill_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weight: Mapped[Decimal] = mapped_column(
        Numeric(8, 3), nullable=False, default=Decimal("1.000")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    split: Mapped[Split] = relationship("Split", back_populates="item_shares")
