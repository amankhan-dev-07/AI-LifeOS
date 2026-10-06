from sqlalchemy.orm import Session

from app.models.task import Task
from app.repositories.task_repository import (
    create_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_user,
    update_task,
)


def create_user_task(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    status: str,
    priority: str,
    due_date,
    goal_id: int | None = None,
    estimated_minutes: int = 45,
) -> Task:
    """Create a task for the current user."""

    return create_task(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        goal_id=goal_id,
        estimated_minutes=estimated_minutes,
    )


def get_user_tasks(
    db: Session,
    user_id: int,
) -> list[Task]:
    """Get all tasks belonging to the current user."""

    return get_tasks_by_user(
        db=db,
        user_id=user_id,
    )


def get_user_task(
    db: Session,
    task_id: int,
    user_id: int,
) -> Task | None:
    """Get one task belonging to the current user."""

    return get_task_by_id(
        db=db,
        task_id=task_id,
        user_id=user_id,
    )


def update_user_task(
    db: Session,
    task: Task,
    **updates,
) -> Task:
    """Update a task belonging to the current user."""

    return update_task(
        db=db,
        task=task,
        **updates,
    )


def delete_user_task(
    db: Session,
    task: Task,
) -> None:
    """Delete a task belonging to the current user."""

    delete_task(
        db=db,
        task=task,
    )