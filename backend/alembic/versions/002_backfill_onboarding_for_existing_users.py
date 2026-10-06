"""backfill onboarding_completed for accounts that predate Phase 8

Revision ID: 002_backfill_onboarding
Revises: 001_add_onboarding_fields
Create Date: 2026-10-04 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '002_backfill_onboarding'
down_revision: Union[str, Sequence[str], None] = '001_add_onboarding_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Mark every pre-existing account as already onboarded.

    001 added the column with `server_default='false'`, so the backfill would
    otherwise leave every account created before Phase 8 reading "not
    onboarded" — and each of them would be shown the brand-new-user flow on
    their next login, including users with real tasks, goals and habits. That
    is precisely the regression Phase 8 must not introduce, so the flag is
    corrected here for rows that already existed when this revision runs.

    Accounts registered *after* this revision are unaffected: they are created
    with the model's own default of False and are meant to see onboarding.

    This runs immediately after 001 in the same `alembic upgrade head`, so
    "rows present now" is exactly "rows that predate Phase 8".
    """

    op.execute(
        """
        UPDATE user_preferences
        SET onboarding_completed = TRUE
        WHERE onboarding_completed = FALSE
        """
    )


def downgrade() -> None:
    """
    Nothing to undo.

    The original per-account onboarding state of accounts that predate Phase 8
    is unknowable — the column did not exist — so reversing this would
    fabricate state rather than restore it. Leaving the flags set is the only
    honest reversal, and it is also the safe one: a user marked onboarded is
    never trapped, whereas a user wrongly marked not-onboarded would be shown
    a first-time flow they have long since finished.
    """

    pass