from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reminder import (
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.services.reminder_service import (
    create_user_reminder,
    delete_user_reminder,
    get_user_reminder,
    get_user_reminders,
    update_user_reminder,
)


router = APIRouter(
    prefix="/reminders",
    tags=["Reminders"],
)


@router.get(
    "",
    response_model=list[ReminderResponse],
)
def list_reminders(
    # Named `status_filter`, not `status`, so it cannot shadow the
    # `fastapi.status` module used by the decorators below.
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by reminder state: pending, completed or cancelled.",
    ),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    reminders = get_user_reminders(
        db=db,
        user_id=current_user.id,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        ReminderResponse.model_validate(reminder)
        for reminder in reminders
    ]


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reminder(
    data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    # `user_id` is taken from the token, never from the payload.
    reminder = create_user_reminder(
        db=db,
        user_id=current_user.id,
        title=data.title,
        message=data.message,
        remind_at=data.remind_at,
        task_id=data.task_id,
        habit_id=data.habit_id,
        planner_event_id=data.planner_event_id,
    )

    return ReminderResponse.model_validate(reminder)


@router.get(
    "/{reminder_id}",
    response_model=ReminderResponse,
)
def get_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    reminder = get_user_reminder(
        db=db,
        reminder_id=reminder_id,
        user_id=current_user.id,
    )

    return ReminderResponse.model_validate(reminder)


@router.patch(
    "/{reminder_id}",
    response_model=ReminderResponse,
)
def update_reminder(
    reminder_id: int,
    data: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    updates = data.model_dump(
        exclude_unset=True,
    )

    reminder = update_user_reminder(
        db=db,
        user_id=current_user.id,
        reminder_id=reminder_id,
        **updates,
    )

    return ReminderResponse.model_validate(reminder)


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_user_reminder(
        db=db,
        user_id=current_user.id,
        reminder_id=reminder_id,
    )
