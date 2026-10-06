from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.reminder import Reminder
from app.repositories.habit_repository import get_habit_by_id
from app.repositories.planner_event_repository import get_event_by_id
from app.repositories.reminder_repository import (
    create_reminder,
    delete_reminder,
    get_reminder_by_id,
    get_reminders_by_user,
    update_reminder,
)
from app.repositories.task_repository import get_task_by_id

# Statuses are kept as a small closed set so the scheduler's query and the UI
# badges can never disagree about what "pending" means.
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

VALID_STATUSES = (STATUS_PENDING, STATUS_COMPLETED, STATUS_CANCELLED)

# How far in the past a create may target. A small grace window keeps a
# reminder that becomes due between page render and submit from being
# rejected outright.
CREATE_GRACE_PERIOD_SECONDS = 60


def utcnow() -> datetime:
    """
    The single clock the reminder domain reads.

    The scheduler compares `remind_at` against this value, so validation must
    use the same one — a divergent clock would let a reminder be accepted as
    "future" and then fire immediately.
    """

    return datetime.utcnow()


def to_naive_utc(value: datetime) -> datetime:
    """
    Normalize an incoming datetime to the naive-UTC convention used by every
    timestamp column in this project.

    The browser sends an ISO string that may or may not carry an offset
    (`2026-10-03T09:00:00Z` from `toISOString`, or `2026-10-03T09:00:00+02:00`
    from a `datetime-local` input). An aware value is converted to UTC and
    stripped; a naive value is already UTC by convention and passes through.
    """

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def derive_status(is_completed: bool, is_cancelled: bool) -> str:
    """Collapse the two boolean flags into the single status string."""

    if is_cancelled:
        return STATUS_CANCELLED

    if is_completed:
        return STATUS_COMPLETED

    return STATUS_PENDING


def get_user_reminder(
    db: Session,
    reminder_id: int,
    user_id: int,
) -> Reminder:
    """Get one reminder belonging to the current user."""

    reminder = get_reminder_by_id(
        db=db,
        reminder_id=reminder_id,
        user_id=user_id,
    )

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found.",
        )

    return reminder


def _validate_task(
    db: Session,
    task_id: int | None,
    user_id: int,
) -> int | None:
    if task_id is None:
        return None

    if not get_task_by_id(db=db, task_id=task_id, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return task_id


def _validate_habit(
    db: Session,
    habit_id: int | None,
    user_id: int,
) -> int | None:
    if habit_id is None:
        return None

    if not get_habit_by_id(db=db, habit_id=habit_id, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found.",
        )

    return habit_id


def _validate_planner_event(
    db: Session,
    planner_event_id: int | None,
    user_id: int,
) -> int | None:
    if planner_event_id is None:
        return None

    if not get_event_by_id(
        db=db,
        event_id=planner_event_id,
        user_id=user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planner event not found.",
        )

    return planner_event_id


def create_user_reminder(
    db: Session,
    user_id: int,
    title: str,
    message: str | None,
    remind_at: datetime,
    task_id: int | None = None,
    habit_id: int | None = None,
    planner_event_id: int | None = None,
) -> Reminder:
    """
    Create a reminder for the current user.

    `user_id` always comes from the authenticated session — never from the
    request body — and every cross-domain reference is ownership-checked
    before the row is written.
    """

    normalized_remind_at = to_naive_utc(remind_at)

    if (
        normalized_remind_at
        < utcnow() - timedelta(seconds=CREATE_GRACE_PERIOD_SECONDS)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reminder time must be in the future.",
        )

    validated_task_id = _validate_task(
        db=db,
        task_id=task_id,
        user_id=user_id,
    )
    validated_habit_id = _validate_habit(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )
    validated_event_id = _validate_planner_event(
        db=db,
        planner_event_id=planner_event_id,
        user_id=user_id,
    )

    return create_reminder(
        db=db,
        user_id=user_id,
        title=title.strip(),
        message=message,
        remind_at=normalized_remind_at,
        task_id=validated_task_id,
        habit_id=validated_habit_id,
        planner_event_id=validated_event_id,
    )


def get_user_reminders(
    db: Session,
    user_id: int,
    status_filter: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Reminder]:
    """Get reminders belonging to the current user."""

    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of: {', '.join(VALID_STATUSES)}.",
        )

    return get_reminders_by_user(
        db=db,
        user_id=user_id,
        status=status_filter,
        start_date=to_naive_utc(start_date) if start_date is not None else None,
        end_date=to_naive_utc(end_date) if end_date is not None else None,
    )


def update_user_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
    **updates,
) -> Reminder:
    """
    Update a reminder belonging to the current user.

    An already-due `remind_at` is accepted on update: an overdue pending
    reminder that missed a scheduler tick stays editable, and moving it back
    into the future simply makes it due again.
    """

    reminder = get_user_reminder(
        db=db,
        reminder_id=reminder_id,
        user_id=user_id,
    )

    if "remind_at" in updates and updates["remind_at"] is not None:
        updates["remind_at"] = to_naive_utc(updates["remind_at"])

    if "title" in updates and updates["title"] is not None:
        updates["title"] = updates["title"].strip()

    if "task_id" in updates:
        updates["task_id"] = _validate_task(
            db=db,
            task_id=updates["task_id"],
            user_id=user_id,
        )

    if "habit_id" in updates:
        updates["habit_id"] = _validate_habit(
            db=db,
            habit_id=updates["habit_id"],
            user_id=user_id,
        )

    if "planner_event_id" in updates:
        updates["planner_event_id"] = _validate_planner_event(
            db=db,
            planner_event_id=updates["planner_event_id"],
            user_id=user_id,
        )

    # Changing the schedule re-arms delivery: a reminder that was already
    # notified should notify again at its new time, and a completed one
    # becomes pending again because it is due again.
    if "remind_at" in updates:
        updates["notified_at"] = None
        updates["is_completed"] = False
        updates["is_cancelled"] = False

    if {"is_completed", "is_cancelled"} & updates.keys():
        is_completed = updates.get("is_completed", reminder.is_completed)
        is_cancelled = updates.get("is_cancelled", reminder.is_cancelled)

        # Cancelling wins over completing: they are mutually exclusive states.
        if is_cancelled:
            is_completed = False

        updates["is_completed"] = is_completed
        updates["is_cancelled"] = is_cancelled

    # `status` is derived, never set directly by the client, so it stays in
    # lockstep with the two booleans on every write path.
    if "is_completed" in updates or "is_cancelled" in updates:
        updates["status"] = derive_status(
            updates.get("is_completed", reminder.is_completed),
            updates.get("is_cancelled", reminder.is_cancelled),
        )

    return update_reminder(
        db=db,
        reminder=reminder,
        **updates,
    )


def complete_user_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
) -> Reminder:
    """Mark a reminder as completed."""

    return update_user_reminder(
        db=db,
        user_id=user_id,
        reminder_id=reminder_id,
        is_completed=True,
        is_cancelled=False,
    )


def cancel_user_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
) -> Reminder:
    """Mark a reminder as cancelled."""

    return update_user_reminder(
        db=db,
        user_id=user_id,
        reminder_id=reminder_id,
        is_completed=False,
        is_cancelled=True,
    )


def delete_user_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
) -> None:
    """Delete a reminder belonging to the current user."""

    reminder = get_user_reminder(
        db=db,
        reminder_id=reminder_id,
        user_id=user_id,
    )

    delete_reminder(
        db=db,
        reminder=reminder,
    )
