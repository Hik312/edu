/* 请求层：全项目**唯一**碰 axios 的地方。
 *
 * 分层铁律：view → store → api/ → client.js。
 * 页面里不许出现 fetch/axios，store 里不许拼 URL —— 后端接口改了只改 api/ 下的文件。
 *
 * 两条约定和后端对齐（别改，改了前端所有错误分支都会失效）：
 *   1. 错误响应体是 {ok:false, msg}，msg 是给人看的中文，直接弹给用户
 *   2. 参数错误返回 400（不是 FastAPI 默认的 422），前端按 400 判断
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const TOKEN_KEY = 'edupath.token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t)
  else localStorage.removeItem(TOKEN_KEY)
}

const client = axios.create({
  baseURL: '/api',
  timeout: 20000
})

client.interceptors.request.use(cfg => {
  const t = getToken()
  if (t) cfg.headers.Authorization = 'Bearer ' + t
  return cfg
})

// 401 只跳一次：一个页面同时发五个请求时，五个都 401，
// 不加这个开关会弹五次提示、跳五次登录页。
let redirecting = false

client.interceptors.response.use(
  res => res.data,
  err => {
    const status = err.response && err.response.status
    const body = err.response && err.response.data
    const msg = (body && body.msg) || err.message || '请求失败'

    if (status === 401) {
      setToken('')
      if (!redirecting) {
        redirecting = true
        ElMessage.warning('登录已过期，请重新登录')
        // 用 location 而不是 router.push：api 层 import router 会和
        // router → guards → store → api 形成循环依赖，运行时报 undefined
        const back = encodeURIComponent(location.pathname + location.search)
        location.replace('/login?redirect=' + back)
        setTimeout(() => {
          redirecting = false
        }, 1500)
      }
      return Promise.reject(new Error(msg))
    }

    // 其它错误在这里统一弹一次，业务代码只管 catch 后回滚状态
    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  }
)

export default client
