from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    tasks = relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    goals = relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    habits = relationship(
        "Habit",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    planner_events = relationship(
        "PlannerEvent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notes = relationship(
        "Note",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reminders = relationship(
        "Reminder",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    preferences = relationship(
        "UserPreferences",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )