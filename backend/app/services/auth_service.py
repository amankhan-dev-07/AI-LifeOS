from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
)


def register_user(
    db: Session,
    email: str,
    full_name: str,
    password: str,
):
    """Register a new user."""

    existing_user = get_user_by_email(
        db,
        email,
    )

    if existing_user:
        raise ValueError("Email is already registered.")

    hashed_password = hash_password(password)

    return create_user(
        db=db,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
    )


def login_user(
    db: Session,
    email: str,
    password: str,
):
    """Authenticate a user and return an access token."""

    user = get_user_by_email(
        db,
        email,
    )

    if not user:
        raise ValueError("Invalid email or password.")

    if not verify_password(
        password,
        user.hashed_password,
    ):
        raise ValueError("Invalid email or password.")

    if not user.is_active:
        raise ValueError("User account is inactive.")

    access_token = create_access_token(
        data={
            "sub": str(user.id),
        }
    )

    return access_token