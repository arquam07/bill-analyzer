"""settlement_requests

Revision ID: f1a2b3c4d5e6
Revises: c7d8e9f0a1b2
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "split_settlements",
        sa.Column(
            "initiated_by_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "split_settlements",
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="accepted",
        ),
    )
    op.add_column(
        "split_settlements",
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill: existing rows were direct settlements created by from_user.
    op.execute(
        "UPDATE split_settlements SET initiated_by_user_id = from_user_id "
        "WHERE initiated_by_user_id IS NULL"
    )
    op.alter_column("split_settlements", "initiated_by_user_id", nullable=False)
    op.create_index(
        "ix_split_settlements_initiated_by_user_id",
        "split_settlements",
        ["initiated_by_user_id"],
    )
    # Drop the default for status — new rows must specify pending or accepted explicitly.
    op.alter_column("split_settlements", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_split_settlements_initiated_by_user_id", table_name="split_settlements")
    op.drop_column("split_settlements", "responded_at")
    op.drop_column("split_settlements", "status")
    op.drop_column("split_settlements", "initiated_by_user_id")
