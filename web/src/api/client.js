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

// 部署到静态托管（如 Qoder Sites）时后端不在同源：构建期用 VITE_API_BASE
// 指向公网后端（例 https://api.example.com/api）；本地开发保持同源 /api。
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

/** 拼后端的绝对地址 —— 只给**不吃 axios baseURL** 的那几类调用用：
 *  原生 `fetch`（SSE 流式问答、翻译跑批）、`<img src>`、`<iframe src>`。
 *
 * ★ 这些调用以前直接写相对 `/api/...`，于是同一份构建放到 Sites 域名上
 *   全数 404（静态托管上根本没有 /api 这条路），放到同源域名上却好好的 ——
 *   线上症状就是知识库「打不开这份 PDF / 原件读取失败（HTTP 404）」。
 *   拼接规则和 axios 的 combineURLs 一致（base 去尾斜杠 + path 去头斜杠），
 *   所以 `apiUrl('/cards')` 和 `client.get('/cards')` 得到同一个地址。
 *
 * @param {string} path 后端路径，以 / 开头，**不要再带 /api**（base 里已经有了）
 */
export function apiUrl(path) {
  return API_BASE.replace(/\/+$/, '') + '/' + String(path).replace(/^\/+/, '')
}

const client = axios.create({
  baseURL: API_BASE,
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
      // ★ 把状态码挂到错误对象上再抛。
      // 调用方（stores/auth.js 的 fetchMe）需要区分「401 掉线」和
      // 「后端重启 / 网络抖动」—— 而它只能拿到这里 reject 出去的东西。
      // 从前一律 `new Error(msg)`，状态码信息在这一层就丢了，store 只好
      // 「一有异常就清 token」，于是后端重启一次就把所有人踢回登录页。
      // 挂一个字段比让每个调用方自己读 axios 原始错误干净。
      const e401 = new Error(msg)
      e401.status = 401
      return Promise.reject(e401)
    }

    // 其它错误：**不**在这里弹提示，只把状态码和 msg 挂到错误对象上 reject。
    // 调用方自己决定怎么展示（页面级 catch 弹 ElMessage，或写进行内错误）。
    // 之所以不全局弹：很多调用方 catch 后会弹自己的文案（如卡片加载失败），
    // 全局再弹一次就重复了；而且空 catch 的调用方（如登录页）会各自负责。
    // ⚠️ 别被老注释骗了——这层曾经写着「统一弹一次」但其实没弹，导致登录 400 静默。
    const e = new Error(msg)
    e.status = status || 0
    return Promise.reject(e)
  }
)

export default client
