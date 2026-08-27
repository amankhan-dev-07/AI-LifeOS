from datetime import date, datetime

from fastapi import HTTPException
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

from app.services.habit_service import (
    create_user_habit,
    delete_user_habit,
    get_user_habit,
    get_user_habits,
    update_user_habit,
)

from app.services.habit_completion_service import (
    complete_habit,
    get_habit_completions,
    remove_habit_completion,
)
from app.services.planner_service import get_daily_plan


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


# =========================================================
# HABIT TOOLS
# =========================================================


def create_habit_tool(
    db: Session,
    user_id: int,
    title: str,
    description: str | None = None,
    frequency: str = "daily",
) -> dict:
    """Create a habit for the current user."""

    habit = create_user_habit(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        frequency=frequency,
    )

    return {
        "success": True,
        "habit": {
            "id": habit.id,
            "user_id": habit.user_id,
            "title": habit.title,
            "description": habit.description,
            "frequency": habit.frequency,
            "is_active": habit.is_active,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "last_completed_at": (
                habit.last_completed_at.isoformat()
                if habit.last_completed_at
                else None
            ),
        },
    }


def get_habits_tool(
    db: Session,
    user_id: int,
) -> dict:
    """Read all habits belonging to the current user."""

    habits = get_user_habits(
        db=db,
        user_id=user_id,
    )

    return {
        "success": True,
        "habits": [
            {
                "id": habit.id,
                "title": habit.title,
                "description": habit.description,
                "frequency": habit.frequency,
                "is_active": habit.is_active,
                "current_streak": habit.current_streak,
                "longest_streak": habit.longest_streak,
                "last_completed_at": (
                    habit.last_completed_at.isoformat()
                    if habit.last_completed_at
                    else None
                ),
            }
            for habit in habits
        ],
    }


def update_habit_tool(
    db: Session,
    user_id: int,
    habit_id: int,
    title: str | None = None,
    description: str | None = None,
    frequency: str | None = None,
    is_active: bool | None = None,
) -> dict:
    """Update a habit belonging to the current user."""

    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )

    if habit is None:
        return {
            "success": False,
            "error": "Habit not found.",
        }

    updates = {
        "title": title,
        "description": description,
        "frequency": frequency,
        "is_active": is_active,
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

    habit = update_user_habit(
        db=db,
        habit=habit,
        **updates,
    )

    return {
        "success": True,
        "habit": {
            "id": habit.id,
            "user_id": habit.user_id,
            "title": habit.title,
            "description": habit.description,
            "frequency": habit.frequency,
            "is_active": habit.is_active,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "last_completed_at": (
                habit.last_completed_at.isoformat()
                if habit.last_completed_at
                else None
            ),
        },
    }


def delete_habit_tool(
    db: Session,
    user_id: int,
    habit_id: int,
) -> dict:
    """Delete a habit belonging to the current user."""

    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )

    if habit is None:
        return {
            "success": False,
            "error": "Habit not found.",
        }

    habit_id_value = habit.id
    habit_title = habit.title

    delete_user_habit(
        db=db,
        habit=habit,
    )

    return {
        "success": True,
        "habit": {
            "id": habit_id_value,
            "title": habit_title,
            "deleted": True,
        },
    }


def complete_habit_tool(
    db: Session,
    user_id: int,
    habit_id: int,
    completed_date: date | None = None,
) -> dict:
    """
    Complete a habit for a specific date.

    If no date is provided, today's date is used.
    Existing streak logic is handled by habit_completion_service.
    """

    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )

    if habit is None:
        return {
            "success": False,
            "error": "Habit not found.",
        }

    if not habit.is_active:
        return {
            "success": False,
            "error": "Habit is inactive.",
        }

    if completed_date is None:
        completed_date = date.today()

    try:
        completion = complete_habit(
            db=db,
            habit=habit,
            completed_date=completed_date,
        )

    except HTTPException as exc:
        return {
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
        }

    return {
        "success": True,
        "habit": {
            "id": habit.id,
            "title": habit.title,
            "frequency": habit.frequency,
            "is_active": habit.is_active,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "last_completed_at": (
                habit.last_completed_at.isoformat()
                if habit.last_completed_at
                else None
            ),
        },
        "completion": {
            "id": completion.id,
            "habit_id": completion.habit_id,
            "completed_date": (
                completion.completed_date.isoformat()
            ),
            "created_at": (
                completion.created_at.isoformat()
            ),
        },
    }


def get_habit_completions_tool(
    db: Session,
    user_id: int,
    habit_id: int,
) -> dict:
    """Read completion history for a user's habit."""

    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )

    if habit is None:
        return {
            "success": False,
            "error": "Habit not found.",
        }

    completions = get_habit_completions(
        db=db,
        habit=habit,
    )

    return {
        "success": True,
        "habit": {
            "id": habit.id,
            "title": habit.title,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "last_completed_at": (
                habit.last_completed_at.isoformat()
                if habit.last_completed_at
                else None
            ),
        },
        "completions": [
            {
                "id": completion.id,
                "habit_id": completion.habit_id,
                "completed_date": (
                    completion.completed_date.isoformat()
                ),
                "created_at": (
                    completion.created_at.isoformat()
                ),
            }
            for completion in completions
        ],
    }


def remove_habit_completion_tool(
    db: Session,
    user_id: int,
    habit_id: int,
    completed_date: date,
) -> dict:
    """Remove a habit completion and recalculate streaks."""

    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=user_id,
    )

    if habit is None:
        return {
            "success": False,
            "error": "Habit not found.",
        }

    try:
        remove_habit_completion(
            db=db,
            habit=habit,
            completed_date=completed_date,
        )

    except HTTPException as exc:
        return {
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
        }

    return {
        "success": True,
        "habit": {
            "id": habit.id,
            "title": habit.title,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "last_completed_at": (
                habit.last_completed_at.isoformat()
                if habit.last_completed_at
                else None
            ),
        },
        "removed_completion": {
            "completed_date": completed_date.isoformat(),
        },
    }
# =========================================================
# DAILY PLANNER TOOL
# =========================================================


def get_daily_plan_tool(
    db: Session,
    user_id: int,
) -> dict:
    """Generate today's plan for the current user."""

    return get_daily_plan(
        db=db,
        user_id=user_id,
    )