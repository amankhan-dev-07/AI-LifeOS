"""add user updated_at and task/habit links

Revision ID: a1b2c3d4e5f6
Revises: e8d2c1b94a10
Create Date: 2026-10-03 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e8d2c1b94a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add updated_at to users table with server default
    op.add_column(
        'users',
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
    )

    # Add goal_id to tasks table (nullable, FK to goals, ON DELETE SET NULL)
    op.add_column(
        'tasks',
        sa.Column('goal_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_tasks_goal_id',
        'tasks', 'goals',
        ['goal_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_tasks_goal_id', 'tasks', ['goal_id'], unique=False)

    # Add estimated_minutes to tasks table
    op.add_column(
        'tasks',
        sa.Column(
            'estimated_minutes',
            sa.Integer(),
            nullable=False,
            server_default='45',
        ),
    )

    # Add goal_id to habits table (nullable, FK to goals, ON DELETE SET NULL)
    op.add_column(
        'habits',
        sa.Column('goal_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_habits_goal_id',
        'habits', 'goals',
        ['goal_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_habits_goal_id', 'habits', ['goal_id'], unique=False)

    # Add composite indexes
    op.create_index('ix_tasks_user_status', 'tasks', ['user_id', 'status'], unique=False)
    op.create_index('ix_goals_user_completed', 'goals', ['user_id', 'is_completed'], unique=False)
    op.create_index('ix_habits_user_active', 'habits', ['user_id', 'is_active'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop composite indexes
    op.drop_index('ix_habits_user_active', table_name='habits')
    op.drop_index('ix_goals_user_completed', table_name='goals')
    op.drop_index('ix_tasks_user_status', table_name='tasks')
    op.drop_index('ix_tasks_goal_id', table_name='tasks')
    op.drop_index('ix_habits_goal_id', table_name='habits')

    # Drop foreign keys
    op.drop_constraint('fk_tasks_goal_id', 'tasks', type_='foreignkey')
    op.drop_constraint('fk_habits_goal_id', 'habits', type_='foreignkey')

    # Drop columns
    op.drop_column('habits', 'goal_id')
    op.drop_column('tasks', 'estimated_minutes')
    op.drop_column('tasks', 'goal_id')
    op.drop_column('users', 'updated_at')