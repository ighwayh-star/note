<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { api } from '@/api/client'
import type { AccountOut, CategoryOut, TransactionOut } from '@/api/types'
import { centsFromYuanText } from '@/utils/money'

type Props = {
  accounts: AccountOut[]
  categories: CategoryOut[]
  editing: TransactionOut | null
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()

const direction = ref<'expense' | 'income'>('expense')
const amountText = ref('')
const occurredAt = ref('')
const accountId = ref<string>('')
const categoryId = ref<string>('')
const merchant = ref('')
const note = ref('')
const saving = ref(false)
const error = ref<string | null>(null)

const accountOptions = computed(() => [
  { value: '', label: '不选择账户' },
  ...props.accounts.map((a) => ({ value: String(a.id), label: a.name })),
])

const categoryOptions = computed(() => {
  const list = props.categories.filter((c) => c.type === direction.value)
  return [{ value: '', label: '未分类' }, ...list.map((c) => ({ value: String(c.id), label: c.name }))]
})

watch(
  () => props.editing,
  (tx) => {
    error.value = null
    if (!tx) {
      direction.value = 'expense'
      amountText.value = ''
      occurredAt.value = new Date().toISOString().slice(0, 16)
      accountId.value = ''
      categoryId.value = ''
      merchant.value = ''
      note.value = ''
      return
    }
    direction.value = tx.direction
    amountText.value = String((tx.amount_cents / 100).toFixed(2))
    occurredAt.value = tx.occurred_at.slice(0, 16)
    accountId.value = tx.account_id ? String(tx.account_id) : ''
    categoryId.value = tx.category_id ? String(tx.category_id) : ''
    merchant.value = tx.merchant || ''
    note.value = tx.note || ''
  },
  { immediate: true },
)

async function save() {
  error.value = null
  const amountCents = centsFromYuanText(amountText.value)
  if (amountCents <= 0) {
    error.value = '金额必须大于0'
    return
  }
  if (!occurredAt.value) {
    error.value = '请选择时间'
    return
  }
  saving.value = true
  try {
    const payload = {
      direction: direction.value,
      amount_cents: amountCents,
      currency: 'CNY',
      occurred_at: new Date(occurredAt.value).toISOString(),
      account_id: accountId.value ? Number(accountId.value) : null,
      category_id: categoryId.value ? Number(categoryId.value) : null,
      merchant: merchant.value || null,
      note: note.value || null,
    }
    if (!props.editing) {
      await api.transactions.create(payload)
    } else {
      await api.transactions.update(props.editing.id, payload as any)
    }
    emit('saved')
  } catch (e: any) {
    error.value = e?.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
    <div class="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white shadow-xl">
      <div class="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
        <div class="text-sm font-semibold text-zinc-900">{{ editing ? '编辑流水' : '新增流水' }}</div>
        <button class="text-sm text-zinc-600 hover:text-zinc-900" @click="emit('close')">关闭</button>
      </div>
      <div class="p-4">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="sm:col-span-1">
            <div class="mb-1 text-xs font-medium text-zinc-700">方向</div>
            <Select
              v-model="direction"
              :options="[
                { value: 'expense', label: '支出' },
                { value: 'income', label: '收入' },
              ]"
            />
          </div>
          <div class="sm:col-span-1">
            <div class="mb-1 text-xs font-medium text-zinc-700">金额（元）</div>
            <Input v-model="amountText" placeholder="例如 12.34" />
          </div>
          <div class="sm:col-span-2">
            <div class="mb-1 text-xs font-medium text-zinc-700">时间</div>
            <input
              v-model="occurredAt"
              type="datetime-local"
              class="h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm"
            />
          </div>
          <div class="sm:col-span-1">
            <div class="mb-1 text-xs font-medium text-zinc-700">账户</div>
            <Select v-model="accountId" :options="accountOptions" />
          </div>
          <div class="sm:col-span-1">
            <div class="mb-1 text-xs font-medium text-zinc-700">分类</div>
            <Select v-model="categoryId" :options="categoryOptions" />
          </div>
          <div class="sm:col-span-2">
            <div class="mb-1 text-xs font-medium text-zinc-700">商家</div>
            <Input v-model="merchant" placeholder="例如 星巴克" />
          </div>
          <div class="sm:col-span-2">
            <div class="mb-1 text-xs font-medium text-zinc-700">备注</div>
            <Input v-model="note" placeholder="例如 早餐" />
          </div>
        </div>

        <div v-if="error" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
          {{ error }}
        </div>

        <div class="mt-4 flex items-center justify-end gap-2">
          <Button variant="ghost" @click="emit('close')">取消</Button>
          <Button :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</Button>
        </div>
      </div>
    </div>
  </div>
</template>

