"""
Tests for Phase 14 AI API endpoints (integration tests).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.task import Task
from app.services.auth_service import create_access_token


@pytest.fixture(scope="function")
def client(db_session: Session, test_user: User):
    """Create a test client with auth and database override."""
    from app.db.session import get_db

    # Override get_db to use our test session
    app.dependency_overrides[get_db] = lambda: db_session

    token = create_access_token(data={"sub": str(test_user.id)})
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_tasks(db_session: Session, test_user: User) -> list[Task]:
    """Seed some tasks for testing."""
    tasks = [
        Task(
            user_id=test_user.id,
            title="Complete project proposal",
            description="Write and submit the Q4 project proposal",
            status="pending",
            priority="high",
        ),
        Task(
            user_id=test_user.id,
            title="Review pull requests",
            description="Review pending PRs from team",
            status="in_progress",
            priority="medium",
        ),
    ]
    for task in tasks:
        db_session.add(task)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)
    return tasks


class TestAIChatEndpoint:
    """Tests for POST /ai/chat endpoint."""

    def test_chat_read_tasks(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test reading tasks via API."""
        response = client.post("/api/v1/ai/chat", json={"message": "Show my tasks"})

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "read"
        assert data["ai_online"] is False
        assert "task" in data["context_used"]
        assert not data["awaiting_user"]
        assert data["plan"] is not None
        assert len(data["plan"]["steps"]) == 1
        assert data["plan"]["steps"][0]["status"] == "succeeded"

    def test_chat_create_task(self, client, db_session: Session, test_user: User):
        """Test creating a task via API."""
        response = client.post("/api/v1/ai/chat", json={"message": "Create a task to write documentation"})

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "create"
        assert not data["awaiting_user"]
        assert data["plan"] is not None
        step = data["plan"]["steps"][0]
        assert step["operation"] == "create"
        assert step["entity"] == "task"
        assert step["status"] == "succeeded"

    def test_chat_delete_requires_confirmation(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test that delete requires confirmation via API."""
        task = seed_tasks[0]
        response = client.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'"})

        assert response.status_code == 200
        data = response.json()
        assert data["awaiting_user"] is True
        assert data["plan"]["requires_confirmation"] is True
        assert len(data["plan"]["steps"]) == 1
        step = data["plan"]["steps"][0]
        assert step["operation"] == "delete"
        assert step["confirmation_required"] is True
        assert step["status"] == "pending"

    def test_chat_search(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test search via API."""
        response = client.post("/api/v1/ai/chat", json={"message": "Search for project"})

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "search"
        assert not data["awaiting_user"]
        assert data["plan"] is not None
        step = data["plan"]["steps"][0]
        assert step["operation"] == "search"
        assert step["entity"] == "intelligence"
        assert step["status"] == "succeeded"


class TestAIConfirmEndpoint:
    """Tests for POST /api/v1/ai/confirm endpoint."""

    def test_confirm_delete_task(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test confirming a task deletion via API."""
        task = seed_tasks[0]

        # Propose deletion
        propose = client.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'"})
        assert propose.status_code == 200
        propose_data = propose.json()
        assert propose_data["awaiting_user"] is True
        plan_id = propose_data["plan"]["plan_id"]

        # Confirm deletion
        confirm = client.post("/api/v1/ai/confirm", json={"plan_id": plan_id})
        assert confirm.status_code == 200
        confirm_data = confirm.json()
        assert confirm_data["awaiting_user"] is False
        assert confirm_data["plan"] is not None
        step = confirm_data["plan"]["steps"][0]
        assert step["status"] == "succeeded"
        assert step["operation"] == "delete"

        # Verify task is deleted
        deleted_task = db_session.query(Task).filter(Task.id == task.id).first()
        assert deleted_task is None

    def test_confirm_invalid_plan_id(self, client, db_session: Session, test_user: User):
        """Test confirming an invalid plan ID."""
        confirm = client.post("/api/v1/ai/confirm", json={"plan_id": "invalid-plan-id"})
        assert confirm.status_code == 200
        data = confirm.json()
        assert data["awaiting_user"] is False
        assert "no longer valid" in data["response"].lower() or "different session" in data["response"].lower()

    def test_confirm_already_used_plan(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test confirming an already-used plan."""
        task = seed_tasks[0]

        propose = client.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'"})
        plan_id = propose.json()["plan"]["plan_id"]

        # First confirmation
        confirm1 = client.post("/api/v1/ai/confirm", json={"plan_id": plan_id})
        assert confirm1.status_code == 200

        # Second confirmation should fail
        confirm2 = client.post("/api/v1/ai/confirm", json={"plan_id": plan_id})
        assert confirm2.status_code == 200
        data = confirm2.json()
        assert "no longer valid" in data["response"].lower()


class TestAICancelEndpoint:
    """Tests for POST /api/v1/ai/cancel endpoint."""

    def test_cancel_delete_task(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test cancelling a task deletion via API."""
        task = seed_tasks[0]

        propose = client.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'"})
        plan_id = propose.json()["plan"]["plan_id"]

        cancel = client.post("/api/v1/ai/cancel", json={"plan_id": plan_id})
        assert cancel.status_code == 200
        data = cancel.json()
        assert data["awaiting_user"] is False
        assert "cancelled" in data["response"].lower()
        assert "nothing was changed" in data["response"].lower()

        # Verify task still exists
        db_session.refresh(task)
        assert task.id is not None

    def test_cancel_invalid_plan_id(self, client, db_session: Session, test_user: User):
        """Test cancelling an invalid plan ID."""
        cancel = client.post("/api/v1/ai/cancel", json={"plan_id": "invalid-plan-id"})
        assert cancel.status_code == 200
        data = cancel.json()
        assert data["awaiting_user"] is False
        assert "no longer valid" in data["response"].lower() or "no longer pending" in data["response"].lower()


class TestAPICrossUserIsolation:
    """Tests for cross-user isolation at API level."""

    def test_user_cannot_access_another_users_plan(self, client, db_session: Session, test_user: User, test_user_2: User, seed_tasks):
        """Test that a user cannot confirm another user's plan."""
        task = seed_tasks[0]

        # test_user creates a plan
        token1 = create_access_token(data={"sub": str(test_user.id)})
        client1 = TestClient(app)
        client1.headers.update({"Authorization": f"Bearer {token1}"})

        propose = client1.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'"})
        plan_id = propose.json()["plan"]["plan_id"]

        # test_user_2 tries to confirm
        token2 = create_access_token(data={"sub": str(test_user_2.id)})
        client2 = TestClient(app)
        client2.headers.update({"Authorization": f"Bearer {token2}"})

        confirm = client2.post("/api/v1/ai/confirm", json={"plan_id": plan_id})
        assert confirm.status_code == 200
        data = confirm.json()
        assert "no longer valid" in data["response"].lower() or "different session" in data["response"].lower()

    def test_unauthorized_request_rejected(self, db_session: Session):
        """Test that requests without auth are rejected."""
        client = TestClient(app)
        # No auth header
        response = client.post("/api/v1/ai/chat", json={"message": "Show my tasks"})
        assert response.status_code == 401

        response = client.post("/api/v1/ai/confirm", json={"plan_id": "test"})
        assert response.status_code == 401

        response = client.post("/api/v1/ai/cancel", json={"plan_id": "test"})
        assert response.status_code == 401


class TestAPIConversationId:
    """Tests for conversation_id tracking."""

    def test_conversation_id_echoed_back(self, client, db_session: Session, test_user: User):
        """Test that conversation_id is echoed in responses."""
        conv_id = "test-conv-123"
        response = client.post("/api/v1/ai/chat", json={"message": "Show my tasks", "conversation_id": conv_id})

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conv_id

    def test_confirm_echoes_conversation_id(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test that confirm echoes conversation_id."""
        task = seed_tasks[0]
        conv_id = "test-conv-456"

        propose = client.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'", "conversation_id": conv_id})
        plan_id = propose.json()["plan"]["plan_id"]

        confirm = client.post("/api/v1/ai/confirm", json={"plan_id": plan_id, "conversation_id": conv_id})
        assert confirm.status_code == 200
        data = confirm.json()
        assert data["conversation_id"] == conv_id

    def test_cancel_echoes_conversation_id(self, client, db_session: Session, test_user: User, seed_tasks):
        """Test that cancel echoes conversation_id."""
        task = seed_tasks[0]
        conv_id = "test-conv-789"

        propose = client.post("/api/v1/ai/chat", json={"message": f"Delete the task '{task.title}'", "conversation_id": conv_id})
        plan_id = propose.json()["plan"]["plan_id"]

        cancel = client.post("/api/v1/ai/cancel", json={"plan_id": plan_id, "conversation_id": conv_id})
        assert cancel.status_code == 200
        data = cancel.json()
        assert data["conversation_id"] == conv_id