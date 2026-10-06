from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reminder import Reminder


def create_reminder(
    db: Session,
    user_id: int,
    title: str,
    message: str | None,
    remind_at: datetime,
    task_id: int | None,
    habit_id: int | None,
    planner_event_id: int | None,
) -> Reminder:
    """Create a new reminder for a user."""

    reminder = Reminder(
        user_id=user_id,
        title=title,
        message=message,
        remind_at=remind_at,
        task_id=task_id,
        habit_id=habit_id,
        planner_event_id=planner_event_id,
    )

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return reminder


def get_reminder_by_id(
    db: Session,
    reminder_id: int,
    user_id: int,
) -> Reminder | None:
    """Get a specific reminder belonging to a user."""

    statement = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == user_id,
    )

    return db.scalar(statement)


def get_reminders_by_user(
    db: Session,
    user_id: int,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Reminder]:
    """
    Get reminders belonging to a user with optional filters.

    Ordering is deterministic — soonest reminder first, id as tiebreaker — so
    the UI never reshuffles between identical polls.
    """

    statement = select(Reminder).where(
        Reminder.user_id == user_id,
    )

    if status is not None:
        statement = statement.where(
            Reminder.status == status,
        )

    if start_date is not None:
        statement = statement.where(
            Reminder.remind_at >= start_date,
        )

    if end_date is not None:
        statement = statement.where(
            Reminder.remind_at <= end_date,
        )

    statement = statement.order_by(
        Reminder.remind_at.asc(),
        Reminder.id.asc(),
    )

    return list(db.scalars(statement).all())


def update_reminder(
    db: Session,
    reminder: Reminder,
    **updates,
) -> Reminder:
    """Update an existing reminder."""

    for field, value in updates.items():
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)

    return reminder


def delete_reminder(
    db: Session,
    reminder: Reminder,
) -> None:
    """Delete an existing reminder."""

    db.delete(reminder)
    db.commit()


def get_due_reminders(
    db: Session,
    now: datetime,
    limit: int = 100,
) -> list[Reminder]:
    """
    Get pending reminders whose time has come, oldest first.

    This is the scheduler's only query. It is scoped to `status = 'pending'`
    so the composite (status, remind_at) index keeps the scan proportional to
    the number of *due* reminders rather than the size of the table.

    `notified_at IS NULL` is a second guard against duplicate delivery: a
    reminder already handed to the notification engine is skipped even if its
    status was reset to pending.
    """

    statement = (
        select(Reminder)
        .where(
            Reminder.status == "pending",
            Reminder.remind_at <= now,
            Reminder.notified_at.is_(None),
        )
        .order_by(
            Reminder.remind_at.asc(),
            Reminder.id.asc(),
        )
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def count_due_reminders(
    db: Session,
    now: datetime,
) -> int:
    """Count pending, due reminders — used by the scheduler's logging only."""

    statement = select(Reminder.id).where(
        Reminder.status == "pending",
        Reminder.remind_at <= now,
        Reminder.notified_at.is_(None),
    )

    return len(db.scalars(statement).all())
