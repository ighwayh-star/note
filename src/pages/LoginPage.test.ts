import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import LoginPage from '@/pages/LoginPage.vue'

describe('LoginPage', () => {
  it('renders login form', async () => {
    setActivePinia(createPinia())
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/login', component: LoginPage }],
    })
    router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginPage, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.text()).toContain('登录')
    expect(wrapper.text()).toContain('邮箱')
    expect(wrapper.text()).toContain('密码')
  })
})

