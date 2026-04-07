<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from '@/components/ui/Button.vue'

const router = useRouter()
const auth = useAuthStore()

function go() {
  if (auth.user) router.push('/dashboard')
  else router.push('/login')
}
</script>

<template>
  <div class="min-h-dvh bg-zinc-50">
    <div class="mx-auto flex max-w-3xl flex-col items-start gap-3 px-4 py-12">
      <div class="text-xl font-semibold text-zinc-900">记账 MVP</div>
      <div class="text-sm text-zinc-600">手动记账 + 基础统计仪表盘（后端 FastAPI / 前端 Vue）</div>
      <Button @click="go">开始使用</Button>
      <div class="mt-6 rounded-xl border border-zinc-200 bg-white p-4 text-xs text-zinc-700">
        <div class="font-medium text-zinc-900">本地默认：</div>
        <div class="mt-1">后端：`http://127.0.0.1:8000`</div>
        <div>前端：`http://127.0.0.1:5173`</div>
      </div>
    </div>
  </div>
</template>
