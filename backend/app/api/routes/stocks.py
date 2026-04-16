from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.stock_service import fetch_quote, fetch_daily_series
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.transaction import Transaction, TransactionType
from app.models.portfolio import Portfolio
from app.api.routes.transactions import compute_holdings, verify_ownership

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}/quote")
async def get_quote(ticker: str, _: User = Depends(get_current_user)):
    return await fetch_quote(ticker.upper())


@router.get("/{ticker}/history")
async def get_history(
    ticker: str,
    outputsize: str = "compact",
    _: User = Depends(get_current_user),
):
    return await fetch_daily_series(ticker.upper(), outputsize)


@router.get("/portfolio/{portfolio_id}/value")
async def get_portfolio_value(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_ownership(portfolio_id, db, current_user)
    transactions = db.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).all()
    holdings = compute_holdings(transactions)

    if not holdings:
        return {"total_value": 0, "holdings": {}}

    # compute average cost per ticker
    cost_basis: dict[str, float] = {}
    qty_basis: dict[str, float] = {}
    for tx in transactions:
        if tx.transaction_type == TransactionType.BUY:
            cost_basis[tx.ticker] = cost_basis.get(tx.ticker, 0) + tx.quantity * tx.price_per_share
            qty_basis[tx.ticker] = qty_basis.get(tx.ticker, 0) + tx.quantity

    result = {}
    total_value = 0.0

    for ticker, qty in holdings.items():
        quote = await fetch_quote(ticker)
        current_price = quote["price"]
        current_value = current_price * qty
        avg_cost = cost_basis.get(ticker, 0) / qty_basis.get(ticker, 1)
        unrealized_pnl = (current_price - avg_cost) * qty

        result[ticker] = {
            "quantity": qty,
            "current_price": current_price,
            "current_value": round(current_value, 2),
            "avg_cost": round(avg_cost, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
        }
        total_value += current_value

    return {"total_value": round(total_value, 2), "holdings": result}
