"""
Tests for Phase 14 AI read commands (acceptance areas 1-8).
"""
import pytest
from sqlalchemy.orm import Session

from app.services.ai_orchestration_service import handle_command
from app.models.user import User


class TestReadCommands:
    """Tests for read commands across all domains."""

    def test_read_intelligence_overview(self, db_session: Session, test_user: User, seed_tasks, seed_goals, seed_habits):
        """Test reading the full intelligence overview (area 1)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show me my LifeOS overview",
        )

        assert response.intent == "read"
        assert response.ai_online is False  # deterministic path
        assert "overview" in response.response.lower() or "stand" in response.response.lower()
        assert "task" in response.context_used or "intelligence" in response.context_used
        assert not response.awaiting_user

    def test_read_tasks(self, db_session: Session, test_user: User, seed_tasks):
        """Test reading tasks (area 2)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my tasks",
        )

        assert response.intent == "read"
        assert "task" in response.context_used
        assert "project proposal" in response.response or "pull request" in response.response
        assert not response.awaiting_user

    def test_read_goals(self, db_session: Session, test_user: User, seed_goals):
        """Test reading goals (area 3)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my goals",
        )

        assert response.intent == "read"
        assert "goal" in response.context_used
        assert "Learn Python" in response.response or "Run 5k" in response.response
        assert not response.awaiting_user

    def test_read_habits(self, db_session: Session, test_user: User, seed_habits):
        """Test reading habits (area 4)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my habits",
        )

        assert response.intent == "read"
        assert "habit" in response.context_used
        assert "meditation" in response.response or "Read before bed" in response.response
        assert "streak" in response.response.lower()
        assert not response.awaiting_user

    def test_read_planner(self, db_session: Session, test_user: User, seed_planner_events):
        """Test reading planner events (area 5)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my planner",
        )

        assert response.intent == "read"
        assert "planner_event" in response.context_used
        assert "Deep work" in response.response or "Gym" in response.response
        assert not response.awaiting_user

    def test_read_notes(self, db_session: Session, test_user: User, seed_notes):
        """Test reading notes (area 6)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my notes",
        )

        assert response.intent == "read"
        assert "note" in response.context_used
        assert "Meeting notes" in response.response or "Shopping list" in response.response
        assert not response.awaiting_user

    def test_read_finance(self, db_session: Session, test_user: User, seed_transactions):
        """Test reading finance/transactions (area 7)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my finances",
        )

        assert response.intent == "read"
        assert "transaction" in response.context_used
        assert "5000" in response.response or "income" in response.response.lower()
        assert "expense" in response.response.lower()
        assert not response.awaiting_user

    def test_read_reminders(self, db_session: Session, test_user: User, seed_reminders):
        """Test reading reminders (area 8)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my reminders",
        )

        assert response.intent == "read"
        assert "reminder" in response.context_used
        assert "standup" in response.response.lower() or "dentist" in response.response.lower()
        assert not response.awaiting_user