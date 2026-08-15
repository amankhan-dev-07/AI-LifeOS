from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.habit_completion import (
    HabitCompletionCreate,
    HabitCompletionResponse,
)
from app.services.habit_completion_service import (
    complete_habit,
    get_habit_completions,
    remove_habit_completion,
)
from app.services.habit_service import get_user_habit


router = APIRouter(
    prefix="/habits",
    tags=["Habit Completions"],
)


@router.post(
    "/{habit_id}/complete",
    response_model=HabitCompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_habit_endpoint(
    habit_id: int,
    data: HabitCompletionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HabitCompletionResponse:
    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=current_user.id,
    )

    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found.",
        )

    completion = complete_habit(
        db=db,
        habit=habit,
        completed_date=data.completed_date,
    )

    return HabitCompletionResponse.model_validate(completion)


@router.get(
    "/{habit_id}/completions",
    response_model=list[HabitCompletionResponse],
)
def list_habit_completions(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HabitCompletionResponse]:
    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=current_user.id,
    )

    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found.",
        )

    completions = get_habit_completions(
        db=db,
        habit=habit,
    )

    return [
        HabitCompletionResponse.model_validate(completion)
        for completion in completions
    ]


@router.delete(
    "/{habit_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_habit_completion_endpoint(
    habit_id: int,
    completed_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    habit = get_user_habit(
        db=db,
        habit_id=habit_id,
        user_id=current_user.id,
    )

    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found.",
        )

    remove_habit_completion(
        db=db,
        habit=habit,
        completed_date=completed_date,
    )