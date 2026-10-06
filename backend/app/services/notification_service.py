from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories.notification_repository import (
    create_notification,
    delete_notification,
    get_notification_by_id,
    get_notifications_by_user,
    get_unread_notifications_by_user,
    update_notification,
)


def get_user_notification(
    db: Session,
    notification_id: int,
    user_id: int,
) -> Notification:
    """Get one notification belonging to the current user."""

    notification = get_notification_by_id(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return notification


def create_user_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str,
    link: str | None,
) -> Notification:
    """Create a notification for the current user."""

    return create_notification(
        db=db,
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link,
    )


def get_user_notifications(
    db: Session,
    user_id: int,
    is_read: bool | None = None,
) -> list[Notification]:
    """Get notifications belonging to the current user."""

    return get_notifications_by_user(
        db=db,
        user_id=user_id,
        is_read=is_read,
    )


def get_user_unread_notifications(
    db: Session,
    user_id: int,
) -> list[Notification]:
    """Get the current user's unread notifications."""

    return get_unread_notifications_by_user(
        db=db,
        user_id=user_id,
    )


def mark_notification_read(
    db: Session,
    user_id: int,
    notification_id: int,
) -> Notification:
    """Mark one notification belonging to the current user as read."""

    notification = get_user_notification(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if notification.is_read:
        return notification

    return update_notification(
        db=db,
        notification=notification,
        is_read=True,
        read_at=datetime.utcnow(),
    )


def mark_all_notifications_read(
    db: Session,
    user_id: int,
) -> int:
    """Mark every unread notification belonging to the current user as read."""

    unread = get_unread_notifications_by_user(
        db=db,
        user_id=user_id,
    )

    if not unread:
        return 0

    read_at = datetime.utcnow()

    for notification in unread:
        notification.is_read = True
        notification.read_at = read_at

    db.commit()

    return len(unread)


def update_user_notification(
    db: Session,
    user_id: int,
    notification_id: int,
    **updates,
) -> Notification:
    """Update a notification belonging to the current user."""

    notification = get_user_notification(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if "is_read" in updates:
        updates["read_at"] = (
            datetime.utcnow()
            if updates["is_read"]
            else None
        )

    return update_notification(
        db=db,
        notification=notification,
        **updates,
    )


def delete_user_notification(
    db: Session,
    user_id: int,
    notification_id: int,
) -> None:
    """Delete a notification belonging to the current user."""

    notification = get_user_notification(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )

    delete_notification(
        db=db,
        notification=notification,
    )