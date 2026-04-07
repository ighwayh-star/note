<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { z } from 'zod'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import Input from '@/components/ui/Input.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const localError = ref<string | null>(null)

const schema = computed(() =>
  z.object({
    email: z.string().email('邮箱格式不正确'),
    password: z.string().min(8, '密码至少8位'),
  }),
)

async function submit() {
  localError.value = null
  const parsed = schema.value.safeParse({ email: email.value, password: password.value })
  if (!parsed.success) {
    localError.value = parsed.error.issues[0]?.message || '请检查输入'
    return
  }
  try {
    if (mode.value === 'register') {
      await auth.register(email.value, password.value)
      mode.value = 'login'
      localError.value = '注册成功，请登录'
      return
    }
    await auth.login(email.value, password.value)
    router.replace('/dashboard')
  } catch (e: any) {
    localError.value = e?.message || '操作失败'
  }
}
</script>

<template>
  <div class="min-h-dvh bg-zinc-50">
    <div class="mx-auto flex max-w-md flex-col gap-4 px-4 py-10">
      <div class="text-center">
        <div class="text-lg font-semibold text-zinc-900">记账 MVP</div>
        <div class="text-xs text-zinc-600">注册/登录后开始记账</div>
      </div>

      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <div class="text-sm font-semibold text-zinc-900">{{ mode === 'login' ? '登录' : '注册' }}</div>
            <button
              class="text-xs text-zinc-600 underline underline-offset-4 hover:text-zinc-900"
              @click="mode = mode === 'login' ? 'register' : 'login'"
            >
              切换到{{ mode === 'login' ? '注册' : '登录' }}
            </button>
          </div>
        </CardHeader>
        <CardContent>
          <form class="flex flex-col gap-3" @submit.prevent="submit">
            <div class="flex flex-col gap-1">
              <div class="text-xs font-medium text-zinc-700">邮箱</div>
              <Input v-model="email" placeholder="you@example.com" />
            </div>
            <div class="flex flex-col gap-1">
              <div class="text-xs font-medium text-zinc-700">密码</div>
              <Input v-model="password" type="password" placeholder="至少8位" />
            </div>
            <div v-if="localError || auth.error" class="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
              {{ localError || auth.error }}
            </div>
            <Button type="submit" :disabled="auth.loading">
              {{ auth.loading ? '处理中…' : mode === 'login' ? '登录' : '注册' }}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

