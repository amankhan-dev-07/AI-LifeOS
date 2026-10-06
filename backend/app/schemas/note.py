from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    content: str = ""

    tag: str = Field(
        default="General",
        min_length=1,
        max_length=50,
    )

    is_pinned: bool = False

    goal_id: int | None = None

    task_id: int | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    content: str | None = None

    tag: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    is_pinned: bool | None = None

    is_archived: bool | None = None

    goal_id: int | None = None

    task_id: int | None = None


class NoteResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    tag: str
    is_pinned: bool
    is_archived: bool
    goal_id: int | None
    task_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)