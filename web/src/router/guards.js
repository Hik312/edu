/* 登录守卫。
 *
 * 必须 await fetchMe() 之后才判断登录态：刷新页面时 token 在 localStorage、
 * user 还是空，直接判断会把已登录的人踢到登录页（这个 bug 很难复现也很难查）。
 */
import { useAuthStore } from '@/stores/auth'

export function setupGuards(router) {
  router.beforeEach(async to => {
    const auth = useAuthStore()

    // 首次导航（含刷新）先向后端确认一次身份，拿到 user 再放行
    if (!auth.ready) await auth.fetchMe()

    if (to.meta.public) {
      // 已登录还去登录页，直接送回首页
      if (auth.isLoggedIn && to.name === 'login') {
        return { path: '/dashboard' }
      }
      return true
    }

    if (!auth.isLoggedIn) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    return true
  })
}
