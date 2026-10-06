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
    progress: int = 0,
) -> Goal:
    """Create a new goal for a user."""

    p = max(0, min(100, int(progress)))
    goal = Goal(
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        target_date=target_date,
        progress=p,
        is_completed=(p >= 100),
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

    if "progress" in updates and updates["progress"] is not None:
        p = max(0, min(100, int(updates["progress"])))
        updates["progress"] = p
        if "is_completed" not in updates or updates["is_completed"] is None:
            updates["is_completed"] = (p >= 100)
    elif "is_completed" in updates and updates["is_completed"] is not None:
        if updates["is_completed"] and goal.progress < 100:
            updates["progress"] = 100
        elif not updates["is_completed"] and goal.progress >= 100:
            updates["progress"] = 0

    for field, value in updates.items():
        if value is not None and hasattr(goal, field):
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