from pydantic import BaseModel


class PlanItem(BaseModel):
    type: str
    id: int
    title: str
    start_time: str
    end_time: str
    priority: str | None = None
    frequency: str | None = None
    current_streak: int | None = None


class PlannerSummary(BaseModel):
    pending_tasks: int
    active_goals: int
    active_habits: int


class DailyPlanResponse(BaseModel):
    success: bool
    date: str
    plan: list[PlanItem]
    goals: list[dict]
    summary: PlannerSummary