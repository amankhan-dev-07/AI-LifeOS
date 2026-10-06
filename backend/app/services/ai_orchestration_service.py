"""
AI Command orchestration.

Sits between the HTTP endpoint and the existing domain services. It owns the
four things Phase 14 adds to the previous brain:

    understand  →  resolve context  →  plan  →  confirm?  →  execute

Design rules this module holds to:

**The model never mutates anything.** `intent_service` interprets language
into a closed vocabulary; every write goes through a domain service below,
with parameters re-validated by that service. There is no path from model
text to the database.

**Confirmation is a property of the plan, not of the model.** Whether a step
needs approval is computed here from the operation and the entity
(`_needs_confirmation`), and a step that requires confirmation is never
executed by the same request that proposed it — the plan is parked under a
`plan_id` and only `/ai/confirm` will run it. The model cannot set or clear
that flag.

**No fake success.** `ActionStep.status` starts at `pending` and only the
executor writes `succeeded`/`failed`, from a real service return. The prose
the client shows is assembled from those recorded outcomes, so "Done" can
only be said when a step actually succeeded, and a partially-applied plan
says which half worked.

**Bounded context.** Nothing here loads a domain the classified intent did not
ask for, and every fetch goes through `ai_context_service`, which caps every
query.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai import intent_service as intent
from app.ai import tools as ai_tools
from app.schemas.ai import (
    ActionPlanSummary,
    ActionStep,
    AIChatResponse,
)
from app.services import ai_context_service as ctx
from app.services.nl_datetime_service import (
    AmbiguousTime,
    describe_datetime,
    resolve_datetime,
)


# =========================================================
# PLAN REGISTRY
# =========================================================
#
# Plans awaiting confirmation are held in memory for a short window. This is
# deliberately not a table: an unapproved plan has changed nothing, so losing
# it on restart costs nothing, and keeping it out of the database avoids
# persisting model-influenced content. Entries are keyed by an unguessable id
# AND bound to the user who created them, so one user's plan id cannot be
# replayed by another.
#
# Bounded on purpose — the target hardware is memory-constrained, and a plan
# that is never approved should not accumulate.

MAX_PENDING_PLANS = 64
PLAN_TTL_SECONDS = 15 * 60

_pending_plans: dict[str, tuple[int, float, "ExecutionPlan"]] = {}


def _now() -> float:
    from time import time

    return time()


def store_plan(user_id: int, plan: "ExecutionPlan") -> str:
    """Park a plan for approval and return its id."""

    plan_id = uuid.uuid4().hex

    _prune_plans()
    _pending_plans[plan_id] = (user_id, _now() + PLAN_TTL_SECONDS, plan)

    return plan_id


def take_plan(plan_id: str, user_id: int) -> "ExecutionPlan | None":
    """
    Claim a stored plan for execution, removing it in the process.

    Ownership is checked here, not only when the plan was created: a leaked
    id is useless without the same session that generated it. Consuming the
    entry means a plan can be approved exactly once — a replayed confirm
    returns nothing rather than running the writes twice.
    """

    _prune_plans()

    entry = _pending_plans.get(plan_id)

    if entry is None:
        return None

    owner, expires_at, plan = entry

    if owner != user_id:
        return None

    del _pending_plans[plan_id]

    if expires_at < _now():
        return None

    return plan


def discard_plan(plan_id: str, user_id: int) -> bool:
    """Drop a plan the user declined."""

    return take_plan(plan_id, user_id) is not None


def _prune_plans() -> None:
    """Evict expired entries, then the oldest, to stay under the cap."""

    current = _now()

    for key in [k for k, (_, exp, _) in _pending_plans.items() if exp < current]:
        del _pending_plans[key]

    overflow = len(_pending_plans) - MAX_PENDING_PLANS

    if overflow <= 0:
        return

    for key, _ in sorted(
        _pending_plans.items(),
        key=lambda item: item[1][1],
    )[:overflow]:
        del _pending_plans[key]


# =========================================================
# INTERNAL PLAN MODEL
# =========================================================


@dataclass
class PlannedStep:
    """A step before validation against the domain schemas."""

    operation: str
    entity: str
    description: str
    parameters: dict
    #: Resolved target id, when one was found by reference.
    target_id: int | None = None
    target_label: str | None = None
    confirmation_required: bool = False
    confirmation_reason: str | None = None
    #: Resolved call into the tool layer, bound after parameter validation.
    runner: object | None = None
    #: Extra data the executor needs but must not persist.
    execution_meta: dict = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """A validated, ordered sequence of steps for one command."""

    steps: list[PlannedStep] = field(default_factory=list)
    #: Prose answer, already assembled from real data.
    answer: str = ""
    #: Domains actually read for this turn.
    context_used: list[str] = field(default_factory=list)
    ai_online: bool = False
    intent: str = "unknown"
    clarification_question: str | None = None
    #: True when the plan only proposes and needs approval to apply.
    awaiting_user: bool = False

    @property
    def requires_confirmation(self) -> bool:
        return any(step.confirmation_required for step in self.steps)


def to_schema(plan: ExecutionPlan, plan_id: str | None) -> ActionPlanSummary | None:
    """Project the internal plan onto the wire contract."""

    if not plan.steps:
        return None

    return ActionPlanSummary(
        plan_id=plan_id or "",
        requires_confirmation=plan.requires_confirmation,
        steps=[
            ActionStep(
                order=index,
                operation=step.operation,
                entity=step.entity,
                description=step.description,
                target_id=step.target_id,
                target_label=step.target_label,
                confirmation_required=step.confirmation_required,
                confirmation_reason=step.confirmation_reason,
                parameters=_safe_parameters(step.parameters),
            )
            for index, step in enumerate(plan.steps, start=1)
        ],
    )


def _safe_parameters(parameters: dict) -> dict:
    """
    Strip internals before a parameter dict goes to the client.

    The bound `runner` and any execution metadata never leave the process;
    the user sees only the values they asked to change.
    """

    return {
        key: value
        for key, value in parameters.items()
        if key not in {"runner", "execution_meta"}
        and isinstance(value, (str, int, float, bool, type(None)))
    }


# =========================================================
# CONFIRMATION POLICY
# =========================================================
#
# The whole safety surface of Phase 14 is this table plus the fact that a
# confirmed step is never run by the request that proposed it.
#
# `read`/`search` never need approval — they change nothing. A single
# create/update/complete is low-impact and runs directly, but only when the
# target was unambiguous (see `_build_update_step`). Everything destructive,
# everything bulk, and anything that writes to the ledger is gated.

_CONFIRM_ENTITY_NAMES = {
    "task": "task",
    "goal": "goal",
    "habit": "habit",
    "note": "note",
    "reminder": "reminder",
    "planner_event": "planner event",
    "transaction": "transaction",
}


def _needs_confirmation(operation: str, entity: str) -> tuple[bool, str | None]:
    """Decide whether a single step requires explicit approval."""

    if operation == "delete":
        return True, (
            f"Deleting a {_CONFIRM_ENTITY_NAMES.get(entity, entity)} is permanent."
        )

    if operation == "plan":
        return True, "Applying a plan creates planner events."

    # A financial write is confirmed regardless of size. The ledger is the one
    # domain where a wrong write is not correctable by editing the record.
    if entity == "transaction" and operation in {"create", "update"}:
        return True, "This writes a record to your finances."

    return False, None


# =========================================================
# STEP BUILDERS
# =========================================================
#
# One builder per (operation, entity). Each returns a `PlannedStep` with a
# bound `runner` — the tool-layer function that will perform it — or `None`
# when the command cannot be turned into something safe to run.
#
# A builder returning `None` is not a failure: it means the command is missing
# something (no title, an unresolvable target, an unparsed date). The caller
# turns that into a clarification question rather than a half-built write.
#
# Every builder validates its parameters through the domain schema before
# binding a runner, so a bad value fails here with a readable message rather
# than as a 422 from deep inside a service.

_CREATE_BUILDERS = {}
_UPDATE_BUILDERS = {}


def _builders_for(step: intent.IntentStep) -> tuple[object | None, bool]:
    """`(builder, takes_targets)` for a classified step."""

    builder = _BUILDERS.get((step.operation, step.entity))

    return builder, builder in _BUILDERS_WITH_TARGETS


def _build_create_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
) -> PlannedStep | None:
    """Build a create step for any supported entity."""

    entity = step.entity
    fragment = step.fragment
    title = intent._clean_title(fragment)

    needs_confirmation, confirmation_reason = _needs_confirmation("create", entity)

    if entity == "task":
        if not title:
            return None

        priority = intent.extract_priority(fragment)

        due = _optional_datetime(
            fragment,
            timezone_name,
            require_time=False,
        )

        return PlannedStep(
            operation="create",
            entity="task",
            description=(
                f"Create task “{title}”"
                + (f" due {describe_datetime(due)}" if due else "")
            ),
            parameters={
                "title": title,
                "priority": priority,
                "due_date": due,
            },
            runner=_runner_create_task,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "goal":
        if not title:
            return None

        category = _goal_category(fragment)

        return PlannedStep(
            operation="create",
            entity="goal",
            description=f"Create goal “{title}”",
            parameters={
                "title": title,
                "category": category,
            },
            runner=_runner_create_goal,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "habit":
        if not title:
            return None

        frequency = intent._frequency(fragment) or "daily"

        return PlannedStep(
            operation="create",
            entity="habit",
            description=f"Create {frequency} habit “{title}”",
            parameters={
                "title": title,
                "frequency": frequency,
            },
            runner=_runner_create_habit,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "note":
        if not title:
            return None

        tag = _note_tag(fragment)

        return PlannedStep(
            operation="create",
            entity="note",
            description=f"Create note “{title}”",
            parameters={
                "title": title,
                "content": "",
                "tag": tag,
            },
            runner=_runner_create_note,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "reminder":
        # A reminder without a time is the one create that cannot be guessed:
        # the backend rejects a past instant outright, and "tomorrow" for a
        # reminder means a specific minute, not a date.
        try:
            remind_at = resolve_datetime(
                fragment,
                timezone_name=timezone_name,
                require_time=True,
            )
        except AmbiguousTime:
            return None

        if remind_at is None:
            return None

        # "remind me to call the client at 6 pm" — the title is what is left
        # once the time clause is removed.
        cleaned = _strip_time_clause(fragment)

        reminder_title = intent._clean_title(cleaned)

        if not reminder_title:
            reminder_title = "Reminder"

        return PlannedStep(
            operation="create",
            entity="reminder",
            description=(
                f"Create reminder “{reminder_title}” "
                f"for {describe_datetime(remind_at)}"
            ),
            parameters={
                "title": reminder_title[:200],
                "remind_at": remind_at,
            },
            runner=_runner_create_reminder,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "transaction":
        parsed = _parse_amount(fragment)

        if parsed is None or not title:
            return None

        amount, kind = parsed

        return PlannedStep(
            operation="create",
            entity="transaction",
            description=(
                f"Record {kind} of {amount:.2f} for “{title}”"
            ),
            parameters={
                "title": title,
                "amount": float(amount),
                "type": kind,
                "category": _transaction_category(fragment),
                "transaction_date": date.today(),
            },
            runner=_runner_create_transaction,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    return None


def _build_update_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
    entities: dict,
) -> PlannedStep | None:
    """
    Build an update step.

    An update needs a target, so the reference in the message is resolved
    against the user's own rows first. An ambiguous or missing target returns
    `None` and becomes a clarification question — the alternative, picking the
    first row that shares a word, is how "move the first one to tomorrow"
    ends up editing the wrong task.
    """

    entity = step.entity
    fragment = step.fragment

    match = entities.get(entity)

    if match is None:
        return None

    target = match.get("target")

    if target is None or match.get("ambiguous"):
        return None

    target_id = target.id
    label = _target_label(target, entity)

    needs_confirmation, confirmation_reason = _needs_confirmation("update", entity)

    if entity == "task":
        updates = {}

        if "priority" in fragment:
            updates["priority"] = intent.extract_priority(fragment)

        if _mentions_reschedule(fragment):
            due = _optional_datetime(fragment, timezone_name)

            if due is not None:
                updates["due_date"] = due

        if not updates:
            return None

        return PlannedStep(
            operation="update",
            entity="task",
            description=f"Update task “{label}” ({_describe_updates(updates)})",
            parameters={
                "task_id": target_id,
                **updates,
            },
            target_id=target_id,
            target_label=label,
            runner=_runner_update_task,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "goal":
        updates = {}

        progress = _extract_progress(fragment)
        if progress is not None:
            updates["progress"] = progress

        if "category" in fragment:
            category = _goal_category(fragment)

            if category:
                updates["category"] = category

        if not updates:
            return None

        return PlannedStep(
            operation="update",
            entity="goal",
            description=f"Update goal “{label}” ({_describe_updates(updates)})",
            parameters={
                "goal_id": target_id,
                **updates,
            },
            target_id=target_id,
            target_label=label,
            runner=_runner_update_goal,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "habit":
        updates = {}

        frequency = intent._frequency(fragment)
        if frequency:
            updates["frequency"] = frequency

        if "pause" in fragment or "deactivate" in fragment:
            updates["is_active"] = False
        elif "activate" in fragment or "resume" in fragment:
            updates["is_active"] = True

        if not updates:
            return None

        return PlannedStep(
            operation="update",
            entity="habit",
            description=f"Update habit “{label}” ({_describe_updates(updates)})",
            parameters={
                "habit_id": target_id,
                **updates,
            },
            target_id=target_id,
            target_label=label,
            runner=_runner_update_habit,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "reminder":
        try:
            remind_at = resolve_datetime(
                fragment,
                timezone_name=timezone_name,
                require_time=True,
            )
        except AmbiguousTime:
            return None

        if remind_at is None:
            return None

        return PlannedStep(
            operation="update",
            entity="reminder",
            description=(
                f"Move reminder “{label}” to {describe_datetime(remind_at)}"
            ),
            parameters={
                "reminder_id": target_id,
                "remind_at": remind_at,
            },
            target_id=target_id,
            target_label=label,
            runner=_runner_update_reminder,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    if entity == "transaction":
        updates = {}

        parsed = _parse_amount(fragment)
        if parsed is not None:
            amount, kind = parsed
            updates["amount"] = float(amount)
            updates["type"] = kind

        category = _transaction_category(fragment)
        if category:
            updates["category"] = category

        if not updates:
            return None

        return PlannedStep(
            operation="update",
            entity="transaction",
            description=f"Update transaction “{label}” ({_describe_updates(updates)})",
            parameters={
                "transaction_id": target_id,
                **updates,
            },
            target_id=target_id,
            target_label=label,
            runner=_runner_update_transaction,
            confirmation_required=needs_confirmation,
            confirmation_reason=confirmation_reason,
        )

    return None


def _build_complete_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
    entities: dict,
) -> PlannedStep | None:
    """Build a complete step for task, goal, habit or reminder."""

    entity = step.entity
    match = entities.get(entity)

    if match is None:
        return None

    target = match.get("target")

    if target is None or match.get("ambiguous"):
        return None

    target_id = target.id
    label = _target_label(target, entity)

    runners = {
        "task": ("task", _runner_complete_task),
        "goal": ("goal", _runner_complete_goal),
        "habit": ("habit", _runner_complete_habit),
        "reminder": ("reminder", _runner_complete_reminder),
    }

    entry = runners.get(entity)

    if entry is None:
        return None

    _, runner = entry

    return PlannedStep(
        operation="complete",
        entity=entity,
        description=f"Mark {_CONFIRM_ENTITY_NAMES[entity]} “{label}” complete",
        parameters={f"{entity}_id": target_id},
        target_id=target_id,
        target_label=label,
        runner=runner,
    )


def _build_delete_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
    entities: dict,
) -> PlannedStep | None:
    """
    Build a delete step.

    Always requires confirmation, and always names the record it will remove —
    the confirmation panel is only useful if the user can see what is about to
    go away before saying yes.
    """

    entity = step.entity
    match = entities.get(entity)

    if match is None:
        return None

    target = match.get("target")

    if target is None or match.get("ambiguous"):
        return None

    target_id = target.id
    label = _target_label(target, entity)

    runners = {
        "task": _runner_delete_task,
        "goal": _runner_delete_goal,
        "habit": _runner_delete_habit,
        "note": _runner_delete_note,
        "reminder": _runner_delete_reminder,
        "planner_event": _runner_delete_planner_event,
        "transaction": _runner_delete_transaction,
    }

    runner = runners.get(entity)

    if runner is None:
        return None

    needs, reason = _needs_confirmation("delete", entity)

    return PlannedStep(
        operation="delete",
        entity=entity,
        description=f"Delete {_CONFIRM_ENTITY_NAMES[entity]} “{label}”",
        parameters={f"{entity}_id": target_id},
        target_id=target_id,
        target_label=label,
        confirmation_required=needs,
        confirmation_reason=reason,
        runner=runner,
    )


def _build_search_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
) -> PlannedStep | None:
    """
    Build a search step.

    Search is a read, so it executes immediately and never needs approval.
    The query is the message minus the search verb, and an empty one is
    rejected here rather than hitting the 422 in `search_service`.
    """

    query = _strip_search_verb(step.fragment)

    if len(query) < 2:
        return None

    return PlannedStep(
        operation="search",
        entity="intelligence",
        description=f"Search LifeOS for “{query}”",
        parameters={"query": query[:100]},
        runner=_runner_search,
    )


def _build_plan_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
) -> PlannedStep | None:
    """
    Build a plan step.

    The deterministic planner already generates a proposal; applying it is a
    separate, confirmed step because it will create multiple planner events
    and may overwrite existing ones. The step runs the planner (read-only),
    then if the user approves, a second pass creates the events.
    """

    return PlannedStep(
        operation="plan",
        entity="planner_event",
        description="Generate a daily plan from tasks, habits and goals",
        parameters={},
        confirmation_required=True,
        confirmation_reason="Applying a plan creates planner events.",
        runner=_runner_apply_plan,
        execution_meta={"propose_first": True},
    )


def _build_read_step(
    db: Session,
    user_id: int,
    step: intent.IntentStep,
    timezone_name: str,
) -> PlannedStep | None:
    """
    Build a read step.

    Read steps execute immediately and never need confirmation. The prose
    answer is assembled from the context that was already fetched — the model
    is only used to *explain* the numbers, never to produce them.
    """

    entity = step.entity

    if entity == "intelligence":
        return PlannedStep(
            operation="read",
            entity="intelligence",
            description="Show LifeOS overview",
            parameters={},
            runner=_runner_read_intelligence,
        )

    return PlannedStep(
        operation="read",
        entity=entity,
        description=f"Show your {_CONFIRM_ENTITY_NAMES.get(entity, entity)}s",
        parameters={},
        runner=_make_read_runner(entity),
    )


# =========================================================
# PARAMETER HELPERS
# =========================================================
#
# Small readers that turn a fragment of the user's own words into a validated
# parameter. Each is total: it returns `None` for "not said", never a guess,
# and the caller turns `None` into a clarification question.


def _target_label(target, entity: str) -> str:
    """The name of a record, for the confirmation panel."""

    label = getattr(target, "title", None) or getattr(target, "name", None)

    return str(label) if label else f"{_CONFIRM_ENTITY_NAMES.get(entity, entity)} #{target.id}"


def _optional_datetime(text: str, timezone_name: str, require_time: bool = False):
    """
    Resolve a time phrase, treating "said nothing" and "said something
    unusable" as one outcome.
    """

    try:
        return resolve_datetime(
            text,
            timezone_name=timezone_name,
            require_time=require_time,
        )
    except AmbiguousTime:
        return None


def _mentions_reschedule(text: str) -> bool:
    lowered = text.lower()

    return any(
        marker in lowered
        for marker in (
            "move",
            "reschedule",
            "push",
            "postpone",
            "due",
            "deadline",
            "by ",
        )
    )


def _describe_updates(updates: dict) -> str:
    """Render an update dict for the confirmation copy."""

    parts = []

    for key, value in updates.items():
        if key == "due_date" and value is not None:
            parts.append(f"due {describe_datetime(value)}")
        elif key == "remind_at" and value is not None:
            parts.append(f"reminder time {describe_datetime(value)}")
        else:
            parts.append(f"{key.replace('_', ' ')} → {value}")

    return ", ".join(parts)


def _extract_progress(text: str) -> int | None:
    """Read "set progress to 40" / "40% done", clamped to the schema's 0-100."""

    lowered = text.lower()

    for pattern in (
        r"progress\s*(?:to|is)?\s*(\d{1,3})",
        r"(\d{1,3})\s*%\s*(?:done|complete|completed)",
        r"(\d{1,3})\s*percent",
    ):
        match = re.search(pattern, lowered)

        if match:
            return max(0, min(100, int(match.group(1))))

    return None


_GOAL_CATEGORIES = (
    "career",
    "health",
    "fitness",
    "finance",
    "education",
    "learning",
    "personal",
    "relationship",
    "family",
    "travel",
    "project",
    "business",
)

_TRANSACTION_CATEGORIES = (
    "food",
    "transport",
    "rent",
    "salary",
    "shopping",
    "health",
    "entertainment",
    "utilities",
    "education",
    "travel",
    "subscription",
    "gift",
    "other",
)


def _match_vocabulary(text: str, vocabulary: tuple[str, ...], default: str) -> str:
    """First vocabulary word the user actually said, else the default."""

    lowered = text.lower()

    for word in vocabulary:
        if word in lowered:
            return word

    return default


def _goal_category(text: str) -> str:
    return _match_vocabulary(text, _GOAL_CATEGORIES, "general")


def _note_tag(text: str) -> str:
    lowered = text.lower()

    match = re.search(r"#([a-z0-9_-]{2,30})", lowered)

    if match:
        return match.group(1)

    if " about " in lowered:
        candidate = lowered.split(" about ", 1)[1].split()[0]
        candidate = re.sub(r"[^a-z0-9_-]", "", candidate)

        if len(candidate) >= 2:
            return candidate

    return "General"


def _transaction_category(text: str) -> str:
    category = _match_vocabulary(text, _TRANSACTION_CATEGORIES, "General")

    return category.capitalize()


_AMOUNT_RE = re.compile(
    r"(?:(?:rs\.?|inr|₹|\$|usd)\s*)?(\d+(?:[.,]\d{1,2})?)"
    r"\s*(k|kilk)?",
    re.IGNORECASE,
)


def _parse_amount(text: str) -> tuple[Decimal, str] | None:
    """
    Read a money amount and its direction ("I spent 250 on books").

    Returns `(amount, "expense"|"income")`. A bare number with no currency
    marker is still accepted, because "i spent 250 on books" is unambiguous
    English — but "add 3 tasks" never reaches here, because the transaction
    phrases always carry a spending or income verb.
    """

    match = _AMOUNT_RE.search(text)

    if match is None:
        return None

    raw = match.group(1).replace(",", ".")

    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return None

    if match.group(2):
        amount = amount * 1000

    if amount <= 0:
        return None

    lowered = text.lower()

    if any(word in lowered for word in ("income", "earned", "salary", "received", "paisa", "kama")):
        return amount, "income"

    return amount, "expense"


#: Time clauses removed from a fragment before the remainder is read as a
#: title, so "call the client at 6 pm" yields "call the client".
_TIME_CLAUSE_RE = re.compile(
    r"\b(?:at|by|around|before|after|on)?\s*"
    r"(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|morning|afternoon|evening|night|noon|midnight|midday)\b.*$",
    re.IGNORECASE,
)

_SEARCH_VERB_PREFIXES = (
    "search for",
    "search my",
    "search",
    "find my",
    "find the",
    "find notes about",
    "find notes on",
    "find note about",
    "find note on",
    "find note",
    "find task",
    "find goal",
    "find habit",
    "find",
    "look for",
    "show me notes about",
    "show me notes on",
    "notes about",
    "notes on",
)


def _strip_search_verb(text: str) -> str:
    lowered = intent._normalize(text)

    for prefix in _SEARCH_VERB_PREFIXES:
        if lowered.startswith(prefix):
            return lowered[len(prefix) :].strip(" .,:;!?-")

    return lowered.strip(" .,:;!?-")


def _strip_time_clause(text: str) -> str:
    """
    Remove the trailing time clause from a fragment.

    Used before a title is read off a reminder or event command. Only a
    *trailing* clause is removed, so "call the client at 6 pm about the
    invoice" keeps the word that identifies the thing being reminded about.
    """

    stripped = _TIME_CLAUSE_RE.sub("", text).strip(" .,:;!?-")

    return stripped or text.strip()


# =========================================================
# RUNNERS
# =========================================================
#
# One runner per (operation, entity). Each takes the *validated* parameters a
# builder produced and performs exactly one thing through the existing service
# layer. A runner returns a real result dict and never raises past the executor:
# a service error is caught here and turned into `success: False` with the
# message the service actually produced.
#
# Because a runner's return value is what the executor reports, "done" can only
# be said when a service really returned — there is no path here that
# synthesises a success.


def _run(tool, db: Session, user_id: int, **kwargs) -> dict:
    """
    Call a tool, converting a service exception into a failed result.

    HTTPException is the domain layer's normal way of refusing a write (a
    reminder in the past, an inactive habit). It is caught here rather than
    propagated, because the executor must be able to keep the remaining steps
    running and report exactly which ones failed and why.
    """

    try:
        result = tool(db=db, user_id=user_id, **kwargs)

    except HTTPException as exc:
        return {
            "success": False,
            "error": str(exc.detail),
        }

    except ValueError as exc:
        return {
            "success": False,
            "error": str(exc),
        }

    return result if isinstance(result, dict) else {"success": True, "result": result}


def _ok(payload_key: str, payload: dict, label: str) -> str:
    """Build a success message from a tool's real return payload."""

    record = payload.get(payload_key) or {}

    identifier = record.get("id")

    return f"{label} saved (id {identifier})."


def _fail(payload: dict, fallback: str) -> str:
    return str(payload.get("error") or fallback)


# --- create --------------------------------------------------------------


def _runner_create_task(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.task import TaskCreate

    try:
        payload = TaskCreate(
            title=parameters["title"],
            description=parameters.get("description") or None,
            priority=parameters.get("priority") or "medium",
            due_date=parameters.get("due_date"),
            estimated_minutes=int(parameters.get("estimated_minutes", 45)),
        )
    except ValueError as exc:
        return {"success": False, "error": f"That task was not valid: {exc}"}

    result = _run(
        ai_tools.create_task_tool,
        db,
        user_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        estimated_minutes=payload.estimated_minutes,
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("task", result, "Task")}


def _runner_create_goal(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.goal import GoalCreate

    try:
        payload = GoalCreate(
            title=parameters["title"],
            description=parameters.get("description") or None,
            category=parameters.get("category") or "general",
            target_date=parameters.get("target_date"),
        )
    except ValueError as exc:
        return {"success": False, "error": f"That goal was not valid: {exc}"}

    result = _run(
        ai_tools.create_goal_tool,
        db,
        user_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        target_date=payload.target_date,
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("goal", result, "Goal")}


def _runner_create_habit(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.habit import HabitCreate

    try:
        payload = HabitCreate(
            title=parameters["title"],
            description=parameters.get("description") or None,
            frequency=parameters.get("frequency") or "daily",
        )
    except ValueError as exc:
        return {"success": False, "error": f"That habit was not valid: {exc}"}

    result = _run(
        ai_tools.create_habit_tool,
        db,
        user_id,
        title=payload.title,
        description=payload.description,
        frequency=payload.frequency,
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("habit", result, "Habit")}


def _runner_create_note(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.note import NoteCreate

    try:
        payload = NoteCreate(
            title=parameters["title"],
            content=parameters.get("content") or "",
            tag=parameters.get("tag") or "General",
            is_pinned=bool(parameters.get("is_pinned")),
        )
    except ValueError as exc:
        return {"success": False, "error": f"That note was not valid: {exc}"}

    result = _run(
        ai_tools.create_note_tool,
        db,
        user_id,
        title=payload.title,
        content=payload.content,
        tag=payload.tag,
        is_pinned=payload.is_pinned,
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("note", result, "Note")}


def _runner_create_reminder(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    result = _run(
        ai_tools.create_reminder_tool,
        db,
        user_id,
        title=parameters["title"],
        remind_at=parameters["remind_at"],
        message=parameters.get("message"),
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("reminder", result, "Reminder")}


def _runner_create_transaction(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.transaction import TransactionCreate

    try:
        payload = TransactionCreate(
            title=parameters["title"],
            amount=Decimal(str(parameters["amount"])),
            type=parameters["type"],
            category=parameters.get("category") or "General",
            transaction_date=parameters.get("transaction_date") or date.today(),
            notes=parameters.get("notes"),
        )
    except ValueError as exc:
        return {"success": False, "error": f"That transaction was not valid: {exc}"}

    result = _run(
        ai_tools.create_transaction_tool,
        db,
        user_id,
        title=payload.title,
        amount=float(payload.amount),
        type=payload.type,
        category=payload.category,
        transaction_date=payload.transaction_date,
        notes=payload.notes,
    )

    if not result.get("success"):
        return result

    record = result.get("transaction") or {}

    return {
        **result,
        "message": (
            f"Recorded {payload.type} of {payload.amount} "
            f"for “{payload.title}” (id {record.get('id')})."
        ),
    }


# --- update --------------------------------------------------------------


def _runner_update_task(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.task import TaskUpdate

    updates = {
        key: parameters[key]
        for key in ("title", "description", "status", "priority", "due_date")
        if parameters.get(key) is not None
    }

    try:
        payload = TaskUpdate(**updates)
    except ValueError as exc:
        return {"success": False, "error": f"That change was not valid: {exc}"}

    result = _run(
        ai_tools.update_task_tool,
        db,
        user_id,
        task_id=parameters["task_id"],
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
    )

    if not result.get("success"):
        return result

    return {
        **result,
        "message": f"Task updated ({_describe_updates(updates)}).",
    }


def _runner_update_goal(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.goal import GoalUpdate

    updates = {
        key: parameters[key]
        for key in ("title", "description", "category", "progress", "target_date")
        if parameters.get(key) is not None
    }

    try:
        payload = GoalUpdate(**updates)
    except ValueError as exc:
        return {"success": False, "error": f"That change was not valid: {exc}"}

    result = _run(
        ai_tools.update_goal_tool,
        db,
        user_id,
        goal_id=parameters["goal_id"],
        title=payload.title,
        description=payload.description,
        category=payload.category,
        target_date=payload.target_date,
        progress=payload.progress,
    )

    if not result.get("success"):
        return result

    return {
        **result,
        "message": f"Goal updated ({_describe_updates(updates)}).",
    }


def _runner_update_habit(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.habit import HabitUpdate

    updates = {
        key: parameters[key]
        for key in ("title", "description", "frequency", "is_active")
        if parameters.get(key) is not None
    }

    try:
        payload = HabitUpdate(**updates)
    except ValueError as exc:
        return {"success": False, "error": f"That change was not valid: {exc}"}

    result = _run(
        ai_tools.update_habit_tool,
        db,
        user_id,
        habit_id=parameters["habit_id"],
        title=payload.title,
        description=payload.description,
        frequency=payload.frequency,
        is_active=payload.is_active,
    )

    if not result.get("success"):
        return result

    return {
        **result,
        "message": f"Habit updated ({_describe_updates(updates)}).",
    }


def _runner_update_reminder(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    result = _run(
        ai_tools.update_reminder_tool,
        db,
        user_id,
        reminder_id=parameters["reminder_id"],
        remind_at=parameters["remind_at"],
    )

    if not result.get("success"):
        return result

    return {
        **result,
        "message": (
            f"Reminder moved to {describe_datetime(parameters['remind_at'])}."
        ),
    }


def _runner_update_transaction(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    from app.schemas.transaction import TransactionUpdate

    updates = {
        key: parameters[key]
        for key in ("title", "amount", "type", "category", "transaction_date", "notes")
        if parameters.get(key) is not None
    }

    try:
        payload = TransactionUpdate(**updates)
    except ValueError as exc:
        return {"success": False, "error": f"That change was not valid: {exc}"}

    result = _run(
        ai_tools.update_transaction_tool,
        db,
        user_id,
        transaction_id=parameters["transaction_id"],
        title=payload.title,
        amount=float(payload.amount) if payload.amount is not None else None,
        type=payload.type,
        category=payload.category,
        transaction_date=payload.transaction_date,
        notes=payload.notes,
    )

    if not result.get("success"):
        return result

    return {
        **result,
        "message": f"Transaction updated ({_describe_updates(updates)}).",
    }


# --- complete ------------------------------------------------------------


def _runner_complete_task(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    result = _run(
        ai_tools.complete_task_tool,
        db,
        user_id,
        task_id=parameters["task_id"],
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("task", result, "Task")}


def _runner_complete_goal(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    result = _run(
        ai_tools.complete_goal_tool,
        db,
        user_id,
        goal_id=parameters["goal_id"],
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("goal", result, "Goal")}


def _runner_complete_habit(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    completed_on = parameters.get("completed_date")

    result = _run(
        ai_tools.complete_habit_tool,
        db,
        user_id,
        habit_id=parameters["habit_id"],
        completed_date=completed_on,
    )

    if not result.get("success"):
        return result

    record = result.get("habit") or {}

    return {
        **result,
        "message": (
            f"Habit logged for {completed_on.isoformat() if completed_on else 'today'}. "
            f"Streak is now {record.get('current_streak', 0)}."
        ),
    }


def _runner_complete_reminder(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    result = _run(
        ai_tools.complete_reminder_tool,
        db,
        user_id,
        reminder_id=parameters["reminder_id"],
    )

    if not result.get("success"):
        return result

    return {**result, "message": _ok("reminder", result, "Reminder")}


# --- delete --------------------------------------------------------------
#
# Every one of these is behind a confirmation, so the runner's job is only to
# perform the delete the user already approved. It still reports the real
# result rather than assuming success.


def _delete_result(result: dict, key: str, label: str) -> dict:
    if not result.get("success"):
        return result

    return {**result, "message": _ok(key, result, label)}


def _runner_delete_task(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(ai_tools.delete_task_tool, db, user_id, task_id=parameters["task_id"]),
        "task",
        "Task",
    )


def _runner_delete_goal(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(ai_tools.delete_goal_tool, db, user_id, goal_id=parameters["goal_id"]),
        "goal",
        "Goal",
    )


def _runner_delete_habit(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(ai_tools.delete_habit_tool, db, user_id, habit_id=parameters["habit_id"]),
        "habit",
        "Habit",
    )


def _runner_delete_note(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(ai_tools.delete_note_tool, db, user_id, note_id=parameters["note_id"]),
        "note",
        "Note",
    )


def _runner_delete_reminder(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(
            ai_tools.delete_reminder_tool,
            db,
            user_id,
            reminder_id=parameters["reminder_id"],
        ),
        "reminder",
        "Reminder",
    )


def _runner_delete_planner_event(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(
            ai_tools.delete_planner_event_tool,
            db,
            user_id,
            event_id=parameters["planner_event_id"],
        ),
        "event",
        "Planner event",
    )


def _runner_delete_transaction(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return _delete_result(
        _run(
            ai_tools.delete_transaction_tool,
            db,
            user_id,
            transaction_id=parameters["transaction_id"],
        ),
        "transaction",
        "Transaction",
    )


# --- read ----------------------------------------------------------------


def _runner_read_intelligence(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    """
    The account-wide read.

    Figures come from `intelligence_service`, which is the same deterministic
    engine the Intelligence panel uses — the AI cannot disagree with the panel
    because it is reading the panel's output.
    """

    result = _run(ai_tools.get_intelligence_tool, db, user_id)

    if not result.get("success", True):
        return result

    return {
        "success": True,
        "intelligence": result,
        "message": "Read your LifeOS overview.",
    }


def _make_read_runner(entity: str):
    """
    Build the read runner for one domain.

    Read steps re-fetch through the same service the screen uses rather than
    reusing whatever the context step happened to load, so an answer and the
    panel it describes are computed from the same code path at the same
    moment.
    """

    tools = {
        "task": (ai_tools.get_tasks_tool, "tasks", "task"),
        "goal": (ai_tools.get_goals_tool, "goals", "goal"),
        "habit": (ai_tools.get_habits_tool, "habits", "habit"),
        "note": (ai_tools.get_notes_tool, "notes", "note"),
        "reminder": (ai_tools.get_reminders_tool, "reminders", "reminder"),
        "transaction": (ai_tools.get_transactions_tool, "transactions", "transaction"),
        "planner_event": (ai_tools.get_planner_events_tool, "events", "planner event"),
    }

    entry = tools.get(entity)

    if entry is None:
        return _runner_read_unsupported

    tool, collection_key, label = entry

    def runner(db: Session, user_id: int, parameters: dict, context=None) -> dict:
        # Reads are scoped to the user's timezone-aware window where the
        # underlying service accepts one, so "my reminders" and "my planner"
        # mean the same day the screens mean.
        kwargs: dict = {}

        if entity == "reminder" and context is not None:
            kwargs["start_date"] = datetime.combine(
                context.today,
                datetime.min.time(),
            )

        if entity == "planner_event" and context is not None:
            kwargs["start_date"] = datetime.combine(
                context.today,
                datetime.min.time(),
            )
            kwargs["end_date"] = datetime.combine(
                context.today + timedelta(days=ctx.HORIZON_DAYS),
                datetime.min.time(),
            )

        try:
            result = tool(db=db, user_id=user_id, **kwargs)
        except HTTPException as exc:
            return {"success": False, "error": str(exc.detail)}

        if not result.get("success", True):
            return result

        records = result.get(collection_key) or []

        return {
            "success": True,
            "records": records,
            "message": (
                f"Read {len(records)} "
                f"{_CONFIRM_ENTITY_NAMES.get(entity, entity)} record(s)."
            ),
        }

    return runner


def _runner_read_unsupported(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    return {
        "success": False,
        "error": "I do not have a way to read that yet.",
    }


# --- search --------------------------------------------------------------


def _runner_search(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    """
    Search across the user's own domains.

    Delegates to `search_service` — the same service the Search page calls —
    so the command surface and the search bar can never disagree about what
    matched.
    """

    try:
        result = ai_tools.search_lifeos_tool(
            db=db,
            user_id=user_id,
            query=parameters["query"],
            limit=ctx.MAX_SEARCH_RESULTS,
        )
    except HTTPException as exc:
        return {"success": False, "error": str(exc.detail)}

    results = result.get("results") or []

    return {
        "success": True,
        "results": results,
        "message": (
            f"Found {result.get('count', len(results))} match(es) for "
            f"“{parameters['query']}”."
        ),
    }


# --- plan ----------------------------------------------------------------


def _runner_generate_plan(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    """
    Generate a daily plan from the existing deterministic planner.

    This step *proposes*. Applying the proposal — creating planner events — is
    a separate, confirmed step (`_runner_apply_plan`) that only runs once the
    user approves, which is why creating events is gated even though writing a
    task is not.
    """

    try:
        plan = ai_tools.get_daily_plan_tool(db=db, user_id=user_id)
    except HTTPException as exc:
        return {"success": False, "error": str(exc.detail)}

    return {
        "success": True,
        "plan": plan,
        "message": f"Proposed a plan with {len(plan.get('plan', []))} block(s).",
    }


def _runner_apply_plan(db: Session, user_id: int, parameters: dict, context=None) -> dict:
    """
    Create planner events for a plan the user has now approved.

    Deliberately not atomic. A partial failure is reported as a partial
    success with the blocks that landed, because silently rolling back — or
    silently finishing — both misrepresent what happened on disk. Each block
    goes through `create_planner_event_tool`, so every row is validated by the
    planner service exactly as a manually-created event would be.
    """

    day = context.today if context else date.today()

    created: list[dict] = []
    failures: list[str] = []

    for block in parameters.get("blocks") or []:
        try:
            start = datetime.combine(day, time.fromisoformat(block["start_time"]))
            end = datetime.combine(day, time.fromisoformat(block["end_time"]))
        except (KeyError, ValueError):
            failures.append(f"block {block!r} had an unreadable time")
            continue

        result = _run(
            ai_tools.create_planner_event_tool,
            db,
            user_id,
            title=block.get("title") or "Focus block",
            description=None,
            event_date=datetime.combine(day, datetime.min.time()),
            start_time=start,
            end_time=end,
            event_type="task" if block.get("type") == "task" else "habit",
            task_id=block.get("id") if block.get("type") == "task" else None,
            habit_id=block.get("id") if block.get("type") == "habit" else None,
        )

        if result.get("success"):
            created.append(result.get("event") or {})
        else:
            failures.append(_fail(result, "Could not create the block."))

    return {
        "success": not failures and bool(created),
        "created": created,
        "failures": failures,
        "message": (
            f"Created {len(created)} planner block(s) for "
            f"{day.isoformat()}."
            if not failures
            else (
                f"Created {len(created)} planner block(s); "
                f"{len(failures)} failed — "
                + "; ".join(failures[:3])
            )
        ),
    }


# =========================================================
# EXECUTION
# =========================================================
#
# The only place a `PlannedStep` is turned into a database change. Two rules:
#
# * Steps run in order and each one's outcome is recorded from its runner's
#   real return value. A step that fails does not abort the rest — a
#   multi-step command where the task was created but the reminder's time was
#   past should say so, not report nothing or report everything.
# * A confirmed step is never executed here. It is parked under a plan id and
#   only `confirm_plan` reaches these runners for it.


def execute_plan(db: Session, user_id: int, plan: ExecutionPlan, context=None) -> ExecutionPlan:
    """
    Run every step that does not require approval, recording real outcomes.

    Returns the same plan, with each step's `status`, `result_message` and the
    rendered `answer` filled in from what the runner actually returned. The
    prose is composed from those same recorded values, never from the runner's
    input, so an answer cannot describe work that did not happen.
    """

    for step in plan.steps:
        if step.confirmation_required:
            # Left `pending` on purpose: it has not run, and the client must
            # not be able to render it as done.
            continue

        outcome = _run_step(db, user_id, step, context)

        step.execution_meta["status"] = (
            "succeeded" if outcome.get("success") else "failed"
        )
        step.execution_meta["result_message"] = outcome.get("message") or _fail(
            outcome,
            "That step did not complete.",
        )
        step.execution_meta["answer"] = _answer_for(step, outcome)

        if not outcome.get("success"):
            step.execution_meta["error"] = _fail(outcome, "That step did not complete.")

    return plan


def _run_step(db: Session, user_id: int, step: PlannedStep, context) -> dict:
    """
    Run one step, converting any escaping exception into a failed result.

    A runner is expected to return `success: False` rather than raise, but a
    database-level error inside a service would otherwise become a 500 on the
    command path — taking the rest of the plan with it and reporting nothing.
    """

    runner = step.runner

    if runner is None:
        return {
            "success": False,
            "error": "That action is not supported.",
        }

    parameters = dict(step.parameters)
    parameters.update(step.execution_meta.get("extra_parameters") or {})

    try:
        return runner(db=db, user_id=user_id, parameters=parameters, context=context)

    except HTTPException as exc:
        return {"success": False, "error": str(exc.detail)}

    except Exception as exc:  # noqa: BLE001
        # Reported, never swallowed: the response carries the real message so
        # a failure is visible rather than dressed up as a success.
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def plan_status_steps(plan: ExecutionPlan) -> list[ActionStep]:
    """Project execution outcomes onto the wire schema."""

    summary = to_schema(plan, plan_id="")

    if summary is None:
        return []

    steps: list[ActionStep] = []

    for schema_step, internal in zip(summary.steps, plan.steps):
        status = internal.execution_meta.get("status")

        steps.append(
            schema_step.model_copy(
                update={
                    "status": status if status in {"succeeded", "failed"} else "pending",
                    "result_message": (
                        internal.execution_meta.get("result_message")
                        or internal.execution_meta.get("error")
                    ),
                }
            )
        )

    return steps


# =========================================================
# ANSWER FORMATTING
# =========================================================
#
# The prose the user reads. Every figure here is one the process just read
# from the user's own records, and the model — when reachable — only rewrites
# this text, it never supplies the numbers.


MAX_LIST_ITEMS = 12


def _bullet_list(items: list[str], empty: str) -> str:
    if not items:
        return empty

    shown = items[:MAX_LIST_ITEMS]
    remainder = len(items) - len(shown)

    lines = [f"- {item}" for item in shown]

    if remainder > 0:
        lines.append(f"- …and {remainder} more.")

    return "\n".join(lines)


def _format_tasks(records: list[dict]) -> str:
    rows = (record for record in records if record.get("status") != "completed")

    if not rows:
        completed = [record for record in records if record.get("status") == "completed"]
        return _bullet_list(
            [f"{record['title']}" for record in completed],
            "You have no tasks at all yet.",
        )

    return _bullet_list(
        [
            f"{record['title']} ({record.get('priority', 'medium')}"
            + (f", due {record['due_date']}" if record.get("due_date") else "")
            + ")"
            for record in rows
        ],
        "You have no open tasks.",
    )


def _format_goals(records: list[dict]) -> str:
    active = [record for record in records if not record.get("is_completed")]

    if not active:
        return "All your goals are complete."

    return _bullet_list(
        [
            f"{record['title']} ({record.get('category', 'general')}, "
            f"{record.get('progress', 0)}%)"
            for record in active
        ],
        "You have no active goals.",
    )


def _format_habits(records: list[dict]) -> str:
    active = [record for record in records if record.get("is_active")]

    if not active:
        return "You have no active habits."

    return _bullet_list(
        [
            f"{record['title']} — {record.get('current_streak', 0)} day streak "
            f"(best {record.get('longest_streak', 0)})"
            for record in active
        ],
        "You have no active habits.",
    )


def _format_notes(records: list[dict]) -> str:
    return _bullet_list(
        [
            f"{record['title']} [{record.get('tag', 'General')}]"
            for record in records
        ],
        "You have no notes.",
    )


def _format_reminders(records: list[dict]) -> str:
    upcoming = [
        record
        for record in records
        if not record.get("is_cancelled") and not record.get("is_completed")
    ]

    if not upcoming:
        return "You have no upcoming reminders."

    return _bullet_list(
        [
            f"{record['title']} — {record.get('remind_at', 'no time set')}"
            for record in upcoming
        ],
        "You have no upcoming reminders.",
    )


def _format_planner_events(records: list[dict]) -> str:
    return _bullet_list(
        [
            f"{record['title']} "
            f"({record.get('start_time') or 'no time'}–{record.get('end_time') or 'no time'})"
            for record in records
        ],
        "You have nothing scheduled.",
    )


def _format_transactions(records: list[dict]) -> str:
    """
    Summarise the ledger.

    Income and expense are totalled from the fetched rows rather than reported
    by the model, and the total is stated alongside the rows it came from so
    the figure is checkable.
    """

    if not records:
        return "You have no transactions recorded."

    income = Decimal("0")
    expenses = Decimal("0")

    for record in records:
        try:
            amount = Decimal(str(record.get("amount", "0")))
        except InvalidOperation:
            continue

        if str(record.get("type", "")).lower() in {"income", "credit"}:
            income += amount
        else:
            expenses += amount

    header = (
        f"{len(records)} transaction(s): "
        f"{income:.2f} income, {expenses:.2f} expenses."
    )

    return header + "\n" + _bullet_list(
        [
            f"{record['title']} — {record.get('amount')} "
            f"({record.get('category', 'General')}, "
            f"{record.get('transaction_date', 'no date')})"
            for record in records
        ],
        "",
    ).lstrip("\n")


def _format_intelligence(payload: dict) -> str:
    """Render the deterministic Intelligence payload as prose."""

    if not payload:
        return "I could not read your LifeOS overview."

    summary = payload.get("summary") or {}
    tasks = payload.get("tasks") or {}
    finance = payload.get("finance") or {}

    headline = summary.get("headline") or "Here is where you stand."
    lines = [f"LifeOS overview:\n{headline}"]

    if summary.get("detail"):
        lines.append(summary["detail"])

    if tasks:
        lines.append(
            f"Tasks: {tasks.get('incomplete', 0)} open, "
            f"{tasks.get('overdue', 0)} overdue, "
            f"{tasks.get('due_soon', 0)} due soon."
        )

    if finance:
        lines.append(
            f"Finance this month: {finance.get('income_total', 0)} in, "
            f"{finance.get('expense_total', 0)} out."
        )

    upcoming = payload.get("upcoming") or []
    if upcoming:
        lines.append(
            _bullet_list(
                [
                    f"{item.get('title')} ({item.get('kind')}) "
                    f"at {item.get('due_at')}"
                    for item in upcoming[:MAX_LIST_ITEMS]
                ],
                "",
            ).lstrip("\n")
        )

    insights = payload.get("insights") or []
    if insights:
        lines.append(
            _bullet_list(
                [
                    f"{insight.get('title')}: {insight.get('detail')}"
                    for insight in insights[:MAX_LIST_ITEMS]
                ],
                "",
            ).lstrip("\n")
        )

    return "\n".join(line for line in lines if line)


def _format_search(results: list[dict]) -> str:
    if not results:
        return "I found nothing matching that in your LifeOS data."

    return _bullet_list(
        [
            f"[{result.get('entity_type', 'record')}] "
            f"{result.get('title', 'Untitled')}"
            + (f" — {result.get('snippet')}" if result.get("snippet") else "")
            for result in results[:MAX_LIST_ITEMS]
        ],
        "I found nothing matching that in your LifeOS data.",
    )


def _format_plan(plan: dict) -> str:
    blocks = plan.get("plan") or []

    if not blocks:
        return (
            "I have nothing to plan — there are no pending tasks or active habits "
            "to schedule."
        )

    lines = [
        _bullet_list(
            [
                f"{block.get('start_time')}–{block.get('end_time')} "
                f"{block.get('title')}"
                for block in blocks
            ],
            "",
        ).lstrip("\n")
    ]

    summary = plan.get("summary") or {}

    if summary:
        lines.append(
            f"Based on {summary.get('pending_tasks', 0)} pending task(s), "
            f"{summary.get('active_habits', 0)} active habit(s) and "
            f"{summary.get('active_goals', 0)} active goal(s)."
        )

    return "\n".join(line for line in lines if line)


_FORMATTERS = {
    "task": _format_tasks,
    "goal": _format_goals,
    "habit": _format_habits,
    "note": _format_notes,
    "reminder": _format_reminders,
    "planner_event": _format_planner_events,
    "transaction": _format_transactions,
    "intelligence": _format_intelligence,
    "search": _format_search,
    "plan": _format_plan,
}


def _answer_for(step: PlannedStep, outcome: dict) -> str:
    """Compose the prose for one executed step from its real return value."""

    if not outcome.get("success"):
        return _fail(outcome, "That step did not complete.")

    if step.operation == "read":
        formatter = _FORMATTERS.get(step.entity)

        if formatter is not None:
            payload = outcome.get("records")

            if payload is None:
                payload = outcome.get("intelligence")

            if isinstance(payload, list):
                return formatter(payload)

            return formatter(payload)

    if step.operation == "search":
        message = outcome.get("message") or ""
        formatted = _format_search(outcome.get("results") or [])
        return f"{message}\n{formatted}"

    if step.operation == "plan":
        return _format_plan(outcome.get("plan") or {})

    return str(outcome.get("message") or "Done.")


# =========================================================
# PUBLIC ENTRY POINTS
# =========================================================
#
# Two functions, one per route. `handle_command` understands and proposes;
# `confirm_plan` executes a proposal the user already approved. They share the
# builder and runner code, and nothing else.


def _user_timezone(db: Session, user_id: int) -> str:
    """
    The authenticated user's IANA timezone.

    Read through the preferences service so an absent or corrupt stored value
    is repaired rather than raising here — the whole command path should not
    fail because of a preference row.
    """

    from app.services.user_preferences_service import get_or_create_user_preferences

    try:
        preferences = get_or_create_user_preferences(db=db, user_id=user_id)
        return preferences.timezone
    except HTTPException:
        return "UTC"


def _domains_for(step: intent.IntentStep) -> list[str]:
    """Which domains this classified step needs to read."""

    if step.operation == "search":
        # Search spans every domain by definition, but stays bounded by
        # `ai_context_service`'s per-entity caps.
        return ["task", "goal", "habit", "note", "reminder", "planner_event", "transaction"]

    if step.operation == "plan":
        return ["task", "habit", "goal", "planner_event"]

    if step.operation == "read" and step.entity == "intelligence":
        return ["intelligence"]

    return [step.entity]


def _needs_target(step: intent.IntentStep) -> bool:
    """Whether the step must resolve a record before it can be built."""

    return step.operation in {"update", "complete", "delete"}


def _get_clarification(spec: intent.IntentSpec, step: intent.IntentStep, reason: str) -> str:
    """
    Generate a specific clarification question based on why the step failed.
    """

    if step.operation == "create" and step.entity == "task" and reason == "builder_failed":
        return "Please provide a title for the task."

    if step.operation == "create" and step.entity == "reminder":
        return (
            "What date and time should the reminder be set for? "
            "For example: “tomorrow at 6 PM”."
        )

    if step.operation in {"update", "complete", "delete"}:
        name = _CONFIRM_ENTITY_NAMES.get(step.entity, step.entity)
        return (
            f"I could not tell exactly which {name} you meant. "
            f"Tell me the name of the {name} and I will find it."
        )

    if step.operation == "update":
        return (
            "I could not tell what you want to change. "
            "Tell me the new value, for example “set the priority to high” "
            "or “move it to tomorrow”."
        )

    if step.operation == "search":
        return "What should I search for?"

    if step.operation == "plan":
        return "Which day should I plan?"

    return spec.clarification_question or "I am not sure how to help with that."


def _build_steps(
    db: Session,
    user_id: int,
    specs: list[intent.IntentSpec],
    timezone_name: str,
    context,
) -> tuple[list[PlannedStep], list[str], intent.IntentStep | None, str | None]:
    """
    Build every step for one command, resolving targets along the way.

    Returns `(steps, domains, unresolved_step, clarification)`. Building
    continues past a clause that cannot be built, so "add a task to call the
    vendor and delete the note called supplier" still creates the task and asks
    about the note rather than doing nothing at all.
    """

    steps: list[PlannedStep] = []
    domains: list[str] = []
    unresolved: intent.IntentStep | None = None
    clarification: str | None = None
    entity_matches: dict[str, dict] = {}

    for spec in specs:
        for step in spec.steps:
            step_domains = _domains_for(step)

            for domain in step_domains:
                if domain not in domains:
                    domains.append(domain)

            # A mutating step on a named record needs that record resolved
            # before the builder can attach a target id.
            if _needs_target(step):
                if step.entity not in entity_matches:
                    entity_matches[step.entity] = _match_for(
                        db,
                        user_id,
                        step,
                        timezone_name,
                    )

                # If target resolution failed (ambiguous/None), add a failed step.
                if entity_matches[step.entity].get("target") is None:
                    steps.append(PlannedStep(
                        operation=step.operation,
                        entity=step.entity,
                        description=f"Could not resolve {step.entity}",
                        parameters={},
                        runner=None,
                    ))
                    if unresolved is None:
                        unresolved = step
                        clarification = _get_clarification(spec, step, reason="target_not_found")
                    continue

            builder, takes_matches = _builders_for(step)

            if builder is None:
                continue

            try:
                if takes_matches:
                    planned = builder(
                        db,
                        user_id,
                        step,
                        timezone_name,
                        entity_matches,
                    )
                else:
                    planned = builder(db, user_id, step, timezone_name)
            except HTTPException:
                continue

            if planned is None:
                steps.append(PlannedStep(
                    operation=step.operation,
                    entity=step.entity,
                    description=f"Could not build {step.entity}",
                    parameters={},
                    runner=None,
                ))
                if unresolved is None:
                    unresolved = step
                    clarification = _get_clarification(spec, step, reason="builder_failed")
                continue

            steps.append(planned)

    return steps, domains, unresolved, clarification


def _match_for(db: Session, user_id: int, step: intent.IntentStep, timezone_name: str) -> dict:
    """
    Resolve the record a mutating step names.

    Returns the context's target plus an `ambiguous` flag the builders read.
    A reference the user did not make — the model path, for instance, leaves
    the fragment empty — resolves to nothing rather than to the newest row.
    """

    resolved = ctx.resolve_target(
        db=db,
        user_id=user_id,
        entity=step.entity,
        reference=step.fragment or step.target_hint or "",
        timezone_name=timezone_name,
    )

    return {
        "target": resolved.target,
        "ambiguous": resolved.target_ambiguous or resolved.target is None,
        "alternatives": resolved.target_alternatives,
    }


_BUILDERS = {
    ("create", "task"): _build_create_step,
    ("create", "goal"): _build_create_step,
    ("create", "habit"): _build_create_step,
    ("create", "note"): _build_create_step,
    ("create", "reminder"): _build_create_step,
    ("create", "transaction"): _build_create_step,
    ("update", "task"): _build_update_step,
    ("update", "goal"): _build_update_step,
    ("update", "habit"): _build_update_step,
    ("update", "reminder"): _build_update_step,
    ("update", "transaction"): _build_update_step,
    ("complete", "task"): _build_complete_step,
    ("complete", "goal"): _build_complete_step,
    ("complete", "habit"): _build_complete_step,
    ("complete", "reminder"): _build_complete_step,
    ("delete", "task"): _build_delete_step,
    ("delete", "goal"): _build_delete_step,
    ("delete", "habit"): _build_delete_step,
    ("delete", "note"): _build_delete_step,
    ("delete", "reminder"): _build_delete_step,
    ("delete", "planner_event"): _build_delete_step,
    ("delete", "transaction"): _build_delete_step,
    ("search", "intelligence"): _build_search_step,
    ("plan", "planner_event"): _build_plan_step,
    ("read", "task"): _build_read_step,
    ("read", "goal"): _build_read_step,
    ("read", "habit"): _build_read_step,
    ("read", "note"): _build_read_step,
    ("read", "reminder"): _build_read_step,
    ("read", "planner_event"): _build_read_step,
    ("read", "transaction"): _build_read_step,
    ("read", "intelligence"): _build_read_step,
}

#: Builders that additionally take the resolved-target map. Read, search and
#: plan steps need no target, so they take the shorter signature.
_BUILDERS_WITH_TARGETS = {
    _build_update_step,
    _build_complete_step,
    _build_delete_step,
}


def _builders_for(step: intent.IntentStep) -> tuple[object | None, bool]:
    """`(builder, takes_targets)` for a classified step."""

    builder = _BUILDERS.get((step.operation, step.entity))

    return builder, builder in _BUILDERS_WITH_TARGETS


def handle_command(
    db: Session,
    user_id: int,
    message: str,
    conversation_id: str | None = None,
) -> AIChatResponse:
    """
    Understand one command, execute what is safe, propose the rest.

    The full flow: understand → resolve context → classify → plan → confirm? →
    execute → answer. Anything requiring approval is returned as a plan with
    `awaiting_user=True` and nothing has been written.
    """

    timezone_name = _user_timezone(db, user_id)

    specs = intent.understand_multi_step(message)

    steps, domains, unresolved, clarification = _build_steps(
        db,
        user_id,
        specs,
        timezone_name,
        None,
    )

    context = ctx.build_context(
        db=db,
        user_id=user_id,
        domains=domains,
        timezone_name=timezone_name,
    )

    plan = ExecutionPlan(
        steps=steps,
        context_used=context.domains,
        intent=specs[0].intent if specs else "unknown",
        ai_online=any(spec.model_online for spec in specs),
    )

    # Nothing was understood. Say so plainly rather than guessing at intent.
    if not steps:
        if clarification is None:
            clarification = "I am not sure how to help with that. Try asking to create a task, check your planner, or search your notes."
        return AIChatResponse(
            response=_unsupported_message(clarification),
            ai_online=plan.ai_online,
            intent="unknown",
            context_used=[],
            conversation_id=conversation_id,
            awaiting_user=True,
            clarification_question=clarification,
        )

    # A plan that needs approval runs nothing at all. Running the safe half
    # and holding the destructive half would leave the user approving a plan
    # whose other steps already happened.
    if plan.requires_confirmation:
        plan_id = store_plan(user_id, plan)
        plan.awaiting_user = True

        return AIChatResponse(
            response=_confirmation_message(plan),
            ai_online=plan.ai_online,
            intent=plan.intent,
            plan=to_schema(plan, plan_id),
            context_used=plan.context_used,
            conversation_id=conversation_id,
            awaiting_user=True,
            clarification_question=clarification,
        )

    execute_plan(db, user_id, plan, context)

    plan.answer = _compose_answer(plan, context, specs, message)

    return AIChatResponse(
        response=plan.answer,
        ai_online=plan.ai_online,
        intent=plan.intent,
        plan=_schema_with_results(plan),
        context_used=plan.context_used,
        conversation_id=conversation_id,
        awaiting_user=False,
        clarification_question=clarification,
    )


def confirm_plan(
    db: Session,
    user_id: int,
    plan_id: str,
    conversation_id: str | None = None,
) -> AIChatResponse:
    """
    Execute a plan the user approved.

    The plan is claimed by id *and* consumed in the process, so a leaked id is
    useless to another user and a plan runs at most once. Only the steps that
    actually required approval are executed; any already-executed steps stay
    `succeeded` and are not repeated.
    """

    plan = take_plan(plan_id, user_id)

    if plan is None:
        return AIChatResponse(
            response=(
                "That confirmation is no longer valid — it may have expired, "
                "already been used, or belonged to a different session. "
                "Please send the command again."
            ),
            ai_online=False,
            intent="unknown",
            context_used=[],
            conversation_id=conversation_id,
            awaiting_user=False,
        )

    timezone_name = _user_timezone(db, user_id)

    context = ctx.build_context(
        db=db,
        user_id=user_id,
        domains=plan.context_used or ["intelligence"],
        timezone_name=timezone_name,
    )

    for step in plan.steps:
        if not step.confirmation_required:
            continue

        # The plan step proposes first and applies second; the apply pass
        # needs the blocks the proposal pass produced.
        if step.operation == "plan" and step.execution_meta.get("apply"):
            proposal = _run_step(db, user_id, step, context)

            if not proposal.get("success"):
                step.execution_meta["status"] = "failed"
                step.execution_meta["result_message"] = _fail(
                    proposal,
                    "I could not generate a plan.",
                )

                continue

            step.execution_meta["extra_parameters"] = {
                "blocks": (proposal.get("plan") or {}).get("plan") or [],
            }

        outcome = _run_step(db, user_id, step, context)

        step.execution_meta["status"] = (
            "succeeded" if outcome.get("success") else "failed"
        )
        step.execution_meta["result_message"] = outcome.get("message") or _fail(
            outcome,
            "That step did not complete.",
        )

        if not outcome.get("success"):
            step.execution_meta["error"] = _fail(outcome, "That step did not complete.")

    plan.answer = _compose_executed_answer(plan)

    return AIChatResponse(
        response=plan.answer,
        ai_online=plan.ai_online,
        intent=plan.intent,
        plan=_schema_with_results(plan),
        context_used=plan.context_used,
        conversation_id=conversation_id,
        awaiting_user=False,
    )


def cancel_plan(
    db: Session,
    user_id: int,
    plan_id: str,
    conversation_id: str | None = None,
) -> AIChatResponse:
    """
    Drop a plan the user declined.

    Nothing was written when the plan was proposed, so cancelling really does
    change nothing — this reports that rather than performing any undo.
    """

    discarded = discard_plan(plan_id, user_id)

    if not discarded:
        return AIChatResponse(
            response=(
                "That confirmation was no longer pending, so there is nothing "
                "to cancel. Nothing was changed either way."
            ),
            ai_online=False,
            intent="unknown",
            context_used=[],
            conversation_id=conversation_id,
            awaiting_user=False,
        )

    return AIChatResponse(
        response="Cancelled. Nothing was changed.",
        ai_online=False,
        intent="cancelled",
        context_used=[],
        conversation_id=conversation_id,
        awaiting_user=False,
    )


# =========================================================
# PROSE
# =========================================================


def _confirmation_message(plan: ExecutionPlan) -> str:
    """What the user sees above the confirmation panel."""

    lines = ["Before I do this, please confirm:"]
    lines.append("")

    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"{index}. {step.description}")

        if step.confirmation_reason:
            lines.append(f"   {step.confirmation_reason}")

    lines.append("")
    lines.append("Nothing has been changed yet.")

    return "\n".join(lines)


def _compose_answer(
    plan: ExecutionPlan,
    context,
    specs: list[intent.IntentSpec],
    message: str,
) -> str:
    """
    Assemble the answer from executed outcomes only.

    A read answer is optionally rewritten by the model when the provider
    actually answered; a write answer is never rewritten, because "created
    your task" must not be something a text generator produced.
    """

    parts: list[str] = []

    for step in plan.steps:
        status = step.execution_meta.get("status")

        if status == "failed":
            parts.append(
                f"Could not: {step.description}. "
                f"{step.execution_meta.get('error')}"
            )
            continue

        if status != "succeeded":
            parts.append(f"Skipped: {step.description}.")
            continue

        if step.operation in {"read", "search", "plan"}:
            rendered = step.execution_meta.get("answer")

            if rendered:
                parts.append(rendered)
                continue

        parts.append(
            f"{step.description} — {step.execution_meta.get('result_message')}"
        )

    if not parts:
        parts.append("I understood the request but there was nothing to apply.")

    answer = "\n\n".join(parts)

    # Only a pure read is handed to the model. A turn that wrote something is
    # answered from the recorded results alone.
    if all(
        step.operation in {"read", "search"}
        for step in plan.steps
        if step.execution_meta.get("status") == "succeeded"
    ):
        context_text = ctx.format_context_text(context, context.domains)

        synthesized = intent.synthesize(message, context_text)

        if synthesized:
            plan.ai_online = True
            answer = synthesized

    return answer


def _compose_executed_answer(plan: ExecutionPlan) -> str:
    """Report exactly which confirmed steps ran, and which did not."""

    succeeded = []
    failed = []

    for step in plan.steps:
        status = step.execution_meta.get("status")

        if status == "succeeded":
            succeeded.append(step.execution_meta.get("result_message") or step.description)
        elif status == "failed":
            failed.append(
                f"{step.description} — {step.execution_meta.get('error')}"
            )

    if not succeeded and not failed:
        return "Confirmed, but nothing needed to change."

    parts = []

    if succeeded:
        parts.append("\n".join(succeeded))

    if failed:
        parts.append("Could not complete:\n" + "\n".join(failed))

    return "\n\n".join(parts)


def _unsupported_message(clarification: str | None) -> str:
    """
    What to say when the command could not be understood.

    Never a guess. If there is a specific question to ask, it is asked;
    otherwise the honest answer names what the command centre can do.
    """

    if clarification:
        return clarification

    return (
        "I did not understand that, and I will not guess at an action. "
        "I can read your tasks, goals, habits, notes, reminders, planner and "
        "finances; search across them; create or update records; complete "
        "them; and delete them after you confirm. "
        "Try one of those, or rephrase."
    )


def _schema_with_results(plan: ExecutionPlan) -> ActionPlanSummary | None:
    """Project a plan plus its execution outcomes onto the wire schema."""

    steps = plan_status_steps(plan)

    if not steps:
        return None

    return ActionPlanSummary(
        plan_id="",
        requires_confirmation=any(step.confirmation_required for step in plan.steps),
        steps=steps,
    )