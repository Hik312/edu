/* 认证域状态。token 存 localStorage —— 后端是无状态 JWT，服务端不存会话。
 *
 * 一个坑：刷新页面后 token 还在 localStorage，但 user 是空的。
 * 所以有 ready 标志，路由守卫必须 await fetchMe() 之后再判断登录态，
 * 否则刷新时会误判成「未登录」直接跳走。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import { getToken, setToken } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(getToken())
  const loading = ref(false)
  const ready = ref(false)

  const isLoggedIn = computed(() => Boolean(token.value) && Boolean(user.value))

  async function login(username, password) {
    loading.value = true
    try {
      const r = await authApi.login(username, password)
      token.value = r.token
      setToken(r.token)
      user.value = r.user
      ready.value = true
      return r.user
    } finally {
      loading.value = false
    }
  }

  async function register(payload) {
    loading.value = true
    try {
      return await authApi.register(payload)
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) {
      ready.value = true
      return null
    }
    try {
      const r = await authApi.me()
      user.value = r.user
      return r.user
    } catch {
      // 401 时拦截器已经负责跳登录页了，这里只负责把本地状态清干净，
      // 不然守卫会拿着一个假登录态把人放进去
      token.value = ''
      setToken('')
      user.value = null
      return null
    } finally {
      ready.value = true
    }
  }

  function logout() {
    token.value = ''
    setToken('')
    user.value = null
    ready.value = true
  }

  return { user, token, loading, ready, isLoggedIn, login, register, fetchMe, logout }
})
