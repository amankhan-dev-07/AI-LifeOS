from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.services.goal_service import get_user_goals
from app.services.habit_service import get_user_habits
from app.services.task_service import get_user_tasks


# =========================================================
# DEFAULT PLANNER SETTINGS
# =========================================================

PLANNER_START_HOUR = 8

TASK_DURATION_MINUTES = {
    "high": 60,
    "medium": 45,
    "low": 30,
}

HABIT_DURATION_MINUTES = 15


def _format_time(value: datetime) -> str:
    """Format datetime as HH:MM."""

    return value.strftime("%H:%M")


def _add_minutes(
    current_time: datetime,
    minutes: int,
) -> datetime:
    """Add minutes to the current planner time."""

    return current_time + timedelta(
        minutes=minutes,
    )


def get_daily_plan(
    db: Session,
    user_id: int,
) -> dict:
    """
    Build a smart time-based daily plan.

    Priority:
    1. High-priority tasks
    2. Active habits
    3. Medium/low-priority tasks

    Default planning starts at 08:00.
    """

    tasks = get_user_tasks(
        db=db,
        user_id=user_id,
    )

    goals = get_user_goals(
        db=db,
        user_id=user_id,
    )

    habits = get_user_habits(
        db=db,
        user_id=user_id,
    )

    # =========================================================
    # PENDING TASKS
    # =========================================================

    pending_tasks = [
        task
        for task in tasks
        if task.status == "pending"
    ]

    priority_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    pending_tasks.sort(
        key=lambda task: (
            priority_order.get(
                task.priority,
                1,
            ),
            task.due_date
            or datetime.max,
        )
    )

    # =========================================================
    # ACTIVE GOALS
    # =========================================================

    active_goals = [
        goal
        for goal in goals
        if not goal.is_completed
    ]

    # =========================================================
    # ACTIVE HABITS
    # =========================================================

    active_habits = [
        habit
        for habit in habits
        if habit.is_active
    ]

    # =========================================================
    # PLANNER CLOCK
    # =========================================================

    current_time = datetime.combine(
        date.today(),
        datetime.min.time(),
    ).replace(
        hour=PLANNER_START_HOUR,
    )

    plan = []

    # =========================================================
    # HIGH PRIORITY TASKS
    # =========================================================

    for task in pending_tasks:

        if task.priority != "high":
            continue

        start_time = current_time

        duration = TASK_DURATION_MINUTES.get(
            task.priority,
            45,
        )

        end_time = _add_minutes(
            start_time,
            duration,
        )

        plan.append(
            {
                "type": "task",
                "id": task.id,
                "title": task.title,
                "start_time": _format_time(start_time),
                "end_time": _format_time(end_time),
                "priority": task.priority,
            }
        )

        current_time = end_time

    # =========================================================
    # HABITS
    # =========================================================

    for habit in active_habits:

        start_time = current_time

        end_time = _add_minutes(
            start_time,
            HABIT_DURATION_MINUTES,
        )

        plan.append(
            {
                "type": "habit",
                "id": habit.id,
                "title": habit.title,
                "start_time": _format_time(start_time),
                "end_time": _format_time(end_time),
                "priority": None,
                "frequency": habit.frequency,
                "current_streak": habit.current_streak,
            }
        )

        current_time = end_time

    # =========================================================
    # MEDIUM / LOW TASKS
    # =========================================================

    for task in pending_tasks:

        if task.priority == "high":
            continue

        start_time = current_time

        duration = TASK_DURATION_MINUTES.get(
            task.priority,
            45,
        )

        end_time = _add_minutes(
            start_time,
            duration,
        )

        plan.append(
            {
                "type": "task",
                "id": task.id,
                "title": task.title,
                "start_time": _format_time(start_time),
                "end_time": _format_time(end_time),
                "priority": task.priority,
            }
        )

        current_time = end_time

    # =========================================================
    # GOAL FOCUS
    # =========================================================

    goal_focus = [
        {
            "id": goal.id,
            "title": goal.title,
            "category": goal.category,
            "target_date": (
                goal.target_date.isoformat()
                if goal.target_date
                else None
            ),
        }
        for goal in active_goals
    ]

    # =========================================================
    # FINAL RESPONSE
    # =========================================================

    return {
        "success": True,
        "date": date.today().isoformat(),
        "plan": plan,
        "goals": goal_focus,
        "summary": {
            "pending_tasks": len(
                pending_tasks
            ),
            "active_goals": len(
                active_goals
            ),
            "active_habits": len(
                active_habits
            ),
        },
    }