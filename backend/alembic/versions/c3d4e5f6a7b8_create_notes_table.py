"""create notes table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-03 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('tag', sa.String(length=50), nullable=False, server_default='General'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('goal_id', sa.Integer(), nullable=True),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['goal_id'],
            ['goals.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['task_id'],
            ['tasks.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notes_id', 'notes', ['id'], unique=False)
    op.create_index('ix_notes_user_id', 'notes', ['user_id'], unique=False)
    op.create_index('ix_notes_user_tag', 'notes', ['user_id', 'tag'], unique=False)
    op.create_index('ix_notes_goal_id', 'notes', ['goal_id'], unique=False)
    op.create_index('ix_notes_task_id', 'notes', ['task_id'], unique=False)
    op.create_index('ix_notes_is_archived', 'notes', ['is_archived'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notes_is_archived', table_name='notes')
    op.drop_index('ix_notes_task_id', table_name='notes')
    op.drop_index('ix_notes_goal_id', table_name='notes')
    op.drop_index('ix_notes_user_tag', table_name='notes')
    op.drop_index('ix_notes_user_id', table_name='notes')
    op.drop_index('ix_notes_id', table_name='notes')
    op.drop_table('notes')