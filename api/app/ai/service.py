from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.actions import cancel_action, confirm_action, create_pending_action
from app.ai.langchain_agent import run_langchain_chat
from app.ai.memory import append_message, get_or_create_conversation, get_recent_messages, get_state, set_state
from app.ai.nlp import (
  infer_direction,
  parse_amount_cents,
  parse_category_id,
  parse_category_name,
  parse_category_target_name,
  parse_merchant,
  parse_occurred_at,
  parse_transaction_keyword,
  parse_transaction_id,
  infer_category_type,
)
from app.ai.rule_agent import run_rule_chat
from app.ai.schemas import AIChatOut, AIProposedAction, AITransactionListItem, AITransactionsCard
from app.core.config import settings
from app.ai.tools import search_transactions
from app.models import Category, User


def _merge_draft(draft: dict, patch: dict) -> dict:
  out = dict(draft or {})
  for k, v in patch.items():
    if v is None:
      continue
    out[k] = v
  return out


def _build_action_from_draft(*, db: Session, user: User, draft: dict, note: str, mode: str) -> AIChatOut | None:
  if not draft.get("amount_cents") or not draft.get("direction"):
    return None
  occurred_at_iso = str(draft.get("occurred_at_iso") or dt.datetime.now(dt.UTC).isoformat())
  action = create_pending_action(
    db=db,
    user=user,
    kind="transaction_create",
    payload={
      "direction": draft["direction"],
      "amount_cents": int(draft["amount_cents"]),
      "currency": str(draft.get("currency") or "CNY"),
      "occurred_at": occurred_at_iso,
      "merchant": draft.get("merchant"),
      "note": note,
      "account_id": None,
      "category_id": None,
      "_meta": {
        "occurred_at_provided": bool(draft.get("occurred_at_provided")),
        "merchant_provided": bool(draft.get("merchant_provided")),
      },
    },
  )
  pa = AIProposedAction(
    id=action.id,
    kind=action.kind,
    payload={
      "summary": f"新增{ '收入' if draft['direction'] == 'income' else '支出' } {int(draft['amount_cents']) / 100:.2f}",
      "fields": {
        "direction": draft["direction"],
        "amount_cents": int(draft["amount_cents"]),
        "currency": str(draft.get("currency") or "CNY"),
        "occurred_at": occurred_at_iso if bool(draft.get("occurred_at_provided")) else None,
        "merchant": draft.get("merchant") if bool(draft.get("merchant_provided")) else None,
        "note": None,
      },
    },
  )
  return AIChatOut(reply="我已生成一条待执行的记账操作，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=draft["conversation_id"])


def _find_category_id_by_name(*, db: Session, user: User, name: str) -> int | None:
  name = name.strip()
  if not name:
    return None
  cat = db.scalar(select(Category).where(Category.user_id == user.id, Category.name == name))
  if cat:
    return cat.id
  like = f"%{name}%"
  rows = list(db.scalars(select(Category).where(Category.user_id == user.id, Category.name.like(like)).order_by(Category.id.desc()).limit(2)))
  if len(rows) == 1:
    return rows[0].id
  return None


def _default_search_range(message: str) -> tuple[dt.date, dt.date]:
  occurred_at, provided = parse_occurred_at(message)
  if provided:
    d = occurred_at.date()
    return d, d
  today = dt.date.today()
  return today - dt.timedelta(days=30), today


def _sync_last_action_state(*, db: Session, user: User, conversation_id: str, state: dict, out: AIChatOut) -> None:
  base = get_state(db=db, user=user, conversation_id=conversation_id)
  next_state = dict(base or state or {})
  if out.proposed_actions:
    next_state["last_action_id"] = out.proposed_actions[-1].id
  set_state(db=db, user=user, conversation_id=conversation_id, state=next_state)


def run_chat(*, message: str, user: User, db: Session, conversation_id: str | None) -> AIChatOut:
  mode = (settings.ai_mode or "rule").lower()
  normalized = re.sub(r"\s+", "", message)
  conv = get_or_create_conversation(db=db, user=user, conversation_id=conversation_id)
  append_message(db=db, user=user, conversation_id=conv.id, role="user", content=message)
  state = get_state(db=db, user=user, conversation_id=conv.id)
  draft = state.get("draft") if isinstance(state.get("draft"), dict) else {}
  if isinstance(draft, dict):
    draft = dict(draft)
  else:
    draft = {}
  draft["conversation_id"] = conv.id

  last_action_id = state.get("last_action_id") if isinstance(state, dict) else None
  if isinstance(last_action_id, str) and last_action_id:
    if normalized in ["确认", "确定", "执行", "是", "好", "可以", "ok"]:
      try:
        audit_id, entity_id = confirm_action(db=db, user=user, action_id=last_action_id)
        next_state = dict(state or {})
        next_state["last_action_id"] = None
        set_state(db=db, user=user, conversation_id=conv.id, state=next_state)
        reply = f"已为你执行上一条提案（audit_id={audit_id}{f', entity_id={entity_id}' if entity_id else ''}）。"
        out = AIChatOut(reply=reply, cards=[], proposed_actions=[], mode=mode, conversation_id=conv.id)
        append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
        return out
      except ValueError as e:
        out = AIChatOut(reply=f"上一条提案无法执行：{str(e)}。你可以让我重新生成一条。", cards=[], proposed_actions=[], mode=mode, conversation_id=conv.id)
        append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
        return out
    if normalized in ["取消", "算了", "不用了", "先不要"]:
      ok = cancel_action(db=db, user=user, action_id=last_action_id)
      next_state = dict(state or {})
      next_state["last_action_id"] = None
      set_state(db=db, user=user, conversation_id=conv.id, state=next_state)
      reply = "已取消上一条提案。" if ok else "上一条提案已失效或已处理。"
      out = AIChatOut(reply=reply, cards=[], proposed_actions=[], mode=mode, conversation_id=conv.id)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

  llm_fallback: AIChatOut | None = None
  if mode in ["openai", "deepseek", "langchain", "llm"]:
    history = get_recent_messages(db=db, user=user, conversation_id=conv.id, limit=12)
    out = run_langchain_chat(message=message, user=user, db=db, history=history, conversation_id=conv.id)
    out.conversation_id = conv.id
    if out.reply and out.reply.startswith("未能完成工具调用") and not out.cards and not out.proposed_actions:
      llm_fallback = out
    else:
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

  amount_cents = parse_amount_cents(normalized)
  if amount_cents is not None and any(k in normalized for k in ["花", "消费", "收入", "入账"]):
    direction = infer_direction(message)
    occurred_at_dt, occurred_at_provided = parse_occurred_at(message)
    merchant, merchant_provided = parse_merchant(message)
    draft = _merge_draft(
      draft,
      {
        "direction": direction,
        "amount_cents": amount_cents,
        "currency": "CNY",
        "occurred_at_iso": occurred_at_dt.isoformat(),
        "occurred_at_provided": occurred_at_provided,
        "merchant": merchant,
        "merchant_provided": merchant_provided,
      },
    )
    out = _build_action_from_draft(db=db, user=user, draft=draft, note=message, mode=mode)
    set_state(db=db, user=user, conversation_id=conv.id, state={"draft": {}})
    if out:
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

  if any(k in normalized for k in ["新增", "记一笔", "记账", "添加"]):
    if amount_cents is not None:
      direction = infer_direction(message)
      occurred_at_dt, occurred_at_provided = parse_occurred_at(message)
      merchant, merchant_provided = parse_merchant(message)
      draft = _merge_draft(
        draft,
        {
          "direction": direction,
          "amount_cents": amount_cents,
          "currency": "CNY",
          "occurred_at_iso": occurred_at_dt.isoformat(),
          "occurred_at_provided": occurred_at_provided,
          "merchant": merchant,
          "merchant_provided": merchant_provided,
        },
      )
    out = _build_action_from_draft(db=db, user=user, draft=draft, note=message, mode=mode)
    if out:
      set_state(db=db, user=user, conversation_id=conv.id, state={"draft": {}})
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out
    set_state(db=db, user=user, conversation_id=conv.id, state={"draft": draft})

  if any(k in normalized for k in ["修改", "更新", "调整", "变更"]):
    tx_id = parse_transaction_id(normalized)
    patch: dict[str, object] = {}
    cat_id = parse_category_id(normalized)
    if cat_id is not None:
      patch["category_id"] = cat_id
    amt = parse_amount_cents(normalized)
    if amt is not None:
      patch["amount_cents"] = amt
    occurred_at_dt, occurred_at_provided = parse_occurred_at(message)
    if occurred_at_provided:
      patch["occurred_at"] = occurred_at_dt.isoformat()
    merchant, merchant_provided = parse_merchant(message)
    if merchant_provided and merchant is not None:
      patch["merchant"] = merchant
    if tx_id is not None and patch:
      action = create_pending_action(
        db=db,
        user=user,
        kind="transaction_update",
        payload={"transaction_id": tx_id, "patch": patch},
      )
      pa = AIProposedAction(
        id=action.id,
        kind=action.kind,
        payload={
          "summary": f"修改流水 #{tx_id}",
          "fields": patch,
        },
      )
      out = AIChatOut(reply="我已生成一条修改提案，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=conv.id)
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

  if re.search(r"(新增|添加|创建|新建|建立).*(分类|类别)", normalized):
    name = parse_category_name(normalized)
    if name:
      cat_type = infer_category_type(message)
      tx_id = parse_transaction_id(normalized)
      if tx_id is None:
        keyword = parse_transaction_keyword(normalized)
        amount_cents = parse_amount_cents(normalized)
        start, end = _default_search_range(message)
        items, _total = search_transactions(db=db, user=user, search=keyword, start=start, end=end, limit=10, offset=0)
        if amount_cents is not None:
          items = [i for i in items if i.amount_cents == amount_cents]
        if len(items) == 1:
          tx_id = items[0].id
      if tx_id is not None and any(k in normalized for k in ["然后", "并", "同时", "再", "归类", "归到", "放到", "归入", "加进去", "加入"]):
        action = create_pending_action(
          db=db,
          user=user,
          kind="category_create_and_assign",
          payload={"name": name, "type": cat_type, "transaction_id": tx_id},
        )
        pa = AIProposedAction(
          id=action.id,
          kind=action.kind,
          payload={
            "summary": f"新增分类：{name}（{ '支出' if cat_type == 'expense' else '收入' }）并归类流水 #{tx_id}",
            "fields": {"name": name, "type": cat_type, "transaction_id": tx_id},
          },
        )
        out = AIChatOut(reply="我已生成一条新增分类并归类流水的提案，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=conv.id)
        _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
        append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
        return out

  if any(k in normalized for k in ["归类", "归到", "放到", "分类到", "归入", "设为", "改成"]):
    tx_id = parse_transaction_id(normalized)
    cat_id = parse_category_id(normalized)
    cat_name = parse_category_target_name(normalized) or parse_category_name(normalized)
    if cat_id is None and cat_name:
      cat_id = _find_category_id_by_name(db=db, user=user, name=cat_name)
    if cat_id is None:
      out = AIChatOut(
        reply="我没能识别到目标分类。你可以说“归类到 餐饮”，或直接给分类ID，例如：分类ID 2。",
        cards=[],
        proposed_actions=[],
        mode=mode,
        conversation_id=conv.id,
      )
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

    patch = {"category_id": cat_id}
    if tx_id is not None:
      action = create_pending_action(
        db=db,
        user=user,
        kind="transaction_update",
        payload={"transaction_id": tx_id, "patch": patch},
      )
      pa = AIProposedAction(
        id=action.id,
        kind=action.kind,
        payload={"summary": f"修改流水 #{tx_id}：设置分类为 {cat_id}", "fields": patch},
      )
      out = AIChatOut(reply="我已生成一条修改提案，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=conv.id)
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

    keyword = parse_transaction_keyword(normalized)
    amount_cents = parse_amount_cents(normalized)
    start, end = _default_search_range(message)
    items, _total = search_transactions(db=db, user=user, search=keyword, start=start, end=end, limit=10, offset=0)
    if amount_cents is not None:
      items = [i for i in items if i.amount_cents == amount_cents]
    if len(items) == 1:
      tx = items[0]
      action = create_pending_action(
        db=db,
        user=user,
        kind="transaction_update",
        payload={"transaction_id": tx.id, "patch": patch},
      )
      pa = AIProposedAction(
        id=action.id,
        kind=action.kind,
        payload={"summary": f"修改流水 #{tx.id}：设置分类为 {cat_id}", "fields": patch},
      )
      out = AIChatOut(reply="我已生成一条修改提案，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=conv.id)
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

    if len(items) == 0:
      out = AIChatOut(
        reply="我没找到你说的那笔流水。请告诉我交易ID（例如：交易ID 2），或者提供更明确的关键词（如商户名或金额）。",
        cards=[],
        proposed_actions=[],
        mode=mode,
        conversation_id=conv.id,
      )
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

    card = AITransactionsCard(
      total=len(items),
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
        for i in items[:5]
      ],
    )
    out = AIChatOut(
      reply="我找到了多笔可能匹配的流水。请回复“交易ID X 归类到 Y”（或直接点列表里记下ID再发我）。",
      cards=[card],
      proposed_actions=[],
      mode=mode,
      conversation_id=conv.id,
    )
    append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
    return out

  if any(
    k in normalized
    for k in [
      "新增分类",
      "添加分类",
      "创建分类",
      "新建分类",
      "建立分类",
      "新增类别",
      "添加类别",
      "创建类别",
      "新建类别",
      "建立类别",
    ]
  ):
    name = parse_category_name(normalized)
    if name:
      cat_type = infer_category_type(message)
      action = create_pending_action(
        db=db,
        user=user,
        kind="category_create",
        payload={"name": name, "type": cat_type},
      )
      pa = AIProposedAction(
        id=action.id,
        kind=action.kind,
        payload={
          "summary": f"新增分类：{name}（{ '支出' if cat_type == 'expense' else '收入' }）",
          "fields": {"name": name, "type": cat_type},
        },
      )
      out = AIChatOut(reply="我已生成一条新增分类提案，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=conv.id)
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

  if re.search(r"(新增|添加|创建|新建|建立).*(分类|类别)", normalized):
    name = parse_category_name(normalized)
    if name:
      cat_type = infer_category_type(message)
      action = create_pending_action(
        db=db,
        user=user,
        kind="category_create",
        payload={"name": name, "type": cat_type},
      )
      pa = AIProposedAction(
        id=action.id,
        kind=action.kind,
        payload={
          "summary": f"新增分类：{name}（{ '支出' if cat_type == 'expense' else '收入' }）",
          "fields": {"name": name, "type": cat_type},
        },
      )
      out = AIChatOut(reply="我已生成一条新增分类提案，请点击确认执行。", cards=[], proposed_actions=[pa], mode=mode, conversation_id=conv.id)
      _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
      append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
      return out

  if mode in ["openai", "deepseek", "langchain", "llm"]:
    out = llm_fallback
    if out is None:
      history = get_recent_messages(db=db, user=user, conversation_id=conv.id, limit=12)
      out = run_langchain_chat(message=message, user=user, db=db, history=history, conversation_id=conv.id)
      out.conversation_id = conv.id
    _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
    append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
    return out

  out = run_rule_chat(message=message, user=user, db=db)
  out.conversation_id = conv.id
  _sync_last_action_state(db=db, user=user, conversation_id=conv.id, state=state, out=out)
  append_message(db=db, user=user, conversation_id=conv.id, role="assistant", content=out.reply)
  return out
