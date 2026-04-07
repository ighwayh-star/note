from __future__ import annotations

import datetime as dt
import json
import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIConversation, AIConversationMessage, User


def get_or_create_conversation(*, db: Session, user: User, conversation_id: str | None) -> AIConversation:
  if conversation_id:
    conv = db.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.user_id == user.id))
    if conv:
      return conv

  conv = AIConversation(
    id=uuid.uuid4().hex,
    user_id=user.id,
    state_json="{}",
    updated_at=dt.datetime.now(dt.UTC),
  )
  db.add(conv)
  db.commit()
  db.refresh(conv)
  return conv


def append_message(*, db: Session, user: User, conversation_id: str, role: Literal["user", "assistant"], content: str) -> None:
  msg = AIConversationMessage(conversation_id=conversation_id, user_id=user.id, role=role, content=content)
  db.add(msg)
  conv = db.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.user_id == user.id))
  if conv:
    conv.updated_at = dt.datetime.now(dt.UTC)
    db.add(conv)
  db.commit()


def get_recent_messages(
  *,
  db: Session,
  user: User,
  conversation_id: str,
  limit: int = 12,
) -> list[dict[str, str]]:
  limit = min(max(limit, 1), 50)
  rows = (
    db.execute(
      select(AIConversationMessage.role, AIConversationMessage.content)
      .where(AIConversationMessage.conversation_id == conversation_id, AIConversationMessage.user_id == user.id)
      .order_by(AIConversationMessage.id.desc())
      .limit(limit)
    )
    .all()
  )
  items = [{"role": str(r[0]), "content": str(r[1])} for r in reversed(rows)]
  return items


def get_state(*, db: Session, user: User, conversation_id: str) -> dict[str, Any]:
  conv = db.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.user_id == user.id))
  if not conv:
    return {}
  try:
    obj = json.loads(conv.state_json or "{}")
    return obj if isinstance(obj, dict) else {}
  except Exception:
    return {}


def set_state(*, db: Session, user: User, conversation_id: str, state: dict[str, Any]) -> None:
  conv = db.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.user_id == user.id))
  if not conv:
    return
  conv.state_json = json.dumps(state, ensure_ascii=False)
  conv.updated_at = dt.datetime.now(dt.UTC)
  db.add(conv)
  db.commit()

