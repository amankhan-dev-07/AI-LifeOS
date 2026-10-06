from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.planner_event import PlannerEvent


def create_event(
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
    """Create a new planner event for a user."""

    event = PlannerEvent(
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

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


def get_event_by_id(
    db: Session,
    event_id: int,
    user_id: int,
) -> PlannerEvent | None:
    """Get a specific planner event belonging to a user."""

    statement = select(PlannerEvent).where(
        PlannerEvent.id == event_id,
        PlannerEvent.user_id == user_id,
    )

    return db.scalar(statement)


def get_events_by_user(
    db: Session,
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    event_type: str | None = None,
    is_completed: bool | None = None,
) -> list[PlannerEvent]:
    """Get planner events belonging to a user with optional filters."""

    statement = select(PlannerEvent).where(
        PlannerEvent.user_id == user_id,
    )

    if start_date is not None:
        statement = statement.where(
            PlannerEvent.event_date >= start_date,
        )

    if end_date is not None:
        statement = statement.where(
            PlannerEvent.event_date <= end_date,
        )

    if event_type is not None:
        statement = statement.where(
            PlannerEvent.event_type == event_type,
        )

    if is_completed is not None:
        statement = statement.where(
            PlannerEvent.is_completed == is_completed,
        )

    statement = statement.order_by(
        PlannerEvent.event_date.asc(),
        PlannerEvent.start_time.asc(),
        PlannerEvent.id.asc(),
    )

    return list(db.scalars(statement).all())


def get_events_by_date(
    db: Session,
    user_id: int,
    event_date: datetime,
) -> list[PlannerEvent]:
    """Get planner events for a user on a specific calendar date."""

    day_start = event_date.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999999)

    return get_events_by_user(
        db=db,
        user_id=user_id,
        start_date=day_start,
        end_date=day_end,
    )


def update_event(
    db: Session,
    event: PlannerEvent,
    **updates,
) -> PlannerEvent:
    """Update an existing planner event."""

    for field, value in updates.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    return event


def delete_event(
    db: Session,
    event: PlannerEvent,
) -> None:
    """Delete an existing planner event."""

    db.delete(event)
    db.commit()