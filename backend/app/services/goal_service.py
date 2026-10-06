from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.repositories.goal_repository import (
    create_goal,
    delete_goal,
    get_goal_by_id,
    get_goals_by_user,
    update_goal,
)


def create_user_goal(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    category: str,
    target_date,
    progress: int = 0,
) -> Goal:
    """Create a goal for the current user."""

    return create_goal(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        target_date=target_date,
        progress=progress,
    )


def get_user_goals(
    db: Session,
    user_id: int,
) -> list[Goal]:
    """Get all goals belonging to the current user."""

    return get_goals_by_user(
        db=db,
        user_id=user_id,
    )


def get_user_goal(
    db: Session,
    goal_id: int,
    user_id: int,
) -> Goal | None:
    """Get one goal belonging to the current user."""

    return get_goal_by_id(
        db=db,
        goal_id=goal_id,
        user_id=user_id,
    )


def update_user_goal(
    db: Session,
    goal: Goal,
    **updates,
) -> Goal:
    """Update a goal belonging to the current user."""

    return update_goal(
        db=db,
        goal=goal,
        **updates,
    )


def delete_user_goal(
    db: Session,
    goal: Goal,
) -> None:
    """Delete a goal belonging to the current user."""

    delete_goal(
        db=db,
        goal=goal,
    )