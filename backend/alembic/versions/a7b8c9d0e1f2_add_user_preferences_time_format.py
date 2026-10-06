"""add user_preferences.time_format

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-03 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Additive only: existing rows keep all their data and receive the
    # '24h' default, which the column's server_default backfills for them.
    op.add_column(
        'user_preferences',
        sa.Column(
            'time_format',
            sa.String(length=5),
            nullable=False,
            server_default='24h',
        ),
    )

    # Existing rows that stored an empty or unusable timezone fall back to
    # the product default. Rows with a valid IANA name are left untouched.
    op.execute(
        """
        UPDATE user_preferences
        SET timezone = 'Asia/Kolkata'
        WHERE timezone IS NULL
           OR btrim(timezone) = ''
           OR timezone NOT IN (
                'UTC',
                'America/Los_Angeles', 'America/Denver', 'America/Chicago',
                'America/New_York', 'Europe/London', 'Europe/Berlin',
                'Asia/Dubai', 'Asia/Kolkata', 'Asia/Singapore',
                'Asia/Tokyo', 'Australia/Sydney'
           )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_preferences', 'time_format')