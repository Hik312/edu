/* AI 精读接口 —— 对应后端 `app/routers/ai.py`。
 *
 * 两条硬规矩，来自踩过的坑，前端必须照做：
 *
 * 1. **`/status` 返回 ok:false 是正常状态，不是故障**。AI 是可选增强，
 *    关掉以后背卡、复习、导入分章照常工作。页面要显示「未启用」而不是报错红条。
 * 2. **精读必须逐章调，不要一次传 indexes 批量**。批量会把 A 章的内容安到 B 章
 *    （实测多次），慢一点是不可谈判的成本。
 */
import client from './client'

/** AI 可用性。
 * @returns {Promise<{ok:boolean, provider:string, model:string, models:string[], msg:string}>}
 * ok 为 false 时 msg 是给人看的原因（没配 Key / Ollama 没起）。
 */
export function getLlmStatus() {
  return client.get('/llm/status')
}

/** 精读：给 docId+index 是按文档章节读，只给 title+text 是直接读一段文字。
 * @param {Object} body 见 `app/schemas.py:EnrichIn`
 * @returns {Promise<{ok:boolean, ai:Object}>}
 * timeout 单独放宽到 3 分钟：本地 8B 精读一章实测 20~60 秒，
 * 全局的 20 秒会在模型慢一点时把正常请求掐成「timeout of 20000ms exceeded」。
 */
export function enrich(body) {
  return client.post('/llm/enrich', body, { timeout: 180000 })
}

/** 把某章的精读结果变成草稿卡。
 * @param {string} docId
 * @param {number} index 章节下标
 * @returns {Promise<{ok:boolean, draft:Object}>}
 */
export function toCard(docId, index) {
  return client.post('/llm/to-card', { docId, index })
}
