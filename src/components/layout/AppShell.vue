<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bot, LayoutGrid, List, LogOut, Tags } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const nav = computed(() => [
  { to: '/dashboard', label: '仪表盘', icon: LayoutGrid },
  { to: '/transactions', label: '流水', icon: List },
  { to: '/categories', label: '分类', icon: Tags },
  { to: '/ai', label: 'AI', icon: Bot },
])

function isActive(to: string) {
  return route.path === to
}

function onLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="min-h-dvh bg-zinc-50">
    <header class="sticky top-0 z-10 border-b border-zinc-200 bg-white/90 backdrop-blur">
      <div class="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <div class="flex items-center gap-2 text-sm font-semibold text-zinc-900">
          <div class="h-8 w-8 rounded-lg bg-zinc-900" />
          记账 MVP
        </div>
        <div class="flex items-center gap-2">
          <div class="hidden text-xs text-zinc-600 sm:block">{{ auth.user?.email }}</div>
          <Button variant="ghost" size="sm" @click="onLogout">
            <LogOut class="h-4 w-4" />
            退出
          </Button>
        </div>
      </div>
    </header>

    <div class="mx-auto grid max-w-5xl grid-cols-1 gap-4 px-4 py-4 md:grid-cols-[220px_1fr]">
      <aside class="md:sticky md:top-16 md:h-[calc(100dvh-4rem)]">
        <nav class="rounded-xl border border-zinc-200 bg-white p-2">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition"
            :class="isActive(item.to) ? 'bg-zinc-100 text-zinc-900' : 'text-zinc-700 hover:bg-zinc-50'"
          >
            <component :is="item.icon" class="h-4 w-4" />
            {{ item.label }}
          </RouterLink>
        </nav>
      </aside>
      <main>
        <slot />
      </main>
    </div>
  </div>
</template>

