import logging
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.search_repository import (
    search_goals,
    search_habits,
    search_notes,
    search_planner_events,
    search_tasks,
    search_transactions,
)
from app.schemas.search import SearchResponse, SearchResult


logger = logging.getLogger(__name__)


MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
DEFAULT_LIMIT = 20
MAX_LIMIT = 50

# Upper bound on rows fetched per domain before merging. Keeps each of the six
# statements bounded regardless of how many matches a term has.
PER_ENTITY_LIMIT_CAP = 25

SNIPPET_LENGTH = 140


def normalize_query(raw_query: str) -> str:
    """Trim the raw query and enforce the accepted length window.

    Raises a 422 for anything outside 2..100 characters so the client gets a
    clear validation error instead of an unbounded query.
    """

    query = (raw_query or "").strip()

    if len(query) < MIN_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Search query must be at least {MIN_QUERY_LENGTH} characters."
            ),
        )

    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Search query must be at most {MAX_QUERY_LENGTH} characters."
            ),
        )

    return query


def clamp_limit(limit: int) -> int:
    """Keep result sets bounded no matter what the client asks for."""

    return max(1, min(limit, MAX_LIMIT))


def _snippet(text: str | None, term: str) -> str | None:
    """Collapse a matched body down to a short snippet around the term."""

    if not text:
        return None

    collapsed = " ".join(text.split())

    if not collapsed:
        return None

    index = collapsed.lower().find(term.lower())

    if index < 0:
        return collapsed[:SNIPPET_LENGTH]

    start = max(0, index - SNIPPET_LENGTH // 3)
    end = min(len(collapsed), start + SNIPPET_LENGTH)

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(collapsed) else ""

    return f"{prefix}{collapsed[start:end]}{suffix}"


def _format_date(value: date | datetime | None) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    return value.isoformat()


def search_lifeos(
    db: Session,
    user_id: int,
    raw_query: str,
    limit: int = DEFAULT_LIMIT,
) -> SearchResponse:
    """Run global search across the authenticated user's LifeOS records.

    Every repository call receives `user_id` and scopes on it, so no query can
    surface another user's data regardless of the search term.
    """

    query = normalize_query(raw_query)
    safe_limit = clamp_limit(limit)

    # Fetch at most PER_ENTITY_LIMIT_CAP rows per domain so one noisy entity type
    # cannot monopolize the response, then trim the merged list to `limit`.
    per_entity_limit = min(safe_limit, PER_ENTITY_LIMIT_CAP)

    try:
        tasks = search_tasks(db, user_id, query, per_entity_limit)
        goals = search_goals(db, user_id, query, per_entity_limit)
        habits = search_habits(db, user_id, query, per_entity_limit)
        notes = search_notes(db, user_id, query, per_entity_limit)
        planner_events = search_planner_events(db, user_id, query, per_entity_limit)
        transactions = search_transactions(db, user_id, query, per_entity_limit)
    except HTTPException:
        raise
    except Exception:
        # Log the real cause server-side, but never leak SQL/database
        # internals to the client.
        logger.exception("Global search query failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search is temporarily unavailable.",
        )

    results: list[SearchResult] = []

    results.extend(
        SearchResult(
            id=row.id,
            entity_type="task",
            title=row.title,
            snippet=_snippet(row.description, query),
            context=row.status,
            route="tasks",
            status=row.status,
            priority=row.priority,
            date=_format_date(row.updated_at),
        )
        for row in tasks
    )

    results.extend(
        SearchResult(
            id=row.id,
            entity_type="goal",
            title=row.title,
            snippet=_snippet(row.description, query),
            context=row.category,
            route="goals",
            status="completed" if row.is_completed else "active",
            date=_format_date(row.target_date),
        )
        for row in goals
    )

    results.extend(
        SearchResult(
            id=row.id,
            entity_type="habit",
            title=row.title,
            snippet=_snippet(row.description, query),
            context=row.frequency,
            route="habits",
            status="active" if row.is_active else "paused",
            frequency=row.frequency,
            date=_format_date(row.updated_at),
        )
        for row in habits
    )

    results.extend(
        SearchResult(
            id=row.id,
            entity_type="note",
            title=row.title,
            snippet=_snippet(row.content, query),
            context="",
            route="notes",
            tag=row.tag,
            date=_format_date(row.updated_at),
        )
        for row in notes
    )

    results.extend(
        SearchResult(
            id=row.id,
            entity_type="planner_event",
            title=row.title,
            snippet=_snippet(row.description, query),
            context=row.event_type,
            route="planner",
            category=row.event_type,
            date=_format_date(row.event_date),
        )
        for row in planner_events
    )

    results.extend(
        SearchResult(
            id=row.id,
            entity_type="transaction",
            title=row.title,
            snippet=_snippet(row.notes, query),
            context=f"{row.type} • {row.category}",
            route="finance",
            category=row.category,
            status=row.type,
            date=_format_date(row.transaction_date),
        )
        for row in transactions
    )

    return SearchResponse(
        query=query,
        count=min(len(results), safe_limit),
        results=results[:safe_limit],
    )