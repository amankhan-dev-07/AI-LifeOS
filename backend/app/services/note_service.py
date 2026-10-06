from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.note import Note
from app.repositories.note_repository import (
    create_note,
    delete_note,
    get_note_by_id,
    get_notes_by_user,
    update_note,
)


def get_user_note(
    db: Session,
    note_id: int,
    user_id: int,
) -> Note:
    """Get one note belonging to the current user."""

    note = get_note_by_id(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found.",
        )

    return note


def create_user_note(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    tag: str,
    is_pinned: bool,
    goal_id: int | None,
    task_id: int | None,
) -> Note:
    """Create a note for the current user."""

    return create_note(
        db=db,
        user_id=user_id,
        title=title,
        content=content,
        tag=tag,
        is_pinned=is_pinned,
        goal_id=goal_id,
        task_id=task_id,
    )


def get_user_notes(
    db: Session,
    user_id: int,
    is_archived: bool | None = None,
    tag: str | None = None,
) -> list[Note]:
    """Get notes belonging to the current user."""

    return get_notes_by_user(
        db=db,
        user_id=user_id,
        is_archived=is_archived,
        tag=tag,
    )


def update_user_note(
    db: Session,
    user_id: int,
    note_id: int,
    **updates,
) -> Note:
    """Update a note belonging to the current user."""

    note = get_user_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    return update_note(
        db=db,
        note=note,
        **updates,
    )


def delete_user_note(
    db: Session,
    user_id: int,
    note_id: int,
) -> None:
    """Delete a note belonging to the current user."""

    note = get_user_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    delete_note(
        db=db,
        note=note,
    )