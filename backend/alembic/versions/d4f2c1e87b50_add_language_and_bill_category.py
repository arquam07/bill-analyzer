"""add user.preferred_language and bill.category

Revision ID: d4f2c1e87b50
Revises: b3e7a2f9c041
Create Date: 2026-05-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f2c1e87b50'
down_revision: Union[str, Sequence[str], None] = 'b3e7a2f9c041'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('preferred_language', sa.String(length=8), nullable=False, server_default='en'),
    )
    op.add_column(
        'bills',
        sa.Column('category', sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('bills', 'category')
    op.drop_column('users', 'preferred_language')
