"""
Response contracts for the LifeOS Intelligence layer.

Design notes
------------
Intelligence is **derived**, not stored. Every number in these payloads is
computed from the caller's own persisted records on each request, so there is
no table of generated insights to keep in sync and nothing to migrate.

Three rules shape the shapes below:

1. **Explainable.** An insight carries a `detail` string built only from counts
   the user could verify themselves ("3 tasks are overdue"), never a causal or
   psychological claim. There is deliberately no "score" field — priority is a
   closed `low | medium | high` set that each rule assigns explicitly.

2. **Narrow.** Only the fields a UI needs to render a row and navigate are
   exposed. Note bodies, transaction notes, habit descriptions and task
   descriptions are never included, matching the rule Global Search already
   follows.

3. **Sectioned, not prose.** The envelope returns structured lists and summary
   objects. There is no single generated text blob, so the frontend renders
   each rule with real components rather than splitting a paragraph.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


# Which rule produced an insight. Closed set, so the frontend can style by type
# and a future rule is an additive change rather than a breaking one.
InsightType = Literal[
    "overdue",
    "upcoming",
    "goal_risk",
    "habit_consistency",
    "planning",
    "task_load",
    "finance",
    "reminder",
    "data_quality",
]

# Every insight belongs to exactly one LifeOS domain.
InsightDomain = Literal[
    "task",
    "goal",
    "habit",
    "planner",
    "note",
    "finance",
    "reminder",
    "notification",
    "system",
]

# Small closed set, assigned explicitly by each rule. Never a computed
# "AI score" — the value is a plain function of the rule's own thresholds.
InsightPriority = Literal["low", "medium", "high"]

# Aggregate condition of the snapshot, used only for the summary headline.
AttentionLevel = Literal["clear", "watch", "busy"]


class Insight(BaseModel):
    """
    One deterministic, explainable observation about the user's own data.

    `id` is a stable slug (`"overdue_tasks"`, `"goal_risk:12"`) so the UI can
    key and de-duplicate rows without inventing an identity scheme. `route` is
    an existing app view key and is only ever set when a real destination
    exists — a null route means "no action button", never a dead control.
    """

    id: str
    type: InsightType
    priority: InsightPriority
    domain: InsightDomain
    title: str

    # The explanation. Factual, quantitative, and checkable against the
    # underlying records — e.g. "Goal 'Ship v2' is at 25% progress with a
    # target date of 2026-10-10 and 8 incomplete linked tasks."
    detail: str

    # Short leading figure for the row, e.g. "3 overdue". None when the rule
    # has no single number to lead with.
    metric: str | None = None

    action_label: str | None = None
    route: str | None = None

    # Set when the insight is about one specific record. The id is always the
    # caller's own — the repository that produced it scoped on user_id.
    entity_type: str | None = None
    entity_id: int | None = None


class AttentionSummary(BaseModel):
    """Overall condition of the snapshot, for the panel headline."""

    level: AttentionLevel
    headline: str
    detail: str
    overdue_count: int = 0
    due_soon_count: int = 0
    incomplete_task_count: int = 0
    unread_notification_count: int = 0


class TaskContext(BaseModel):
    total: int
    incomplete: int
    completed: int
    overdue: int
    due_soon: int
    unlinked: int = Field(
        default=0,
        description="Incomplete tasks with no goal attached.",
    )


class GoalSignal(BaseModel):
    """One goal, as the intelligence layer sees it. Per-goal rules write here."""

    id: int
    title: str
    progress: int
    is_completed: bool
    target_date: datetime | None = None
    days_to_target: int | None = None
    incomplete_task_count: int = 0
    active_habit_count: int = 0


class HabitSignal(BaseModel):
    """One habit with the consistency figures the rules reason about."""

    id: int
    title: str
    frequency: str
    is_active: bool
    current_streak: int
    longest_streak: int
    completions_14d: int
    completions_30d: int
    last_completed_on: datetime | None = None


class UpcomingItem(BaseModel):
    """
    A dated thing to attend to: an overdue task, a task due soon, an upcoming
    planner event, or a pending reminder. Deliberately uniform so the UI can
    render one list without branching per domain.
    """

    id: str
    domain: InsightDomain
    kind: Literal["overdue", "due_soon", "planner_event", "reminder"]
    title: str
    due_at: datetime
    route: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None


class FinanceCategory(BaseModel):
    category: str
    total: Decimal


class FinanceSignal(BaseModel):
    """
    Factual totals for the current calendar month, from persisted
    transactions. Totals are Decimals so the JSON carries the same exact
    decimal strings the Transactions endpoint already returns.
    """

    period_start: date
    period_end: date
    income_total: Decimal = Decimal("0.00")
    expense_total: Decimal = Decimal("0.00")
    transaction_count: int = 0
    top_expense_categories: list[FinanceCategory] = Field(default_factory=list)


class IntelligenceResponse(BaseModel):
    """
    The intelligence envelope.

    `insights` is the master, already-sorted list; the UI filters it by
    `type` and `priority` to build its own sections. Deriving those views
    client-side instead of shipping a second, duplicated copy of every insight
    keeps the payload small — the performance constraint this app is held to.
    """

    generated_at: datetime
    summary: AttentionSummary
    tasks: TaskContext
    goals: list[GoalSignal] = Field(default_factory=list)
    habits: list[HabitSignal] = Field(default_factory=list)
    upcoming: list[UpcomingItem] = Field(default_factory=list)
    finance: FinanceSignal | None = None
    insights: list[Insight] = Field(default_factory=list)

    # False only when the user has no records in any inspected domain. The UI
    # shows its empty state from this rather than inferring emptiness from
    # empty arrays.
    has_data: bool = True

    # Which domains actually hold data, so the UI can say "no habits yet"
    # instead of implying a habit finding of zero.
    populated_domains: list[str] = Field(default_factory=list)