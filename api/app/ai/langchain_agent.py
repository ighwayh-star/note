from __future__ import annotations

import datetime as dt
import importlib
import json
import re
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.ai.actions import create_pending_action
from app.ai.schemas import (
  AIChatOut,
  AIProposedAction,
  AIResponseCard,
  AIStatsByCategoryCard,
  AIStatsByCategoryRow,
  AIStatsSummaryCard,
  AITransactionsCard,
  AITransactionListItem,
)
from app.ai.tools import search_transactions, stats_by_category, stats_summary
from app.core.config import settings
from app.models import User


def _require(pkg: str) -> None:
  try:
    importlib.import_module(pkg)
  except Exception as e:
    raise RuntimeError(f"Missing dependency: {pkg}") from e


def _parse_date(s: str) -> dt.date:
  return dt.date.fromisoformat(s)


def _infer_date_range_from_message(message: str) -> tuple[dt.date, dt.date]:
  today = dt.date.today()

  m = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})", message)
  if m:
    return dt.date.fromisoformat(m.group(1)), dt.date.fromisoformat(m.group(2))

  if any(k in message for k in ["今年", "本年"]):
    return dt.date(today.year, 1, 1), today

  if any(k in message for k in ["本月", "这个月"]):
    return dt.date(today.year, today.month, 1), today

  if any(k in message for k in ["本周", "这周"]):
    start = today - dt.timedelta(days=today.weekday())
    return start, today

  m1 = re.findall(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", message)
  if len(m1) >= 2:
    s = m1[0]
    e = m1[1]
    return dt.date(int(s[0]), int(s[1]), int(s[2])), dt.date(int(e[0]), int(e[1]), int(e[2]))

  if len(m1) == 1 and any(k in message for k in ["到今天", "至今", "到现在", "到今日", "截止今天", "截止目前"]):
    s = m1[0]
    return dt.date(int(s[0]), int(s[1]), int(s[2])), today

  return today - dt.timedelta(days=30), today


def _parse_card(card: dict[str, Any]) -> AIResponseCard | None:
  card_type = card.get("type")
  if card_type == "stats_summary":
    return AIStatsSummaryCard.model_validate(card)
  if card_type == "stats_by_category":
    return AIStatsByCategoryCard.model_validate(card)
  if card_type == "transactions":
    return AITransactionsCard.model_validate(card)
  return None


def run_langchain_chat(
  *,
  message: str,
  user: User,
  db: Session,
  history: list[dict[str, str]] | None = None,
  conversation_id: str = "",
) -> AIChatOut:
  mode = (settings.ai_mode or "openai").lower()
  api_key: str | None
  model: str
  base_url: str | None = None
  if mode == "deepseek":
    api_key = settings.deepseek_api_key
    model = settings.deepseek_model
    base_url = settings.deepseek_base_url
    if not api_key:
      raise RuntimeError("DEEPSEEK_API_KEY is required when ai_mode=deepseek")
  else:
    api_key = settings.openai_api_key
    model = settings.openai_model
    if not api_key:
      raise RuntimeError("OPENAI_API_KEY is required when ai_mode=openai")

  _require("langchain_openai")
  _require("langchain_core")

  messages_mod = importlib.import_module("langchain_core.messages")
  tools_mod = importlib.import_module("langchain_core.tools")
  openai_mod = importlib.import_module("langchain_openai")
  HumanMessage = getattr(messages_mod, "HumanMessage")
  AIMessage = getattr(messages_mod, "AIMessage")
  SystemMessage = getattr(messages_mod, "SystemMessage")
  ToolMessage = getattr(messages_mod, "ToolMessage")
  tool = getattr(tools_mod, "tool")
  ChatOpenAI = getattr(openai_mod, "ChatOpenAI")

  collected_cards: list[AIResponseCard] = []
  collected_actions: list[AIProposedAction] = []

  @tool
  def get_stats_summary(start: str | None = None, end: str | None = None) -> dict[str, Any]:
    """Get income/expense summary within [start, end] (YYYY-MM-DD)."""
    if start and end:
      start_d, end_d = _parse_date(start), _parse_date(end)
    else:
      start_d, end_d = _infer_date_range_from_message(message)
      start = start or start_d.isoformat()
      end = end or end_d.isoformat()
    s = stats_summary(db=db, user=user, start=start_d, end=end_d)
    card = AIStatsSummaryCard(
      start=start,
      end=end,
      income_cents=s["income_cents"],
      expense_cents=s["expense_cents"],
      net_cents=s["net_cents"],
      transactions_count=s["transactions_count"],
    )
    return {"card": card.model_dump()}

  @tool
  def get_stats_by_category(start: str | None = None, end: str | None = None, direction: str = "expense") -> dict[str, Any]:
    """Get totals grouped by category within [start, end] (YYYY-MM-DD)."""
    if start and end:
      start_d, end_d = _parse_date(start), _parse_date(end)
    else:
      start_d, end_d = _infer_date_range_from_message(message)
      start = start or start_d.isoformat()
      end = end or end_d.isoformat()
    direction_value: Literal["income", "expense"] = "income" if direction == "income" else "expense"
    raw_rows = stats_by_category(
      db=db,
      user=user,
      start=start_d,
      end=end_d,
      direction=direction_value,
    )
    rows = [
      AIStatsByCategoryRow(
        category_id=r["category_id"],
        category_name=r["category_name"],
        total_cents=r["total_cents"],
      )
      for r in raw_rows
    ]
    card = AIStatsByCategoryCard(start=start, end=end, direction=direction_value, rows=rows)
    return {"card": card.model_dump()}

  @tool
  def list_transactions(start: str | None = None, end: str | None = None, search: str | None = None, limit: int = 20) -> dict[str, Any]:
    """List transactions within [start, end] (YYYY-MM-DD), optionally filtered by keyword."""
    if start and end:
      start_d, end_d = _parse_date(start), _parse_date(end)
    else:
      start_d, end_d = _infer_date_range_from_message(message)
      start = start or start_d.isoformat()
      end = end or end_d.isoformat()
    items, total = search_transactions(db=db, user=user, start=start_d, end=end_d, search=search, limit=limit, offset=0)
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
    return {"card": card.model_dump()}

  @tool
  def propose_transaction_create(
    direction: str,
    amount: float,
    occurred_at: str | None = None,
    currency: str = "CNY",
    merchant: str | None = None,
    note: str | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
  ) -> dict[str, Any]:
    """Propose creating a transaction (requires user confirmation before execution)."""
    direction_value: Literal["income", "expense"] = "income" if direction == "income" else "expense"
    occurred_at_provided = occurred_at is not None
    merchant_provided = merchant is not None
    when = occurred_at or dt.datetime.now(dt.UTC).isoformat()
    action = create_pending_action(
      db=db,
      user=user,
      kind="transaction_create",
      payload={
        "direction": direction_value,
        "amount_cents": int(round(abs(amount) * 100)),
        "currency": currency,
        "occurred_at": when,
        "merchant": merchant,
        "note": note,
        "account_id": account_id,
        "category_id": category_id,
        "_meta": {
          "occurred_at_provided": occurred_at_provided,
          "merchant_provided": merchant_provided,
        },
      },
    )
    pa = AIProposedAction(
      id=action.id,
      kind=action.kind,
      payload={
        "summary": f"新增{ '收入' if direction_value == 'income' else '支出' } {abs(amount):.2f} {currency}",
        "fields": {
          "direction": direction_value,
          "amount_cents": int(round(abs(amount) * 100)),
          "currency": currency,
          "occurred_at": when if occurred_at_provided else None,
          "merchant": merchant if merchant_provided else None,
          "note": note,
        },
      },
    )
    collected_actions.append(pa)
    return {"proposed_action": pa.model_dump()}

  @tool
  def propose_transaction_update(
    transaction_id: int,
    amount: float | None = None,
    occurred_at: str | None = None,
    merchant: str | None = None,
    note: str | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
  ) -> dict[str, Any]:
    """Propose updating a transaction by id (requires user confirmation before execution)."""
    patch: dict[str, Any] = {}
    if amount is not None:
      patch["amount_cents"] = int(round(abs(amount) * 100))
    if occurred_at is not None:
      patch["occurred_at"] = occurred_at
    if merchant is not None:
      patch["merchant"] = merchant
    if note is not None:
      patch["note"] = note
    if account_id is not None:
      patch["account_id"] = account_id
    if category_id is not None:
      patch["category_id"] = category_id
    action = create_pending_action(
      db=db,
      user=user,
      kind="transaction_update",
      payload={"transaction_id": transaction_id, "patch": patch},
    )
    pa = AIProposedAction(
      id=action.id,
      kind=action.kind,
      payload={"summary": f"修改流水 #{transaction_id}（待确认）"},
    )
    collected_actions.append(pa)
    return {"proposed_action": pa.model_dump()}

  @tool
  def propose_transaction_delete(transaction_id: int) -> dict[str, Any]:
    """Propose deleting a transaction by id (requires user confirmation before execution)."""
    action = create_pending_action(
      db=db,
      user=user,
      kind="transaction_delete",
      payload={"transaction_id": transaction_id},
    )
    pa = AIProposedAction(
      id=action.id,
      kind=action.kind,
      payload={"summary": f"删除流水 #{transaction_id}（待确认）"},
    )
    collected_actions.append(pa)
    return {"proposed_action": pa.model_dump()}

  @tool
  def propose_category_create(name: str, type: str = "expense") -> dict[str, Any]:
    """Propose creating a category (requires user confirmation before execution)."""
    type_value: Literal["income", "expense"] = "income" if type == "income" else "expense"
    action = create_pending_action(
      db=db,
      user=user,
      kind="category_create",
      payload={"name": name, "type": type_value},
    )
    pa = AIProposedAction(
      id=action.id,
      kind=action.kind,
      payload={
        "summary": f"新增分类：{name}（{ '支出' if type_value == 'expense' else '收入' }）",
        "fields": {"name": name, "type": type_value},
      },
    )
    collected_actions.append(pa)
    return {"proposed_action": pa.model_dump()}

  @tool
  def propose_category_create_and_assign(name: str, transaction_id: int, type: str = "expense") -> dict[str, Any]:
    """Propose creating a category and assigning a transaction to it (requires user confirmation before execution)."""
    type_value: Literal["income", "expense"] = "income" if type == "income" else "expense"
    action = create_pending_action(
      db=db,
      user=user,
      kind="category_create_and_assign",
      payload={"name": name, "type": type_value, "transaction_id": transaction_id},
    )
    pa = AIProposedAction(
      id=action.id,
      kind=action.kind,
      payload={
        "summary": f"新增分类：{name}（{ '支出' if type_value == 'expense' else '收入' }）并归类流水 #{transaction_id}",
        "fields": {"name": name, "type": type_value, "transaction_id": transaction_id},
      },
    )
    collected_actions.append(pa)
    return {"proposed_action": pa.model_dump()}

  system = SystemMessage(
    content=(
      "你是一个记账应用的助手。"
      "你只能通过工具访问数据。"
      "当用户要求新增/修改/删除流水时，你必须调用 propose_transaction_* 工具生成待确认操作，并提示用户确认执行。"
      "当用户要求新增/创建分类时，你必须调用 propose_category_create 工具生成待确认操作。"
      "当用户要求新增分类并把某笔流水归到该分类时，你必须调用 propose_category_create_and_assign。"
      f"今天是 {dt.date.today().isoformat()}。如果用户说“今年/本月/本周/到今天为止/至今”，请你自行换算为日期范围，不要反复追问。"
      "当用户给出一个起始日期并说“到今天为止/至今”，默认结束日期为今天。"
      "当你调用工具后，根据工具结果用简洁中文回答。"
    )
  )

  try:
    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0)
  except TypeError:
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0)
  llm_with_tools = llm.bind_tools(
    [
      get_stats_summary,
      get_stats_by_category,
      list_transactions,
      propose_transaction_create,
      propose_transaction_update,
      propose_transaction_delete,
      propose_category_create,
      propose_category_create_and_assign,
    ]
  )

  messages: list[Any] = [system]
  for h in history or []:
    role = (h.get("role") or "").lower()
    content = h.get("content") or ""
    if not content:
      continue
    if role == "assistant":
      messages.append(AIMessage(content=content))
    elif role == "user":
      messages.append(HumanMessage(content=content))
  messages.append(HumanMessage(content=message))

  def _tool_call_parts(tc: Any) -> tuple[str | None, dict[str, Any], str | None]:
    name: str | None = None
    args: Any = None
    call_id: str | None = None

    if isinstance(tc, dict):
      call_id = tc.get("id") or tc.get("tool_call_id")
      fn = tc.get("function")
      if isinstance(fn, dict):
        name = fn.get("name")
        args = fn.get("arguments") or fn.get("args")
      else:
        name = tc.get("name")
        args = tc.get("args") or tc.get("arguments")
    else:
      call_id = getattr(tc, "id", None) or getattr(tc, "tool_call_id", None)
      name = getattr(tc, "name", None)
      args = getattr(tc, "args", None) or getattr(tc, "arguments", None)
      fn = getattr(tc, "function", None)
      if isinstance(fn, dict):
        name = fn.get("name") or name
        args = fn.get("arguments") or fn.get("args") or args
      else:
        fn_name = getattr(fn, "name", None)
        fn_args = getattr(fn, "arguments", None)
        name = fn_name or name
        args = fn_args or args

    if isinstance(args, str):
      try:
        args = json.loads(args)
      except Exception:
        args = {}
    if not isinstance(args, dict):
      args = {}
    return name, args, call_id

  for _ in range(3):
    ai_msg = llm_with_tools.invoke(messages)
    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    if not tool_calls:
      return AIChatOut(reply=str(getattr(ai_msg, "content", "")) or "完成", cards=collected_cards, proposed_actions=collected_actions, mode=mode)

    messages.append(ai_msg)
    for tc in tool_calls:
      name, args, call_id = _tool_call_parts(tc)
      if not name:
        continue

      if name == "get_stats_summary":
        out = get_stats_summary.invoke(args)
      elif name == "get_stats_by_category":
        out = get_stats_by_category.invoke(args)
      elif name == "list_transactions":
        out = list_transactions.invoke(args)
      elif name == "propose_transaction_create":
        out = propose_transaction_create.invoke(args)
      elif name == "propose_transaction_update":
        out = propose_transaction_update.invoke(args)
      elif name == "propose_transaction_delete":
        out = propose_transaction_delete.invoke(args)
      elif name == "propose_category_create":
        out = propose_category_create.invoke(args)
      elif name == "propose_category_create_and_assign":
        out = propose_category_create_and_assign.invoke(args)
      else:
        out = {"error": "unknown tool"}

      card = out.get("card") if isinstance(out, dict) else None
      if isinstance(card, dict):
        parsed_card = _parse_card(card)
        if parsed_card:
          collected_cards.append(parsed_card)
      proposed = out.get("proposed_action") if isinstance(out, dict) else None
      if isinstance(proposed, dict) and proposed.get("id") and proposed.get("kind"):
        try:
          collected_actions.append(AIProposedAction.model_validate(proposed))
        except Exception:
          pass
      messages.append(ToolMessage(content=json.dumps(out, ensure_ascii=False), tool_call_id=str(call_id or name)))

  return AIChatOut(
    reply="未能完成工具调用。请换个说法，或补充关键信息（如交易ID、分类名、金额、时间范围）。",
    cards=collected_cards,
    proposed_actions=collected_actions,
    mode=mode,
  )
