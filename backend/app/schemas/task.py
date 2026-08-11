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


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)