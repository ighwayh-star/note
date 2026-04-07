import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { UserOut } from '@/api/types'

type AuthState = {
  user: UserOut | null
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    loading: false,
    error: null,
  }),
  getters: {
    isAuthed: (s) => !!s.user,
  },
  actions: {
    async bootstrap() {
      const token = localStorage.getItem('access_token')
      if (!token) return
      this.loading = true
      this.error = null
      try {
        this.user = await api.auth.me()
      } catch (e: any) {
        localStorage.removeItem('access_token')
        this.user = null
        this.error = e?.message || '加载用户失败'
      } finally {
        this.loading = false
      }
    },
    async login(email: string, password: string) {
      this.loading = true
      this.error = null
      try {
        await api.auth.login(email, password)
        this.user = await api.auth.me()
      } catch (e: any) {
        this.error = e?.message || '登录失败'
        throw e
      } finally {
        this.loading = false
      }
    },
    async register(email: string, password: string) {
      this.loading = true
      this.error = null
      try {
        await api.auth.register(email, password)
      } catch (e: any) {
        this.error = e?.message || '注册失败'
        throw e
      } finally {
        this.loading = false
      }
    },
    logout() {
      api.auth.logout()
      this.user = null
    },
  },
})

