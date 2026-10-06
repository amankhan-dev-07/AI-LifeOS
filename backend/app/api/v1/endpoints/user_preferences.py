from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user_preferences import (
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from app.services.user_preferences_service import (
    get_or_create_user_preferences,
    update_user_preferences,
)


router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
)


@router.get(
    "",
    response_model=UserPreferencesResponse,
)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    preferences = get_or_create_user_preferences(
        db=db,
        user_id=current_user.id,
    )

    return UserPreferencesResponse.model_validate(preferences)


@router.patch(
    "",
    response_model=UserPreferencesResponse,
)
def update_preferences(
    data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    updates = data.model_dump(
        exclude_unset=True,
    )

    preferences = update_user_preferences(
        db=db,
        user_id=current_user.id,
        **updates,
    )

    return UserPreferencesResponse.model_validate(preferences)