from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timezones import (
    DEFAULT_TIMEZONE,
    is_valid_timezone,
    normalize_timezone,
)
from app.models.user_preferences import UserPreferences
from app.repositories.user_preferences_repository import (
    create_preferences,
    get_preferences_by_user,
    update_preferences,
)

DEFAULT_THEME = "dark"
DEFAULT_PLANNER_START_HOUR = 8

TIME_FORMAT_12H = "12h"
TIME_FORMAT_24H = "24h"
VALID_TIME_FORMATS = (TIME_FORMAT_12H, TIME_FORMAT_24H)
DEFAULT_TIME_FORMAT = TIME_FORMAT_24H

__all__ = [
    "DEFAULT_THEME",
    "DEFAULT_PLANNER_START_HOUR",
    "DEFAULT_TIMEZONE",
    "DEFAULT_TIME_FORMAT",
    "VALID_TIME_FORMATS",
    "is_valid_timezone",
    "normalize_time_format",
    "normalize_timezone",
    "get_or_create_user_preferences",
    "update_user_preferences",
]


def normalize_time_format(time_format: str | None) -> str:
    """Coerce a stored time format into one of the two supported values."""

    if time_format in VALID_TIME_FORMATS:
        return time_format

    return DEFAULT_TIME_FORMAT


def get_or_create_user_preferences(
    db: Session,
    user_id: int,
) -> UserPreferences:
    """Get the current user's preferences, creating defaults when absent."""

    preferences = get_preferences_by_user(
        db=db,
        user_id=user_id,
    )

    if preferences:
        # Repair legacy rows in place so a stale timezone never reaches the
        # datetime layer. This also backfills `time_format` on rows written
        # before that column existed.
        changed = False

        normalized_timezone = normalize_timezone(preferences.timezone)
        if normalized_timezone != preferences.timezone:
            preferences.timezone = normalized_timezone
            changed = True

        normalized_format = normalize_time_format(preferences.time_format)
        if normalized_format != preferences.time_format:
            preferences.time_format = normalized_format
            changed = True

        if changed:
            db.commit()
            db.refresh(preferences)

        return preferences

    try:
        return create_preferences(
            db=db,
            user_id=user_id,
            theme=DEFAULT_THEME,
            daily_briefing_enabled=True,
            security_alerts_enabled=True,
            planner_start_hour=DEFAULT_PLANNER_START_HOUR,
            timezone=DEFAULT_TIMEZONE,
            time_format=DEFAULT_TIME_FORMAT,
        )
    except IntegrityError:
        # Another request created the row first; the unique
        # constraint on user_id makes that row authoritative.
        db.rollback()

        preferences = get_preferences_by_user(
            db=db,
            user_id=user_id,
        )

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Preferences could not be created.",
            )

        return preferences


def update_user_preferences(
    db: Session,
    user_id: int,
    **updates,
) -> UserPreferences:
    """Update the current user's preferences."""

    preferences = get_or_create_user_preferences(
        db=db,
        user_id=user_id,
    )

    # Validate before writing so an unknown IANA name or format is rejected
    # with a 400 rather than silently persisted and repaired on the next read.
    if "timezone" in updates and updates["timezone"] is not None:
        candidate = updates["timezone"].strip()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timezone cannot be empty. Use an IANA name such as Asia/Kolkata.",
            )

        if not is_valid_timezone(candidate):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown timezone. Use an IANA name such as Asia/Kolkata.",
            )

        updates["timezone"] = candidate

    if "time_format" in updates and updates["time_format"] is not None:
        if updates["time_format"] not in VALID_TIME_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"time_format must be one of: {', '.join(VALID_TIME_FORMATS)}.",
            )

    return update_preferences(
        db=db,
        preferences=preferences,
        **updates,
    )