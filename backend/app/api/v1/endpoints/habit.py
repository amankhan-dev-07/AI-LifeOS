from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.habit import HabitCreate, HabitResponse, HabitUpdate
from app.services.habit_service import (
    create_user_habit,
    delete_user_habit,
    get_user_habit,
    get_user_habits,
    update_user_habit,
)


router = APIRouter(
    prefix="/habits",
    tags=["Habits"],
)


@router.post(
    "",
    response_model=HabitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_habit(
    data: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HabitResponse:
    habit = create_user_habit(
        db=db,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        frequency=data.frequency,
    )

    return HabitResponse.model_validate(habit)


@router.get(
    "",
    response_model=list[HabitResponse],
)
def list_habits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HabitResponse]:
    habits = get_user_habits(
        db=db,
        user_id=current_user.id,
    )

    return [
        HabitResponse.model_validate(habit)
        for habit in habits
    ]


@router.get(
    "/{habit_id}",
    response_model=HabitResponse,
)
def get_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HabitResponse:
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

    return HabitResponse.model_validate(habit)


@router.put(
    "/{habit_id}",
    response_model=HabitResponse,
)
def update_habit(
    habit_id: int,
    data: HabitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HabitResponse:
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

    updates = data.model_dump(
        exclude_unset=True,
    )

    habit = update_user_habit(
        db=db,
        habit=habit,
        **updates,
    )

    return HabitResponse.model_validate(habit)


@router.delete(
    "/{habit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_habit(
    habit_id: int,
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

    delete_user_habit(
        db=db,
        habit=habit,
    )