"""
LifeOS Intelligence — orchestration.

Wires the three stages together and owns the boundary between them:

    context   (intelligence_context_service)  snapshot of persisted records
      ↓
    insight   (intelligence_rules_service)    deterministic rules over it
      ↓
    action    (here)                           route + label the UI navigates by

This is also the seam a future LLM stage would attach to. It would slot in
between `build_context` and `evaluate` — receiving the same snapshot, and
returning insights in the same shape — without either the context builder or
the rules changing. Nothing here assumes such a stage exists: the endpoint is
fully served by the deterministic path, with no network call, no API key and
no configuration.

`get_intelligence` is the only public entry point. It is deliberately
read-only and side-effect free, so calling it twice in a row with unchanged
data produces identical output.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.schemas.intelligence import IntelligenceResponse
from app.services import intelligence_rules_service as rules
from app.services.intelligence_context_service import (
    build_context,
    build_task_context,
)


def get_intelligence(
    db: Session,
    user_id: int,
    now: datetime | None = None,
) -> IntelligenceResponse:
    """
    Build the intelligence payload for one user.

    `user_id` is passed in by the endpoint from the authenticated request and
    is the only scope applied — every query underneath re-applies it, so
    nothing outside this user's records can reach the response. There is no
    code path here that reads a user id from the request body or query string.
    """

    context = build_context(db=db, user_id=user_id, now=now)

    insights = rules.evaluate(context)

    return IntelligenceResponse(
        generated_at=context.generated_at,
        summary=rules.build_attention_summary(context),
        tasks=build_task_context(context),
        goals=context.goals,
        habits=context.habits,
        upcoming=context.upcoming,
        finance=context.finance,
        insights=insights,
        has_data=context.has_data,
        populated_domains=context.populated_domains,
    )