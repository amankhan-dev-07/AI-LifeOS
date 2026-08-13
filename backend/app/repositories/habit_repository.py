from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.habit import Habit


def create_habit(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    frequency: str,
) -> Habit:
    """Create a new habit for a user."""

    habit = Habit(
        user_id=user_id,
        title=title,
        description=description,
        frequency=frequency,
    )

    db.add(habit)
    db.commit()
    db.refresh(habit)

    return habit


def get_habits_by_user(
    db: Session,
    user_id: int,
) -> list[Habit]:
    """Get all habits belonging to a user."""

    statement = (
        select(Habit)
        .where(Habit.user_id == user_id)
        .order_by(Habit.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_habit_by_id(
    db: Session,
    habit_id: int,
    user_id: int,
) -> Habit | None:
    """Get a specific habit belonging to a user."""

    statement = select(Habit).where(
        Habit.id == habit_id,
        Habit.user_id == user_id,
    )

    return db.scalar(statement)


def update_habit(
    db: Session,
    habit: Habit,
    **updates,
) -> Habit:
    """Update an existing habit."""

    for field, value in updates.items():
        if value is not None:
            setattr(habit, field, value)

    db.commit()
    db.refresh(habit)

    return habit


def delete_habit(
    db: Session,
    habit: Habit,
) -> None:
    """Delete an existing habit."""

    db.delete(habit)
    db.commit()