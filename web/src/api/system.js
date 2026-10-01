/* 结构类只读接口：健康、存储状态、统计、分类树、知识框架、知识图谱。
 *
 * 这一组全是「读字典表」性质的数据，变更频率极低，但被用到的地方很多
 * （导航、筛选、图谱），所以单独放一个文件。
 */
import client from './client'

/** 健康探测。含 framework / store / cards 等运行时信息。
 * @returns {Promise<Object>} 例：{ok, framework, store, cards, today, llm}
 */
export function health() {
  return client.get('/health')
}

/** 存储后端状态。用来回答「我现在到底写进了哪里」。
 * @returns {Promise<{ok:boolean, storage:Object}>}
 * storage 关键字段：store 实际后端、want 期望后端、degraded 降级原因（正常为 null）
 */
export function storage() {
  return client.get('/storage')
}

/** 学习统计概览。
 * @returns {Promise<{ok:boolean, stats:Object}>}
 */
export function stats() {
  return client.get('/stats')
}

/** 分类树。整个会话内基本不变，页面自己缓存即可。
 * @returns {Promise<{ok:boolean, catalog:Array<Object>}>}
 */
export function catalog() {
  return client.get('/catalog')
}

/** 知识框架（MOC 树）：比 catalog 深一层，铺到 topicPath。
 * @returns {Promise<{ok:boolean, tree:Array<Object>}>}
 */
export function outline() {
  return client.get('/outline')
}

/** 知识图谱。节点是卡片，边来自 related 的 prereq / extends / compare。
 * @param {Object} [params]
 * @param {string} [params.scope] 下钻层级，见后端 system.py
 * @returns {Promise<{ok:boolean, nodes:Array, edges:Array}>}
 */
export function graph(params) {
  return client.get('/graph', { params })
}

/** 某张卡的直接邻居。图谱页面点节点时用，不用每次拉全图。
 * @param {string} cid 卡片 id
 * @returns {Promise<{ok:boolean, nodes:Array, edges:Array}>}
 */
export function neighbors(cid) {
  return client.get('/graph/neighbors/' + encodeURIComponent(cid))
}

/** 岗位定义（data/roles.js 预置的几个 + 各自的 keywords/subjects）。
 *  是**内容**不是状态：改岗位清单改的是 data/roles.js。
 * @returns {Promise<{ok:boolean, roles:Array<{id,name,desc,subjects:Array<string>}>}>}
 */
export function getRoles() {
  return client.get('/roles')
}

/** 学习方向预设（data/directions.js）+ 每个方向能推出多少张卡。
 *  是**内容**不是状态：加方向改 data/directions.js，选了哪个方向存档案。
 * @returns {Promise<{ok:boolean, directions:Array<{id,name,desc,keywords:Array<string>,count:number}>}>}
 */
export function getDirections() {
  return client.get('/directions')
}

/** 按岗位（或自选科目）算知识地图：每个技能组的卡片、掌握情况与缺口。
 * @param {Object} params
 * @param {string} [params.role]     预置岗位 id，如 'java-backend'
 * @param {string} [params.subjects] 自定义科目，逗号分隔，如 'python,ai'
 * @returns {Promise<{ok:boolean, plan:Object}>}
 *  plan.summary：{keywords, covered, percent, cards, mastered}
 *  plan.skills[]：{subject, name, weight, count, learned, mastered,
 *                  cards[{id,title,oneLine,level}], covered[string], missing[string]}
 *  缺口按**技能词**算（不是按科目）—— 科目有卡 ≠ 覆盖了岗位要的那条考点。
 */
export function getPlan(params) {
  return client.get('/plan', { params })
}
