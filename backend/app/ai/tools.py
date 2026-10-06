from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.dashboard_service import get_dashboard
from app.services.intelligence_service import get_intelligence
from app.services.note_service import (
    create_user_note,
    delete_user_note,
    get_user_note,
    get_user_notes,
    update_user_note,
)
from app.services.planner_event_service import (
    create_user_event,
    delete_user_event,
    get_user_event,
    get_user_events,
    update_user_event,
)
from app.services.reminder_service import (
    cancel_user_reminder,
    complete_user_reminder,
    create_user_reminder,
    delete_user_reminder,
    get_user_reminder,
    get_user_reminders,
    update_user_reminder,
)
from app.services.search_service import search_lifeos
from app.services.transaction_service import (
    create_user_transaction,
    delete_user_transaction,
    get_user_transaction,
    get_user_transactions,
    update_user_transaction,
)

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
    estimated_minutes: int = 45,
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
        estimated_minutes=estimated_minutes,
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
            "progress": goal.progress,
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
                "progress": goal.progress,
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
    progress: int | None = None,
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
        "progress": progress,
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
            "progress": goal.progress,
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
        progress=100,
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
            "progress": goal.progress,
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


# =========================================================
# SEARCH TOOL
# =========================================================


def search_lifeos_tool(
    db: Session,
    user_id: int,
    query: str,
    limit: int = 20,
) -> dict:
    """Search across all LifeOS domains for the current user."""

    result = search_lifeos(
        db=db,
        user_id=user_id,
        raw_query=query,
        limit=limit,
    )

    return result.model_dump()


# =========================================================
# INTELLIGENCE TOOL
# =========================================================


def get_intelligence_tool(
    db: Session,
    user_id: int,
) -> dict:
    """Get deterministic intelligence insights for the current user."""

    result = get_intelligence(
        db=db,
        user_id=user_id,
    )

    return result.model_dump()


# =========================================================
# NOTE TOOLS
# =========================================================


def create_note_tool(
    db: Session,
    user_id: int,
    title: str,
    content: str = "",
    tag: str = "General",
    is_pinned: bool = False,
    goal_id: int | None = None,
    task_id: int | None = None,
) -> dict:
    """Create a note for the current user."""

    note = create_user_note(
        db=db,
        user_id=user_id,
        title=title,
        content=content,
        tag=tag,
        is_pinned=is_pinned,
        goal_id=goal_id,
        task_id=task_id,
    )

    return {
        "success": True,
        "note": {
            "id": note.id,
            "user_id": note.user_id,
            "title": note.title,
            "content": note.content,
            "tag": note.tag,
            "is_pinned": note.is_pinned,
            "is_archived": note.is_archived,
            "goal_id": note.goal_id,
            "task_id": note.task_id,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        },
    }


def get_notes_tool(
    db: Session,
    user_id: int,
    is_archived: bool | None = None,
    tag: str | None = None,
) -> dict:
    """Read notes belonging to the current user."""

    notes = get_user_notes(
        db=db,
        user_id=user_id,
        is_archived=is_archived,
        tag=tag,
    )

    return {
        "success": True,
        "notes": [
            {
                "id": note.id,
                "user_id": note.user_id,
                "title": note.title,
                "content": note.content,
                "tag": note.tag,
                "is_pinned": note.is_pinned,
                "is_archived": note.is_archived,
                "goal_id": note.goal_id,
                "task_id": note.task_id,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            }
            for note in notes
        ],
    }


def update_note_tool(
    db: Session,
    user_id: int,
    note_id: int,
    **updates,
) -> dict:
    """Update a note belonging to the current user."""

    note = get_user_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    if note is None:
        return {
            "success": False,
            "error": "Note not found.",
        }

    note = update_user_note(
        db=db,
        user_id=user_id,
        note_id=note_id,
        **updates,
    )

    return {
        "success": True,
        "note": {
            "id": note.id,
            "user_id": note.user_id,
            "title": note.title,
            "content": note.content,
            "tag": note.tag,
            "is_pinned": note.is_pinned,
            "is_archived": note.is_archived,
            "goal_id": note.goal_id,
            "task_id": note.task_id,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        },
    }


def delete_note_tool(
    db: Session,
    user_id: int,
    note_id: int,
) -> dict:
    """Delete a note belonging to the current user."""

    note = get_user_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    if note is None:
        return {
            "success": False,
            "error": "Note not found.",
        }

    note_id_value = note.id
    note_title = note.title

    delete_user_note(
        db=db,
        user_id=user_id,
        note_id=note_id,
    )

    return {
        "success": True,
        "note": {
            "id": note_id_value,
            "title": note_title,
            "deleted": True,
        },
    }


# =========================================================
# REMINDER TOOLS
# =========================================================


def create_reminder_tool(
    db: Session,
    user_id: int,
    title: str,
    remind_at: datetime,
    message: str | None = None,
    task_id: int | None = None,
    habit_id: int | None = None,
    planner_event_id: int | None = None,
) -> dict:
    """Create a reminder for the current user."""

    reminder = create_user_reminder(
        db=db,
        user_id=user_id,
        title=title.strip(),
        message=message,
        remind_at=remind_at,
        task_id=task_id,
        habit_id=habit_id,
        planner_event_id=planner_event_id,
    )

    return {
        "success": True,
        "reminder": {
            "id": reminder.id,
            "user_id": reminder.user_id,
            "title": reminder.title,
            "message": reminder.message,
            "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
            "status": reminder.status,
            "is_completed": reminder.is_completed,
            "is_cancelled": reminder.is_cancelled,
            "notified_at": reminder.notified_at.isoformat() if reminder.notified_at else None,
            "task_id": reminder.task_id,
            "habit_id": reminder.habit_id,
            "planner_event_id": reminder.planner_event_id,
            "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
            "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
        },
    }


def get_reminders_tool(
    db: Session,
    user_id: int,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """Read reminders belonging to the current user."""

    reminders = get_user_reminders(
        db=db,
        user_id=user_id,
        status_filter=status,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "success": True,
        "reminders": [
            {
                "id": reminder.id,
                "user_id": reminder.user_id,
                "title": reminder.title,
                "message": reminder.message,
                "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
                "status": reminder.status,
                "is_completed": reminder.is_completed,
                "is_cancelled": reminder.is_cancelled,
                "notified_at": reminder.notified_at.isoformat() if reminder.notified_at else None,
                "task_id": reminder.task_id,
                "habit_id": reminder.habit_id,
                "planner_event_id": reminder.planner_event_id,
                "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
                "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
            }
            for reminder in reminders
        ],
    }


def update_reminder_tool(
    db: Session,
    user_id: int,
    reminder_id: int,
    **updates,
) -> dict:
    """Update a reminder belonging to the current user."""

    reminder = get_user_reminder(
        db=db,
        reminder_id=reminder_id,
        user_id=user_id,
    )

    if reminder is None:
        return {
            "success": False,
            "error": "Reminder not found.",
        }

    reminder = update_user_reminder(
        db=db,
        user_id=user_id,
        reminder_id=reminder_id,
        **updates,
    )

    return {
        "success": True,
        "reminder": {
            "id": reminder.id,
            "user_id": reminder.user_id,
            "title": reminder.title,
            "message": reminder.message,
            "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
            "status": reminder.status,
            "is_completed": reminder.is_completed,
            "is_cancelled": reminder.is_cancelled,
            "notified_at": reminder.notified_at.isoformat() if reminder.notified_at else None,
            "task_id": reminder.task_id,
            "habit_id": reminder.habit_id,
            "planner_event_id": reminder.planner_event_id,
            "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
            "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
        },
    }


def complete_reminder_tool(
    db: Session,
    user_id: int,
    reminder_id: int,
) -> dict:
    """Mark a reminder as completed."""

    reminder = complete_user_reminder(
        db=db,
        user_id=user_id,
        reminder_id=reminder_id,
    )

    return {
        "success": True,
        "reminder": {
            "id": reminder.id,
            "user_id": reminder.user_id,
            "title": reminder.title,
            "message": reminder.message,
            "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
            "status": reminder.status,
            "is_completed": reminder.is_completed,
            "is_cancelled": reminder.is_cancelled,
            "notified_at": reminder.notified_at.isoformat() if reminder.notified_at else None,
            "task_id": reminder.task_id,
            "habit_id": reminder.habit_id,
            "planner_event_id": reminder.planner_event_id,
            "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
            "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
        },
    }


def delete_reminder_tool(
    db: Session,
    user_id: int,
    reminder_id: int,
) -> dict:
    """Delete a reminder belonging to the current user."""

    reminder = get_user_reminder(
        db=db,
        reminder_id=reminder_id,
        user_id=user_id,
    )

    if reminder is None:
        return {
            "success": False,
            "error": "Reminder not found.",
        }

    reminder_id_value = reminder.id
    reminder_title = reminder.title

    delete_user_reminder(
        db=db,
        user_id=user_id,
        reminder_id=reminder_id,
    )

    return {
        "success": True,
        "reminder": {
            "id": reminder_id_value,
            "title": reminder_title,
            "deleted": True,
        },
    }


# =========================================================
# FINANCE TOOLS
# =========================================================


def create_transaction_tool(
    db: Session,
    user_id: int,
    title: str,
    amount: float,
    type: str,
    category: str = "General",
    transaction_date: date | None = None,
    notes: str | None = None,
) -> dict:
    """Create a transaction for the current user."""

    from decimal import Decimal

    transaction = create_user_transaction(
        db=db,
        user_id=user_id,
        title=title,
        amount=Decimal(str(amount)),
        type=type,
        category=category,
        transaction_date=transaction_date or date.today(),
        notes=notes,
    )

    return {
        "success": True,
        "transaction": {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "title": transaction.title,
            "amount": str(transaction.amount),
            "type": transaction.type,
            "category": transaction.category,
            "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            "notes": transaction.notes,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
        },
    }


def get_transactions_tool(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    type: str | None = None,
    category: str | None = None,
) -> dict:
    """Read transactions belonging to the current user."""

    transactions = get_user_transactions(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        type=type,
        category=category,
    )

    return {
        "success": True,
        "transactions": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "title": t.title,
                "amount": str(t.amount),
                "type": t.type,
                "category": t.category,
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                "notes": t.notes,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in transactions
        ],
    }


def update_transaction_tool(
    db: Session,
    user_id: int,
    transaction_id: int,
    **updates,
) -> dict:
    """Update a transaction belonging to the current user."""

    transaction = get_user_transaction(
        db=db,
        transaction_id=transaction_id,
        user_id=user_id,
    )

    if transaction is None:
        return {
            "success": False,
            "error": "Transaction not found.",
        }

    transaction = update_user_transaction(
        db=db,
        user_id=user_id,
        transaction_id=transaction_id,
        **updates,
    )

    return {
        "success": True,
        "transaction": {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "title": transaction.title,
            "amount": str(transaction.amount),
            "type": transaction.type,
            "category": transaction.category,
            "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            "notes": transaction.notes,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
        },
    }


def delete_transaction_tool(
    db: Session,
    user_id: int,
    transaction_id: int,
) -> dict:
    """Delete a transaction belonging to the current user."""

    transaction = get_user_transaction(
        db=db,
        transaction_id=transaction_id,
        user_id=user_id,
    )

    if transaction is None:
        return {
            "success": False,
            "error": "Transaction not found.",
        }

    transaction_id_value = transaction.id
    transaction_title = transaction.title

    delete_user_transaction(
        db=db,
        user_id=user_id,
        transaction_id=transaction_id,
    )

    return {
        "success": True,
        "transaction": {
            "id": transaction_id_value,
            "title": transaction_title,
            "deleted": True,
        },
    }


# =========================================================
# PLANNER EVENT TOOLS
# =========================================================


def get_planner_events_tool(
    db: Session,
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    event_type: str | None = None,
) -> dict:
    """Read planner events belonging to the current user."""

    events = get_user_events(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
    )

    return {
        "success": True,
        "events": [
            {
                "id": event.id,
                "user_id": event.user_id,
                "title": event.title,
                "description": event.description,
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "start_time": event.start_time.isoformat() if event.start_time else None,
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "event_type": event.event_type,
                "task_id": event.task_id,
                "habit_id": event.habit_id,
                "is_completed": event.is_completed,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "updated_at": event.updated_at.isoformat() if event.updated_at else None,
            }
            for event in events
        ],
    }


def create_planner_event_tool(
    db: Session,
    user_id: int,
    title: str,
    event_date: datetime,
    start_time: datetime,
    end_time: datetime,
    event_type: str = "custom",
    description: str | None = None,
    task_id: int | None = None,
    habit_id: int | None = None,
) -> dict:
    """Create a planner event for the current user."""

    event = create_user_event(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        event_type=event_type,
        task_id=task_id,
        habit_id=habit_id,
    )

    return {
        "success": True,
        "event": {
            "id": event.id,
            "user_id": event.user_id,
            "title": event.title,
            "description": event.description,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "event_type": event.event_type,
            "task_id": event.task_id,
            "habit_id": event.habit_id,
            "is_completed": event.is_completed,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        },
    }


def update_planner_event_tool(
    db: Session,
    user_id: int,
    event_id: int,
    **updates,
) -> dict:
    """Update a planner event belonging to the current user."""

    event = get_user_event(
        db=db,
        event_id=event_id,
        user_id=user_id,
    )

    if event is None:
        return {
            "success": False,
            "error": "Planner event not found.",
        }

    event = update_user_event(
        db=db,
        user_id=user_id,
        event_id=event_id,
        **updates,
    )

    return {
        "success": True,
        "event": {
            "id": event.id,
            "user_id": event.user_id,
            "title": event.title,
            "description": event.description,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "event_type": event.event_type,
            "task_id": event.task_id,
            "habit_id": event.habit_id,
            "is_completed": event.is_completed,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        },
    }


def delete_planner_event_tool(
    db: Session,
    user_id: int,
    event_id: int,
) -> dict:
    """Delete a planner event belonging to the current user."""

    event = get_user_event(
        db=db,
        event_id=event_id,
        user_id=user_id,
    )

    if event is None:
        return {
            "success": False,
            "error": "Planner event not found.",
        }

    event_id_value = event.id
    event_title = event.title

    delete_user_event(
        db=db,
        user_id=user_id,
        event_id=event_id,
    )

    return {
        "success": True,
        "event": {
            "id": event_id_value,
            "title": event_title,
            "deleted": True,
        },
    }