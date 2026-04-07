<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import Select from '@/components/ui/Select.vue'
import { api } from '@/api/client'
import type { StatsByCategoryOut, StatsSummaryOut } from '@/api/types'
import { endOfMonth, startOfMonth, toISODate } from '@/utils/date'
import { formatCents } from '@/utils/money'

const start = ref(toISODate(startOfMonth()))
const end = ref(toISODate(endOfMonth()))
const direction = ref<'expense' | 'income'>('expense')

const loading = ref(false)
const summary = ref<StatsSummaryOut | null>(null)
const byCategory = ref<StatsByCategoryOut | null>(null)
const error = ref<string | null>(null)

const directionOptions = computed(() => [
  { value: 'expense', label: '支出' },
  { value: 'income', label: '收入' },
])

async function load() {
  loading.value = true
  error.value = null
  try {
    const [s, c] = await Promise.all([
      api.stats.summary(start.value, end.value),
      api.stats.byCategory(start.value, end.value, direction.value),
    ])
    summary.value = s
    byCategory.value = c
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div class="text-base font-semibold text-zinc-900">仪表盘</div>
          <div class="text-xs text-zinc-600">按时间范围查看收支与分类汇总</div>
        </div>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div class="flex items-center gap-2">
            <input v-model="start" type="date" class="h-10 rounded-lg border border-zinc-200 bg-white px-3 text-sm" />
            <div class="text-xs text-zinc-500">到</div>
            <input v-model="end" type="date" class="h-10 rounded-lg border border-zinc-200 bg-white px-3 text-sm" />
          </div>
          <div class="w-40">
            <Select v-model="direction" :options="directionOptions" />
          </div>
          <button
            class="h-10 rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-800"
            :disabled="loading"
            @click="load"
          >
            刷新
          </button>
        </div>
      </div>

      <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ error }}
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <div class="text-xs font-medium text-zinc-700">收入</div>
          </CardHeader>
          <CardContent>
            <div class="text-lg font-semibold text-zinc-900">{{ formatCents(summary?.income_cents || 0) }}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div class="text-xs font-medium text-zinc-700">支出</div>
          </CardHeader>
          <CardContent>
            <div class="text-lg font-semibold text-zinc-900">{{ formatCents(summary?.expense_cents || 0) }}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div class="text-xs font-medium text-zinc-700">净额</div>
          </CardHeader>
          <CardContent>
            <div class="text-lg font-semibold text-zinc-900">{{ formatCents(summary?.net_cents || 0) }}</div>
            <div class="mt-1 text-xs text-zinc-600">共 {{ summary?.transactions_count || 0 }} 笔</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div class="text-sm font-semibold text-zinc-900">按分类汇总（{{ direction === 'expense' ? '支出' : '收入' }}）</div>
        </CardHeader>
        <CardContent>
          <div v-if="loading" class="space-y-2">
            <div v-for="i in 6" :key="i" class="h-9 w-full animate-pulse rounded-lg bg-zinc-100" />
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="r in byCategory?.rows || []"
              :key="String(r.category_id) + r.category_name"
              class="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-3 py-2"
            >
              <div class="text-sm text-zinc-900">{{ r.category_name }}</div>
              <div class="text-sm font-medium text-zinc-900">{{ formatCents(r.total_cents) }}</div>
            </div>
            <div v-if="(byCategory?.rows || []).length === 0" class="text-sm text-zinc-600">暂无数据</div>
          </div>
        </CardContent>
      </Card>
    </div>
  </AppShell>
</template>

