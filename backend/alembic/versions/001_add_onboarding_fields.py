"""add onboarding fields to user_preferences

Revision ID: 001_add_onboarding_fields
Revises: a7b8c9d0e1f2
Create Date: 2026-10-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_add_onboarding_fields'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add onboarding_completed with server default false
    op.add_column(
        'user_preferences',
        sa.Column(
            'onboarding_completed',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )

    # Add onboarding_version with server default 1
    op.add_column(
        'user_preferences',
        sa.Column(
            'onboarding_version',
            sa.Integer(),
            nullable=False,
            server_default='1',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_preferences', 'onboarding_version')
    op.drop_column('user_preferences', 'onboarding_completed')