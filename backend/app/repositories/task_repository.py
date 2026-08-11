from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


def create_task(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    status: str,
    priority: str,
    due_date,
) -> Task:
    """Create a new task for a user."""

    task = Task(
        user_id=user_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def get_tasks_by_user(
    db: Session,
    user_id: int,
) -> list[Task]:
    """Get all tasks belonging to a user."""

    statement = (
        select(Task)
        .where(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_task_by_id(
    db: Session,
    task_id: int,
    user_id: int,
) -> Task | None:
    """Get a specific task belonging to a user."""

    statement = select(Task).where(
        Task.id == task_id,
        Task.user_id == user_id,
    )

    return db.scalar(statement)


def update_task(
    db: Session,
    task: Task,
    **updates,
) -> Task:
    """Update an existing task."""

    for field, value in updates.items():
        if value is not None:
            setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


def delete_task(
    db: Session,
    task: Task,
) -> None:
    """Delete an existing task."""

    db.delete(task)
    db.commit()