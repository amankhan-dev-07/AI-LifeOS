from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import update_user_full_name


def update_user_profile(
    db: Session,
    user: User,
    full_name: str,
) -> User:
    """Update the current user's profile."""

    return update_user_full_name(
        db=db,
        user=user,
        full_name=full_name,
    )