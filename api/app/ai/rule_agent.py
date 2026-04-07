from __future__ import annotations

import datetime as dt
import re
from typing import Literal

from sqlalchemy.orm import Session

from app.ai.actions import create_pending_action
from app.ai.schemas import (
  AIChatOut,
  AIProposedAction,
  AIStatsByCategoryCard,
  AIStatsByCategoryRow,
  AIStatsSummaryCard,
  AITransactionsCard,
  AITransactionListItem,
)
from app.ai.tools import search_transactions, stats_by_category, stats_summary
from app.models import User


_DATE_RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})")
_DATE_ANY_RE = re.compile(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})")
_AMOUNT_RE = re.compile(r"(-?\d+(?:\.\d{1,2})?)")


def _parse_date_range(message: str) -> tuple[dt.date, dt.date]:
  today = dt.date.today()

  m = _DATE_RANGE_RE.search(message)
  if m:
    start = dt.date.fromisoformat(m.group(1))
    end = dt.date.fromisoformat(m.group(2))
    return start, end

  if any(k in message for k in ["今年", "本年"]):
    return dt.date(today.year, 1, 1), today

  if any(k in message for k in ["本月", "这个月"]):
    return dt.date(today.year, today.month, 1), today

  if any(k in message for k in ["本周", "这周"]):
    start = today - dt.timedelta(days=today.weekday())
    return start, today

  dates = list(_DATE_ANY_RE.finditer(message))
  if len(dates) >= 2:
    s = dates[0]
    e = dates[1]
    return (
      dt.date(int(s.group(1)), int(s.group(2)), int(s.group(3))),
      dt.date(int(e.group(1)), int(e.group(2)), int(e.group(3))),
    )

  if len(dates) == 1 and any(k in message for k in ["到今天", "至今", "到现在", "到今日", "截止今天", "截止目前"]):
    s = dates[0]
    start = dt.date(int(s.group(1)), int(s.group(2)), int(s.group(3)))
    return start, today

  start = today - dt.timedelta(days=30)
  return start, today


def _infer_direction(message: str) -> Literal["income", "expense"]:
  if "收入" in message and "支出" not in message:
    return "income"
  return "expense"


def run_rule_chat(*, message: str, user: User, db: Session) -> AIChatOut:
  start, end = _parse_date_range(message)

  if any(k in message for k in ["新增", "记一笔", "记账", "添加"]):
    m = _AMOUNT_RE.search(message)
    if not m:
      return AIChatOut(reply="请告诉我金额，例如：新增支出 12.5", cards=[], proposed_actions=[], mode="rule")
    amount = float(m.group(1))
    direction: Literal["income", "expense"] = "income" if "收入" in message else "expense"
    occurred_at = dt.datetime.now(dt.UTC).isoformat()
    action = create_pending_action(
      db=db,
      user=user,
      kind="transaction_create",
      payload={
        "direction": direction,
        "amount_cents": int(round(abs(amount) * 100)),
        "currency": "CNY",
        "occurred_at": occurred_at,
        "merchant": None,
        "note": message,
      },
    )
    pa = AIProposedAction(id=action.id, kind=action.kind, payload={"summary": f"新增{ '收入' if direction == 'income' else '支出' } {abs(amount):.2f}"})
    return AIChatOut(reply="我已生成一条待执行的记账操作，请点击确认执行。", cards=[], proposed_actions=[pa], mode="rule")

  if any(k in message for k in ["列出", "明细", "流水"]):
    search = None
    q = re.search(r"[\"“](.+?)[\"”]", message)
    if q:
      search = q.group(1).strip()

    items, total = search_transactions(db=db, user=user, search=search, start=start, end=end, limit=20, offset=0)
    card = AITransactionsCard(
      total=total,
      items=[
        AITransactionListItem(
          id=i.id,
          direction=i.direction,
          amount_cents=i.amount_cents,
          currency=i.currency,
          occurred_at=i.occurred_at.isoformat(),
          account_id=i.account_id,
          category_id=i.category_id,
          merchant=i.merchant,
          note=i.note,
        )
        for i in items
      ],
    )
    reply = f"已为你查询 {start.isoformat()} 到 {end.isoformat()} 的流水（最多返回 20 条）。"
    if search:
      reply = f"已为你查询 {start.isoformat()} 到 {end.isoformat()} 的流水（关键词：{search}，最多返回 20 条）。"
    return AIChatOut(reply=reply, cards=[card], proposed_actions=[], mode="rule")

  if "分类" in message:
    direction = _infer_direction(message)
    raw_rows = stats_by_category(db=db, user=user, start=start, end=end, direction=direction)
    rows = [
      AIStatsByCategoryRow(
        category_id=r["category_id"],
        category_name=r["category_name"],
        total_cents=r["total_cents"],
      )
      for r in raw_rows
    ]
    card = AIStatsByCategoryCard(
      start=start.isoformat(),
      end=end.isoformat(),
      direction=direction,
      rows=rows,
    )
    reply = f"已为你汇总 {start.isoformat()} 到 {end.isoformat()} 的按分类{ '支出' if direction == 'expense' else '收入' }。"
    return AIChatOut(reply=reply, cards=[card], proposed_actions=[], mode="rule")

  s = stats_summary(db=db, user=user, start=start, end=end)
  card = AIStatsSummaryCard(
    start=start.isoformat(),
    end=end.isoformat(),
    income_cents=s["income_cents"],
    expense_cents=s["expense_cents"],
    net_cents=s["net_cents"],
    transactions_count=s["transactions_count"],
  )
  reply = f"已为你汇总 {start.isoformat()} 到 {end.isoformat()} 的收支。"
  return AIChatOut(reply=reply, cards=[card], proposed_actions=[], mode="rule")
