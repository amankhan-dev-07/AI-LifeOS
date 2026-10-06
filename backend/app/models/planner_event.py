from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PlannerEvent(Base):
    __tablename__ = "planner_events"

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

    event_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="task",
    )

    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    habit_id: Mapped[int | None] = mapped_column(
        ForeignKey("habits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
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
        back_populates="planner_events",
    )
    task = relationship(
        "Task",
        back_populates="planner_events",
    )
    habit = relationship(
        "Habit",
        back_populates="planner_events",
    )
    # Cross-domain link from a reminder (SET NULL on delete).
    reminders = relationship(
        "Reminder",
        back_populates="planner_event",
    )

    __table_args__ = (
        Index(
            "ix_planner_events_user_date",
            "user_id",
            "event_date",
        ),
    )