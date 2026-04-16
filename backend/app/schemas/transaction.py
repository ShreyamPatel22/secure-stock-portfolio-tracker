from pydantic import BaseModel, field_validator
from datetime import datetime
from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    ticker: str
    transaction_type: TransactionType
    quantity: float
    price_per_share: float

    @field_validator("quantity", "price_per_share")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Must be positive")
        return v

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class TransactionOut(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    transaction_type: TransactionType
    quantity: float
    price_per_share: float
    executed_at: datetime

    model_config = {"from_attributes": True}
