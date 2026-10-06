from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def create_transaction(
    db: Session,
    user_id: int,
    title: str,
    amount,
    type: str,
    category: str,
    transaction_date: date,
    notes: str | None,
) -> Transaction:
    """Create a new transaction for a user."""

    transaction = Transaction(
        user_id=user_id,
        title=title,
        amount=amount,
        type=type,
        category=category,
        transaction_date=transaction_date,
        notes=notes,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def get_transaction_by_id(
    db: Session,
    transaction_id: int,
    user_id: int,
) -> Transaction | None:
    """Get a specific transaction belonging to a user."""

    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    )

    return db.scalar(statement)


def get_transactions_by_user(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    type: str | None = None,
    category: str | None = None,
) -> list[Transaction]:
    """Get transactions belonging to a user with optional filters."""

    statement = select(Transaction).where(
        Transaction.user_id == user_id,
    )

    if start_date is not None:
        statement = statement.where(
            Transaction.transaction_date >= start_date,
        )

    if end_date is not None:
        statement = statement.where(
            Transaction.transaction_date <= end_date,
        )

    if type is not None:
        statement = statement.where(
            Transaction.type == type,
        )

    if category is not None:
        statement = statement.where(
            Transaction.category == category,
        )

    statement = statement.order_by(
        Transaction.transaction_date.desc(),
        Transaction.id.desc(),
    )

    return list(db.scalars(statement).all())


def update_transaction(
    db: Session,
    transaction: Transaction,
    **updates,
) -> Transaction:
    """Update an existing transaction."""

    for field, value in updates.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)

    return transaction


def delete_transaction(
    db: Session,
    transaction: Transaction,
) -> None:
    """Delete an existing transaction."""

    db.delete(transaction)
    db.commit()