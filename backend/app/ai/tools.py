from datetime import datetime

from sqlalchemy.orm import Session

from app.services.dashboard_service import get_dashboard
from app.services.goal_service import (
    create_user_goal,
    delete_user_goal,
    get_user_goal,
    get_user_goals,
    update_user_goal,
)
from app.services.task_service import (
    create_user_task,
    delete_user_task,
    get_user_task,
    get_user_tasks,
    update_user_task,
)


# =========================================================
# DASHBOARD
# =========================================================


def get_dashboard_tool(
    db: Session,
    user_id: int,
) -> dict:
    """Read the current user's LifeOS dashboard."""

    dashboard = get_dashboard(
        db=db,
        user_id=user_id,
    )

    return dashboard.model_dump()


# =========================================================
# TASK TOOLS
# =========================================================


def create_task_tool(
    db: Session,
    user_id: int,
    title: str,
    description: str | None = None,
    priority: str = "medium",
    due_date: datetime | None = None,
) -> dict:
    """Create a task for the current user."""

    task = create_user_task(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        status="pending",
        priority=priority,
        due_date=due_date,
    )

    return {
        "success": True,
        "task": {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": (
                task.due_date.isoformat()
                if task.due_date
                else None
            ),
        },
    }


def get_tasks_tool(
    db: Session,
    user_id: int,
) -> dict:
    """Read all tasks belonging to the current user."""

    tasks = get_user_tasks(
        db=db,
        user_id=user_id,
    )

    return {
        "success": True,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "due_date": (
                    task.due_date.isoformat()
                    if task.due_date
                    else None
                ),
            }
            for task in tasks
        ],
    }


def update_task_tool(
    db: Session,
    user_id: int,
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_date: datetime | None = None,
) -> dict:
    """Update a task belonging to the current user."""

    task = get_user_task(
        db=db,
        task_id=task_id,
        user_id=user_id,
    )

    if task is None:
        return {
            "success": False,
            "error": "Task not found.",
        }

    updates = {
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "due_date": due_date,
    }

    updates = {
        key: value
        for key, value in updates.items()
        if value is not None
    }

    if not updates:
        return {
            "success": False,
            "error": "No changes were provided.",
        }

    task = update_user_task(
        db=db,
        task=task,
        **updates,
    )

    return {
        "success": True,
        "task": {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": (
                task.due_date.isoformat()
                if task.due_date
                else None
            ),
        },
    }


def complete_task_tool(
    db: Session,
    user_id: int,
    task_id: int,
) -> dict:
    """Mark a task as completed."""

    task = get_user_task(
        db=db,
        task_id=task_id,
        user_id=user_id,
    )

    if task is None:
        return {
            "success": False,
            "error": "Task not found.",
        }

    task = update_user_task(
        db=db,
        task=task,
        status="completed",
    )

    return {
        "success": True,
        "task": {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": (
                task.due_date.isoformat()
                if task.due_date
                else None
            ),
        },
    }


def delete_task_tool(
    db: Session,
    user_id: int,
    task_id: int,
) -> dict:
    """Delete a task belonging to the current user."""

    task = get_user_task(
        db=db,
        task_id=task_id,
        user_id=user_id,
    )

    if task is None:
        return {
            "success": False,
            "error": "Task not found.",
        }

    task_id_value = task.id
    task_title = task.title

    delete_user_task(
        db=db,
        task=task,
    )

    return {
        "success": True,
        "task": {
            "id": task_id_value,
            "title": task_title,
            "deleted": True,
        },
    }


# =========================================================
# GOAL TOOLS
# =========================================================


def create_goal_tool(
    db: Session,
    user_id: int,
    title: str,
    description: str | None = None,
    category: str = "general",
    target_date: datetime | None = None,
) -> dict:
    """Create a goal for the current user."""

    goal = create_user_goal(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        target_date=target_date,
    )

    return {
        "success": True,
        "goal": {
            "id": goal.id,
            "user_id": goal.user_id,
            "title": goal.title,
            "description": goal.description,
            "category": goal.category,
            "target_date": (
                goal.target_date.isoformat()
                if goal.target_date
                else None
            ),
            "is_completed": goal.is_completed,
        },
    }


def get_goals_tool(
    db: Session,
    user_id: int,
) -> dict:
    """Read all goals belonging to the current user."""

    goals = get_user_goals(
        db=db,
        user_id=user_id,
    )

    return {
        "success": True,
        "goals": [
            {
                "id": goal.id,
                "title": goal.title,
                "description": goal.description,
                "category": goal.category,
                "target_date": (
                    goal.target_date.isoformat()
                    if goal.target_date
                    else None
                ),
                "is_completed": goal.is_completed,
            }
            for goal in goals
        ],
    }


def update_goal_tool(
    db: Session,
    user_id: int,
    goal_id: int,
    title: str | None = None,
    description: str | None = None,
    category: str | None = None,
    target_date: datetime | None = None,
    is_completed: bool | None = None,
) -> dict:
    """Update a goal belonging to the current user."""

    goal = get_user_goal(
        db=db,
        goal_id=goal_id,
        user_id=user_id,
    )

    if goal is None:
        return {
            "success": False,
            "error": "Goal not found.",
        }

    updates = {
        "title": title,
        "description": description,
        "category": category,
        "target_date": target_date,
        "is_completed": is_completed,
    }

    updates = {
        key: value
        for key, value in updates.items()
        if value is not None
    }

    if not updates:
        return {
            "success": False,
            "error": "No changes were provided.",
        }

    goal = update_user_goal(
        db=db,
        goal=goal,
        **updates,
    )

    return {
        "success": True,
        "goal": {
            "id": goal.id,
            "user_id": goal.user_id,
            "title": goal.title,
            "description": goal.description,
            "category": goal.category,
            "target_date": (
                goal.target_date.isoformat()
                if goal.target_date
                else None
            ),
            "is_completed": goal.is_completed,
        },
    }


def complete_goal_tool(
    db: Session,
    user_id: int,
    goal_id: int,
) -> dict:
    """Mark a goal as completed."""

    goal = get_user_goal(
        db=db,
        goal_id=goal_id,
        user_id=user_id,
    )

    if goal is None:
        return {
            "success": False,
            "error": "Goal not found.",
        }

    goal = update_user_goal(
        db=db,
        goal=goal,
        is_completed=True,
    )

    return {
        "success": True,
        "goal": {
            "id": goal.id,
            "user_id": goal.user_id,
            "title": goal.title,
            "description": goal.description,
            "category": goal.category,
            "target_date": (
                goal.target_date.isoformat()
                if goal.target_date
                else None
            ),
            "is_completed": goal.is_completed,
        },
    }


def delete_goal_tool(
    db: Session,
    user_id: int,
    goal_id: int,
) -> dict:
    """Delete a goal belonging to the current user."""

    goal = get_user_goal(
        db=db,
        goal_id=goal_id,
        user_id=user_id,
    )

    if goal is None:
        return {
            "success": False,
            "error": "Goal not found.",
        }

    goal_id_value = goal.id
    goal_title = goal.title

    delete_user_goal(
        db=db,
        goal=goal,
    )

    return {
        "success": True,
        "goal": {
            "id": goal_id_value,
            "title": goal_title,
            "deleted": True,
        },
    }