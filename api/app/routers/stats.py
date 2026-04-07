from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, Transaction, User
from app.schemas import StatsByCategoryOut, StatsCategoryRow, StatsSummaryOut
from app.security import get_current_user


router = APIRouter(prefix="/stats", tags=["stats"])


def _day_bounds(start: dt.date, end: dt.date) -> tuple[dt.datetime, dt.datetime]:
  start_dt = dt.datetime.combine(start, dt.time.min, tzinfo=dt.UTC)
  end_dt = dt.datetime.combine(end, dt.time.max, tzinfo=dt.UTC)
  return start_dt, end_dt


@router.get("/summary", response_model=StatsSummaryOut)
def summary(
  start: dt.date,
  end: dt.date,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> StatsSummaryOut:
  start_dt, end_dt = _day_bounds(start, end)
  base = and_(
    Transaction.user_id == user.id,
    Transaction.deleted_at.is_(None),
    Transaction.occurred_at >= start_dt,
    Transaction.occurred_at <= end_dt,
  )

  income = db.scalar(
    select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(base, Transaction.direction == "income")
  )
  expense = db.scalar(
    select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(base, Transaction.direction == "expense")
  )
  count = db.scalar(select(func.count()).select_from(Transaction).where(base))
  income_i = int(income or 0)
  expense_i = int(expense or 0)
  return StatsSummaryOut(
    start=start,
    end=end,
    income_cents=income_i,
    expense_cents=expense_i,
    net_cents=income_i - expense_i,
    transactions_count=int(count or 0),
  )


@router.get("/by-category", response_model=StatsByCategoryOut)
def by_category(
  start: dt.date,
  end: dt.date,
  direction: str = "expense",
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> StatsByCategoryOut:
  start_dt, end_dt = _day_bounds(start, end)

  rows = db.execute(
    select(
      Transaction.category_id,
      func.coalesce(Category.name, "未分类").label("category_name"),
      func.coalesce(func.sum(Transaction.amount_cents), 0).label("total_cents"),
    )
    .select_from(Transaction)
    .outerjoin(Category, and_(Transaction.category_id == Category.id, Category.user_id == user.id))
    .where(
      Transaction.user_id == user.id,
      Transaction.deleted_at.is_(None),
      Transaction.direction == direction,
      Transaction.occurred_at >= start_dt,
      Transaction.occurred_at <= end_dt,
    )
    .group_by(Transaction.category_id, Category.name)
    .order_by(func.sum(Transaction.amount_cents).desc())
  ).all()

  out_rows = [
    StatsCategoryRow(category_id=r[0], category_name=str(r[1]), total_cents=int(r[2] or 0))
    for r in rows
  ]

  return StatsByCategoryOut(start=start, end=end, direction=direction, rows=out_rows)

