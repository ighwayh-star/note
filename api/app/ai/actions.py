from __future__ import annotations

import datetime as dt
import json
import uuid
from typing import Any, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIPendingAction, AuditLog, Category, Transaction, User


def create_pending_action(*, db: Session, user: User, kind: str, payload: dict[str, Any]) -> AIPendingAction:
  action = AIPendingAction(
    id=uuid.uuid4().hex,
    user_id=user.id,
    kind=kind,
    payload_json=json.dumps(payload, ensure_ascii=False),
    status="pending",
  )
  db.add(action)
  db.commit()
  db.refresh(action)
  return action


def _get_pending(*, db: Session, user: User, action_id: str) -> AIPendingAction | None:
  return db.scalar(select(AIPendingAction).where(AIPendingAction.id == action_id, AIPendingAction.user_id == user.id))


def _tx_to_dict(tx: Transaction) -> dict[str, Any]:
  return {
    "id": tx.id,
    "user_id": tx.user_id,
    "direction": tx.direction,
    "amount_cents": tx.amount_cents,
    "currency": tx.currency,
    "occurred_at": tx.occurred_at.isoformat(),
    "account_id": tx.account_id,
    "category_id": tx.category_id,
    "merchant": tx.merchant,
    "note": tx.note,
    "deleted_at": tx.deleted_at.isoformat() if tx.deleted_at else None,
  }


def _cat_to_dict(cat: Category) -> dict[str, Any]:
  return {
    "id": cat.id,
    "user_id": cat.user_id,
    "name": cat.name,
    "type": cat.type,
  }


def confirm_action(*, db: Session, user: User, action_id: str) -> tuple[int, int | None]:
  action = _get_pending(db=db, user=user, action_id=action_id)
  if not action or action.status != "pending":
    raise ValueError("Invalid or expired action")

  payload = json.loads(action.payload_json)
  kind = action.kind

  audit_id: int | None = None
  entity_id: int | None = None

  if kind == "transaction_create":
    tx = Transaction(
      user_id=user.id,
      direction=payload["direction"],
      amount_cents=int(payload["amount_cents"]),
      currency=str(payload.get("currency") or "CNY"),
      occurred_at=dt.datetime.fromisoformat(payload["occurred_at"]),
      account_id=payload.get("account_id"),
      category_id=payload.get("category_id"),
      merchant=payload.get("merchant"),
      note=payload.get("note"),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    entity_id = tx.id
    log = AuditLog(
      user_id=user.id,
      actor="ai",
      action_kind="transaction_create",
      entity_type="transaction",
      entity_id=tx.id,
      before_json=None,
      after_json=json.dumps(_tx_to_dict(tx), ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    audit_id = log.id

  elif kind == "transaction_update":
    tx_id = int(payload["transaction_id"])
    tx = db.scalar(select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == user.id, Transaction.deleted_at.is_(None)))
    if not tx:
      action.status = "failed"
      db.add(action)
      db.commit()
      raise ValueError("Transaction not found")

    before = _tx_to_dict(tx)
    patch: dict[str, Any] = payload["patch"]
    for k, v in patch.items():
      if k == "occurred_at" and isinstance(v, str):
        setattr(tx, k, dt.datetime.fromisoformat(v))
      else:
        setattr(tx, k, v)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    entity_id = tx.id
    log = AuditLog(
      user_id=user.id,
      actor="ai",
      action_kind="transaction_update",
      entity_type="transaction",
      entity_id=tx.id,
      before_json=json.dumps(before, ensure_ascii=False),
      after_json=json.dumps(_tx_to_dict(tx), ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    audit_id = log.id

  elif kind == "transaction_delete":
    tx_id = int(payload["transaction_id"])
    tx = db.scalar(select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == user.id, Transaction.deleted_at.is_(None)))
    if not tx:
      action.status = "failed"
      db.add(action)
      db.commit()
      raise ValueError("Transaction not found")
    before = _tx_to_dict(tx)
    tx.deleted_at = dt.datetime.now(dt.UTC)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    entity_id = tx.id
    log = AuditLog(
      user_id=user.id,
      actor="ai",
      action_kind="transaction_delete",
      entity_type="transaction",
      entity_id=tx.id,
      before_json=json.dumps(before, ensure_ascii=False),
      after_json=json.dumps(_tx_to_dict(tx), ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    audit_id = log.id

  elif kind == "category_create":
    cat = Category(user_id=user.id, name=str(payload["name"]), type=str(payload["type"]))
    db.add(cat)
    try:
      db.commit()
    except IntegrityError:
      db.rollback()
      action.status = "failed"
      db.add(action)
      db.commit()
      raise ValueError("Category already exists")
    db.refresh(cat)
    entity_id = cat.id
    log = AuditLog(
      user_id=user.id,
      actor="ai",
      action_kind="category_create",
      entity_type="category",
      entity_id=cat.id,
      before_json=None,
      after_json=json.dumps(_cat_to_dict(cat), ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    audit_id = log.id

  elif kind == "category_create_and_assign":
    tx_id = int(payload["transaction_id"])
    tx = db.scalar(select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == user.id, Transaction.deleted_at.is_(None)))
    if not tx:
      action.status = "failed"
      db.add(action)
      db.commit()
      raise ValueError("Transaction not found")

    cat = Category(user_id=user.id, name=str(payload["name"]), type=str(payload["type"]))
    db.add(cat)
    try:
      db.commit()
    except IntegrityError:
      db.rollback()
      action.status = "failed"
      db.add(action)
      db.commit()
      raise ValueError("Category already exists")
    db.refresh(cat)

    cat_log = AuditLog(
      user_id=user.id,
      actor="ai",
      action_kind="category_create",
      entity_type="category",
      entity_id=cat.id,
      before_json=None,
      after_json=json.dumps(_cat_to_dict(cat), ensure_ascii=False),
    )
    db.add(cat_log)
    db.commit()
    db.refresh(cat_log)

    before = _tx_to_dict(tx)
    tx.category_id = cat.id
    db.add(tx)
    db.commit()
    db.refresh(tx)
    entity_id = cat.id
    tx_log = AuditLog(
      user_id=user.id,
      actor="ai",
      action_kind="transaction_update",
      entity_type="transaction",
      entity_id=tx.id,
      before_json=json.dumps(before, ensure_ascii=False),
      after_json=json.dumps(_tx_to_dict(tx), ensure_ascii=False),
    )
    db.add(tx_log)
    db.commit()
    db.refresh(tx_log)
    audit_id = tx_log.id

  action.status = "confirmed"
  db.add(action)
  db.commit()
  if audit_id is None:
    raise ValueError("Failed to execute action")
  return audit_id, entity_id


def cancel_action(*, db: Session, user: User, action_id: str) -> bool:
  action = _get_pending(db=db, user=user, action_id=action_id)
  if not action or action.status != "pending":
    return False
  action.status = "cancelled"
  db.add(action)
  db.commit()
  return True


def undo_last_ai_action(*, db: Session, user: User) -> bool:
  log = db.scalar(select(AuditLog).where(AuditLog.user_id == user.id, AuditLog.actor == "ai").order_by(AuditLog.id.desc()))
  if not log or not log.entity_id:
    return False

  if log.entity_type == "category":
    cat = db.scalar(select(Category).where(Category.id == log.entity_id, Category.user_id == user.id))
    if not cat:
      return False
    db.delete(cat)
    db.commit()
    return True

  tx = db.scalar(select(Transaction).where(Transaction.id == log.entity_id, Transaction.user_id == user.id))
  if not tx:
    return False

  if log.action_kind == "transaction_create":
    tx.deleted_at = dt.datetime.now(dt.UTC)
    db.add(tx)
    db.commit()
    return True

  if log.before_json:
    before = json.loads(log.before_json)
    tx.direction = before["direction"]
    tx.amount_cents = int(before["amount_cents"])
    tx.currency = str(before["currency"])
    tx.occurred_at = dt.datetime.fromisoformat(before["occurred_at"])
    tx.account_id = before.get("account_id")
    tx.category_id = before.get("category_id")
    tx.merchant = before.get("merchant")
    tx.note = before.get("note")
    tx.deleted_at = dt.datetime.fromisoformat(before["deleted_at"]) if before.get("deleted_at") else None
    db.add(tx)
    db.commit()
    return True

  return False


def undo_last_ai_transaction_action(*, db: Session, user: User) -> bool:
  return undo_last_ai_action(db=db, user=user)
