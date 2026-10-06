"""
Wire contract for the AI Command Center.

The orchestration layer builds an `AICommandResponse` from its own internal
plan; nothing the model produces reaches the client directly. The model only
ever supplies the *interpretation* of a request — the plan, the confirmation
decision and the executed results are all assembled and validated server-side
before these shapes are filled in.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# =========================================================
# REQUEST
# =========================================================


class AIChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )

    # Client-generated handle used to keep a short conversation thread
    # together. It is opaque to the backend: it is echoed back so the client
    # can match a response to the turn it issued, and never used as a key to
    # read or write another user's data.
    conversation_id: str | None = Field(
        default=None,
        max_length=64,
    )

    # Id of a plan the user is approving or declining from the confirmation UI.
    # Required by /ai/confirm and ignored by /ai/chat.
    plan_id: str | None = Field(
        default=None,
        max_length=64,
    )


# =========================================================
# PLAN
# =========================================================


ActionOperation = Literal[
    "read",
    "create",
    "update",
    "complete",
    "delete",
    "search",
    "plan",
]

ActionEntity = Literal[
    "task",
    "goal",
    "habit",
    "note",
    "reminder",
    "planner_event",
    "transaction",
    "intelligence",
]


class ActionStep(BaseModel):
    """One validated step of a plan.

    `parameters` carries only values the backend re-validates against the
    domain schemas before execution, so a wrong field here fails loudly at the
    service boundary instead of silently writing a bad row.
    """

    order: int = Field(..., ge=1)

    operation: ActionOperation

    entity: ActionEntity

    #: Human-readable description of what this step will do, already rendered
    #: from validated values rather than from raw model text.
    description: str = Field(..., min_length=1, max_length=300)

    #: Resolved record the step targets, when one was found. Populated during
    #: context resolution, so the confirmation UI can name real records.
    target_id: int | None = None

    target_label: str | None = Field(
        default=None,
        max_length=300,
    )

    confirmation_required: bool = False

    confirmation_reason: str | None = Field(
        default=None,
        max_length=300,
    )

    parameters: dict[str, Any] = Field(default_factory=dict)

    #: Filled after execution. Never pre-filled — a step ships to the client
    #: with `status="pending"` and is only ever marked succeeded or failed by
    #: the executor, so the UI cannot render success for work that did not run.
    status: Literal[
        "pending",
        "succeeded",
        "failed",
        "skipped",
    ] = "pending"

    result_message: str | None = Field(
        default=None,
        max_length=500,
    )


class ActionPlanSummary(BaseModel):
    plan_id: str

    requires_confirmation: bool = False

    steps: list[ActionStep] = Field(default_factory=list)


# =========================================================
# CONFIRMATION
# =========================================================


class ActionConfirmRequest(BaseModel):
    plan_id: str = Field(..., max_length=64)

    conversation_id: str | None = Field(
        default=None,
        max_length=64,
    )


class ActionCancelRequest(BaseModel):
    plan_id: str = Field(..., max_length=64)

    conversation_id: str | None = Field(
        default=None,
        max_length=64,
    )


# =========================================================
# RESPONSE
# =========================================================


class AIChatResponse(BaseModel):
    """One turn of the command conversation.

    `response` is prose written by the deterministic formatter in the
    orchestration layer. `ai_online` reports whether a real provider call
    actually succeeded during this turn, so the UI never claims the model is
    available on the strength of a fallback path.
    """

    response: str

    ai_online: bool = True

    intent: str | None = Field(
        default=None,
        max_length=40,
    )

    plan: ActionPlanSummary | None = None

    #: Names of the LifeOS domains this turn actually read, so the UI can
    #: show which records informed the answer.
    context_used: list[str] = Field(default_factory=list)

    conversation_id: str | None = Field(
        default=None,
        max_length=64,
    )

    #: True when the request was understood but is waiting on the user — either
    #: a confirmation on a destructive step, or an answer to a clarification
    #: question. In both cases nothing has been written.
    awaiting_user: bool = False

    clarification_question: str | None = Field(
        default=None,
        max_length=500,
    )