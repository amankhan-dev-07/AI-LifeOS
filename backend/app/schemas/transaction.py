from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    amount: Decimal

    type: str = Field(
        min_length=1,
        max_length=20,
    )

    category: str = Field(
        default="General",
        min_length=1,
        max_length=50,
    )

    transaction_date: date

    notes: str | None = None


class TransactionUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    amount: Decimal | None = None

    type: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    transaction_date: date | None = None

    notes: str | None = None


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    amount: Decimal
    type: str
    category: str
    transaction_date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)