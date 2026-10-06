"""
AI Command Center routes.

Three endpoints, and the split between them is the safety boundary:

    POST /ai/chat     understand, execute what is safe, propose the rest
    POST /ai/confirm  execute a plan the user just approved
    POST /ai/cancel   drop a plan the user declined

`/ai/chat` never runs a step that requires approval — it parks the plan under
a `plan_id` and returns. Only `/ai/confirm` reaches those runners, and only
for a plan whose id matches the authenticated user's own pending plan. The
model cannot approve anything, because it has no route into either decision.

`user_id` is taken from `get_current_user` on every route and from nowhere
else. It is never read from the request body, and no caller-supplied id can
reach a service.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    ActionCancelRequest,
    ActionConfirmRequest,
    AIChatRequest,
    AIChatResponse,
)
from app.services.ai_orchestration_service import (
    cancel_plan,
    confirm_plan,
    handle_command,
)


router = APIRouter(
    prefix="/ai",
    tags=["AI Brain"],
)


@router.post(
    "/chat",
    response_model=AIChatResponse,
)
def chat_with_ai(
    data: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIChatResponse:
    """
    Handle one command.

    Returns the full envelope: prose, whether a real provider call succeeded,
    the validated plan with each step's recorded status, and which LifeOS
    domains informed the answer.
    """

    return handle_command(
        db=db,
        user_id=current_user.id,
        message=data.message,
        conversation_id=data.conversation_id,
    )


@router.post(
    "/confirm",
    response_model=AIChatResponse,
)
def confirm_ai_action(
    data: ActionConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIChatResponse:
    """
    Execute a plan the user approved.

    A `plan_id` that is unknown, expired, already used, or owned by another
    user is reported as such and nothing runs — the response says so rather
    than failing silently or claiming success.
    """

    return confirm_plan(
        db=db,
        user_id=current_user.id,
        plan_id=data.plan_id,
        conversation_id=data.conversation_id,
    )


@router.post(
    "/cancel",
    response_model=AIChatResponse,
)
def cancel_ai_action(
    data: ActionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIChatResponse:
    """Drop a pending plan without applying it."""

    return cancel_plan(
        db=db,
        user_id=current_user.id,
        plan_id=data.plan_id,
        conversation_id=data.conversation_id,
    )