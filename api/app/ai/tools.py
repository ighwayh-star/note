from __future__ import annotations

import datetime as dt
from typing import Literal, TypedDict

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Category, Transaction, User


class StatsSummaryData(TypedDict):
  income_cents: int
  expense_cents: int
  net_cents: int
  transactions_count: int


class StatsByCategoryDataRow(TypedDict):
  category_id: int | None
  category_name: str
  total_cents: int


def _day_bounds(start: dt.date, end: dt.date) -> tuple[dt.datetime, dt.datetime]:
  start_dt = dt.datetime.combine(start, dt.time.min, tzinfo=dt.UTC)
  end_dt = dt.datetime.combine(end, dt.time.max, tzinfo=dt.UTC)
  return start_dt, end_dt


def search_transactions(
  *,
  db: Session,
  user: User,
  search: str | None = None,
  start: dt.date | None = None,
  end: dt.date | None = None,
  direction: str | None = None,
  limit: int = 20,
  offset: int = 0,
) -> tuple[list[Transaction], int]:
  limit = min(max(limit, 1), 200)
  offset = max(offset, 0)

  filters = [Transaction.user_id == user.id, Transaction.deleted_at.is_(None)]
  if start and end:
    start_dt, end_dt = _day_bounds(start, end)
    filters.append(and_(Transaction.occurred_at >= start_dt, Transaction.occurred_at <= end_dt))
  if direction:
    filters.append(Transaction.direction == direction)
  if search:
    like = f"%{search.strip()}%"
    filters.append(or_(Transaction.merchant.like(like), Transaction.note.like(like)))

  base = select(Transaction).where(*filters).order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
  total = db.scalar(select(func.count()).select_from(base.subquery()))
  items = list(db.scalars(base.limit(limit).offset(offset)))
  return items, int(total or 0)


def stats_summary(*, db: Session, user: User, start: dt.date, end: dt.date) -> StatsSummaryData:
  start_dt, end_dt = _day_bounds(start, end)
  base = and_(Transaction.user_id == user.id, Transaction.occurred_at >= start_dt, Transaction.occurred_at <= end_dt)
  base = and_(base, Transaction.deleted_at.is_(None))

  income = db.scalar(select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(base, Transaction.direction == "income"))
  expense = db.scalar(select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(base, Transaction.direction == "expense"))
  count = db.scalar(select(func.count()).select_from(Transaction).where(base))

  income_i = int(income or 0)
  expense_i = int(expense or 0)
  return {
    "income_cents": income_i,
    "expense_cents": expense_i,
    "net_cents": income_i - expense_i,
    "transactions_count": int(count or 0),
  }


def stats_by_category(
  *,
  db: Session,
  user: User,
  start: dt.date,
  end: dt.date,
  direction: Literal["income", "expense"],
) -> list[StatsByCategoryDataRow]:
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

  return [
    {
      "category_id": r[0],
      "category_name": str(r[1]),
      "total_cents": int(r[2] or 0),
    }
    for r in rows
  ]
