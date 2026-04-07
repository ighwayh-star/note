<script setup lang="ts">
import { ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import Input from '@/components/ui/Input.vue'
import { api } from '@/api/client'
import type { AIChatOut, AIResponseCard } from '@/api/types'
import { formatCents } from '@/utils/money'

type ChatMsg = {
  role: 'user' | 'assistant'
  text: string
  cards?: AIResponseCard[]
  actions?: AIChatOut['proposed_actions']
  mode?: string
}

function actionField(a: any, key: string): any {
  return a?.payload?.fields ? a.payload.fields[key] : undefined
}

const sending = ref(false)
const error = ref<string | null>(null)
const input = ref('')

const acting = ref<Record<string, boolean>>({})
const conversationId = ref<string | null>(null)
const initialMessages: ChatMsg[] = [
  {
    role: 'assistant',
    text: '你可以问我：\n- 2026-01-01 到 2026-01-31 支出多少\n- 2026-01-01 到 2026-01-31 按分类统计\n- 2026-01-01 到 2026-01-31 列出流水 “Coffee”\n- 我今天下午在肯德基花了50元',
  },
]
const messages = ref<ChatMsg[]>([...initialMessages])

async function send() {
  const text = input.value.trim()
  if (!text) return
  error.value = null
  messages.value.push({ role: 'user', text })
  input.value = ''
  sending.value = true
  try {
    const res = await api.ai.chat(text, conversationId.value)
    conversationId.value = res.conversation_id
    messages.value.push({ role: 'assistant', text: res.reply, cards: res.cards, actions: res.proposed_actions, mode: res.mode })
  } catch (e: any) {
    error.value = e?.message || '发送失败'
  } finally {
    sending.value = false
  }
}

async function confirmAction(id: string) {
  acting.value[id] = true
  error.value = null
  try {
    const res = await api.ai.confirm(id)
    const tail = res.entity_id ? `（entity_id=${res.entity_id}）` : ''
    messages.value.push({ role: 'assistant', text: `已执行：${id}${tail}`, mode: 'system' })
  } catch (e: any) {
    error.value = e?.message || '确认失败'
  } finally {
    acting.value[id] = false
  }
}

async function cancelAction(id: string) {
  acting.value[id] = true
  error.value = null
  try {
    await api.ai.cancel(id)
    messages.value.push({ role: 'assistant', text: `已取消：${id}`, mode: 'system' })
  } catch (e: any) {
    error.value = e?.message || '取消失败'
  } finally {
    acting.value[id] = false
  }
}

async function undoLast() {
  error.value = null
  try {
    await api.ai.undoLast()
    messages.value.push({ role: 'assistant', text: '已撤销最近一次 AI 写入操作', mode: 'system' })
  } catch (e: any) {
    error.value = e?.message || '撤销失败'
  }
}

function newChat() {
  conversationId.value = null
  messages.value = [...initialMessages]
  error.value = null
  input.value = ''
}
</script>

<template>
  <AppShell>
    <div class="flex flex-col gap-4">
      <div>
        <div class="text-base font-semibold text-zinc-900">AI 助手</div>
        <div class="text-xs text-zinc-600">支持查询与写入（写入需要二次确认）</div>
      </div>

      <Card>
        <CardHeader>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div class="flex-1">
              <Input v-model="input" placeholder="输入你的问题，建议包含 YYYY-MM-DD 到 YYYY-MM-DD" @keydown.enter.prevent="send" />
            </div>
            <div class="flex items-center gap-2">
              <Button :disabled="sending" @click="send">{{ sending ? '发送中…' : '发送' }}</Button>
              <Button :disabled="sending" variant="ghost" @click="undoLast">撤销上次</Button>
              <Button :disabled="sending" variant="ghost" @click="newChat">新对话</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="error" class="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
            {{ error }}
          </div>

          <div class="space-y-3">
            <div
              v-for="(m, idx) in messages"
              :key="idx"
              class="rounded-xl border border-zinc-200 bg-white px-3 py-2"
            >
              <div class="flex items-center justify-between">
                <div class="text-xs font-medium text-zinc-700">{{ m.role === 'user' ? '我' : 'AI' }}</div>
                <div v-if="m.role === 'assistant' && m.mode" class="text-[10px] text-zinc-500">{{ m.mode }}</div>
              </div>
              <div class="mt-1 whitespace-pre-wrap text-sm text-zinc-900">{{ m.text }}</div>

              <div v-if="m.actions && m.actions.length" class="mt-3 space-y-2">
                <div
                  v-for="a in m.actions"
                  :key="a.id"
                  class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="min-w-0">
                      <div class="truncate text-xs font-medium text-zinc-900">{{ a.kind }}</div>
                      <div class="mt-0.5 text-xs text-zinc-700">
                        {{ (a.payload as any).summary || a.id }}
                      </div>
                      <div class="mt-2 space-y-1 text-[11px] text-zinc-700">
                        <div v-if="actionField(a, 'merchant')" class="truncate">地点/商户：{{ actionField(a, 'merchant') }}</div>
                        <div v-if="actionField(a, 'occurred_at')">时间：{{ new Date(actionField(a, 'occurred_at')).toLocaleString('zh-CN') }}</div>
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <Button :disabled="acting[a.id]" @click="confirmAction(a.id)">{{ acting[a.id] ? '处理中…' : '确认执行' }}</Button>
                      <Button :disabled="acting[a.id]" variant="ghost" @click="cancelAction(a.id)">取消</Button>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="m.cards && m.cards.length" class="mt-3 space-y-2">
                <div v-for="(c, i) in m.cards" :key="i" class="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
                  <template v-if="c.type === 'stats_summary'">
                    <div class="text-xs font-medium text-zinc-700">收支汇总（{{ c.start }} ~ {{ c.end }}）</div>
                    <div class="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
                      <div class="rounded-lg bg-white p-2">
                        <div class="text-[10px] text-zinc-500">收入</div>
                        <div class="text-sm font-semibold text-zinc-900">{{ formatCents(c.income_cents) }}</div>
                      </div>
                      <div class="rounded-lg bg-white p-2">
                        <div class="text-[10px] text-zinc-500">支出</div>
                        <div class="text-sm font-semibold text-zinc-900">{{ formatCents(c.expense_cents) }}</div>
                      </div>
                      <div class="rounded-lg bg-white p-2">
                        <div class="text-[10px] text-zinc-500">净额</div>
                        <div class="text-sm font-semibold text-zinc-900">{{ formatCents(c.net_cents) }}</div>
                      </div>
                      <div class="rounded-lg bg-white p-2">
                        <div class="text-[10px] text-zinc-500">笔数</div>
                        <div class="text-sm font-semibold text-zinc-900">{{ c.transactions_count }}</div>
                      </div>
                    </div>
                  </template>

                  <template v-else-if="c.type === 'stats_by_category'">
                    <div class="text-xs font-medium text-zinc-700">
                      按分类汇总（{{ c.direction === 'expense' ? '支出' : '收入' }}，{{ c.start }} ~ {{ c.end }}）
                    </div>
                    <div class="mt-2 space-y-1">
                      <div
                        v-for="r in c.rows"
                        :key="String(r.category_id) + r.category_name"
                        class="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm"
                      >
                        <div class="text-zinc-900">{{ r.category_name }}</div>
                        <div class="font-medium text-zinc-900">{{ formatCents(r.total_cents) }}</div>
                      </div>
                      <div v-if="c.rows.length === 0" class="text-sm text-zinc-600">暂无数据</div>
                    </div>
                  </template>

                  <template v-else-if="c.type === 'transactions'">
                    <div class="text-xs font-medium text-zinc-700">流水明细（共 {{ c.total }} 笔，展示前 {{ c.items.length }} 笔）</div>
                    <div class="mt-2 space-y-1">
                      <div
                        v-for="tx in c.items"
                        :key="tx.id"
                        class="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm"
                      >
                        <div class="min-w-0">
                          <div class="truncate text-zinc-900">#{{ tx.id }} {{ tx.merchant || '—' }}</div>
                          <div class="mt-0.5 text-[10px] text-zinc-500">{{ new Date(tx.occurred_at).toLocaleString('zh-CN') }}</div>
                        </div>
                        <div class="font-medium text-zinc-900">{{ formatCents(tx.amount_cents, tx.currency) }}</div>
                      </div>
                      <div v-if="c.items.length === 0" class="text-sm text-zinc-600">暂无流水</div>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </AppShell>
</template>
