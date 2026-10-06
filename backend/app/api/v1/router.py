from fastapi import APIRouter

from app.api.v1.endpoints.planner import router as planner_router
from app.api.v1.endpoints.planner_event import router as planner_event_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.goal import router as goal_router
from app.api.v1.endpoints.habit import router as habit_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.task import router as tasks_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.habit_completion import router as habit_completion_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.note import router as note_router
from app.api.v1.endpoints.transaction import router as transaction_router
from app.api.v1.endpoints.notification import router as notification_router
from app.api.v1.endpoints.user_preferences import router as preferences_router
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.reminder import router as reminder_router
from app.api.v1.endpoints.intelligence import router as intelligence_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(tasks_router)
api_router.include_router(goal_router)
api_router.include_router(habit_router)
api_router.include_router(habit_completion_router)
api_router.include_router(dashboard_router)
api_router.include_router(ai_router)
api_router.include_router(planner_router)
api_router.include_router(planner_event_router)
api_router.include_router(note_router)
api_router.include_router(transaction_router)
api_router.include_router(notification_router)
api_router.include_router(preferences_router)
api_router.include_router(search_router)
api_router.include_router(reminder_router)
api_router.include_router(intelligence_router)