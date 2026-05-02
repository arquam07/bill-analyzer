"""add_split_request_items

Revision ID: b3e7a2f9c041
Revises: cad8c8900b73
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3e7a2f9c041'
down_revision: Union[str, Sequence[str], None] = 'cad8c8900b73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'split_request_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('split_request_id', sa.UUID(), nullable=False),
        sa.Column('bill_item_id', sa.UUID(), nullable=False),
        sa.Column('share_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['split_request_id'], ['split_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bill_item_id'], ['bill_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('split_request_id', 'bill_item_id', name='uq_sri_request_item'),
    )
    op.create_index(
        op.f('ix_split_request_items_split_request_id'),
        'split_request_items',
        ['split_request_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_split_request_items_bill_item_id'),
        'split_request_items',
        ['bill_item_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_split_request_items_bill_item_id'), table_name='split_request_items')
    op.drop_index(op.f('ix_split_request_items_split_request_id'), table_name='split_request_items')
    op.drop_table('split_request_items')
