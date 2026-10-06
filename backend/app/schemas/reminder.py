from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReminderCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    message: str | None = None

    remind_at: datetime

    task_id: int | None = None

    habit_id: int | None = None

    planner_event_id: int | None = None


class ReminderUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    message: str | None = None

    remind_at: datetime | None = None

    task_id: int | None = None

    habit_id: int | None = None

    planner_event_id: int | None = None

    is_completed: bool | None = None

    is_cancelled: bool | None = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str | None
    remind_at: datetime
    status: str
    is_completed: bool
    is_cancelled: bool
    notified_at: datetime | None
    task_id: int | None
    habit_id: int | None
    planner_event_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
