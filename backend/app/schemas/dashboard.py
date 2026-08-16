from pydantic import BaseModel


class TaskSummary(BaseModel):
    total: int
    pending: int
    completed: int


class GoalSummary(BaseModel):
    total: int
    active: int
    completed: int


class HabitSummary(BaseModel):
    total: int
    active: int
    current_streak: int
    best_streak: int


class DashboardResponse(BaseModel):
    tasks: TaskSummary
    goals: GoalSummary
    habits: HabitSummary