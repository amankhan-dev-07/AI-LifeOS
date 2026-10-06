"""create reminders table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('remind_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_cancelled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('habit_id', sa.Integer(), nullable=True),
        sa.Column('planner_event_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        # Ownership cascades; cross-domain links are cleared instead, so
        # deleting a task/habit/event never destroys the user's reminder.
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['habit_id'], ['habits.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['planner_event_id'], ['planner_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reminders_id', 'reminders', ['id'], unique=False)
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'], unique=False)
    op.create_index('ix_reminders_task_id', 'reminders', ['task_id'], unique=False)
    op.create_index('ix_reminders_habit_id', 'reminders', ['habit_id'], unique=False)
    op.create_index('ix_reminders_planner_event_id', 'reminders', ['planner_event_id'], unique=False)
    # Backs the scheduler's due query and per-user ordering.
    op.create_index('ix_reminders_status_remind_at', 'reminders', ['status', 'remind_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_reminders_status_remind_at', table_name='reminders')
    op.drop_index('ix_reminders_planner_event_id', table_name='reminders')
    op.drop_index('ix_reminders_habit_id', table_name='reminders')
    op.drop_index('ix_reminders_task_id', table_name='reminders')
    op.drop_index('ix_reminders_user_id', table_name='reminders')
    op.drop_index('ix_reminders_id', table_name='reminders')
    op.drop_table('reminders')
