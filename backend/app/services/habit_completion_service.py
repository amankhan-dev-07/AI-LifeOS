from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.habit import Habit
from app.models.habit_completion import HabitCompletion
from app.repositories.habit_completion_repository import (
    create_completion,
    delete_completion,
    get_completion_by_date,
    get_completions_by_habit,
)


def calculate_streaks(
    habit: Habit,
    completions: list[HabitCompletion],
) -> None:
    """Calculate current and longest streaks for a habit."""

    today = date.today()

    # Ignore future completion dates.
    completed_dates = {
        completion.completed_date
        for completion in completions
        if completion.completed_date <= today
    }

    # No completed dates.
    if not completed_dates:
        habit.current_streak = 0
        habit.longest_streak = 0
        habit.last_completed_at = None
        return

    sorted_dates = sorted(completed_dates)

    # ---------------------------------------------------------
    # Calculate longest streak
    # ---------------------------------------------------------

    longest_streak = 1
    streak_count = 1

    for index in range(1, len(sorted_dates)):
        previous_date = sorted_dates[index - 1]
        current_date = sorted_dates[index]

        if current_date == previous_date + timedelta(days=1):
            streak_count += 1

            longest_streak = max(
                longest_streak,
                streak_count,
            )
        else:
            streak_count = 1

    # ---------------------------------------------------------
    # Calculate current streak
    # ---------------------------------------------------------

    yesterday = today - timedelta(days=1)

    if today in completed_dates:
        current_streak = 1
        check_date = today

        while check_date - timedelta(days=1) in completed_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    elif yesterday in completed_dates:
        current_streak = 1
        check_date = yesterday

        while check_date - timedelta(days=1) in completed_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    else:
        current_streak = 0

    # ---------------------------------------------------------
    # Update habit streak fields
    # ---------------------------------------------------------

    habit.current_streak = current_streak
    habit.longest_streak = longest_streak

    # ---------------------------------------------------------
    # Update last completed date
    # ---------------------------------------------------------

    latest_completed_date = max(completed_dates)

    habit.last_completed_at = datetime.combine(
        latest_completed_date,
        datetime.min.time(),
    )


def complete_habit(
    db: Session,
    habit: Habit,
    completed_date: date,
) -> HabitCompletion:
    """Mark a habit as completed for a specific date."""

    existing_completion = get_completion_by_date(
        db=db,
        habit_id=habit.id,
        completed_date=completed_date,
    )

    if existing_completion:
        completions = get_completions_by_habit(
            db=db,
            habit_id=habit.id,
        )
        calculate_streaks(
            habit=habit,
            completions=completions,
        )
        db.commit()
        db.refresh(habit)
        return existing_completion

    completion = create_completion(
        db=db,
        habit_id=habit.id,
        completed_date=completed_date,
    )

    completions = get_completions_by_habit(
        db=db,
        habit_id=habit.id,
    )

    calculate_streaks(
        habit=habit,
        completions=completions,
    )

    db.commit()
    db.refresh(habit)

    return completion


def get_habit_completions(
    db: Session,
    habit: Habit,
) -> list[HabitCompletion]:
    """Get completion history for a habit."""

    return get_completions_by_habit(
        db=db,
        habit_id=habit.id,
    )


def remove_habit_completion(
    db: Session,
    habit: Habit,
    completed_date: date,
) -> None:
    """Remove a completion and recalculate streaks."""

    completion = get_completion_by_date(
        db=db,
        habit_id=habit.id,
        completed_date=completed_date,
    )

    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit completion not found.",
        )

    delete_completion(
        db=db,
        completion=completion,
    )

    completions = get_completions_by_habit(
        db=db,
        habit_id=habit.id,
    )

    calculate_streaks(
        habit=habit,
        completions=completions,
    )

    db.commit()
    db.refresh(habit)