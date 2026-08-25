from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_brain_service import ask_brain


router = APIRouter(
    prefix="/ai",
    tags=["AI Brain"],
)


@router.post(
    "/chat",
    response_model=AIChatResponse,
)
def chat_with_ai(
    data: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIChatResponse:

    response = ask_brain(
        message=data.message,
        db=db,
        user_id=current_user.id,
    )

    return AIChatResponse(
        response=response,
    )