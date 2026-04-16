from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from app.db.session import get_db
from app.models.transaction import Transaction, TransactionType
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.core.security import get_current_user

router = APIRouter(prefix="/portfolios/{portfolio_id}/transactions", tags=["transactions"])


def verify_ownership(portfolio_id: int, db: Session, user: User) -> Portfolio:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return portfolio


def compute_holdings(transactions: list[Transaction]) -> Dict[str, float]:
    holdings: Dict[str, float] = {}
    for tx in transactions:
        holdings[tx.ticker] = holdings.get(tx.ticker, 0)
        if tx.transaction_type == TransactionType.BUY:
            holdings[tx.ticker] += tx.quantity
        else:
            holdings[tx.ticker] -= tx.quantity
    return {k: v for k, v in holdings.items() if v > 0}


def compute_pnl(transactions: list[Transaction]) -> Dict[str, float]:
    """Realized P&L per ticker using FIFO cost basis."""
    lots: Dict[str, list] = {}
    pnl: Dict[str, float] = {}
    for tx in sorted(transactions, key=lambda t: t.executed_at):
        t = tx.ticker
        lots.setdefault(t, [])
        pnl.setdefault(t, 0.0)
        if tx.transaction_type == TransactionType.BUY:
            lots[t].append([tx.quantity, tx.price_per_share])
        else:
            remaining = tx.quantity
            while remaining > 0 and lots[t]:
                lot_qty, lot_price = lots[t][0]
                used = min(remaining, lot_qty)
                pnl[t] += used * (tx.price_per_share - lot_price)
                lots[t][0][0] -= used
                if lots[t][0][0] == 0:
                    lots[t].pop(0)
                remaining -= used
    return pnl


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    portfolio_id: int,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_ownership(portfolio_id, db, current_user)

    if payload.transaction_type == TransactionType.SELL:
        existing = db.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()
        holdings = compute_holdings(existing)
        if holdings.get(payload.ticker, 0) < payload.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient holdings for {payload.ticker}")

    tx = Transaction(**payload.model_dump(), portfolio_id=portfolio_id)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/", response_model=List[TransactionOut])
def list_transactions(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_ownership(portfolio_id, db, current_user)
    return db.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()


@router.get("/holdings", response_model=Dict[str, float])
def get_holdings(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_ownership(portfolio_id, db, current_user)
    transactions = db.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()
    return compute_holdings(transactions)


@router.get("/pnl", response_model=Dict[str, float])
def get_pnl(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_ownership(portfolio_id, db, current_user)
    transactions = db.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()
    return compute_pnl(transactions)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_ownership(portfolio_id, db, current_user)
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.portfolio_id == portfolio_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
