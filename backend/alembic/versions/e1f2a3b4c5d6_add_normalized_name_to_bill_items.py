"""add normalized_name to bill_items

Revision ID: e1f2a3b4c5d6
Revises: a1b2c3d4e5f6
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bill_items",
        sa.Column("normalized_name", sa.String(256), nullable=True),
    )
    op.create_index(
        "ix_bill_items_normalized_name", "bill_items", ["normalized_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_bill_items_normalized_name", table_name="bill_items")
    op.drop_column("bill_items", "normalized_name")
