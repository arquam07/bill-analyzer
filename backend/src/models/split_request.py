import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"


class SplitRequest(Base):
    __tablename__ = "split_requests"
    __table_args__ = (
        UniqueConstraint(
            "bill_id", "from_user_id", "to_user_id", name="uq_split_request_bill_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=STATUS_PENDING
    )
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    from_user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[from_user_id]
    )
    to_user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[to_user_id]
    )
    bill: Mapped["Bill"] = relationship("Bill")  # type: ignore[name-defined]
    items: Mapped[list["SplitRequestItem"]] = relationship(
        "SplitRequestItem",
        back_populates="split_request",
        cascade="all, delete-orphan",
    )


class SplitRequestItem(Base):
    __tablename__ = "split_request_items"
    __table_args__ = (
        UniqueConstraint(
            "split_request_id", "bill_item_id", name="uq_sri_request_item"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    split_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bill_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bill_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    split_request: Mapped["SplitRequest"] = relationship(
        "SplitRequest", back_populates="items"
    )
    bill_item: Mapped["BillItem"] = relationship("BillItem")  # type: ignore[name-defined]


class SplitSettlement(Base):
    __tablename__ = "split_settlements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=STATUS_PENDING
    )
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    from_user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[from_user_id]
    )
    to_user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[to_user_id]
    )
    initiated_by: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[initiated_by_user_id]
    )
