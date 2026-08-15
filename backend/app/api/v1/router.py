from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.goal import router as goal_router
from app.api.v1.endpoints.habit import router as habit_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.task import router as tasks_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.habit_completion import router as habit_completion_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(tasks_router)
api_router.include_router(goal_router)
api_router.include_router(habit_router)
api_router.include_router(habit_completion_router)