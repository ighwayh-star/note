from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
  password_hash: Mapped[str] = mapped_column(String(255))
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class Account(Base):
  __tablename__ = "accounts"
  __table_args__ = (UniqueConstraint("user_id", "name", name="uq_accounts_user_name"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  name: Mapped[str] = mapped_column(String(64))
  currency: Mapped[str] = mapped_column(String(8), default="CNY")
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class Category(Base):
  __tablename__ = "categories"
  __table_args__ = (UniqueConstraint("user_id", "name", "type", name="uq_categories_user_name_type"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  name: Mapped[str] = mapped_column(String(64))
  type: Mapped[str] = mapped_column(String(16))
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class Transaction(Base):
  __tablename__ = "transactions"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  direction: Mapped[str] = mapped_column(String(16), index=True)
  amount_cents: Mapped[int] = mapped_column(Integer)
  currency: Mapped[str] = mapped_column(String(8), default="CNY")
  occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
  account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
  category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
  merchant: Mapped[str | None] = mapped_column(String(128), nullable=True)
  note: Mapped[str | None] = mapped_column(String(512), nullable=True)
  deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))
  updated_at: Mapped[dt.datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: dt.datetime.now(dt.UTC),
    onupdate=lambda: dt.datetime.now(dt.UTC),
  )


class AuditLog(Base):
  __tablename__ = "audit_logs"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  actor: Mapped[str] = mapped_column(String(16))
  action_kind: Mapped[str] = mapped_column(String(64), index=True)
  entity_type: Mapped[str] = mapped_column(String(64), index=True)
  entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
  before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class AIPendingAction(Base):
  __tablename__ = "ai_pending_actions"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  kind: Mapped[str] = mapped_column(String(64), index=True)
  payload_json: Mapped[str] = mapped_column(Text)
  status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class AIConversation(Base):
  __tablename__ = "ai_conversations"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  state_json: Mapped[str] = mapped_column(Text, default="{}")
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))
  updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))


class AIConversationMessage(Base):
  __tablename__ = "ai_conversation_messages"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  conversation_id: Mapped[str] = mapped_column(ForeignKey("ai_conversations.id"), index=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
  role: Mapped[str] = mapped_column(String(16), index=True)
  content: Mapped[str] = mapped_column(Text)
  created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC))

