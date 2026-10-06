from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.intelligence import IntelligenceResponse
from app.services.intelligence_service import get_intelligence


router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence"],
)


@router.get(
    "",
    response_model=IntelligenceResponse,
    summary="Deterministic insights over the authenticated user's LifeOS data",
)
def intelligence_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntelligenceResponse:
    """
    Snapshot the caller's own records and return derived, explainable insights.

    The user is resolved exclusively from the bearer token — no user_id is
    accepted from the client — so the response is always scoped to the caller.

    Everything here is computed per request from persisted rows. Nothing is
    stored, no external service is called, and the response is identical for
    identical data.
    """

    return get_intelligence(
        db=db,
        user_id=current_user.id,
    )