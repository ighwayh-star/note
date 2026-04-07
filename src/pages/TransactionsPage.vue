<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { api } from '@/api/client'
import type { AccountOut, CategoryOut, TransactionOut } from '@/api/types'
import { formatCents } from '@/utils/money'
import TransactionEditor from '@/components/transactions/TransactionEditor.vue'

const loading = ref(false)
const error = ref<string | null>(null)
const items = ref<TransactionOut[]>([])
const total = ref(0)

const accounts = ref<AccountOut[]>([])
const categories = ref<CategoryOut[]>([])

const search = ref('')
const direction = ref<'all' | 'income' | 'expense'>('all')
const accountId = ref<string>('')
const categoryId = ref<string>('')
const limit = ref(50)
const offset = ref(0)

const showEditor = ref(false)
const editing = ref<TransactionOut | null>(null)

const directionOptions = computed(() => [
  { value: 'all', label: '全部' },
  { value: 'expense', label: '支出' },
  { value: 'income', label: '收入' },
])

const accountOptions = computed(() => [
  { value: '', label: '全部账户' },
  ...accounts.value.map((a) => ({ value: String(a.id), label: a.name })),
])

const categoryOptions = computed(() => [
  { value: '', label: '全部分类' },
  ...categories.value.map((c) => ({ value: String(c.id), label: `${c.type === 'expense' ? '支出' : '收入'} · ${c.name}` })),
])

async function load() {
  loading.value = true
  error.value = null
  try {
    const [acc, cat, tx] = await Promise.all([
      api.accounts.list(),
      api.categories.list(),
      api.transactions.list({
        search: search.value || undefined,
        direction: direction.value === 'all' ? undefined : direction.value,
        account_id: accountId.value ? Number(accountId.value) : undefined,
        category_id: categoryId.value ? Number(categoryId.value) : undefined,
        limit: limit.value,
        offset: offset.value,
      }),
    ])
    accounts.value = acc
    categories.value = cat
    items.value = tx.items
    total.value = tx.total
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  showEditor.value = true
}

function openEdit(tx: TransactionOut) {
  editing.value = tx
  showEditor.value = true
}

async function onDelete(tx: TransactionOut) {
  if (!confirm('确认删除该流水？')) return
  try {
    await api.transactions.remove(tx.id)
    await load()
  } catch (e: any) {
    error.value = e?.message || '删除失败'
  }
}

async function onSaved() {
  showEditor.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div class="text-base font-semibold text-zinc-900">流水</div>
          <div class="text-xs text-zinc-600">手动新增、编辑、删除与搜索</div>
        </div>
        <div class="flex items-center gap-2">
          <Button @click="openCreate">新增流水</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-4">
            <Input v-model="search" placeholder="搜索商家/备注" />
            <Select v-model="direction" :options="directionOptions" />
            <Select v-model="accountId" :options="accountOptions" />
            <Select v-model="categoryId" :options="categoryOptions" />
          </div>
          <div class="mt-2 flex items-center justify-between">
            <div class="text-xs text-zinc-600">共 {{ total }} 笔</div>
            <Button variant="ghost" size="sm" :disabled="loading" @click="load">刷新</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="error" class="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
            {{ error }}
          </div>
          <div v-if="loading" class="space-y-2">
            <div v-for="i in 8" :key="i" class="h-10 w-full animate-pulse rounded-lg bg-zinc-100" />
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="tx in items"
              :key="tx.id"
              class="flex flex-col gap-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <div
                    class="inline-flex h-6 items-center rounded-md px-2 text-xs"
                    :class="tx.direction === 'expense' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'"
                  >
                    {{ tx.direction === 'expense' ? '支出' : '收入' }}
                  </div>
                  <div class="truncate text-sm font-medium text-zinc-900">{{ tx.merchant || '—' }}</div>
                </div>
                <div class="mt-1 text-xs text-zinc-600">
                  {{ new Date(tx.occurred_at).toLocaleString('zh-CN') }}
                  <span v-if="tx.note"> · {{ tx.note }}</span>
                </div>
              </div>
              <div class="flex items-center justify-between gap-2 sm:justify-end">
                <div class="text-sm font-semibold text-zinc-900">{{ formatCents(tx.amount_cents, tx.currency) }}</div>
                <div class="flex items-center gap-2">
                  <Button size="sm" variant="ghost" @click="openEdit(tx)">编辑</Button>
                  <Button size="sm" variant="danger" @click="onDelete(tx)">删除</Button>
                </div>
              </div>
            </div>
            <div v-if="items.length === 0" class="text-sm text-zinc-600">暂无流水</div>
          </div>
        </CardContent>
      </Card>
    </div>

    <TransactionEditor
      v-if="showEditor"
      :accounts="accounts"
      :categories="categories"
      :editing="editing"
      @close="showEditor = false"
      @saved="onSaved"
    />
  </AppShell>
</template>

