from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
    )

    target_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="goals",
    )
    tasks = relationship(
        "Task",
        back_populates="goal",
        # Task is owned by User (User.tasks has delete-orphan), not by Goal.
        # The FK has ON DELETE SET NULL — tasks survive goal deletion.
        # No ORM cascades needed; the DB handles the NULLing.
        cascade="",
    )
    habits = relationship(
        "Habit",
        back_populates="goal",
        cascade="all, delete-orphan",
    )
    notes = relationship(
        "Note",
        back_populates="goal",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_goals_user_completed",
            "user_id",
            "is_completed",
        ),
    )