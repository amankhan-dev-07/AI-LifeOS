from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.planner_event import (
    PlannerEventCreate,
    PlannerEventResponse,
    PlannerEventUpdate,
)
from app.services.planner_event_service import (
    create_user_event,
    delete_user_event,
    get_user_event,
    get_user_events,
    update_user_event,
)


router = APIRouter(
    prefix="/planner-events",
    tags=["Planner Events"],
)


@router.post(
    "",
    response_model=PlannerEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    data: PlannerEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlannerEventResponse:
    event = create_user_event(
        db=db,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        event_date=data.event_date,
        start_time=data.start_time,
        end_time=data.end_time,
        event_type=data.event_type,
        task_id=data.task_id,
        habit_id=data.habit_id,
    )

    return PlannerEventResponse.model_validate(event)


@router.get(
    "",
    response_model=list[PlannerEventResponse],
)
def list_events(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    is_completed: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlannerEventResponse]:
    events = get_user_events(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        is_completed=is_completed,
    )

    return [
        PlannerEventResponse.model_validate(event)
        for event in events
    ]


@router.get(
    "/{event_id}",
    response_model=PlannerEventResponse,
)
def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlannerEventResponse:
    event = get_user_event(
        db=db,
        event_id=event_id,
        user_id=current_user.id,
    )

    return PlannerEventResponse.model_validate(event)


@router.patch(
    "/{event_id}",
    response_model=PlannerEventResponse,
)
def update_event(
    event_id: int,
    data: PlannerEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlannerEventResponse:
    updates = data.model_dump(
        exclude_unset=True,
    )

    event = update_user_event(
        db=db,
        user_id=current_user.id,
        event_id=event_id,
        **updates,
    )

    return PlannerEventResponse.model_validate(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_user_event(
        db=db,
        user_id=current_user.id,
        event_id=event_id,
    )