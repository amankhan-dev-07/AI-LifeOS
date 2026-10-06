from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlannerEventCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    event_date: datetime

    start_time: datetime

    end_time: datetime

    event_type: str = Field(
        default="task",
        min_length=1,
        max_length=20,
    )

    task_id: int | None = None

    habit_id: int | None = None


class PlannerEventUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    event_date: datetime | None = None

    start_time: datetime | None = None

    end_time: datetime | None = None

    event_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    task_id: int | None = None

    habit_id: int | None = None

    is_completed: bool | None = None


class PlannerEventResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    event_date: datetime
    start_time: datetime
    end_time: datetime
    event_type: str
    task_id: int | None
    habit_id: int | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)