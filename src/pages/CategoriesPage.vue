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
import type { CategoryOut } from '@/api/types'

const loading = ref(false)
const error = ref<string | null>(null)
const items = ref<CategoryOut[]>([])

const name = ref('')
const type = ref<'expense' | 'income'>('expense')
const saving = ref(false)

const typeOptions = computed(() => [
  { value: 'expense', label: '支出' },
  { value: 'income', label: '收入' },
])

const grouped = computed(() => ({
  expense: items.value.filter((c) => c.type === 'expense'),
  income: items.value.filter((c) => c.type === 'income'),
}))

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await api.categories.list()
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function create() {
  const n = name.value.trim()
  if (!n) return
  saving.value = true
  error.value = null
  try {
    await api.categories.create(n, type.value)
    name.value = ''
    await load()
  } catch (e: any) {
    error.value = e?.message || '创建失败'
  } finally {
    saving.value = false
  }
}

async function removeItem(c: CategoryOut) {
  if (!confirm(`确认删除分类：${c.name}？`)) return
  error.value = null
  try {
    await api.categories.remove(c.id)
    await load()
  } catch (e: any) {
    error.value = e?.message || '删除失败'
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="flex flex-col gap-4">
      <div>
        <div class="text-base font-semibold text-zinc-900">分类</div>
        <div class="text-xs text-zinc-600">手动新增与删除分类</div>
      </div>

      <Card>
        <CardHeader>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <Input v-model="name" placeholder="分类名称，例如：餐饮" @keydown.enter.prevent="create" />
            <Select v-model="type" :options="typeOptions" />
            <Button :disabled="saving" @click="create">{{ saving ? '创建中…' : '新增分类' }}</Button>
          </div>
          <div class="mt-2 flex items-center justify-between">
            <div class="text-xs text-zinc-600">共 {{ items.length }} 个</div>
            <Button variant="ghost" size="sm" :disabled="loading" @click="load">刷新</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="error" class="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
            {{ error }}
          </div>

          <div v-if="loading" class="space-y-2">
            <div v-for="i in 6" :key="i" class="h-9 w-full animate-pulse rounded-lg bg-zinc-100" />
          </div>

          <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <div class="mb-2 text-xs font-medium text-zinc-700">支出</div>
              <div class="space-y-2">
                <div
                  v-for="c in grouped.expense"
                  :key="c.id"
                  class="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-3 py-2"
                >
                  <div class="text-sm text-zinc-900">{{ c.name }}</div>
                  <Button size="sm" variant="danger" @click="removeItem(c)">删除</Button>
                </div>
                <div v-if="grouped.expense.length === 0" class="text-sm text-zinc-600">暂无支出分类</div>
              </div>
            </div>

            <div>
              <div class="mb-2 text-xs font-medium text-zinc-700">收入</div>
              <div class="space-y-2">
                <div
                  v-for="c in grouped.income"
                  :key="c.id"
                  class="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-3 py-2"
                >
                  <div class="text-sm text-zinc-900">{{ c.name }}</div>
                  <Button size="sm" variant="danger" @click="removeItem(c)">删除</Button>
                </div>
                <div v-if="grouped.income.length === 0" class="text-sm text-zinc-600">暂无收入分类</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </AppShell>
</template>

