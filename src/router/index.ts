import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import TransactionsPage from '@/pages/TransactionsPage.vue'
import AIChatPage from '@/pages/AIChatPage.vue'
import CategoriesPage from '@/pages/CategoriesPage.vue'
import { useAuthStore } from '@/stores/auth'

// 定义路由配置
const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
  },
  { path: '/login', name: 'login', component: LoginPage },
  { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { requiresAuth: true } },
  { path: '/transactions', name: 'transactions', component: TransactionsPage, meta: { requiresAuth: true } },
  { path: '/categories', name: 'categories', component: CategoriesPage, meta: { requiresAuth: true } },
  { path: '/ai', name: 'ai', component: AIChatPage, meta: { requiresAuth: true } },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.user && localStorage.getItem('access_token')) {
    await auth.bootstrap()
  }
  if (to.meta.requiresAuth && !auth.user) return { path: '/login' }
  if (to.path === '/' && auth.user) return { path: '/dashboard' }
  return true
})

export default router
