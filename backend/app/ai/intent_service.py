"""
Request understanding for the AI Command Center.

Turns a free-text command into a validated `IntentSpec` — a small closed
vocabulary of intent, entity, and operation, plus whatever parameters the
resolver could extract server-side.

Two paths produce one:

1. **The local model** (`qwen2.5:1.5b` via Ollama) is asked to emit a JSON
   object under a strict schema. Its output is parsed, then *re-validated
   against the closed vocabulary below* — an unknown intent, entity or
   operation is discarded rather than passed through, because a small local
   model will happily invent a plausible-looking verb that the backend has
   no implementation for. Inventing support is the failure this module exists
   to prevent.

2. **A deterministic matcher** covers the phrasings the product already
   recognises (including the romanised Hindi the previous brain supported), so
   the core read/create/complete paths keep working with no model running at
   all. This is the same posture the Intelligence panel takes: nothing about
   ordinary LifeOS operation depends on a provider being reachable.

The model path *synthesizes* — it explains and disambiguates. It never
resolves a target record or a date; those are read off the user's own rows by
`context_service` and `nl_datetime_service`, which is why a hallucinated
model response cannot produce a wrong record write.

This module performs no database access and no network calls beyond the one
optional model request. Nothing here is trusted as authoritative over the
services.
"""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"

#: Short timeout. The command surface must stay responsive on the target
#: hardware; a slow local model is better reported honestly than waited on.
MODEL_TIMEOUT_SECONDS = 25

#: Cap on tokens generated for a classification. The whole response is a
#: short JSON object; anything longer is the model rambling and is truncated.
MODEL_NUM_PREDICT = 200

MAX_MESSAGE_LENGTH = 2000
MAX_CONVERSATION_TURNS = 6
MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 4000


# =========================================================
# CLOSED VOCABULARY
# =========================================================

INTENTS = (
    "read",
    "create",
    "update",
    "complete",
    "delete",
    "search",
    "plan",
    "clarify",
    "unknown",
)

OPERATIONS = ("read", "create", "update", "complete", "delete", "search", "plan")

ENTITIES = (
    "task",
    "goal",
    "habit",
    "note",
    "reminder",
    "planner_event",
    "transaction",
    "intelligence",
)

#: Read intents that carry no entity at all — questions about the account as a
#: whole ("how am I doing") rather than about one record type.
OVERVIEW_ENTITIES = ("intelligence",)


@dataclass(frozen=True)
class IntentStep:
    """One intended operation within a request."""

    intent: str
    operation: str
    entity: str
    #: Verbatim fragment of the user's message this step came from. Used to
    #: resolve the title and the date, never as a stored value.
    fragment: str
    target_hint: str | None = None


@dataclass(frozen=True)
class IntentSpec:
    """
    A validated understanding of one user request.

    `steps` may hold more than one entry: "finish the assignment and call the
    client at 6" is a create-task and a create-reminder in one message. An
    empty `steps` list with `intent == "unknown"` is the honest "I did not
    understand this" case, which the endpoint renders as an explicit
    unsupported message rather than guessing.
    """

    intent: str
    steps: tuple[IntentStep, ...] = ()
    clarification_question: str | None = None
    #: True only when a real provider request succeeded this turn. The UI must
    #: not claim AI is online on the strength of the deterministic path.
    model_online: bool = False
    #: Where the understanding came from, for the response envelope.
    source: str = "deterministic"


# =========================================================
# DETERMINISTIC MATCHING
# =========================================================

#: (entity, intent) → phrases. Ordered longest-first at match time so
#: "complete my task" beats a bare "task".
_PHRASES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # --- search -------------------------------------------------------
    (
        "intelligence",
        "search",
        (
            "search for",
            "search my",
            "find my",
            "find the",
            "find notes",
            "find note",
            "find task",
            "find goal",
            "find habit",
            "find transaction",
            "look for",
            "show me notes about",
            "notes about",
            "search",
        ),
    ),
    # --- delete -------------------------------------------------------
    (
        "task",
        "delete",
        (
            "delete the task",
            "delete my task",
            "delete task",
            "remove the task",
            "remove my task",
            "remove task",
            "task hata",
            "task delete",
            "delete task",
            "hata do task",
        ),
    ),
    (
        "goal",
        "delete",
        (
            "delete the goal",
            "delete my goal",
            "delete goal",
            "remove the goal",
            "remove goal",
            "goal hata",
            "goal delete",
        ),
    ),
    (
        "habit",
        "delete",
        (
            "delete the habit",
            "delete my habit",
            "delete habit",
            "remove the habit",
            "remove habit",
            "habit hata",
            "habit delete",
        ),
    ),
    (
        "note",
        "delete",
        (
            "delete the note",
            "delete my note",
            "delete note",
            "remove the note",
            "remove note",
            "note hata",
            "note delete",
        ),
    ),
    (
        "reminder",
        "delete",
        (
            "delete the reminder",
            "delete my reminder",
            "delete reminder",
            "remove the reminder",
            "remove reminder",
            "reminder hata",
            "reminder delete",
        ),
    ),
    (
        "planner_event",
        "delete",
        (
            "delete the event",
            "delete event",
            "remove the event",
            "remove event",
            "clear my planner",
            "delete planner event",
        ),
    ),
    (
        "transaction",
        "delete",
        (
            "delete the transaction",
            "delete transaction",
            "remove the transaction",
            "remove transaction",
        ),
    ),
    # --- complete -----------------------------------------------------
    (
        "task",
        "complete",
        (
            "mark * as complete",
            "mark * complete",
            "complete * task",
            "finish * task",
        ),
    ),
    (
        "goal",
        "complete",
        (
            "mark the goal",
            "mark goal",
            "complete the goal",
            "complete goal",
            "finish the goal",
            "finish goal",
            "goal complete",
            "goal pura",
        ),
    ),
    (
        "habit",
        "complete",
        (
            "mark the habit",
            "mark habit",
            "check in",
            "check-in",
            "checkin",
            "complete the habit",
            "complete habit",
            "log the habit",
            "log habit",
            "habit complete",
            "habit pura",
            "complete habit",
            "mark habit complete",
            "complete",
            "check",
            "log",
            "complete the",
        ),
    ),
    (
        "reminder",
        "complete",
        (
            "mark the reminder",
            "complete the reminder",
            "complete reminder",
            "reminder complete",
        ),
    ),
    # --- create -------------------------------------------------------
    (
        "task",
        "create",
        (
            "add a task",
            "add my task",
            "add task",
            "create a task",
            "create task",
            "make a task",
            "make task",
            "new task",
            "task bana",
            "task banao",
            "task create",
            "task add",
            "task daal",
            "task likh",
            "ek task",
            "i need to",
            "i have to",
            "remind me to study",
            "todo",
            # modifiers between create and entity
            "create a high priority task",
            "create a medium priority task",
            "create a low priority task",
            "create high priority task",
            "create medium priority task",
            "create low priority task",
        ),
    ),
    (
        "goal",
        "create",
        (
            "add a goal",
            "add goal",
            "create a goal",
            "create goal",
            "make a goal",
            "make goal",
            "new goal",
            "goal bana",
            "goal banao",
            "goal create",
            "goal add",
            "ek goal",
            "my goal is to",
        ),
    ),
    (
        "habit",
        "create",
        (
            "add a habit",
            "add habit",
            "create a habit",
            "create habit",
            "make a habit",
            "make habit",
            "start a habit",
            "new habit",
            "habit bana",
            "habit banao",
            "habit create",
            "habit add",
            "ek habit",
            # modifiers between create and entity
            "create a daily habit",
            "create a weekly habit",
            "create a monthly habit",
            "create daily habit",
            "create weekly habit",
            "create monthly habit",
        ),
    ),
    (
        "note",
        "create",
        (
            "add a note",
            "add note",
            "create a note",
            "create note",
            "write a note",
            "write note",
            "new note",
            "note likh",
            "note bana",
            "note banao",
            "note add",
            "note create",
            "ek note",
        ),
    ),
    (
        "reminder",
        "create",
        (
            "remind me to",
            "remind me",
            "set a reminder",
            "set reminder",
            "create a reminder",
            "create reminder",
            "add a reminder",
            "add reminder",
            "reminder bana",
            "reminder set",
            "yaad dila",
            "remind me about",
        ),
    ),
    (
        "transaction",
        "create",
        (
            "add an expense",
            "add expense",
            "log an expense",
            "log expense",
            "record an expense",
            "record expense",
            "i spent",
            "i paid",
            "add income",
            "record income",
            "log income",
            "kharch",
            "record an income",
            "add an income",
        ),
    ),
    (
        "planner_event",
        "create",
        (
            "add an event",
            "add event",
            "create an event",
            "create event",
            "schedule a meeting",
            "schedule meeting",
            "block time for",
            "event bana",
            "event banao",
        ),
    ),
    # --- update -------------------------------------------------------
    (
        "task",
        "update",
        (
            "update * task",
            "set * priority",
            "set priority of *",
            "set priority of * to *",
            "change * task",
            "modify * task",
            "move * to *",
            "reschedule * to *",
            "postpone *",
            "task priority",
            "priority change",
        ),
    ),
    (
        "transaction",
        "update",
        (
            "update the transaction",
            "update transaction",
            "change the transaction",
            "change transaction",
            "modify the transaction",
            "modify transaction",
        ),
    ),
    (
        "goal",
        "update",
        (
            "update the goal",
            "update goal",
            "change the goal",
            "change goal",
            "goal progress",
            "update progress of",
            "set progress of",
            "set progress",
            "progress of",
        ),
    ),
    (
        "habit",
        "update",
        (
            "update the habit",
            "update habit",
            "change the habit",
            "change habit",
            "habit frequency",
            "activate habit",
            "deactivate habit",
            "pause habit",
        ),
    ),
    (
        "note",
        "update",
        (
            "update the note",
            "update note",
            "edit the note",
            "edit note",
            "change the note",
            "change note",
        ),
    ),
    (
        "reminder",
        "update",
        (
            "update the reminder",
            "update reminder",
            "reschedule the reminder",
            "reschedule reminder",
            "move the reminder",
        ),
    ),
    (
        "planner_event",
        "update",
        (
            "update the event",
            "update event",
            "change the time",
            "reschedule the event",
        ),
    ),
    # --- read ---------------------------------------------------------
    (
        "task",
        "read",
        (
            "show my tasks",
            "show the tasks",
            "show tasks",
            "list my tasks",
            "list tasks",
            "my tasks",
            "my task",
            "what tasks",
            "which tasks",
            "important tasks",
            "overdue tasks",
            "pending tasks",
            "due this week",
            "tasks bata",
            "task bata",
            "tasks dikha",
            "kaam bata",
            "kaam dikha",
        ),
    ),
    (
        "goal",
        "read",
        (
            "show my goals",
            "show goals",
            "list my goals",
            "list goals",
            "my goals",
            "my goal",
            "what goals",
            "goals bata",
            "goal bata",
            "goals dikha",
            "how is my",
            "how are my",
            "progress on my",
        ),
    ),
    (
        "habit",
        "read",
        (
            "show my habits",
            "show habits",
            "list my habits",
            "list habits",
            "my habits",
            "my habit",
            "habit streaks",
            "my streak",
            "habits bata",
            "habit bata",
            "habits dikha",
            "habit history",
            "check my habits",
        ),
    ),
    (
        "note",
        "read",
        (
            "show my notes",
            "show notes",
            "list my notes",
            "list notes",
            "my notes",
            "what notes",
            "notes bata",
            "notes dikha",
        ),
    ),
    (
        "reminder",
        "read",
        (
            "show my reminders",
            "show reminders",
            "list my reminders",
            "list reminders",
            "my reminders",
            "what reminders",
            "reminders bata",
            "reminders dikha",
            "what do i have",
        ),
    ),
    (
        "planner_event",
        "read",
        (
            "show my planner",
            "show planner",
            "show my schedule",
            "my planner",
            "my schedule",
            "planner events",
            "show my events",
            "tomorrow's schedule",
            "tomorrows schedule",
        ),
    ),
    (
        "transaction",
        "read",
        (
            "how much did i spend",
            "how much have i spent",
            "my expenses",
            "my spending",
            "my income",
            "my transactions",
            "my finances",
            "show my finances",
            "show finances",
            "my finance overview",
            "finance overview",
            "show transactions",
            "show my transactions",
            "finance bata",
            "kitna kharch",
            "spending this month",
            "expenses this month",
        ),
    ),
)

#: Questions about the account as a whole. These resolve to the deterministic
#: Intelligence panel, which already computes every figure they ask about.
_OVERVIEW_PHRASES = (
    "how am i doing",
    "how am i",
    "how's my day",
    "hows my day",
    "what's important today",
    "whats important today",
    "what is important today",
    "what should i focus on",
    "what should i do today",
    "what should i do",
    "what's my status",
    "whats my status",
    "my status",
    "lifeos status",
    "lifeos overview",
    "my lifeos overview",
    "my lifeos",
    "show me my lifeos",
    "show my lifeos",
    "current status",
    "overall status",
    "give me a briefing",
    "brief me",
    "daily briefing",
    "analyse my",
    "analyze my",
    "review my",
    "what needs attention",
    "how productive",
    "productivity",
    "summarize my",
    "summarise my",
    "kaisa chal",
    "mera status",
    "aaj kya karna",
)

#: Planning requests. The planner generates a proposal; applying it is a
#: separate, confirmed step.
_PLAN_PHRASES = (
    "plan my",
    "plan for",
    "plan tomorrow",
    "plan today",
    "plan my day",
    "plan my week",
    "make a plan",
    "make a schedule",
    "create a plan",
    "schedule my day",
    "organize my day",
    "organise my day",
    "what's my plan",
    "what is my plan",
    "aaj ka plan",
    "mera plan",
    "kal ka plan",
    "suggest a plan",
    "propose a plan",
    "focus on this week",
    "what should i focus on this week",
)

#: Verb prefixes stripped before a create/update title is read off the message.
_TITLE_PREFIXES = (
    "i need to ",
    "i have to ",
    "i must ",
    "i want to ",
    "i'll ",
    "i will ",
    "please ",
    "can you ",
    "could you ",
    "remind me to ",
    "remind me about ",
    "remind me ",
    "todo:",
    "todo ",
    "task:",
    "goal:",
    "habit:",
    "note:",
    "set a reminder to ",
    "set reminder to ",
    "set a reminder for ",
    "set reminder for ",
    "set a reminder ",
    "set reminder ",
    "add a reminder to ",
    "add a reminder for ",
    "add a reminder ",
    "add reminder to ",
    "add reminder for ",
    "create a task to ",
    "create a task for ",
    "create a task called ",
    "create a task named ",
    "create task to ",
    "create task for ",
    "create task called ",
    "create task named ",
    "create a task",
    "add a task",
    "create a goal",
    "add a goal",
    "create a habit",
    "add a habit",
    "create a note",
    "add a note",
    "make a task to ",
    "make a task for ",
    "make task to ",
    "make task for ",
    "add a task to ",
    "add a task for ",
    "add task to ",
    "add task for ",
    "new task ",
    "create a goal to ",
    "create a goal for ",
    "create goal to ",
    "create goal for ",
    "make a goal to ",
    "make a goal for ",
    "add a goal to ",
    "add a goal for ",
    "new goal ",
    "my goal is to ",
    "create a habit to ",
    "create a habit for ",
    "create habit to ",
    "create habit for ",
    "make a habit to ",
    "add a habit to ",
    "add a habit for ",
    "new habit ",
    "create a note called ",
    "create a note named ",
    "create a note about ",
    "create note called ",
    "create note named ",
    "write a note about ",
    "write a note on ",
    "write note about ",
    "add a note about ",
    "add a note on ",
    "add note about ",
    "new note about ",
    "new note ",
    "ka task bana do ",
    "ki task bana do ",
    "ka task bana de ",
    "ki task bana de ",
    "ka task bana ",
    "ki task bana ",
    "task bana do ",
    "task bana de ",
    "task bana ",
    "task banao ",
    "task create kar ",
    "task create ",
    "task add kar ",
    "task add ",
    "task likh ",
    "ek task ",
    "ka goal bana do ",
    "ki goal bana do ",
    "ka goal bana de ",
    "goal bana do ",
    "goal bana de ",
    "goal bana ",
    "goal banao ",
    "goal create kar ",
    "goal create ",
    "ek goal ",
    "ka habit bana do ",
    "ki habit bana do ",
    "ka habit bana de ",
    "habit bana do ",
    "habit bana de ",
    "habit bana ",
    "habit banao ",
    "habit create kar ",
    "habit create ",
    "ek habit ",
    "note likh ",
    "note bana ",
    "note banao ",
    "ek note ",
)

#: Trailing clauses that are never part of a title.
_TITLE_SUFFIXES = (
    " for tomorrow",
    " tomorrow",
    " for today",
    " today",
    " tonight",
    " this week",
    " next week",
    " by tomorrow",
    " high priority",
    " priority high",
    " medium priority",
    " priority medium",
    " low priority",
    " priority low",
)

_PRIORITY_RE = re.compile(
    r"\b(high|medium|low)\s+priority\b"
    r"|\bpriority\s+(?:to\s+)?(high|medium|low)\b"
    r"|\bto\s+(high|medium|low)\b"
)

#: Modifier phrases that appear between create-verb and entity.
#: Removed before phrase matching so "create a high priority task" matches "create a task".
_MODIFIER_PATTERNS = (
    r"\ba\s+high\s+priority\b",
    r"\ba\s+medium\s+priority\b",
    r"\ba\s+low\s+priority\b",
    r"\bhigh\s+priority\b",
    r"\bmedium\s+priority\b",
    r"\blow\s+priority\b",
    r"\bpriority\s+high\b",
    r"\bpriority\s+medium\b",
    r"\bpriority\s+low\b",
    r"\bdaily\b",
    r"\bweekly\b",
    r"\bmonthly\b",
)


def _remove_modifiers_for_matching(text: str) -> str:
    """Remove known modifier words to allow flexible phrase matching.

    E.g., "create a high priority task" -> "create a task"
    so the existing phrase "create a task" matches.
    """
    result = text
    for pattern in _MODIFIER_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    # Clean up extra spaces left by removals
    result = re.sub(r"\s+", " ", result).strip()
    return result


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    collapsed = re.sub(r"\s+", " ", lowered)
    return collapsed


def _match_phrase(
    text: str,
    phrases: tuple[str, ...],
) -> tuple[str, int] | None:
    """Longest phrase contained in `text`, with its index."""

    best: tuple[str, int] | None = None

    for phrase in phrases:
        # Support * as a wildcard for variable titles/content
        pattern = re.escape(phrase).replace(r"\*", r".*?")
        match = re.search(pattern, text)
        if match:
            index = match.start()
            if best is None or len(phrase) > len(best[0]):
                best = (phrase, index)

    return best


def extract_title(text: str) -> str | None:
    """
    Read a record title off a command fragment.

    Deterministic and deliberately conservative: it strips known command
    prefixes and trailing date/priority clauses, then trims connectors. If
    what remains is too short to be a title it returns `None` rather than
    echoing the whole sentence back as a task called "remind me to call the
    client".

    Preserves original capitalization in the returned title.
    """

    # Keep original for preserving case; use lowercase for matching
    original = text.strip().strip(" .,:;!?-")
    candidate = original.lower()

    # Strip leading noise that is not part of the title.
    changed = True
    while changed:
        changed = False
        for prefix in _TITLE_PREFIXES:
            if candidate.startswith(prefix):
                # Remove from both original and candidate
                original = original[len(prefix):].strip()
                candidate = candidate[len(prefix):].strip()
                changed = True

    for suffix in _TITLE_SUFFIXES:
        if candidate.endswith(suffix):
            # Remove from both original and candidate
            original = original[:-len(suffix)].strip()
            candidate = candidate[:-len(suffix)].strip()
            changed = True

    original = original.strip(" .,:;!?-\"'")
    candidate = candidate.strip(" .,:;!?-\"'")

    # Strip a trailing date/priority clause that landed mid-sentence, e.g.
    # "finish the assignment high priority" after a prefix already matched.
    # Use case-insensitive regex on candidate, apply to original
    candidate = re.sub(
        r"\b(high|medium|low)\s+priority\b.*$",
        "",
        candidate,
    ).strip()
    # Re-apply to original using same logic (find in candidate, remove from original)
    # We'll use a simpler approach: regex on original with IGNORECASE
    original = re.sub(
        r"\b(high|medium|low)\s+priority\b.*$",
        "",
        original,
        flags=re.IGNORECASE,
    ).strip()

    original = re.sub(r"\btoday\b.*$", "", original, flags=re.IGNORECASE).strip()
    original = re.sub(r"\btomorrow\b.*$", "", original, flags=re.IGNORECASE).strip()
    original = re.sub(r"\btonight\b.*$", "", original, flags=re.IGNORECASE).strip()

    original = original.strip(" .,:;!?-'\"")

    # Validation still uses lowercase candidate
    candidate = original.lower()
    if not candidate:
        return "Please provide a title for the task."

    return original[:MAX_TITLE_LENGTH]


def _clean_title(text: str) -> str | None:
    candidate = extract_title(text)

    if not candidate:
        return None

    if candidate == "Please provide a title for the task.":
        return None

    # A leftover verb means the prefix table did not cover this phrasing; the
    # whole sentence is not a title and must not become one.
    if re.match(
        r"^(please\s+)?(create|make|add|set|schedule|plan|delete|remove|task|goal|habit|note|reminder)"
        r"\b",
        candidate,
    ):
        return None

    if len(candidate) < 2:
        return None

    return candidate[:MAX_TITLE_LENGTH]


def extract_priority(text: str) -> str:
    """Read an explicit priority, defaulting to medium like the task schema."""

    match = _PRIORITY_RE.search(text.lower())

    if match:
        return match.group(1) or match.group(2) or match.group(3)

    return "medium"


def _frequency(text: str) -> str | None:
    lowered = text.lower()

    for candidate in ("daily", "weekly", "monthly"):
        if candidate in lowered:
            return candidate

    if "roz" in lowered or "har din" in lowered or "every day" in lowered:
        return "daily"

    if "hafte" in lowered or "hafta" in lowered or "weekly" in lowered:
        return "weekly"

    if "mahine" in lowered or "mahina" in lowered or "monthly" in lowered:
        return "monthly"

    return None


def _looks_like_question(text: str) -> bool:
    stripped = text.strip()

    return stripped.endswith("?") or bool(
        re.match(r"^(what|when|where|which|who|how|why|do|does|did|is|are|can)\b", stripped.lower())
    )


def understand_deterministically(message: str) -> IntentSpec:
    """
    Classify a command with no model call.

    Ordering is load-bearing and runs most-specific-first:

    1. planning and overview phrasings, which read across domains;
    2. explicit entity phrases, longest phrase winning, so "remind me to
       finish my task" reads as an update rather than a create-reminder;
    3. create/update/complete/delete, which are all mutations and so are
       only reached when no read phrase claimed the message.
    """

    text = _normalize(message)

    if not text:
        return IntentSpec(intent="unknown", source="deterministic")

    # --- planning -----------------------------------------------------
    match = _match_phrase(text, _PLAN_PHRASES)
    if match:
        return IntentSpec(
            intent="plan",
            steps=(
                IntentStep(
                    intent="plan",
                    operation="plan",
                    entity="planner_event",
                    fragment=message,  # Preserve original casing for title extraction
                ),
            ),
            source="deterministic",
        )

    # --- account-wide overview ---------------------------------------
    match = _match_phrase(text, _OVERVIEW_PHRASES)
    if match:
        return IntentSpec(
            intent="read",
            steps=(
                IntentStep(
                    intent="read",
                    operation="read",
                    entity="intelligence",
                    fragment=message,  # Preserve original casing
                ),
            ),
            source="deterministic",
        )

    # --- entity-scoped commands --------------------------------------
    # For create commands, remove modifiers before matching so
    # "create a high priority task" matches "create a task"
    match_text = _remove_modifiers_for_matching(text) if text.startswith(("create", "make", "add", "new")) else text

    matches: list[tuple[int, str, str]] = []

    for entity, operation, phrases in _PHRASES:
        found = _match_phrase(match_text, phrases)

        if found:
            matches.append((len(found[0]), entity, operation))

    if matches:
        # Longest phrase wins. This is what keeps "remind me to finish my
        # task" from being read as a create-reminder: the update phrase is
        # longer than the bare "remind me".
        matches.sort(key=lambda item: item[0], reverse=True)

        _, entity, operation = matches[0]

        return IntentSpec(
            intent=operation,
            steps=(
                IntentStep(
                    intent=operation,
                    operation=operation,
                    entity=entity,
                    fragment=message,  # Preserve original casing for title extraction
                ),
            ),
            source="deterministic",
        )

    # --- fallback -----------------------------------------------------
    if _looks_like_question(message):
        # A question we cannot place. Hand it to the model, which may still
        # read it against real data; the caller decides what to say if not.
        return IntentSpec(
            intent="unknown",
            clarification_question=None,
            source="deterministic",
        )

    # An imperative we cannot place either.
    return IntentSpec(intent="unknown", source="deterministic")


def _split_clauses(message: str) -> list[str]:
    """
    Split a multi-step command on connectives.

    Splits on " and then ", " and also ", " also ", " then " and on a comma
    only when both halves carry a verb — so "buy milk, bread and eggs" stays
    one clause, while "create a task to submit the report and call the client
    at 6" becomes two.
    """

    text = _normalize(message)

    for separator in (" and then ", " and also ", " then also ", " then "):
        if separator in text:
            return [part.strip() for part in text.split(separator) if part.strip()]

    parts = [part.strip() for part in text.split(" and ") if part.strip()]

    if len(parts) < 2:
        return [text] if text else []

    # Only accept the split when each half reads as its own command.
    if all(_reads_as_clause(part) for part in parts):
        return parts

    return [text]


_VERB_HINTS = (
    "create",
    "make",
    "add",
    "remind",
    "delete",
    "remove",
    "update",
    "change",
    "complete",
    "finish",
    "mark",
    "schedule",
    "plan",
    "set",
    "move",
    "log",
    "record",
    "write",
    "show",
    "list",
    "find",
    "check",
    "search",
    "i need to",
    "i have to",
    "i must",
    "bana",
    "banao",
    "likh",
    "daal",
    "kar",
    "dikha",
    "bata",
    "hata",
    "mita",
)


def _reads_as_clause(part: str) -> bool:
    return any(verb in part for verb in _VERB_HINTS)


def understand_multi_step(message: str) -> list[IntentSpec]:
    """
    Split a command into clauses and understand each independently.

    Returns one spec per clause. A message that does not actually decompose
    comes back as a single-element list, so the caller has one code path.
    """

    clauses = _split_clauses(message)

    if len(clauses) <= 1:
        return [understand_deterministically(message)]

    specs: list[IntentSpec] = []

    for clause in clauses:
        spec = understand_deterministically(clause)

        if spec.intent != "unknown":
            specs.append(spec)

    if not specs:
        return [understand_deterministically(message)]

    return specs


# =========================================================
# LOCAL MODEL PATH
# =========================================================

_CLASSIFY_PROMPT = """You classify commands for a personal productivity app.

Reply with ONLY a JSON object, no other text.

Schema:
{"intent": "read|create|update|complete|delete|search|plan|unknown",
 "entity": "task|goal|habit|note|reminder|planner_event|transaction|intelligence",
 "confidence": 0.0-1.0}

Rules:
- "show my X", "what X do I have", "how much X" => read
- "create/add/make a X", "remind me to" => create
- "change/update/move" => update
- "mark complete/done", "check in" => complete
- "delete/remove" => delete
- "find/search X about Y" => search
- "plan my day/week", "what should I focus on" => plan
- Questions about overall progress use entity "intelligence".
- If genuinely unclear, use "unknown".

Examples:
"how many tasks are pending" -> {"intent":"read","entity":"task","confidence":0.9}
"i need to submit the report by friday" -> {"intent":"create","entity":"task","confidence":0.8}
"what should i focus on this week" -> {"intent":"plan","entity":"planner_event","confidence":0.7}
"how much did i spend in march" -> {"intent":"read","entity":"transaction","confidence":0.9}
"mark the gym habit complete" -> {"intent":"complete","entity":"habit","confidence":0.9}

Command: {message}
JSON:"""


def _extract_json(raw: str) -> dict | None:
    """
    Pull the first JSON object out of a model response.

    Small models wrap JSON in prose or a code fence, and sometimes append a
    trailing character. Scanning for the balanced outer braces tolerates that
    without adding a parser dependency.
    """

    if not raw:
        return None

    text = raw.strip()

    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                candidate = text[start : index + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    return None

                return parsed if isinstance(parsed, dict) else None

    return None


def _validate_model_output(payload: dict | None) -> IntentStep | None:
    """
    Reject anything outside the closed vocabulary.

    This is the boundary that stops a hallucinated verb or entity from
    reaching the executor. A model that answers `{"intent":"delete_everything"}`
    or names an entity with no implementation gets `None`, and the caller
    falls back to the deterministic understanding — the request is still
    served, but never with a capability the backend does not have.
    """

    if not payload:
        return None

    intent = str(payload.get("intent", "")).strip().lower()
    entity = str(payload.get("entity", "")).strip().lower()

    if intent not in INTENTS or entity not in ENTITIES:
        return None

    # `clarify` and `unknown` carry no action; the caller answers them.
    if intent in {"clarify", "unknown"}:
        return None

    operation = "plan" if intent == "plan" else intent

    if operation not in OPERATIONS:
        return None

    # An account-wide read is the Intelligence panel, not a record lookup.
    if intent == "read" and entity in {"planner_event", "intelligence"}:
        entity = "intelligence"

    return IntentStep(
        intent=intent,
        operation=operation,
        entity=entity,
        fragment="",
        target_hint=None,
    )


def ask_local_model(message: str) -> tuple[IntentStep | None, str | None]:
    """
    Ask the local model to classify a command.

    Returns `(step, raw_text)`. `step` is `None` when the model was
    unreachable, timed out, returned something unparseable, or named a
    capability outside the closed vocabulary — all four are ordinary
    outcomes, not errors, and the caller falls back to the deterministic
    path. `raw_text` is the model's reply, used for free-text synthesis when
    the model is online but the request was a read.
    """

    prompt = _CLASSIFY_PROMPT.replace("{message}", message.strip()[:MAX_MESSAGE_LENGTH])

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": MODEL_NUM_PREDICT,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))

        raw = (body.get("response") or "").strip()

        if not raw:
            return None, None

        return _validate_model_output(_extract_json(raw)), raw

    except urllib.error.URLError:
        return None, None
    except (TimeoutError, OSError):
        return None, None
    except json.JSONDecodeError:
        return None, None
    except Exception:
        # A provider failure must never surface as a 500 on the command path;
        # the deterministic understanding still serves the request.
        return None, None


def synthesize(
    message: str,
    context_text: str,
) -> str | None:
    """
    Ask the local model to explain already-computed facts.

    Used only for read intents, and only with context this process assembled
    from the user's own records. The prompt states that the figures are
    authoritative and that inventing a number is worse than saying less, but
    that instruction is a guardrail, not the guarantee — the guarantee is
    that every figure quoted back is one the client also received in the
    structured payload.
    """

    prompt = f"""You are the assistant inside AI-LifeOS.

Answer the user's question using only the LifeOS data below.
Never invent a number, a record, or an action.
If the data does not answer the question, say so plainly.
Keep it to a few short sentences. No lists longer than six items.

Verified LifeOS data:
{context_text}

Question: {message.strip()[:MAX_MESSAGE_LENGTH]}

Answer:"""

    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 320,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))

        text = (result.get("response") or "").strip()

        if not text:
            return None

        if len(text) > 2000:
            text = text[:2000].rsplit(" ", 1)[0]

        return text

    except urllib.error.URLError:
        return None
    except (TimeoutError, OSError):
        return None
    except json.JSONDecodeError:
        return None
    except Exception:
        return None


def provider_available() -> bool:
    """Whether Ollama answered a trivial generation request right now."""

    body = {
        "model": OLLAMA_MODEL,
        "prompt": "ok",
        "stream": False,
        "options": {"num_predict": 1},
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            json.loads(response.read().decode("utf-8"))

        return True

    except Exception:
        return False