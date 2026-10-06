from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str,
    link: str | None,
) -> Notification:
    """Create a new notification for a user."""

    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def get_notification_by_id(
    db: Session,
    notification_id: int,
    user_id: int,
) -> Notification | None:
    """Get a specific notification belonging to a user."""

    statement = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )

    return db.scalar(statement)


def get_notifications_by_user(
    db: Session,
    user_id: int,
    is_read: bool | None = None,
) -> list[Notification]:
    """Get notifications belonging to a user, newest first."""

    statement = select(Notification).where(
        Notification.user_id == user_id,
    )

    if is_read is not None:
        statement = statement.where(
            Notification.is_read == is_read,
        )

    statement = statement.order_by(
        Notification.created_at.desc(),
        Notification.id.desc(),
    )

    return list(db.scalars(statement).all())


def get_unread_notifications_by_user(
    db: Session,
    user_id: int,
) -> list[Notification]:
    """Get unread notifications belonging to a user, newest first."""

    return get_notifications_by_user(
        db=db,
        user_id=user_id,
        is_read=False,
    )


def update_notification(
    db: Session,
    notification: Notification,
    **updates,
) -> Notification:
    """Update an existing notification."""

    for field, value in updates.items():
        setattr(notification, field, value)

    db.commit()
    db.refresh(notification)

    return notification


def delete_notification(
    db: Session,
    notification: Notification,
) -> None:
    """Delete an existing notification."""

    db.delete(notification)
    db.commit()