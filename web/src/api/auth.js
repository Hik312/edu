/* 认证域接口。后端路由前缀 /api/auth，这里只写后半段。
 *
 * 登录方式目前只有一种（账号密码），但这一层不要塞任何跟「端」有关的字段 ——
 * 将来接别的登录方式（微信 openid 等）时，换的应该是后端换 token 的那一步，
 * 不是这里。
 */
import client from './client'

/** 登录。
 * @param {string} username
 * @param {string} password
 * @returns {Promise<{ok:boolean, token:string, user:Object}>}
 */
export function login(username, password) {
  return client.post('/auth/login', { username, password })
}

/** 注册。第一个注册成功的账号会自动成为 admin，
 *  这是为了让单机自用场景下不用手工改库就有管理权限（见后端 routers/auth.py）。
 * @param {Object} payload {username, password, displayName?}
 * @returns {Promise<{ok:boolean, token:string, user:Object}>}
 */
export function register(payload) {
  return client.post('/auth/register', payload)
}

/** 当前登录用户。
 * @returns {Promise<{ok:boolean, user:Object}>}
 */
export function me() {
  return client.get('/auth/me')
}

/** 用户列表。**只有管理员能调** —— 后端会校验 role，非管理员拿 403。
 *
 * 页面层也要挡一道：普通学习者看到一堆自己点不开的入口只会觉得产品糙。
 * @returns {Promise<{ok:boolean, total:number, users:Array<Object>}>}
 * 每项含 id / username / displayName / role / openid / createdAt（**不含 password_hash**）
 */
export function listUsers() {
  return client.get('/auth/users')
}
