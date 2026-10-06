"""create transactions table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-03 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='General'),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'], unique=False)
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'], unique=False)
    op.create_index('ix_transactions_user_date', 'transactions', ['user_id', 'transaction_date'], unique=False)
    op.create_index('ix_transactions_user_type', 'transactions', ['user_id', 'type'], unique=False)
    op.create_index('ix_transactions_category', 'transactions', ['category'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_transactions_category', table_name='transactions')
    op.drop_index('ix_transactions_user_type', table_name='transactions')
    op.drop_index('ix_transactions_user_date', table_name='transactions')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    op.drop_index('ix_transactions_id', table_name='transactions')
    op.drop_table('transactions')