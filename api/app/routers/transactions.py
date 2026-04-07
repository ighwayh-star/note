from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db import get_db
from app.models import Account, Category, Transaction, User
from app.schemas import PaginatedTransactionsOut, TransactionCreateIn, TransactionOut, TransactionUpdateIn
from app.security import get_current_user


router = APIRouter(prefix="/transactions", tags=["transactions"])


def _day_bounds(start: dt.date, end: dt.date) -> tuple[dt.datetime, dt.datetime]:
  start_dt = dt.datetime.combine(start, dt.time.min, tzinfo=dt.UTC)
  end_dt = dt.datetime.combine(end, dt.time.max, tzinfo=dt.UTC)
  return start_dt, end_dt


@router.get("", response_model=PaginatedTransactionsOut)
def list_transactions(
  start: dt.date | None = None,
  end: dt.date | None = None,
  direction: str | None = None,
  account_id: int | None = None,
  category_id: int | None = None,
  search: str | None = None,
  limit: int = 50,
  offset: int = 0,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> PaginatedTransactionsOut:
  limit = min(max(limit, 1), 200)
  offset = max(offset, 0)

  filters: list[ColumnElement[bool]] = [Transaction.user_id == user.id]
  filters.append(Transaction.deleted_at.is_(None))
  if start and end:
    start_dt, end_dt = _day_bounds(start, end)
    filters.append(and_(Transaction.occurred_at >= start_dt, Transaction.occurred_at <= end_dt))
  if direction:
    filters.append(Transaction.direction == direction)
  if account_id is not None:
    filters.append(Transaction.account_id == account_id)
  if category_id is not None:
    filters.append(Transaction.category_id == category_id)
  if search:
    like = f"%{search.strip()}%"
    filters.append(or_(Transaction.merchant.like(like), Transaction.note.like(like)))

  base: Select[tuple[Transaction]] = (
    select(Transaction).where(*filters).order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
  )

  total = db.scalar(select(func.count()).select_from(base.subquery()))
  items = list(db.scalars(base.limit(limit).offset(offset)))
  return PaginatedTransactionsOut(items=[TransactionOut.model_validate(i) for i in items], total=int(total or 0))


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
  payload: TransactionCreateIn,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Transaction:
  if payload.account_id is not None:
    ok = db.scalar(select(func.count()).select_from(Account).where(Account.id == payload.account_id, Account.user_id == user.id))
    if int(ok or 0) != 1:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_id")
  if payload.category_id is not None:
    ok = db.scalar(select(func.count()).select_from(Category).where(Category.id == payload.category_id, Category.user_id == user.id))
    if int(ok or 0) != 1:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category_id")

  tx = Transaction(
    user_id=user.id,
    direction=payload.direction,
    amount_cents=payload.amount_cents,
    currency=payload.currency,
    occurred_at=payload.occurred_at,
    account_id=payload.account_id,
    category_id=payload.category_id,
    merchant=payload.merchant,
    note=payload.note,
  )
  db.add(tx)
  db.commit()
  db.refresh(tx)
  return tx


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
  transaction_id: int,
  payload: TransactionUpdateIn,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Transaction:
  tx = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id, Transaction.deleted_at.is_(None)))
  if not tx:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

  data = payload.model_dump(exclude_unset=True)
  if "account_id" in data and data["account_id"] is not None:
    ok = db.scalar(select(func.count()).select_from(Account).where(Account.id == data["account_id"], Account.user_id == user.id))
    if int(ok or 0) != 1:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_id")
  if "category_id" in data and data["category_id"] is not None:
    ok = db.scalar(select(func.count()).select_from(Category).where(Category.id == data["category_id"], Category.user_id == user.id))
    if int(ok or 0) != 1:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category_id")
  for k, v in data.items():
    setattr(tx, k, v)
  db.add(tx)
  db.commit()
  db.refresh(tx)
  return tx


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
  transaction_id: int,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Response:
  tx = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id, Transaction.deleted_at.is_(None)))
  if not tx:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
  tx.deleted_at = dt.datetime.now(dt.UTC)
  db.add(tx)
  db.commit()
  return Response(status_code=status.HTTP_204_NO_CONTENT)

