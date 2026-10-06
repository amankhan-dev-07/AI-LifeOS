"""reconcile goals progress column

Revision ID: e8d2c1b94a10
Revises: db3f31b5979d
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8d2c1b94a10'
down_revision: Union[str, Sequence[str], None] = 'db3f31b5979d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - reconcile goals.progress column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('goals')]

    if 'progress' not in columns:
        op.add_column(
            'goals',
            sa.Column(
                'progress',
                sa.Integer(),
                nullable=False,
                server_default='0',
            ),
        )
        op.execute("UPDATE goals SET progress = 100 WHERE is_completed = true")
        op.execute("UPDATE goals SET progress = 0 WHERE is_completed = false")


def downgrade() -> None:
    """Downgrade schema - remove goals.progress column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('goals')]

    if 'progress' in columns:
        op.drop_column('goals', 'progress')
