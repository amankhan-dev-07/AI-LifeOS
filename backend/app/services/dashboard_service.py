from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.habit import Habit
from app.models.task import Task
from app.schemas.dashboard import (
    DashboardResponse,
    GoalSummary,
    HabitSummary,
    TaskSummary,
)


def get_dashboard(
    db: Session,
    user_id: int,
) -> DashboardResponse:
    """Build the dashboard summary for a user."""

    # ---------------------------------------------------------
    # Tasks
    # ---------------------------------------------------------

    task_total = db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
        )
    ) or 0

    task_completed = db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == "completed",
        )
    ) or 0

    task_pending = db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == "pending",
        )
    ) or 0

    # ---------------------------------------------------------
    # Goals
    # ---------------------------------------------------------

    goal_total = db.scalar(
        select(func.count(Goal.id)).where(
            Goal.user_id == user_id,
        )
    ) or 0

    goal_completed = db.scalar(
        select(func.count(Goal.id)).where(
            Goal.user_id == user_id,
            Goal.is_completed.is_(True),
        )
    ) or 0

    goal_active = db.scalar(
        select(func.count(Goal.id)).where(
            Goal.user_id == user_id,
            Goal.is_completed.is_(False),
        )
    ) or 0

    # ---------------------------------------------------------
    # Habits
    # ---------------------------------------------------------

    habits = list(
        db.scalars(
            select(Habit).where(
                Habit.user_id == user_id,
            )
        ).all()
    )

    habit_total = len(habits)

    habit_active = sum(
        1
        for habit in habits
        if habit.is_active
    )

    current_streak = max(
        (
            habit.current_streak
            for habit in habits
            if habit.is_active
        ),
        default=0,
    )

    best_streak = max(
        (
            habit.longest_streak
            for habit in habits
        ),
        default=0,
    )

    # ---------------------------------------------------------
    # Dashboard response
    # ---------------------------------------------------------

    return DashboardResponse(
        tasks=TaskSummary(
            total=task_total,
            pending=task_pending,
            completed=task_completed,
        ),
        goals=GoalSummary(
            total=goal_total,
            active=goal_active,
            completed=goal_completed,
        ),
        habits=HabitSummary(
            total=habit_total,
            active=habit_active,
            current_streak=current_streak,
            best_streak=best_streak,
        ),
    )