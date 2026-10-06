"""
LifeOS context snapshot.

Turns the authenticated user's persisted records into one small, bounded
dataclass that the rule engine reasons over. This is the "Context" half of
Phase 6's Context → Insight → Actionable Suggestion chain.

Two properties are deliberate:

**Derived, never stored.** There is no snapshot table. The same data is
recomputed from the same rows on every request, so an insight can never go
stale relative to the records it claims to describe. Nothing here writes.

**Bounded.** Every query is either a scalar aggregate or a `LIMIT`ed query.
Snapshot size is a function of the rule thresholds, not of how much data the
user owns — a user with 50,000 tasks produces the same snapshot as one with
five.

`now` is a parameter rather than being read inside the service. Every rule
that compares a timestamp to "now" therefore uses the identical instant, so
two rules can never disagree about whether a task was overdue at the moment
the snapshot was taken.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories import intelligence_repository as repo
from app.schemas.intelligence import (
    FinanceCategory,
    FinanceSignal,
    GoalSignal,
    HabitSignal,
    TaskContext,
    UpcomingItem,
)


# =========================================================
# Thresholds
# =========================================================
#
# Every threshold the rules use lives here, as a named constant with the
# reasoning next to it. A rule that inlines `if count > 7` is unexplainable
# from the outside; a rule that compares against `TASK_LOAD_HIGH_THRESHOLD`
# is auditable, and changing the product's notion of "a lot of tasks" becomes
# a one-line edit instead of a hunt through the rule body.

#: Tasks due within this window are "due soon" rather than merely upcoming.
DUE_SOON_HOURS = 72

#: Open planner events per day beyond which the day counts as overloaded.
PLANNER_BUSY_EVENTS_PER_DAY = 5

#: Open planner events beyond which a single day is called out as very heavy.
PLANNER_HEAVY_EVENTS_PER_DAY = 8

#: Horizon the planning rule looks at when looking for overloaded days.
PLANNER_HORIZON_DAYS = 14

#: Open tasks at or above this count are reported as an unusually heavy load.
TASK_LOAD_HIGH_THRESHOLD = 15

#: Open tasks at or above this (but below the high threshold) are reported as a
#: moderately heavy load.
TASK_LOAD_MEDIUM_THRESHOLD = 8

#: Minimum completions in the window before a habit consistency finding fires.
#: Below this the habit is simply young or new, and saying anything about its
#: consistency would be unsupported.
HABIT_MIN_SAMPLE_SIZE = 3

#: Window used for the "consistency" half of the habit rule.
HABIT_CONSISTENCY_WINDOW_DAYS = 14

#: Window used to describe how long a habit has been going without a
#: completion. Always a countdown from the window's end, so it never runs past
#: the window it is measuring.
HABIT_RECENT_WINDOW_DAYS = 7

#: Planner/reminder horizon used to build the `upcoming` list.
UPCOMING_HORIZON_DAYS = 7

#: Cap on entries rendered in the `upcoming` list. Keeps the payload small;
#: the counts in `summary` remain exact regardless of this cap.
UPCOMING_MAX_ITEMS = 12

#: Cap on per-entity insights (one per goal, per habit, per task). Aggregates
#: such as "3 tasks are overdue" are always emitted in full — they are the
#: cheapest and most useful rows — and only entity-level rows are capped.
MAX_ENTITY_INSIGHTS = 10

#: Note recency window used for the "recent notes" context line.
RECENT_NOTES_WINDOW_DAYS = 7


# =========================================================
# Snapshot
# =========================================================


@dataclass(frozen=True)
class LifeOSContext:
    """
    Everything the rule engine is allowed to see.

    A plain frozen dataclass rather than a Pydantic model on purpose: this is
    an internal boundary between two services, never serialized to the client.
    The wire contract is `app.schemas.intelligence`, built by
    `intelligence_service` from this snapshot. Keeping the two separate means
    the transport shape can change without touching rule logic, and rules can
    be tested by constructing a context directly — no database required.
    """

    generated_at: datetime

    # Tasks
    task_total: int = 0
    task_completed: int = 0
    task_incomplete: int = 0
    task_overdue: int = 0
    task_due_soon: int = 0
    task_unlinked: int = 0
    overdue_tasks: list = field(default_factory=list)
    due_soon_tasks: list = field(default_factory=list)

    # Goals
    goal_total: int = 0
    goal_active: int = 0
    goals_without_target_date: int = 0
    goals: list[GoalSignal] = field(default_factory=list)

    # Habits
    habit_active: int = 0
    habits: list[HabitSignal] = field(default_factory=list)

    # Planner
    planner_event_total: int = 0
    planner_unlinked: int = 0
    upcoming_events: list = field(default_factory=list)
    busy_days: list = field(default_factory=list)

    # Reminders
    reminder_total: int = 0
    reminder_pending: int = 0
    follow_up_reminders: list = field(default_factory=list)

    # Notes
    note_total: int = 0
    note_recent: int = 0

    # Finance
    transaction_total: int = 0
    finance: FinanceSignal | None = None

    # Notifications
    unread_notifications: int = 0

    # Dated items from tasks and the planner, merged and ordered, so the UI
    # renders one list instead of one per domain.
    upcoming: list[UpcomingItem] = field(default_factory=list)

    # Which domains actually hold data, so an empty domain reads as "you have
    # none yet" rather than as a finding of zero.
    populated_domains: list[str] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        """Whether the user has any records in any inspected domain."""

        return bool(self.populated_domains)

    @property
    def due_soon_horizon(self) -> datetime:
        return self.generated_at + timedelta(hours=DUE_SOON_HOURS)

    @property
    def upcoming_horizon(self) -> datetime:
        return self.generated_at + timedelta(days=UPCOMING_HORIZON_DAYS)

    @property
    def planner_horizon(self) -> datetime:
        return self.generated_at + timedelta(days=PLANNER_HORIZON_DAYS)

    def has_domain(self, domain: str) -> bool:
        return domain in self.populated_domains


def _record(domain: str, populated: list[str], has_records: bool) -> None:
    if has_records:
        populated.append(domain)


def build_context(
    db: Session,
    user_id: int,
    now: datetime | None = None,
) -> LifeOSContext:
    """
    Build the snapshot for `user_id`.

    `now` defaults to the project's naive-UTC clock, matching
    `reminder_service.utcnow` and the `datetime.utcnow` used as the column
    default on every timestamp in this schema. One clock, so no timestamp is
    ever compared against a differently-defined "today".
    """

    moment = now if now is not None else datetime.utcnow()

    populated: list[str] = []

    # ---------------------------------------------------------
    # Tasks
    # ---------------------------------------------------------

    task_total = repo.count_tasks(db, user_id)
    task_completed = repo.count_completed_tasks(db, user_id)
    task_incomplete = repo.count_incomplete_tasks(db, user_id)
    task_overdue = repo.count_overdue_tasks(db, user_id, moment)
    task_due_soon = repo.count_due_soon_tasks(
        db,
        user_id,
        moment,
        moment + timedelta(hours=DUE_SOON_HOURS),
    )
    task_unlinked = repo.count_unlinked_incomplete_tasks(db, user_id)

    overdue_tasks = repo.get_overdue_tasks(db, user_id, moment)
    due_soon_tasks = repo.get_due_soon_tasks(
        db,
        user_id,
        moment,
        moment + timedelta(hours=DUE_SOON_HOURS),
    )

    _record("task", populated, task_total > 0)

    # ---------------------------------------------------------
    # Goals
    # ---------------------------------------------------------

    goal_total = repo.count_goals(db, user_id)
    goal_active = repo.count_active_goals(db, user_id)
    goals_without_target_date = repo.count_goals_without_target_date(db, user_id)

    goals: list[GoalSignal] = []

    for row in repo.get_goal_signals(db, user_id):
        target_date = row.target_date

        days_to_target = None

        if target_date is not None:
            days_to_target = (target_date.date() - moment.date()).days

        goals.append(
            GoalSignal(
                id=row.id,
                title=row.title,
                progress=row.progress,
                is_completed=row.is_completed,
                target_date=target_date,
                days_to_target=days_to_target,
                incomplete_task_count=row.incomplete_task_count or 0,
                active_habit_count=row.active_habit_count or 0,
            )
        )

    _record("goal", populated, goal_total > 0)

    # ---------------------------------------------------------
    # Habits
    # ---------------------------------------------------------

    habit_active = repo.count_active_habits(db, user_id)

    habits: list[HabitSignal] = []

    for row in repo.get_habit_signals(db, user_id, moment):
        last_completed_on = row["last_completed_on"]

        habits.append(
            HabitSignal(
                id=row["id"],
                title=row["title"],
                frequency=row["frequency"],
                is_active=True,
                current_streak=row["current_streak"],
                longest_streak=row["longest_streak"],
                completions_14d=row["completions_14d"],
                completions_30d=row["completions_30d"],
                # `completed_date` is a `Date`; the schema types this as a
                # datetime for consistency with the other signals, so it is
                # widened at midnight rather than leaking a date.
                last_completed_on=(
                    datetime.combine(last_completed_on, datetime.min.time())
                    if last_completed_on is not None
                    else None
                ),
            )
        )

    _record("habit", populated, habit_active > 0)

    # ---------------------------------------------------------
    # Planner
    # ---------------------------------------------------------

    planner_horizon = moment + timedelta(days=PLANNER_HORIZON_DAYS)

    # `event_date` is a calendar-day column: the Planner always writes it at
    # midnight (`PlannerView` sends `dateKey + "T00:00:00"`). Comparing that
    # midnight against the current *instant* would exclude every block filed
    # under today — today's 00:00 is in the past by definition, so a day of
    # scheduling disappears from the moment the day begins. Both planner
    # queries therefore start from the beginning of the current UTC day, which
    # keeps the naive-UTC convention intact and makes "today's blocks" mean
    # what the Planner page shows under "Today".
    planner_day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)

    planner_event_total = repo.count_planner_events(db, user_id)
    planner_unlinked = repo.count_unlinked_planner_events(db, user_id)

    upcoming_events = repo.get_upcoming_planner_events(
        db,
        user_id,
        planner_day_start,
        moment + timedelta(days=UPCOMING_HORIZON_DAYS),
    )

    busy_days = repo.get_busy_days(
        db,
        user_id,
        planner_day_start,
        planner_horizon,
        PLANNER_BUSY_EVENTS_PER_DAY,
    )

    _record("planner", populated, planner_event_total > 0)

    # ---------------------------------------------------------
    # Reminders
    # ---------------------------------------------------------

    reminder_total = repo.count_reminders(db, user_id)
    reminder_pending = repo.count_pending_reminders(db, user_id)
    follow_up_reminders = repo.get_follow_up_reminders(db, user_id, moment)

    _record("reminder", populated, reminder_total > 0)

    # ---------------------------------------------------------
    # Notes
    # ---------------------------------------------------------

    note_total = repo.count_active_notes(db, user_id)
    note_recent = repo.count_recent_notes(
        db,
        user_id,
        moment - timedelta(days=RECENT_NOTES_WINDOW_DAYS),
    )

    _record("note", populated, note_total > 0)

    # ---------------------------------------------------------
    # Finance
    # ---------------------------------------------------------

    transaction_total = repo.count_transactions(db, user_id)

    finance: FinanceSignal | None = None

    if transaction_total > 0:
        period_start = date(moment.year, moment.month, 1)

        if moment.month == 12:
            period_end = date(moment.year, 12, 31)
        else:
            period_end = date(moment.year, moment.month + 1, 1)

        totals = repo.summarize_transactions(
            db,
            user_id,
            period_start,
            period_end,
        )

        categories = [
            FinanceCategory(
                category=row.category,
                total=row.total if isinstance(row.total, Decimal) else Decimal(str(row.total)),
            )
            for row in repo.get_top_expense_categories(
                db,
                user_id,
                period_start,
                period_end,
            )
        ]

        finance = FinanceSignal(
            period_start=period_start,
            period_end=period_end,
            income_total=_as_decimal(totals["income_total"]),
            expense_total=_as_decimal(totals["expense_total"]),
            transaction_count=totals["transaction_count"],
            top_expense_categories=categories,
        )

    _record("finance", populated, transaction_total > 0)

    # ---------------------------------------------------------
    # Notifications
    # ---------------------------------------------------------

    unread_notifications = repo.count_unread_notifications(db, user_id)

    # ---------------------------------------------------------
    # Upcoming list
    # ---------------------------------------------------------

    upcoming = _build_upcoming(
        overdue_tasks=overdue_tasks,
        due_soon_tasks=due_soon_tasks,
        upcoming_events=upcoming_events,
    )

    return LifeOSContext(
        generated_at=moment,
        task_total=task_total,
        task_completed=task_completed,
        task_incomplete=task_incomplete,
        task_overdue=task_overdue,
        task_due_soon=task_due_soon,
        task_unlinked=task_unlinked,
        overdue_tasks=overdue_tasks,
        due_soon_tasks=due_soon_tasks,
        goal_total=goal_total,
        goal_active=goal_active,
        goals_without_target_date=goals_without_target_date,
        goals=goals,
        habit_active=habit_active,
        habits=habits,
        planner_event_total=planner_event_total,
        planner_unlinked=planner_unlinked,
        upcoming_events=upcoming_events,
        busy_days=busy_days,
        reminder_total=reminder_total,
        reminder_pending=reminder_pending,
        follow_up_reminders=follow_up_reminders,
        note_total=note_total,
        note_recent=note_recent,
        transaction_total=transaction_total,
        finance=finance,
        unread_notifications=unread_notifications,
        upcoming=upcoming,
        populated_domains=populated,
    )


def _as_decimal(value) -> Decimal:
    """
    Coerce a summed amount to an exact two-decimal `Decimal`.

    SQLite returns an integer for a `SUM` over whole numbers and PostgreSQL a
    `Decimal`; both are normalized here so the JSON always carries a decimal
    string, matching what `TransactionResponse` already emits.
    """

    if value is None:
        return Decimal("0.00")

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value)).quantize(Decimal("0.01"))


def _build_upcoming(
    overdue_tasks: list,
    due_soon_tasks: list,
    upcoming_events: list,
) -> list[UpcomingItem]:
    """
    Merge dated items from every domain into one ordered list.

    Uniform `UpcomingItem` shape across task/planner sources so the UI renders
    a single list without branching per domain. Ordering is by due instant
    with the id as a tiebreaker, so an identical reload never reshuffles rows.
    """

    items: list[UpcomingItem] = []

    for row in overdue_tasks:
        items.append(
            UpcomingItem(
                id=f"overdue:{row.id}",
                domain="task",
                kind="overdue",
                title=row.title,
                due_at=row.due_date,
                route="tasks",
                entity_type="task",
                entity_id=row.id,
            )
        )

    for row in due_soon_tasks:
        items.append(
            UpcomingItem(
                id=f"due_soon:{row.id}",
                domain="task",
                kind="due_soon",
                title=row.title,
                due_at=row.due_date,
                route="tasks",
                entity_type="task",
                entity_id=row.id,
            )
        )

    for row in upcoming_events:
        items.append(
            UpcomingItem(
                id=f"event:{row.id}",
                domain="planner",
                kind="planner_event",
                title=row.title,
                # `start_time` is the instant the block actually begins;
                # `event_date` is the calendar day it is filed under. The
                # former orders the list correctly across a multi-day span.
                due_at=row.start_time,
                route="planner",
                entity_type="planner_event",
                entity_id=row.id,
            )
        )

    items.sort(key=lambda item: (item.due_at, item.id))

    return items[:UPCOMING_MAX_ITEMS]


def build_task_context(context: LifeOSContext) -> TaskContext:
    """Project the snapshot's task figures onto the wire model."""

    return TaskContext(
        total=context.task_total,
        incomplete=context.task_incomplete,
        completed=context.task_completed,
        overdue=context.task_overdue,
        due_soon=context.task_due_soon,
        unlinked=context.task_unlinked,
    )