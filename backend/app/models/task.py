from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

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

    goal_id: Mapped[int | None] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
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

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=45,
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
        back_populates="tasks",
    )
    goal = relationship(
        "Goal",
        back_populates="tasks",
    )
    planner_events = relationship(
        "PlannerEvent",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    notes = relationship(
        "Note",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    # Cross-domain link from a reminder. The FK is SET NULL, so removing a
    # task must never cascade away the user's reminder.
    reminders = relationship(
        "Reminder",
        back_populates="task",
    )

    __table_args__ = (
        Index(
            "ix_tasks_user_status",
            "user_id",
            "status",
        ),
    )