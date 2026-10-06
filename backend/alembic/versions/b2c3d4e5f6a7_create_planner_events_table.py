"""create planner_events table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-03 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'planner_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False, server_default='task'),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('habit_id', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['task_id'],
            ['tasks.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['habit_id'],
            ['habits.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_planner_events_id', 'planner_events', ['id'], unique=False)
    op.create_index('ix_planner_events_user_id', 'planner_events', ['user_id'], unique=False)
    op.create_index('ix_planner_events_user_date', 'planner_events', ['user_id', 'event_date'], unique=False)
    op.create_index('ix_planner_events_task_id', 'planner_events', ['task_id'], unique=False)
    op.create_index('ix_planner_events_habit_id', 'planner_events', ['habit_id'], unique=False)
    op.create_index('ix_planner_events_is_completed', 'planner_events', ['is_completed'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_planner_events_is_completed', table_name='planner_events')
    op.drop_index('ix_planner_events_habit_id', table_name='planner_events')
    op.drop_index('ix_planner_events_task_id', table_name='planner_events')
    op.drop_index('ix_planner_events_user_date', table_name='planner_events')
    op.drop_index('ix_planner_events_user_id', table_name='planner_events')
    op.drop_index('ix_planner_events_id', table_name='planner_events')
    op.drop_table('planner_events')