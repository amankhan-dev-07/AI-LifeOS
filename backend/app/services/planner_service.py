# from datetime import date, datetime

from datetime import date, datetime
# from sqlalchemy.orm import Session
from sqlalchemy.orm import Session

from app.services.goal_service import get_user_goals
from app.services.habit_service import get_user_habits
from app.services.task_service import get_user_tasks


def get_daily_plan(
    db: Session,
    user_id: int,
) -> dict:
    """
    Build a simple daily plan from the user's
    pending tasks, active goals and active habits.
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

    # ---------------------------------------------------------
    # Pending tasks
    # ---------------------------------------------------------

    pending_tasks = [
        task
        for task in tasks
        if task.status == "pending"
    ]

    # Highest priority first.
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

    # ---------------------------------------------------------
    # Active goals
    # ---------------------------------------------------------

    active_goals = [
        goal
        for goal in goals
        if not goal.is_completed
    ]

    # ---------------------------------------------------------
    # Active habits
    # ---------------------------------------------------------

    active_habits = [
        habit
        for habit in habits
        if habit.is_active
    ]

    # ---------------------------------------------------------
    # Build plan
    # ---------------------------------------------------------

    plan = []

    # High priority tasks first.
    for task in pending_tasks:

        if task.priority == "high":
            plan.append(
                {
                    "type": "task",
                    "id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "due_date": (
                        task.due_date.isoformat()
                        if task.due_date
                        else None
                    ),
                }
            )

    # Then active habits.
    for habit in active_habits:

        plan.append(
            {
                "type": "habit",
                "id": habit.id,
                "title": habit.title,
                "frequency": habit.frequency,
                "current_streak": habit.current_streak,
            }
        )

    # Then remaining tasks.
    for task in pending_tasks:

        if task.priority != "high":
            plan.append(
                {
                    "type": "task",
                    "id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "due_date": (
                        task.due_date.isoformat()
                        if task.due_date
                        else None
                    ),
                }
            )

    # ---------------------------------------------------------
    # Goal focus
    # ---------------------------------------------------------

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

    return {
        "success": True,
        "date": date.today().isoformat(),
        "plan": plan,
        "goals": goal_focus,
        "summary": {
            "pending_tasks": len(pending_tasks),
            "active_goals": len(active_goals),
            "active_habits": len(active_habits),
        },
    }
