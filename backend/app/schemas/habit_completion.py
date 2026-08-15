from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class HabitCompletionCreate(BaseModel):
    completed_date: date


class HabitCompletionResponse(BaseModel):
    id: int
    habit_id: int
    completed_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)