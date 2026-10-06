"""
Read-only, user-scoped aggregations for the LifeOS Intelligence layer.

Why a separate repository rather than extending the existing ones
-----------------------------------------------------------------
The per-domain repositories (`task_repository`, `transaction_repository`, ...)
return ORM rows for CRUD screens. Intelligence needs the opposite: small
aggregates computed in the database — counts, `GROUP BY` buckets, sums — so
the amount of Python-side work and the size of the response stay constant no
matter how many rows the user owns.

Every function here is scoped by `user_id` in its `WHERE` clause. There is no
entry point that accepts an optional user filter, because an optional scope is
exactly how cross-user leakage happens. Nothing here writes, and no function
returns a live ORM entity to the caller.

Performance notes
-----------------
- Counts and sums are `SELECT count()` / `SELECT sum()` — they never
  materialise rows.
- Row-returning queries are ordered and `LIMIT`ed, so a user with 10,000
  tasks costs the same as one with 20.
- Cross-entity counts (a goal's incomplete tasks) are correlated subqueries,
  not one extra query per parent row.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import Numeric, Row, func, select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.habit import Habit
from app.models.habit_completion import HabitCompletion
from app.models.note import Note
from app.models.notification import Notification
from app.models.planner_event import PlannerEvent
from app.models.reminder import Reminder
from app.models.task import Task
from app.models.transaction import Transaction


# Cap on any row-returning query. The intelligence panel renders a fixed-size
# list, so fetching more would only cost memory and bandwidth.
DEFAULT_ROW_LIMIT = 50

# Summed money is re-cast to a fixed scale so SQLite's integer-backed NUMERIC
# and PostgreSQL's NUMERIC both return an exact `Decimal` rather than a float.
MONEY_NUMERIC = Numeric(14, 2)


# =========================================================
# TASKS
# =========================================================


def count_tasks(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Task.id)).where(Task.user_id == user_id)
    ) or 0


def count_completed_tasks(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == "completed",
        )
    ) or 0


def count_incomplete_tasks(
    db: Session,
    user_id: int,
) -> int:
    """
    Every task that is not `completed`.

    `status` is a free string — the create/update schemas cap its length but do
    not restrict its values — so "incomplete" is defined by exclusion rather
    than by listing known open states. A task stored as `todo`, `in_progress`,
    or any other non-completed value is then counted correctly instead of
    silently vanishing from the user's totals. The `complete_task_tool`
    workflow in `app/ai/tools.py` writes `"completed"`, which is the one
    value this definition treats as done.
    """

    return db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status != "completed",
        )
    ) or 0


def count_overdue_tasks(
    db: Session,
    user_id: int,
    now: datetime,
) -> int:
    return db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status != "completed",
            Task.due_date.is_not(None),
            Task.due_date < now,
        )
    ) or 0


def count_due_soon_tasks(
    db: Session,
    user_id: int,
    now: datetime,
    horizon: datetime,
) -> int:
    return db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status != "completed",
            Task.due_date.is_not(None),
            Task.due_date >= now,
            Task.due_date <= horizon,
        )
    ) or 0


def count_unlinked_incomplete_tasks(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status != "completed",
            Task.goal_id.is_(None),
        )
    ) or 0


def get_overdue_tasks(
    db: Session,
    user_id: int,
    now: datetime,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    """Oldest overdue task first — the ones that have been waiting longest."""

    statement = (
        select(Task.id, Task.title, Task.priority, Task.due_date)
        .where(
            Task.user_id == user_id,
            Task.status != "completed",
            Task.due_date.is_not(None),
            Task.due_date < now,
        )
        .order_by(Task.due_date.asc(), Task.id.asc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


def get_due_soon_tasks(
    db: Session,
    user_id: int,
    now: datetime,
    horizon: datetime,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    statement = (
        select(Task.id, Task.title, Task.priority, Task.due_date)
        .where(
            Task.user_id == user_id,
            Task.status != "completed",
            Task.due_date.is_not(None),
            Task.due_date >= now,
            Task.due_date <= horizon,
        )
        .order_by(Task.due_date.asc(), Task.id.asc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


# =========================================================
# GOALS
# =========================================================


def count_goals(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Goal.id)).where(Goal.user_id == user_id)
    ) or 0


def count_active_goals(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Goal.id)).where(
            Goal.user_id == user_id,
            Goal.is_completed.is_(False),
        )
    ) or 0


def count_goals_without_target_date(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Goal.id)).where(
            Goal.user_id == user_id,
            Goal.is_completed.is_(False),
            Goal.target_date.is_(None),
        )
    ) or 0


def get_goal_signals(
    db: Session,
    user_id: int,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    """
    Active goals with their linked-work counts.

    Both counts are correlated subqueries that repeat the caller's `user_id`,
    so a goal can never accumulate another user's tasks or habits even if a
    row were ever to reference one.
    """

    incomplete_tasks = (
        select(func.count(Task.id))
        .where(
            Task.goal_id == Goal.id,
            Task.user_id == user_id,
            Task.status != "completed",
        )
        .correlate(Goal)
        .scalar_subquery()
    )

    active_habits = (
        select(func.count(Habit.id))
        .where(
            Habit.goal_id == Goal.id,
            Habit.user_id == user_id,
            Habit.is_active.is_(True),
        )
        .correlate(Goal)
        .scalar_subquery()
    )

    statement = (
        select(
            Goal.id,
            Goal.title,
            Goal.progress,
            Goal.is_completed,
            Goal.target_date,
            incomplete_tasks.label("incomplete_task_count"),
            active_habits.label("active_habit_count"),
        )
        .where(
            Goal.user_id == user_id,
            Goal.is_completed.is_(False),
        )
        # Goals with a target date are the ones a date-based rule can reason
        # about, so they come first; undated goals keep id order behind them.
        .order_by(Goal.target_date.asc().nulls_last(), Goal.id.asc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


# =========================================================
# HABITS
# =========================================================


def get_habit_signals(
    db: Session,
    user_id: int,
    now: datetime,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    """
    Active habits plus real completion counts over the last 14 and 30 days.

    The counts come from `habit_completions`, not from the cached
    `current_streak` column: streak is a *consecutive* measure, and a rule
    about overall consistency needs the raw count over a window. This also
    sidesteps the fact that `calculate_streaks` stamps
    `last_completed_at` as midnight on the completed date.

    `HabitCompletion` has no `user_id` of its own — it is reached only through
    its habit — so the habit set is built first and every completion lookup is
    filtered to that exact set of ids. A completion row can therefore only
    ever be attributed to one of the caller's own habits.
    """

    habits = list(
        db.scalars(
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(True),
            )
            .order_by(Habit.id.asc())
            .limit(limit)
        ).all()
    )

    if not habits:
        return []

    habit_ids = [habit.id for habit in habits]

    # `completed_date` is a `Date`, so the cut-offs are dates too.
    today = now.date()
    cutoff_14 = today - timedelta(days=14)
    cutoff_30 = today - timedelta(days=30)

    # habit_id -> [count_14d, count_30d, most recent completed_date]
    tallies: dict[int, list] = {
        habit_id: [0, 0, None] for habit_id in habit_ids
    }

    statement = (
        select(HabitCompletion.habit_id, HabitCompletion.completed_date)
        .where(
            HabitCompletion.habit_id.in_(habit_ids),
            # A future-dated row is a data-entry artefact, not a completion.
            HabitCompletion.completed_date <= today,
            HabitCompletion.completed_date >= cutoff_30,
        )
        .order_by(HabitCompletion.completed_date.asc())
    )

    for habit_id, completed_date in db.execute(statement).all():
        tally = tallies[habit_id]
        tally[1] += 1

        if completed_date >= cutoff_14:
            tally[0] += 1

        if tally[2] is None or completed_date > tally[2]:
            tally[2] = completed_date

    return [
        {
            "id": habit.id,
            "title": habit.title,
            "frequency": habit.frequency,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "completions_14d": tally[0],
            "completions_30d": tally[1],
            "last_completed_on": tally[2],
        }
        for habit, tally in ((habit, tallies[habit.id]) for habit in habits)
    ]


def count_active_habits(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Habit.id)).where(
            Habit.user_id == user_id,
            Habit.is_active.is_(True),
        )
    ) or 0


# =========================================================
# PLANNER
# =========================================================


def count_planner_events(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(PlannerEvent.id)).where(
            PlannerEvent.user_id == user_id
        )
    ) or 0


def get_upcoming_planner_events(
    db: Session,
    user_id: int,
    now: datetime,
    horizon: datetime,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    """
    Planner events from `now` through `horizon`, oldest first.

    `now` must be a day boundary (midnight), not the current instant:
    `event_date` is stored at midnight by the Planner, so comparing it against
    a mid-day instant would drop every event filed under the current day. See
    `build_context`, which passes `moment.replace(hour=0, ...)`.
    """

    statement = (
        select(
            PlannerEvent.id,
            PlannerEvent.title,
            PlannerEvent.event_date,
            PlannerEvent.start_time,
            PlannerEvent.end_time,
            PlannerEvent.event_type,
            PlannerEvent.is_completed,
        )
        .where(
            PlannerEvent.user_id == user_id,
            PlannerEvent.event_date >= now,
            PlannerEvent.event_date <= horizon,
        )
        .order_by(PlannerEvent.start_time.asc(), PlannerEvent.id.asc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


def get_busy_days(
    db: Session,
    user_id: int,
    now: datetime,
    horizon: datetime,
    per_day_threshold: int,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    """
    Upcoming days holding at least `per_day_threshold` open events.

    The `GROUP BY`/`HAVING` run in the database, so a month of planner data is
    reduced to at most `limit` rows before it reaches Python. That is what
    keeps the planning rule cheap regardless of how much is scheduled.

    Only incomplete events count: a day whose blocks are all checked off is
    booked, not overloaded.

    As in `get_upcoming_planner_events`, `now` must be a day boundary
    (midnight) so the current day is included rather than filtered away.
    """

    statement = (
        select(
            func.date(PlannerEvent.event_date).label("day"),
            func.count(PlannerEvent.id).label("event_count"),
        )
        .where(
            PlannerEvent.user_id == user_id,
            PlannerEvent.is_completed.is_(False),
            PlannerEvent.event_date >= now,
            PlannerEvent.event_date <= horizon,
        )
        .group_by(func.date(PlannerEvent.event_date))
        .having(func.count(PlannerEvent.id) >= per_day_threshold)
        .order_by(func.date(PlannerEvent.event_date).asc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


def count_unlinked_planner_events(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(PlannerEvent.id)).where(
            PlannerEvent.user_id == user_id,
            PlannerEvent.task_id.is_(None),
            PlannerEvent.habit_id.is_(None),
        )
    ) or 0


# =========================================================
# REMINDERS
# =========================================================


def count_pending_reminders(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id,
            Reminder.status == "pending",
        )
    ) or 0


def count_reminders(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id
        )
    ) or 0


def get_follow_up_reminders(
    db: Session,
    user_id: int,
    now: datetime,
    limit: int = DEFAULT_ROW_LIMIT,
) -> list[Row]:
    """
    Pending reminders whose time has passed but that are still pending.

    Deliberately *not* the scheduler's due query. The scheduler selects
    `notified_at IS NULL`, so a reminder it has already delivered but the user
    never completed falls here instead. The two sets are intentionally
    different: an undelivered reminder is the scheduler's business, a
    delivered-and-still-pending one is a genuine follow-up signal.
    """

    statement = (
        select(
            Reminder.id,
            Reminder.title,
            Reminder.remind_at,
            Reminder.notified_at,
        )
        .where(
            Reminder.user_id == user_id,
            Reminder.status == "pending",
            Reminder.remind_at <= now,
        )
        .order_by(Reminder.remind_at.asc(), Reminder.id.asc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


# =========================================================
# NOTES
# =========================================================


def count_active_notes(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Note.id)).where(
            Note.user_id == user_id,
            Note.is_archived.is_(False),
        )
    ) or 0


def count_recent_notes(
    db: Session,
    user_id: int,
    since: datetime,
) -> int:
    return db.scalar(
        select(func.count(Note.id)).where(
            Note.user_id == user_id,
            Note.is_archived.is_(False),
            Note.created_at >= since,
        )
    ) or 0


# =========================================================
# FINANCE
# =========================================================


def _money_window(
    user_id: int,
    start_date: date,
    end_date: date,
):
    return (
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
    )


def summarize_transactions(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date,
) -> Row | None:
    """
    Income total, expense total and count for a date window — three scalars.

    Kept as three statements rather than one grouped query because income and
    expense are the two values the summary needs and a single
    `GROUP BY type` row would still have to be re-assembled in Python anyway.
    Both sums return `Decimal`, matching `TransactionResponse`.
    """

    income = db.scalar(
        select(func.coalesce(func.sum(func.cast(Transaction.amount, MONEY_NUMERIC)), 0)).where(
            *_money_window(user_id, start_date, end_date),
            Transaction.type == "income",
        )
    )

    expense = db.scalar(
        select(func.coalesce(func.sum(func.cast(Transaction.amount, MONEY_NUMERIC)), 0)).where(
            *_money_window(user_id, start_date, end_date),
            Transaction.type == "expense",
        )
    )

    count = db.scalar(
        select(func.count(Transaction.id)).where(
            *_money_window(user_id, start_date, end_date),
        )
    ) or 0

    return {
        "income_total": income,
        "expense_total": expense,
        "transaction_count": count,
    }


def get_top_expense_categories(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date,
    limit: int = 3,
) -> list[Row]:
    """
    Busiest expense categories by transaction count.

    Ordered by count rather than by summed amount: with three rows the user is
    shown which categories are actually recurring, which is a fact the data
    supports. Ranking by sum would be a judgement about which category
    "matters most", and this layer does not make those.
    """

    statement = (
        select(
            Transaction.category,
            func.coalesce(
                func.sum(func.cast(Transaction.amount, MONEY_NUMERIC)),
                0,
            ).label("total"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .where(
            *_money_window(user_id, start_date, end_date),
            Transaction.type == "expense",
        )
        .group_by(Transaction.category)
        .order_by(
            func.count(Transaction.id).desc(),
            Transaction.category.asc(),
        )
        .limit(limit)
    )

    return list(db.execute(statement).all())


def count_transactions(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id
        )
    ) or 0


# =========================================================
# NOTIFICATIONS
# =========================================================


def count_unread_notifications(
    db: Session,
    user_id: int,
) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ) or 0