from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenOut(BaseModel):
  access_token: str
  token_type: str = "bearer"


class UserOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: int
  email: EmailStr


class RegisterIn(BaseModel):
  email: EmailStr
  password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
  email: EmailStr
  password: str


class AccountOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: int
  name: str
  currency: str


class AccountCreateIn(BaseModel):
  name: str = Field(min_length=1, max_length=64)
  currency: str = Field(default="CNY", min_length=1, max_length=8)


class CategoryOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: int
  name: str
  type: str


class CategoryCreateIn(BaseModel):
  name: str = Field(min_length=1, max_length=64)
  type: str = Field(pattern="^(income|expense)$")


class TransactionOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: int
  direction: str
  amount_cents: int
  currency: str
  occurred_at: dt.datetime
  account_id: int | None
  category_id: int | None
  merchant: str | None
  note: str | None


class TransactionCreateIn(BaseModel):
  direction: str = Field(pattern="^(income|expense)$")
  amount_cents: int = Field(ge=1)
  currency: str = Field(default="CNY", min_length=1, max_length=8)
  occurred_at: dt.datetime
  account_id: int | None = None
  category_id: int | None = None
  merchant: str | None = Field(default=None, max_length=128)
  note: str | None = Field(default=None, max_length=512)


class TransactionUpdateIn(BaseModel):
  direction: str | None = Field(default=None, pattern="^(income|expense)$")
  amount_cents: int | None = Field(default=None, ge=1)
  currency: str | None = Field(default=None, min_length=1, max_length=8)
  occurred_at: dt.datetime | None = None
  account_id: int | None = None
  category_id: int | None = None
  merchant: str | None = Field(default=None, max_length=128)
  note: str | None = Field(default=None, max_length=512)


class PaginatedTransactionsOut(BaseModel):
  items: list[TransactionOut]
  total: int


class StatsSummaryOut(BaseModel):
  start: dt.date
  end: dt.date
  income_cents: int
  expense_cents: int
  net_cents: int
  transactions_count: int


class StatsCategoryRow(BaseModel):
  category_id: int | None
  category_name: str
  total_cents: int


class StatsByCategoryOut(BaseModel):
  start: dt.date
  end: dt.date
  direction: str
  rows: list[StatsCategoryRow]

