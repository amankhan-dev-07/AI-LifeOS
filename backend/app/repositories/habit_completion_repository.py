from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.habit_completion import HabitCompletion


def create_completion(
    db: Session,
    habit_id: int,
    completed_date: date,
) -> HabitCompletion:
    """Create a completion record for a habit."""

    completion = HabitCompletion(
        habit_id=habit_id,
        completed_date=completed_date,
    )

    db.add(completion)
    db.commit()
    db.refresh(completion)

    return completion


def get_completion_by_date(
    db: Session,
    habit_id: int,
    completed_date: date,
) -> HabitCompletion | None:
    """Get a completion record for a specific habit and date."""

    statement = select(HabitCompletion).where(
        HabitCompletion.habit_id == habit_id,
        HabitCompletion.completed_date == completed_date,
    )

    return db.scalar(statement)


def get_completions_by_habit(
    db: Session,
    habit_id: int,
) -> list[HabitCompletion]:
    """Get all completion records for a habit."""

    statement = (
        select(HabitCompletion)
        .where(HabitCompletion.habit_id == habit_id)
        .order_by(HabitCompletion.completed_date.desc())
    )

    return list(db.scalars(statement).all())


def delete_completion(
    db: Session,
    completion: HabitCompletion,
) -> None:
    """Delete a completion record."""

    db.delete(completion)
    db.commit()