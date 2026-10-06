from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.note import Note


def create_note(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    tag: str,
    is_pinned: bool,
    goal_id: int | None,
    task_id: int | None,
) -> Note:
    """Create a new note for a user."""

    note = Note(
        user_id=user_id,
        title=title,
        content=content,
        tag=tag,
        is_pinned=is_pinned,
        goal_id=goal_id,
        task_id=task_id,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return note


def get_note_by_id(
    db: Session,
    note_id: int,
    user_id: int,
) -> Note | None:
    """Get a specific note belonging to a user."""

    statement = select(Note).where(
        Note.id == note_id,
        Note.user_id == user_id,
    )

    return db.scalar(statement)


def get_notes_by_user(
    db: Session,
    user_id: int,
    is_archived: bool | None = None,
    tag: str | None = None,
) -> list[Note]:
    """Get notes belonging to a user with optional filters."""

    statement = select(Note).where(
        Note.user_id == user_id,
    )

    if is_archived is not None:
        statement = statement.where(
            Note.is_archived == is_archived,
        )

    if tag is not None:
        statement = statement.where(
            Note.tag == tag,
        )

    statement = statement.order_by(
        Note.is_pinned.desc(),
        Note.created_at.desc(),
        Note.id.desc(),
    )

    return list(db.scalars(statement).all())


def update_note(
    db: Session,
    note: Note,
    **updates,
) -> Note:
    """Update an existing note."""

    for field, value in updates.items():
        setattr(note, field, value)

    db.commit()
    db.refresh(note)

    return note


def delete_note(
    db: Session,
    note: Note,
) -> None:
    """Delete an existing note."""

    db.delete(note)
    db.commit()