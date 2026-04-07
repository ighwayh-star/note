import { httpJson } from '@/utils/http'
import type {
  AccountOut,
  AIConfirmOut,
  AIChatOut,
  CategoryOut,
  PaginatedTransactionsOut,
  StatsByCategoryOut,
  StatsSummaryOut,
  TokenOut,
  TransactionOut,
  UserOut,
} from '@/api/types'

const API_BASE = 'http://127.0.0.1:8000'

function authHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      httpJson<UserOut>(`${API_BASE}/api/auth/register`, { method: 'POST', json: { email, password } }),
    login: async (email: string, password: string) => {
      const t = await httpJson<TokenOut>(`${API_BASE}/api/auth/login`, { method: 'POST', json: { email, password } })
      localStorage.setItem('access_token', t.access_token)
      return t
    },
    logout: () => {
      localStorage.removeItem('access_token')
    },
    me: () => httpJson<UserOut>(`${API_BASE}/api/users/me`, { headers: authHeader() }),
  },
  accounts: {
    list: () => httpJson<AccountOut[]>(`${API_BASE}/api/accounts`, { headers: authHeader() }),
    create: (name: string, currency: string) =>
      httpJson<AccountOut>(`${API_BASE}/api/accounts`, { method: 'POST', headers: authHeader(), json: { name, currency } }),
    remove: (id: number) =>
      httpJson<void>(`${API_BASE}/api/accounts/${id}`, { method: 'DELETE', headers: authHeader() }),
  },
  categories: {
    list: () => httpJson<CategoryOut[]>(`${API_BASE}/api/categories`, { headers: authHeader() }),
    create: (name: string, type: 'income' | 'expense') =>
      httpJson<CategoryOut>(`${API_BASE}/api/categories`, { method: 'POST', headers: authHeader(), json: { name, type } }),
    remove: (id: number) =>
      httpJson<void>(`${API_BASE}/api/categories/${id}`, { method: 'DELETE', headers: authHeader() }),
  },
  transactions: {
    list: (params: {
      start?: string
      end?: string
      direction?: 'income' | 'expense'
      account_id?: number
      category_id?: number
      search?: string
      limit?: number
      offset?: number
    }) => {
      const url = new URL(`${API_BASE}/api/transactions`)
      Object.entries(params).forEach(([k, v]) => {
        if (v === undefined || v === null) return
        url.searchParams.set(k, String(v))
      })
      return httpJson<PaginatedTransactionsOut>(url.toString(), { headers: authHeader() })
    },
    create: (payload: {
      direction: 'income' | 'expense'
      amount_cents: number
      currency: string
      occurred_at: string
      account_id?: number | null
      category_id?: number | null
      merchant?: string | null
      note?: string | null
    }) =>
      httpJson<TransactionOut>(`${API_BASE}/api/transactions`, { method: 'POST', headers: authHeader(), json: payload }),
    update: (id: number, patch: Partial<Omit<TransactionOut, 'id'>>) =>
      httpJson<TransactionOut>(`${API_BASE}/api/transactions/${id}`, { method: 'PUT', headers: authHeader(), json: patch }),
    remove: (id: number) =>
      httpJson<void>(`${API_BASE}/api/transactions/${id}`, { method: 'DELETE', headers: authHeader() }),
  },
  stats: {
    summary: (start: string, end: string) =>
      httpJson<StatsSummaryOut>(`${API_BASE}/api/stats/summary?start=${start}&end=${end}`, { headers: authHeader() }),
    byCategory: (start: string, end: string, direction: 'income' | 'expense') =>
      httpJson<StatsByCategoryOut>(
        `${API_BASE}/api/stats/by-category?start=${start}&end=${end}&direction=${direction}`,
        { headers: authHeader() },
      ),
  },
  ai: {
    chat: (message: string, conversation_id?: string | null) =>
      httpJson<AIChatOut>(`${API_BASE}/api/ai/chat`, {
        method: 'POST',
        headers: authHeader(),
        json: { message, conversation_id: conversation_id || null },
      }),
    confirm: (action_id: string) =>
      httpJson<AIConfirmOut>(`${API_BASE}/api/ai/confirm`, { method: 'POST', headers: authHeader(), json: { action_id } }),
    cancel: (action_id: string) =>
      httpJson<AIConfirmOut>(`${API_BASE}/api/ai/cancel`, { method: 'POST', headers: authHeader(), json: { action_id } }),
    undoLast: () => httpJson<AIConfirmOut>(`${API_BASE}/api/ai/undo-last`, { method: 'POST', headers: authHeader() }),
  },
}

