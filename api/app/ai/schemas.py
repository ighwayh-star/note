from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AIChatIn(BaseModel):
  message: str = Field(min_length=1, max_length=4000)
  conversation_id: str | None = None


class AIStatsSummaryCard(BaseModel):
  type: Literal["stats_summary"] = "stats_summary"
  start: str
  end: str
  income_cents: int
  expense_cents: int
  net_cents: int
  transactions_count: int


class AIStatsByCategoryRow(BaseModel):
  category_id: int | None
  category_name: str
  total_cents: int


class AIStatsByCategoryCard(BaseModel):
  type: Literal["stats_by_category"] = "stats_by_category"
  start: str
  end: str
  direction: Literal["income", "expense"]
  rows: list[AIStatsByCategoryRow]


class AITransactionListItem(BaseModel):
  id: int
  direction: str
  amount_cents: int
  currency: str
  occurred_at: str
  account_id: int | None
  category_id: int | None
  merchant: str | None
  note: str | None


class AITransactionsCard(BaseModel):
  type: Literal["transactions"] = "transactions"
  total: int
  items: list[AITransactionListItem]


AIResponseCard = AIStatsSummaryCard | AIStatsByCategoryCard | AITransactionsCard


class AIProposedAction(BaseModel):
  id: str
  kind: str
  payload: dict


class AIConfirmIn(BaseModel):
  action_id: str


class AIConfirmOut(BaseModel):
  ok: bool
  audit_id: int | None = None
  entity_id: int | None = None


class AIChatOut(BaseModel):
  reply: str
  cards: list[AIResponseCard] = Field(default_factory=list)
  proposed_actions: list[AIProposedAction] = Field(default_factory=list)
  mode: str
  conversation_id: str = ""
