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

  /** 修改个人信息（目前只有昵称）。成功后就地更新 user，
   *  免得页面显示新名字、侧栏还是旧的 —— 刷新才一致的体验很糙。 */
  async function updateProfile(payload) {
    const r = await authApi.updateMe(payload)
    user.value = r.user
    return r.user
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
    } catch (err) {
      // ★ 只有 401 才算「token 失效」，别的错误不能把人踢下线。
      // 从前是无条件清 token：后端重启中 / 瞬时 502 / 网络抖动时刷新页面，
      // 用户会被默默送回登录页，登录页还说「登录已过期」—— 明明什么都没过期。
      // 状态码由 api/client.js 的拦截器挂在 error.status 上（它会先把
      // 原始 axios 错误吃掉，所以这里读不到 err.response）。
      const status = err?.status
      if (status === 401) {
        // 拦截器已经负责跳登录页，这里只把本地状态清干净，
        // 不然守卫会拿着一个假登录态把人放进去
        token.value = ''
        setToken('')
        user.value = null
      }
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

  return { user, token, loading, ready, isLoggedIn, login, register, updateProfile, fetchMe, logout }
})
