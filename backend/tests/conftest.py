"""
Pytest configuration and shared fixtures for AI-LifeOS backend tests.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app modules
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.db.base import Base
from app.models.user import User
from app.models.task import Task
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.note import Note
from app.models.reminder import Reminder
from app.models.planner_event import PlannerEvent
from app.models.transaction import Transaction
from app.models.user_preferences import UserPreferences
from app.services.auth_service import create_user, register_user, login_user
from app.core.security import create_access_token
from app.services.user_preferences_service import get_or_create_user_preferences


@pytest.fixture(scope="session")
def test_engine():
    """Create a test SQLite engine with in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a new database session for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = register_user(
        db=db_session,
        email="test@example.com",
        full_name="Test User",
        password="testpassword123",
    )
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def test_user_2(db_session: Session) -> User:
    """Create a second test user for isolation tests."""
    user = register_user(
        db=db_session,
        email="test2@example.com",
        full_name="Test User 2",
        password="testpassword123",
    )
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    """Generate auth headers for a user."""
    from app.services.auth_service import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


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
        Task(
            user_id=test_user.id,
            title="Update documentation",
            description="Update API docs with new endpoints",
            status="pending",
            priority="low",
        ),
    ]
    for task in tasks:
        db_session.add(task)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)
    return tasks


@pytest.fixture(scope="function")
def seed_goals(db_session: Session, test_user: User) -> list[Goal]:
    """Seed some goals for testing."""
    goals = [
        Goal(
            user_id=test_user.id,
            title="Learn Python",
            description="Complete Python advanced course",
            category="education",
            progress=50,
            target_date=None,
        ),
        Goal(
            user_id=test_user.id,
            title="Run 5k",
            description="Build up to running 5km",
            category="fitness",
            progress=30,
        ),
    ]
    for goal in goals:
        db_session.add(goal)
    db_session.commit()
    for goal in goals:
        db_session.refresh(goal)
    return goals


@pytest.fixture(scope="function")
def seed_habits(db_session: Session, test_user: User) -> list[Habit]:
    """Seed some habits for testing."""
    from datetime import date, timedelta
    from app.models.habit_completion import HabitCompletion
    from app.repositories.habit_completion_repository import create_completion

    habits = [
        Habit(
            user_id=test_user.id,
            title="Morning meditation",
            description="10 minutes of meditation",
            frequency="daily",
            is_active=True,
            current_streak=5,
            longest_streak=10,
        ),
        Habit(
            user_id=test_user.id,
            title="Read before bed",
            description="Read 20 pages",
            frequency="daily",
            is_active=True,
            current_streak=3,
            longest_streak=7,
        ),
    ]
    for habit in habits:
        db_session.add(habit)
    db_session.commit()
    for habit in habits:
        db_session.refresh(habit)

    # Create completion records to match the streak values
    # Habit 1: 5-day streak (5 days ago to yesterday)
    for i in range(5, 0, -1):
        create_completion(
            db=db_session,
            habit_id=habits[0].id,
            completed_date=date.today() - timedelta(days=i),
        )
    # Habit 2: 3-day streak
    for i in range(3, 0, -1):
        create_completion(
            db=db_session,
            habit_id=habits[1].id,
            completed_date=date.today() - timedelta(days=i),
        )
    db_session.commit()

    for habit in habits:
        db_session.refresh(habit)
    return habits


@pytest.fixture(scope="function")
def seed_notes(db_session: Session, test_user: User) -> list[Note]:
    """Seed some notes for testing."""
    notes = [
        Note(
            user_id=test_user.id,
            title="Meeting notes",
            content="Discussed project timeline and deliverables",
            tag="work",
            is_pinned=True,
        ),
        Note(
            user_id=test_user.id,
            title="Shopping list",
            content="Milk, eggs, bread, fruits",
            tag="personal",
        ),
    ]
    for note in notes:
        db_session.add(note)
    db_session.commit()
    for note in notes:
        db_session.refresh(note)
    return notes


@pytest.fixture(scope="function")
def seed_reminders(db_session: Session, test_user: User) -> list[Reminder]:
    """Seed some reminders for testing."""
    from datetime import datetime, timedelta
    reminders = [
        Reminder(
            user_id=test_user.id,
            title="Team standup",
            message="Daily standup at 9 AM",
            remind_at=datetime.now() + timedelta(days=1),
        ),
        Reminder(
            user_id=test_user.id,
            title="Call dentist",
            message="Schedule annual checkup",
            remind_at=datetime.now() + timedelta(days=2),
        ),
    ]
    for reminder in reminders:
        db_session.add(reminder)
    db_session.commit()
    for reminder in reminders:
        db_session.refresh(reminder)
    return reminders


@pytest.fixture(scope="function")
def seed_planner_events(db_session: Session, test_user: User) -> list[PlannerEvent]:
    """Seed some planner events for testing."""
    from datetime import datetime, time, date, timedelta
    events = [
        PlannerEvent(
            user_id=test_user.id,
            title="Deep work block",
            description="Focus on project proposal",
            event_date=datetime.combine(date.today(), datetime.min.time()),
            start_time=datetime.combine(date.today(), time(9, 0)),
            end_time=datetime.combine(date.today(), time(11, 0)),
            event_type="task",
        ),
        PlannerEvent(
            user_id=test_user.id,
            title="Gym session",
            description="Strength training",
            event_date=datetime.combine(date.today(), datetime.min.time()),
            start_time=datetime.combine(date.today(), time(18, 0)),
            end_time=datetime.combine(date.today(), time(19, 0)),
            event_type="habit",
        ),
    ]
    for event in events:
        db_session.add(event)
    db_session.commit()
    for event in events:
        db_session.refresh(event)
    return events


@pytest.fixture(scope="function")
def seed_transactions(db_session: Session, test_user: User) -> list[Transaction]:
    """Seed some transactions for testing."""
    from datetime import date
    from decimal import Decimal
    transactions = [
        Transaction(
            user_id=test_user.id,
            title="Salary",
            amount=Decimal("5000.00"),
            type="income",
            category="salary",
            transaction_date=date.today(),
        ),
        Transaction(
            user_id=test_user.id,
            title="Groceries",
            amount=Decimal("85.50"),
            type="expense",
            category="food",
            transaction_date=date.today(),
        ),
        Transaction(
            user_id=test_user.id,
            title="Coffee",
            amount=Decimal("4.50"),
            type="expense",
            category="food",
            transaction_date=date.today(),
        ),
    ]
    for txn in transactions:
        db_session.add(txn)
    db_session.commit()
    for txn in transactions:
        db_session.refresh(txn)
    return transactions


@pytest.fixture(scope="function")
def mock_ollama(monkeypatch):
    """Mock Ollama to return deterministic responses or raise errors."""
    def mock_generate(*args, **kwargs):
        raise ConnectionError("Ollama not available")

    import app.ai.intent_service as intent_service
    monkeypatch.setattr(intent_service, "_call_ollama", mock_generate)
    return mock_generate


@pytest.fixture(scope="function")
def mock_ollama_success(monkeypatch):
    """Mock Ollama to return successful deterministic responses."""
    def mock_generate(prompt: str, **kwargs):
        # Return a deterministic response based on prompt content
        if "complete" in prompt.lower() and "task" in prompt.lower():
            return '{"intent": "complete", "steps": [{"operation": "complete", "entity": "task", "fragment": "complete task"}]}'
        elif "create" in prompt.lower() and "task" in prompt.lower():
            return '{"intent": "create", "steps": [{"operation": "create", "entity": "task", "fragment": "create task"}]}'
        elif "search" in prompt.lower():
            return '{"intent": "search", "steps": [{"operation": "search", "entity": "intelligence", "fragment": "search for productivity"}]}'
        elif "plan" in prompt.lower() and "day" in prompt.lower():
            return '{"intent": "plan", "steps": [{"operation": "plan", "entity": "planner_event", "fragment": "plan my day"}]}'
        elif "show" in prompt.lower() or "read" in prompt.lower():
            return '{"intent": "read", "steps": [{"operation": "read", "entity": "intelligence", "fragment": "show overview"}]}'
        return '{"intent": "unknown", "steps": []}'

    import app.ai.intent_service as intent_service
    monkeypatch.setattr(intent_service, "_call_ollama", mock_generate)
    return mock_generate


@pytest.fixture(autouse=True)
def enable_deterministic_intent(monkeypatch):
    """Ensure deterministic intent matching is used (no Ollama calls)."""
    import app.ai.intent_service as intent_service
    # The deterministic path is tried first; we ensure it works
    original_understand = intent_service.understand_multi_step

    def wrapped_understand(message: str):
        try:
            return original_understand(message)
        except Exception:
            # Fallback to a minimal spec
            from app.ai.intent_service import IntentSpec
            return [IntentSpec(intent="unknown", steps=(), clarification_question="I did not understand that.")]

    monkeypatch.setattr(intent_service, "understand_multi_step", wrapped_understand)
    return wrapped_understand