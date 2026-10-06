from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction_service import (
    create_user_transaction,
    delete_user_transaction,
    get_user_transaction,
    get_user_transactions,
    update_user_transaction,
)


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    transaction = create_user_transaction(
        db=db,
        user_id=current_user.id,
        title=data.title,
        amount=data.amount,
        type=data.type,
        category=data.category,
        transaction_date=data.transaction_date,
        notes=data.notes,
    )

    return TransactionResponse.model_validate(transaction)


@router.get(
    "",
    response_model=list[TransactionResponse],
)
def list_transactions(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TransactionResponse]:
    transactions = get_user_transactions(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        type=type,
        category=category,
    )

    return [
        TransactionResponse.model_validate(transaction)
        for transaction in transactions
    ]


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    transaction = get_user_transaction(
        db=db,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )

    return TransactionResponse.model_validate(transaction)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    updates = data.model_dump(
        exclude_unset=True,
    )

    transaction = update_user_transaction(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
        **updates,
    )

    return TransactionResponse.model_validate(transaction)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_user_transaction(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )