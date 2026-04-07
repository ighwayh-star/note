export type TokenOut = {
  access_token: string
  token_type: 'bearer'
}

export type UserOut = {
  id: number
  email: string
}

export type AccountOut = {
  id: number
  name: string
  currency: string
}

export type CategoryOut = {
  id: number
  name: string
  type: 'income' | 'expense'
}

export type TransactionOut = {
  id: number
  direction: 'income' | 'expense'
  amount_cents: number
  currency: string
  occurred_at: string
  account_id: number | null
  category_id: number | null
  merchant: string | null
  note: string | null
}

export type PaginatedTransactionsOut = {
  items: TransactionOut[]
  total: number
}

export type StatsSummaryOut = {
  start: string
  end: string
  income_cents: number
  expense_cents: number
  net_cents: number
  transactions_count: number
}

export type StatsCategoryRow = {
  category_id: number | null
  category_name: string
  total_cents: number
}

export type StatsByCategoryOut = {
  start: string
  end: string
  direction: 'income' | 'expense'
  rows: StatsCategoryRow[]
}

export type AIChatIn = {
  message: string
  conversation_id?: string | null
}

export type AICardStatsSummary = {
  type: 'stats_summary'
  start: string
  end: string
  income_cents: number
  expense_cents: number
  net_cents: number
  transactions_count: number
}

export type AICardStatsByCategory = {
  type: 'stats_by_category'
  start: string
  end: string
  direction: 'income' | 'expense'
  rows: StatsCategoryRow[]
}

export type AICardTransactions = {
  type: 'transactions'
  total: number
  items: TransactionOut[]
}

export type AIResponseCard = AICardStatsSummary | AICardStatsByCategory | AICardTransactions

export type AIChatOut = {
  reply: string
  cards: AIResponseCard[]
  proposed_actions: { id: string; kind: string; payload: Record<string, unknown> }[]
  mode: string
  conversation_id: string
}

export type AIConfirmIn = {
  action_id: string
}

export type AIConfirmOut = {
  ok: boolean
  audit_id?: number | null
  entity_id?: number | null
}

