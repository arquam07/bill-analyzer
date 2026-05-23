"""google_oauth

Revision ID: c7d8e9f0a1b2
Revises: 584619657d97
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "584619657d97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_id", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_column("users", "google_id")
