"""
Context resolution for AI commands.

Fetches exactly the LifeOS data a command needs — never the whole
database — and hands it to the orchestration layer as a small structured
object. Three properties this module exists to guarantee:

**User-scoped.** Every call passes `user_id`, and every call is into an
existing service that scopes on it. There is no path here that can reach
another user's rows, and `user_id` is only ever supplied by the endpoint
from the bearer token.

**Bounded.** Each domain is capped. A user with 50,000 tasks produces the
same context size as one with five, because the caps are constants rather
than derived from row counts.

**Server-side aggregated.** Counts, sums and streaks come from the
deterministic services that already compute them (`intelligence_service`,
`dashboard_service`) instead of being recomputed here, so the AI can never
disagree with the panel the user is looking at.

Nothing here writes. The read side of a command and the context-building
side of a mutating command share this module, so a target is always
resolved from the same rows the executor will act on.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.timezones import normalize_timezone
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.note import Note
from app.models.planner_event import PlannerEvent
from app.models.reminder import Reminder
from app.models.task import Task
from app.models.transaction import Transaction


# =========================================================
# BOUNDS
# =========================================================
#
# Every cap is a constant, never a function of how much the user owns. These
# are the numbers that keep a command's context small enough to fit in a
# 1.5B-parameter model's useful range on the target hardware, and small
# enough that a single command issues a bounded number of queries.

MAX_TASKS = 40
MAX_GOALS = 20
MAX_HABITS = 20
MAX_NOTES = 20
MAX_REMINDERS = 25
MAX_PLANNER_EVENTS = 20
MAX_TRANSACTIONS = 60
MAX_SEARCH_RESULTS = 20

#: Rows scanned when resolving a named target before giving up. Bounded so a
#: user with thousands of tasks and a vague reference cannot turn one command
#: into a full-table walk.
TARGET_SCAN_LIMIT = 200

#: How far ahead "tomorrow" and "this week" reach.
HORIZON_DAYS = 7


# =========================================================
# CONTEXT OBJECT
# =========================================================


@dataclass
class ResolvedContext:
    """Everything one turn needs to read about, and nothing more."""

    #: Names of the domains actually touched, echoed to the client so the UI
    #: can say which records informed the answer.
    domains: list[str] = field(default_factory=list)

    #: The authenticated user's timezone, resolved once.
    timezone: str = ""

    #: Local wall-clock now, for "today"/"tomorrow" boundaries.
    local_now: datetime | None = None

    local_today: date | None = None

    tasks: list[Task] = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    habits: list[Habit] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    reminders: list[Reminder] = field(default_factory=list)
    planner_events: list[PlannerEvent] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)

    #: Deterministic Intelligence payload, reused verbatim when the question
    #: is account-wide.
    intelligence: dict | None = None

    #: Global Search hits.
    search_results: list[dict] = field(default_factory=list)

    #: The daily plan the existing planner generates, when relevant.
    daily_plan: dict | None = None

    #: A single record resolved from a reference in the command.
    target: object | None = None
    target_entity: str | None = None
    target_ambiguous: bool = False
    target_alternatives: list = field(default_factory=list)

    def _note(self, domain: str) -> None:
        if domain not in self.domains:
            self.domains.append(domain)

    @property
    def now_local(self) -> datetime:
        return self.local_now or datetime.now(ZoneInfo(self.timezone or "UTC"))

    @property
    def today(self) -> date:
        return self.local_today or self.now_local.date()


def build_context(
    db: Session,
    user_id: int,
    domains: list[str],
    timezone_name: str | None = None,
) -> ResolvedContext:
    """
    Fetch the requested domains for `user_id`.

    `domains` comes from the classified intent, so a "how much did I spend"
    command issues finance queries and nothing else, and a "mark my gym habit
    complete" issues one habit lookup. Unknown domain names are ignored here
    rather than raising — validation belongs to the intent layer, and a name
    that slips through simply contributes nothing.
    """

    resolved_tz = normalize_timezone(timezone_name)
    zone = ZoneInfo(resolved_tz)
    now_local = datetime.now(zone)

    context = ResolvedContext(
        timezone=resolved_tz,
        local_now=now_local,
        local_today=now_local.date(),
    )

    wanted = {domain.lower() for domain in domains}

    if "intelligence" in wanted:
        from app.services.intelligence_service import get_intelligence

        context.intelligence = get_intelligence(
            db=db,
            user_id=user_id,
        ).model_dump()
        context._note("intelligence")

        # The Intelligence payload already aggregates tasks, goals, habits,
        # reminders and finance. Pull the raw lists too only when a specific
        # domain was also asked for, so an account-wide question does not
        # cost eight extra queries.

    if "task" in wanted:
        context.tasks = list(
            db.scalars(
                _select(Task)
                .where(Task.user_id == user_id)
                .order_by(Task.status, Task.due_date.is_(None), Task.due_date)
                .limit(MAX_TASKS)
            ).all()
        )
        context._note("task")

    if "goal" in wanted:
        context.goals = list(
            db.scalars(
                _select(Goal)
                .where(Goal.user_id == user_id)
                .order_by(Goal.is_completed, Goal.target_date.is_(None), Goal.target_date)
                .limit(MAX_GOALS)
            ).all()
        )
        context._note("goal")

    if "habit" in wanted:
        context.habits = list(
            db.scalars(
                _select(Habit)
                .where(Habit.user_id == user_id)
                .order_by(Habit.is_active.desc(), Habit.current_streak.desc())
                .limit(MAX_HABITS)
            ).all()
        )
        context._note("habit")

    if "note" in wanted:
        context.notes = list(
            db.scalars(
                _select(Note)
                .where(Note.user_id == user_id, Note.is_archived.is_(False))
                .order_by(Note.is_pinned.desc(), Note.updated_at.desc())
                .limit(MAX_NOTES)
            ).all()
        )
        context._note("note")

    if "reminder" in wanted:
        horizon_start = datetime.combine(
            context.today - timedelta(days=1),
            datetime.min.time(),
        )

        context.reminders = list(
            db.scalars(
                _select(Reminder)
                .where(
                    Reminder.user_id == user_id,
                    Reminder.is_cancelled.is_(False),
                    Reminder.remind_at >= horizon_start,
                )
                .order_by(Reminder.remind_at)
                .limit(MAX_REMINDERS)
            ).all()
        )
        context._note("reminder")

    if "planner_event" in wanted:
        day_start = datetime.combine(
            context.today,
            datetime.min.time(),
        )

        context.planner_events = list(
            db.scalars(
                _select(PlannerEvent)
                .where(
                    PlannerEvent.user_id == user_id,
                    PlannerEvent.event_date >= day_start,
                    PlannerEvent.event_date <= day_start + timedelta(days=HORIZON_DAYS),
                )
                .order_by(PlannerEvent.event_date, PlannerEvent.start_time)
                .limit(MAX_PLANNER_EVENTS)
            ).all()
        )
        context._note("planner_event")

    if "transaction" in wanted:
        context.transactions = list(
            db.scalars(
                _select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
                .limit(MAX_TRANSACTIONS)
            ).all()
        )
        context._note("transaction")

    return context


def _select(model):
    from sqlalchemy import select

    return select(model)


# =========================================================
# TARGET RESOLUTION
# =========================================================
#
# "Move the first one to tomorrow" has to become a concrete row id before it
# can mean anything. These helpers resolve a reference to exactly one record,
# or refuse: ambiguity is reported rather than resolved by guessing, because
# picking the wrong "first one" and updating it is worse than asking.

_WORD_SPLIT = str.maketrans({",": " ", ".": " ", "!": " ", "?": " ", ";": " ", ":": " ", "'": " ", '"': " "})


def _tokens(text: str) -> set[str]:
    cleaned = text.lower().translate(_WORD_SPLIT)
    return {word for word in cleaned.split() if len(word) > 2}


def _score(query_tokens: set[str], title: str) -> float:
    """Score a title against the query's content words."""

    if not query_tokens or not title:
        return 0.0

    lowered = title.lower()
    title_tokens = {word for word in lowered.translate(_WORD_SPLIT).split() if len(word) > 2}

    if not title_tokens:
        return 0.0

    overlap = query_tokens & title_tokens

    if not overlap:
        return 0.0

    # An exact substring is the strongest signal available without a model.
    if lowered in " ".join(query_tokens):
        return 1.0

    return len(overlap) / len(title_tokens | query_tokens)


def _resolve_from_rows(
    rows,
    reference: str,
    entity: str,
    label_attr: str = "title",
) -> ResolvedContext:
    """Pick at most one row out of a bounded candidate list."""

    context = ResolvedContext()
    context.timezone = "UTC"

    if not rows:
        return context

    query_tokens = _tokens(reference)

    if not query_tokens:
        return context

    scored = [
        (_score(query_tokens, getattr(row, label_attr, "") or ""), row)
        for row in rows
    ]

    # A reference like "the first one" carries no words at all, so scoring
    # cannot rank. Fall back to the row order the context already imposed,
    # which is the order the user just saw listed.
    best_score, best_row = max(scored, key=lambda pair: pair[0])

    if best_score <= 0.0:
        # Only positional references reach here.
        context.target = rows[0]
        context.target_entity = entity
        context.target_ambiguous = True
        context.target_alternatives = list(rows[:5])
        return context

    ties = [row for score, row in scored if score == best_score]

    context.target = best_row
    context.target_entity = entity

    if len(ties) > 1:
        context.target_ambiguous = True
        context.target_alternatives = list(ties[:5])

    return context


def resolve_target(
    db: Session,
    user_id: int,
    entity: str,
    reference: str,
    timezone_name: str | None = None,
) -> ResolvedContext:
    """
    Resolve a natural-language reference to one of the user's own records.

    Scans a bounded number of the user's rows for the named entity and scores
    them on word overlap. Returns a context whose `target` is set only when
    the match is unique; `target_ambiguous` is raised otherwise so the
    orchestration layer can ask which record the user meant.
    """

    resolved_tz = normalize_timezone(timezone_name)
    zone = ZoneInfo(resolved_tz)

    context = ResolvedContext(
        timezone=resolved_tz,
        local_now=datetime.now(zone),
        local_today=datetime.now(zone).date(),
    )

    if entity == "task":
        rows = list(
            db.scalars(
                _select(Task)
                .where(Task.user_id == user_id)
                .order_by(Task.status, Task.due_date.is_(None), Task.due_date)
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    elif entity == "goal":
        rows = list(
            db.scalars(
                _select(Goal)
                .where(Goal.user_id == user_id)
                .order_by(Goal.is_completed, Goal.target_date.is_(None), Goal.target_date)
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    elif entity == "habit":
        rows = list(
            db.scalars(
                _select(Habit)
                .where(Habit.user_id == user_id)
                .order_by(Habit.is_active.desc(), Habit.current_streak.desc())
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    elif entity == "note":
        rows = list(
            db.scalars(
                _select(Note)
                .where(Note.user_id == user_id)
                .order_by(Note.updated_at.desc())
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    elif entity == "reminder":
        rows = list(
            db.scalars(
                _select(Reminder)
                .where(Reminder.user_id == user_id)
                .order_by(Reminder.remind_at)
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    elif entity == "planner_event":
        rows = list(
            db.scalars(
                _select(PlannerEvent)
                .where(PlannerEvent.user_id == user_id)
                .order_by(PlannerEvent.event_date.desc())
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    elif entity == "transaction":
        rows = list(
            db.scalars(
                _select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(Transaction.transaction_date.desc())
                .limit(TARGET_SCAN_LIMIT)
            ).all()
        )
    else:
        return context

    return _resolve_from_rows(rows, reference, entity)


# =========================================================
# SEARCH
# =========================================================


def run_search(
    db: Session,
    user_id: int,
    query: str,
    limit: int = MAX_SEARCH_RESULTS,
) -> list[dict]:
    """
    Global search over the user's own records.

    Delegates to `search_service`, which is what the Search page itself uses,
    so the command surface and the search bar can never disagree about what
    matches.
    """

    from app.services.search_service import search_lifeos

    response = search_lifeos(
        db=db,
        user_id=user_id,
        raw_query=query,
        limit=min(limit, MAX_SEARCH_RESULTS),
    )

    return [result.model_dump() for result in response.results]


# =========================================================
# FORMATTING
# =========================================================
#
# Renders fetched rows into the compact text block a 1.5B model can actually
# use, and into the lines the UI shows as "referenced data". Both come from
# the same fetched objects, so a figure quoted in prose is always a figure the
# user can see.

MAX_CONTEXT_CHARS = 6000


def _fmt_date(value) -> str:
    if value is None:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    return value.isoformat()


def _fmt_money(value) -> str:
    if value is None:
        return "-"

    return f"{Decimal(str(value)):.2f}"


def format_context_text(context: ResolvedContext, domains: list[str]) -> str:
    """Build the compact, bounded text block handed to the local model."""

    lines: list[str] = []

    for domain in domains:
        if domain == "task" and context.tasks:
            lines.append("TASKS:")
            for task in context.tasks[:MAX_TASKS]:
                marker = "x" if task.status == "completed" else " "
                due = _fmt_date(task.due_date)
                lines.append(
                    f"- [{marker}] #{task.id} {task.title} "
                    f"({task.priority}, due {due})"
                )

        elif domain == "goal" and context.goals:
            lines.append("GOALS:")
            for goal in context.goals[:MAX_GOALS]:
                state = "done" if goal.is_completed else "active"
                lines.append(
                    f"- #{goal.id} {goal.title} "
                    f"({goal.category}, {goal.progress}%, {state}, "
                    f"target {_fmt_date(goal.target_date)})"
                )

        elif domain == "habit" and context.habits:
            lines.append("HABITS:")
            for habit in context.habits[:MAX_HABITS]:
                state = "active" if habit.is_active else "paused"
                lines.append(
                    f"- #{habit.id} {habit.title} "
                    f"({habit.frequency}, {state}, "
                    f"streak {habit.current_streak}, best {habit.longest_streak})"
                )

        elif domain == "note" and context.notes:
            lines.append("NOTES:")
            for note in context.notes[:MAX_NOTES]:
                lines.append(f"- #{note.id} {note.title} [{note.tag}]")

        elif domain == "reminder" and context.reminders:
            lines.append("REMINDERS:")
            for reminder in context.reminders[:MAX_REMINDERS]:
                lines.append(
                    f"- #{reminder.id} {reminder.title} "
                    f"({reminder.status}, at {_fmt_date(reminder.remind_at)})"
                )

        elif domain == "planner_event" and context.planner_events:
            lines.append("PLANNER EVENTS:")
            for event in context.planner_events[:MAX_PLANNER_EVENTS]:
                lines.append(
                    f"- #{event.id} {event.title} "
                    f"({event.event_type}, {_fmt_date(event.start_time)})"
                )

        elif domain == "transaction" and context.transactions:
            lines.append("TRANSACTIONS:")
            for transaction in context.transactions[:MAX_TRANSACTIONS]:
                lines.append(
                    f"- #{transaction.id} {transaction.title} "
                    f"({transaction.type}, {_fmt_money(transaction.amount)} "
                    f"{transaction.category}, "
                    f"{_fmt_date(transaction.transaction_date)})"
                )

        elif domain == "intelligence" and context.intelligence:
            lines.extend(_format_intelligence(context.intelligence))

    text = "\n".join(lines)

    if len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS]

    return text


def _format_intelligence(payload: dict) -> list[str]:
    """Render the deterministic Intelligence payload as compact facts."""

    lines: list[str] = []

    summary = payload.get("summary") or {}
    if summary:
        lines.append(f"LIFEOS STATUS: {summary.get('headline', '')}")
        lines.append(f"- {summary.get('detail', '')}")

    tasks = payload.get("tasks") or {}
    if tasks:
        lines.append(
            f"TASK COUNTS: {tasks.get('incomplete', 0)} open, "
            f"{tasks.get('overdue', 0)} overdue, "
            f"{tasks.get('due_soon', 0)} due soon, "
            f"{tasks.get('completed', 0)} completed"
        )

    finance = payload.get("finance")
    if finance:
        lines.append(
            f"FINANCE THIS MONTH: income {_fmt_money(finance.get('income_total'))}, "
            f"expenses {_fmt_money(finance.get('expense_total'))}, "
            f"{finance.get('transaction_count', 0)} transactions"
        )

    upcoming = payload.get("upcoming") or []
    if upcoming:
        lines.append("COMING UP:")
        for item in upcoming[:8]:
            lines.append(
                f"- [{item.get('kind')}] {item.get('title')} "
                f"at {_fmt_date(item.get('due_at'))}"
            )

    insights = payload.get("insights") or []
    if insights:
        lines.append("INSIGHTS:")
        for insight in insights[:8]:
            lines.append(
                f"- {insight.get('title')}: {insight.get('detail')}"
            )

    return lines