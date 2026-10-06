from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EntityType = Literal[
    "task",
    "goal",
    "habit",
    "note",
    "planner_event",
    "transaction",
]


class SearchResult(BaseModel):
    """One record matched by global search.

    Deliberately narrow: only fields the frontend needs to render a result row
    and navigate to the owning page. Full note bodies, transaction amounts and
    other internal columns are never exposed here.
    """

    id: int
    entity_type: EntityType = Field(
        description="Which LifeOS entity this result came from.",
    )
    title: str
    snippet: str | None = None
    context: str | None = None
    route: str = Field(
        description="Frontend view key the result belongs to.",
    )
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    frequency: str | None = None
    tag: str | None = None
    date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Result envelope for a single global search call."""

    query: str
    count: int
    results: list[SearchResult]