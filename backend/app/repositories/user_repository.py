from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """Get a user by email."""

    statement = select(User).where(User.email == email)

    return db.scalar(statement)


def get_user_by_id(
    db: Session,
    user_id: int,
) -> User | None:
    """Get a user by ID."""

    statement = select(User).where(User.id == user_id)

    return db.scalar(statement)


def create_user(
    db: Session,
    email: str,
    full_name: str,
    hashed_password: str,
) -> User:
    """Create and persist a new user."""

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def update_user_full_name(
    db: Session,
    user: User,
    full_name: str,
) -> User:
    """Update a user's full name."""

    user.full_name = full_name

    db.commit()
    db.refresh(user)

    return user