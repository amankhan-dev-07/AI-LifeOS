from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.repositories.transaction_repository import (
    create_transaction,
    delete_transaction,
    get_transaction_by_id,
    get_transactions_by_user,
    update_transaction,
)

TRANSACTION_TYPES = (
    "income",
    "expense",
)


def validate_transaction_type(type: str) -> str:
    """Ensure a transaction type is one of the supported values."""

    if type not in TRANSACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction type.",
        )

    return type


def validate_amount(amount) -> Decimal:
    """Coerce an amount to a positive two-decimal Decimal."""

    try:
        value = Decimal(str(amount))
    except (ArithmeticError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction amount.",
        )

    if not value.is_finite():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction amount.",
        )

    if value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction amount must be greater than zero.",
        )

    return value.quantize(Decimal("0.01"))


def get_user_transaction(
    db: Session,
    transaction_id: int,
    user_id: int,
) -> Transaction:
    """Get one transaction belonging to the current user."""

    transaction = get_transaction_by_id(
        db=db,
        transaction_id=transaction_id,
        user_id=user_id,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found.",
        )

    return transaction


def create_user_transaction(
    db: Session,
    user_id: int,
    title: str,
    amount,
    type: str,
    category: str,
    transaction_date: date,
    notes: str | None,
) -> Transaction:
    """Create a transaction for the current user."""

    validate_transaction_type(type)
    value = validate_amount(amount)

    return create_transaction(
        db=db,
        user_id=user_id,
        title=title,
        amount=value,
        type=type,
        category=category,
        transaction_date=transaction_date,
        notes=notes,
    )


def get_user_transactions(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    type: str | None = None,
    category: str | None = None,
) -> list[Transaction]:
    """Get transactions belonging to the current user."""

    if type is not None:
        validate_transaction_type(type)

    return get_transactions_by_user(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        type=type,
        category=category,
    )


def update_user_transaction(
    db: Session,
    user_id: int,
    transaction_id: int,
    **updates,
) -> Transaction:
    """Update a transaction belonging to the current user."""

    transaction = get_user_transaction(
        db=db,
        transaction_id=transaction_id,
        user_id=user_id,
    )

    if "type" in updates and updates["type"] is not None:
        validate_transaction_type(updates["type"])

    if "amount" in updates and updates["amount"] is not None:
        updates["amount"] = validate_amount(updates["amount"])

    return update_transaction(
        db=db,
        transaction=transaction,
        **updates,
    )


def delete_user_transaction(
    db: Session,
    user_id: int,
    transaction_id: int,
) -> None:
    """Delete a transaction belonging to the current user."""

    transaction = get_user_transaction(
        db=db,
        transaction_id=transaction_id,
        user_id=user_id,
    )

    delete_transaction(
        db=db,
        transaction=transaction,
    )