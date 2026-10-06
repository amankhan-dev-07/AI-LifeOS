from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HabitCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    frequency: str = Field(
        default="daily",
        min_length=1,
        max_length=20,
    )

    goal_id: int | None = None


class HabitUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    frequency: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    is_active: bool | None = None

    current_streak: int | None = Field(
        default=None,
        ge=0,
    )

    longest_streak: int | None = Field(
        default=None,
        ge=0,
    )

    last_completed_at: datetime | None = None

    goal_id: int | None = None


class HabitResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    frequency: str
    goal_id: int | None
    is_active: bool
    current_streak: int
    longest_streak: int
    last_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)