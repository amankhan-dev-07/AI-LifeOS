from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.services.goal_service import (
    create_user_goal,
    delete_user_goal,
    get_user_goal,
    get_user_goals,
    update_user_goal,
)


router = APIRouter(
    prefix="/goals",
    tags=["Goals"],
)


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_goal(
    data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    goal = create_user_goal(
        db=db,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        target_date=data.target_date,
    )

    return GoalResponse.model_validate(goal)


@router.get(
    "",
    response_model=list[GoalResponse],
)
def list_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GoalResponse]:
    goals = get_user_goals(
        db=db,
        user_id=current_user.id,
    )

    return [
        GoalResponse.model_validate(goal)
        for goal in goals
    ]


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
)
def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    goal = get_user_goal(
        db=db,
        goal_id=goal_id,
        user_id=current_user.id,
    )

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found.",
        )

    return GoalResponse.model_validate(goal)


@router.put(
    "/{goal_id}",
    response_model=GoalResponse,
)
def update_goal(
    goal_id: int,
    data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    goal = get_user_goal(
        db=db,
        goal_id=goal_id,
        user_id=current_user.id,
    )

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found.",
        )

    updates = data.model_dump(
        exclude_unset=True,
    )

    goal = update_user_goal(
        db=db,
        goal=goal,
        **updates,
    )

    return GoalResponse.model_validate(goal)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    goal = get_user_goal(
        db=db,
        goal_id=goal_id,
        user_id=current_user.id,
    )

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found.",
        )

    delete_user_goal(
        db=db,
        goal=goal,
    )