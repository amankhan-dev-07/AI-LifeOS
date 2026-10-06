from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services.search_service import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_QUERY_LENGTH,
    MIN_QUERY_LENGTH,
    search_lifeos,
)


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.get(
    "",
    response_model=SearchResponse,
    summary="Global search across the authenticated user's LifeOS records",
)
def global_search(
    q: str = Query(
        ...,
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        description="Search term. Trimmed, 2-100 characters.",
    ),
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Maximum number of results to return.",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search tasks, goals, habits, notes, planner events and transactions.

    The user is resolved exclusively from the bearer token — no user_id is
    accepted from the client — so results are always scoped to the caller.
    """

    return search_lifeos(
        db=db,
        user_id=current_user.id,
        raw_query=q,
        limit=limit,
    )