from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_preferences import UserPreferences


def get_preferences_by_user(
    db: Session,
    user_id: int,
) -> UserPreferences | None:
    """Get the preference row belonging to a user."""

    statement = select(UserPreferences).where(
        UserPreferences.user_id == user_id,
    )

    return db.scalar(statement)


def create_preferences(
    db: Session,
    user_id: int,
    theme: str,
    daily_briefing_enabled: bool,
    security_alerts_enabled: bool,
    planner_start_hour: int,
    timezone: str,
    time_format: str,
) -> UserPreferences:
    """Create the preference row for a user."""

    preferences = UserPreferences(
        user_id=user_id,
        theme=theme,
        daily_briefing_enabled=daily_briefing_enabled,
        security_alerts_enabled=security_alerts_enabled,
        planner_start_hour=planner_start_hour,
        timezone=timezone,
        time_format=time_format,
    )

    db.add(preferences)
    db.commit()
    db.refresh(preferences)

    return preferences


def update_preferences(
    db: Session,
    preferences: UserPreferences,
    **updates,
) -> UserPreferences:
    """Update an existing preference row."""

    for field, value in updates.items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)

    return preferences