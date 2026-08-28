from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.planner_service import get_daily_plan


router = APIRouter(
    prefix="/planner",
    tags=["Planner"],
)


@router.get("/today")
def get_today_planner(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return get_daily_plan(
        db=db,
        user_id=current_user.id,
    )