from sqlalchemy.orm import Session

from app.models.habit import Habit
from app.repositories.habit_repository import (
    create_habit,
    delete_habit,
    get_habit_by_id,
    get_habits_by_user,
    update_habit,
)


def create_user_habit(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    frequency: str,
    goal_id: int | None = None,
) -> Habit:
    """Create a habit for the current user."""

    return create_habit(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        frequency=frequency,
        goal_id=goal_id,
    )


def get_user_habits(
    db: Session,
    user_id: int,
) -> list[Habit]:
    """Get all habits belonging to the current user."""

    return get_habits_by_user(
        db=db,
        user_id=user_id,
    )


def get_user_habit(
    db: Session,
    habit_id: int,
    user_id: int,
) -> Habit | None:
    """Get one habit belonging to the current user."""

    return get_habit_by_id(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )


def update_user_habit(
    db: Session,
    habit: Habit,
    **updates,
) -> Habit:
    """Update a habit belonging to the current user."""

    return update_habit(
        db=db,
        habit=habit,
        **updates,
    )


def delete_user_habit(
    db: Session,
    habit: Habit,
) -> None:
    """Delete a habit belonging to the current user."""

    delete_habit(
        db=db,
        habit=habit,
    )