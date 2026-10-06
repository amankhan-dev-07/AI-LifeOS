from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.planner_event import PlannerEvent
from app.repositories.planner_event_repository import (
    create_event,
    delete_event,
    get_event_by_id,
    get_events_by_date,
    get_events_by_user,
    update_event,
)

PLANNER_EVENT_TYPES = (
    "task",
    "habit",
    "focus_block",
    "custom",
)


def validate_event_type(event_type: str) -> str:
    """Ensure an event type is one of the supported planner values."""

    if event_type not in PLANNER_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid planner event type.",
        )

    return event_type


def get_user_event(
    db: Session,
    event_id: int,
    user_id: int,
) -> PlannerEvent:
    """Get one planner event belonging to the current user."""

    event = get_event_by_id(
        db=db,
        event_id=event_id,
        user_id=user_id,
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planner event not found.",
        )

    return event


def create_user_event(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    event_date: datetime,
    start_time: datetime,
    end_time: datetime,
    event_type: str,
    task_id: int | None,
    habit_id: int | None,
) -> PlannerEvent:
    """Create a planner event for the current user."""

    validate_event_type(event_type)

    return create_event(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        event_type=event_type,
        task_id=task_id,
        habit_id=habit_id,
    )


def get_user_events(
    db: Session,
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    event_type: str | None = None,
    is_completed: bool | None = None,
) -> list[PlannerEvent]:
    """Get planner events belonging to the current user."""

    if event_type is not None:
        validate_event_type(event_type)

    return get_events_by_user(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        is_completed=is_completed,
    )


def get_user_events_for_date(
    db: Session,
    user_id: int,
    event_date: datetime,
) -> list[PlannerEvent]:
    """Get the current user's planner events for a single date."""

    return get_events_by_date(
        db=db,
        user_id=user_id,
        event_date=event_date,
    )


def update_user_event(
    db: Session,
    user_id: int,
    event_id: int,
    **updates,
) -> PlannerEvent:
    """Update a planner event belonging to the current user."""

    event = get_user_event(
        db=db,
        event_id=event_id,
        user_id=user_id,
    )

    if "event_type" in updates and updates["event_type"] is not None:
        validate_event_type(updates["event_type"])

    return update_event(
        db=db,
        event=event,
        **updates,
    )


def delete_user_event(
    db: Session,
    user_id: int,
    event_id: int,
) -> None:
    """Delete a planner event belonging to the current user."""

    event = get_user_event(
        db=db,
        event_id=event_id,
        user_id=user_id,
    )

    delete_event(
        db=db,
        event=event,
    )