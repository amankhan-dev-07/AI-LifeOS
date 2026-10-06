from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.note import (
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)
from app.services.note_service import (
    create_user_note,
    delete_user_note,
    get_user_note,
    get_user_notes,
    update_user_note,
)


router = APIRouter(
    prefix="/notes",
    tags=["Notes"],
)


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    note = create_user_note(
        db=db,
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        tag=data.tag,
        is_pinned=data.is_pinned,
        goal_id=data.goal_id,
        task_id=data.task_id,
    )

    return NoteResponse.model_validate(note)


@router.get(
    "",
    response_model=list[NoteResponse],
)
def list_notes(
    is_archived: bool | None = Query(default=None),
    tag: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteResponse]:
    notes = get_user_notes(
        db=db,
        user_id=current_user.id,
        is_archived=is_archived,
        tag=tag,
    )

    return [
        NoteResponse.model_validate(note)
        for note in notes
    ]


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
)
def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    note = get_user_note(
        db=db,
        note_id=note_id,
        user_id=current_user.id,
    )

    return NoteResponse.model_validate(note)


@router.patch(
    "/{note_id}",
    response_model=NoteResponse,
)
def update_note(
    note_id: int,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    updates = data.model_dump(
        exclude_unset=True,
    )

    note = update_user_note(
        db=db,
        user_id=current_user.id,
        note_id=note_id,
        **updates,
    )

    return NoteResponse.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_user_note(
        db=db,
        user_id=current_user.id,
        note_id=note_id,
    )