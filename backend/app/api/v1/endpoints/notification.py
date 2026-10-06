from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services.notification_service import (
    get_user_notification,
    get_user_notifications,
    get_user_unread_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=list[NotificationResponse],
)
def list_notifications(
    is_read: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    notifications = get_user_notifications(
        db=db,
        user_id=current_user.id,
        is_read=is_read,
    )

    return [
        NotificationResponse.model_validate(notification)
        for notification in notifications
    ]


@router.get(
    "/unread",
    response_model=list[NotificationResponse],
)
def list_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    notifications = get_user_unread_notifications(
        db=db,
        user_id=current_user.id,
    )

    return [
        NotificationResponse.model_validate(notification)
        for notification in notifications
    ]


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    mark_all_notifications_read(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
)
def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    notification = get_user_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )

    return NotificationResponse.model_validate(notification)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    notification = mark_notification_read(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )

    return NotificationResponse.model_validate(notification)