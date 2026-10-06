from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    status: str = Field(
        default="pending",
        max_length=20,
    )

    priority: str = Field(
        default="medium",
        max_length=20,
    )

    due_date: datetime | None = None

    goal_id: int | None = None

    estimated_minutes: int = Field(
        default=45,
        ge=1,
    )


class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    status: str | None = Field(
        default=None,
        max_length=20,
    )

    priority: str | None = Field(
        default=None,
        max_length=20,
    )

    due_date: datetime | None = None

    goal_id: int | None = None

    estimated_minutes: int | None = Field(
        default=None,
        ge=1,
    )


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    goal_id: int | None
    estimated_minutes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)