from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal


def create_goal(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    category: str,
    target_date,
) -> Goal:
    """Create a new goal for a user."""

    goal = Goal(
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        target_date=target_date,
    )

    db.add(goal)
    db.commit()
    db.refresh(goal)

    return goal


def get_goals_by_user(
    db: Session,
    user_id: int,
) -> list[Goal]:
    """Get all goals belonging to a user."""

    statement = (
        select(Goal)
        .where(Goal.user_id == user_id)
        .order_by(Goal.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_goal_by_id(
    db: Session,
    goal_id: int,
    user_id: int,
) -> Goal | None:
    """Get a specific goal belonging to a user."""

    statement = select(Goal).where(
        Goal.id == goal_id,
        Goal.user_id == user_id,
    )

    return db.scalar(statement)


def update_goal(
    db: Session,
    goal: Goal,
    **updates,
) -> Goal:
    """Update an existing goal."""

    for field, value in updates.items():
        if value is not None:
            setattr(goal, field, value)

    db.commit()
    db.refresh(goal)

    return goal


def delete_goal(
    db: Session,
    goal: Goal,
) -> None:
    """Delete an existing goal."""

    db.delete(goal)
    db.commit()