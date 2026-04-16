from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioOut
from app.core.security import get_current_user

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_owned_portfolio(portfolio_id: int, db: Session, user: User) -> Portfolio:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return portfolio


@router.post("/", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = Portfolio(**payload.model_dump(), owner_id=current_user.id)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.get("/", response_model=List[PortfolioOut])
def list_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Portfolio).filter(Portfolio.owner_id == current_user.id).all()


@router.get("/{portfolio_id}", response_model=PortfolioOut)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_owned_portfolio(portfolio_id, db, current_user)


@router.patch("/{portfolio_id}", response_model=PortfolioOut)
def update_portfolio(
    portfolio_id: int,
    payload: PortfolioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = get_owned_portfolio(portfolio_id, db, current_user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(portfolio, field, value)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = get_owned_portfolio(portfolio_id, db, current_user)
    db.delete(portfolio)
    db.commit()
