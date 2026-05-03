"""add friendships and deferred split requests

Revision ID: a1b2c3d4e5f6
Revises: d4f2c1e87b50
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd4f2c1e87b50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'friendships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('requester_id', sa.UUID(), nullable=False),
        sa.Column('addressee_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['addressee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_friendships_requester_id'), 'friendships', ['requester_id'], unique=False)
    op.create_index(op.f('ix_friendships_addressee_id'), 'friendships', ['addressee_id'], unique=False)

    op.create_table(
        'deferred_split_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('friendship_id', sa.UUID(), nullable=False),
        sa.Column('bill_id', sa.UUID(), nullable=False),
        sa.Column('from_user_id', sa.UUID(), nullable=False),
        sa.Column('to_user_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('bill_item_ids', JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['friendship_id'], ['friendships.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_deferred_split_requests_friendship_id'), 'deferred_split_requests', ['friendship_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_deferred_split_requests_friendship_id'), table_name='deferred_split_requests')
    op.drop_table('deferred_split_requests')
    op.drop_index(op.f('ix_friendships_addressee_id'), table_name='friendships')
    op.drop_index(op.f('ix_friendships_requester_id'), table_name='friendships')
    op.drop_table('friendships')
