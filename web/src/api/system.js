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

/** 当前间隔调度算法 + 可切换项。
 *
 * `ALGO` 换掉之后界面上完全看不出来（同一批卡、同一套队列），
 * 但背后的间隔模型已经变了。驾驶舱用它显示一个徽标，
 * 让「现在是谁在算我的复习间隔」这个问题有个答案。
 * @returns {Promise<{ok:boolean, current:Object, options:Array<Object>}>}
 */
export function getAlgo() {
  return client.get('/algo')
}

/** 知识框架（MOC 树）：比 catalog 深一层，铺到 topicPath。
 * @returns {Promise<{ok:boolean, tree:Array<Object>}>}
 */
export function outline() {
  return client.get('/outline')
}

/** 知识图谱。节点是卡片，边来自 related 的 prereq / extends / compare。
 * @param {Object} [params]
 * @param {string} [params.category] 一级分类，如 'work'
 * @param {string} [params.subject]  科目，如 'java'。传了它就忽略 category
 * @returns {Promise<{ok:boolean, graph:{nodes:Array,edges:Array}}>}
 */
export function graph(params) {
  return client.get('/graph', { params })
}

/** 某张卡的直接邻居。图谱页面点节点时用，不用每次拉全图。
 * @param {string} cid 卡片 id
 * @param {number} [depth] 1~3
 * @returns {Promise<{ok:boolean, center:string, nodes:Array, edges:Array}>}
 */
/** 某节点的邻居子图。
 *
 *  ★ 用 **query 传 cid**，不要拼进路径。节点 id 形如 `sub:work/ai`、
 *    `topic:ai/Agent/框架` —— 含 `:` 和 `/`。拼进路径会有两个致命问题：
 *    ① 路径参数不跨 `/` → 路由匹配不上，请求掉进 SPA 回落；
 *    ② 回落拿 `dist/api/.../sub:work/ai` 当静态文件找 →
 *       Windows 抛 WinError 123，前端收到 500「服务器内部错误」，
 *       真因（URL 少编码一位）被彻底掩盖。
 *
 * @param {string} cid 节点 id（卡或章节都行，原样传）
 * @param {number} [depth=1] 1~3 跳
 * @param {boolean} [untilCards=false] 展开到见到卡为止。
 *   **点章节节点（subject/topic/category）时必须开**：层级是
 *   subject → topic → … → card，卡挂的层数不固定，按跳数停会只看见章节。
 * @returns {Promise<{ok:boolean, center:string, nodes:Array, edges:Array}>}
 */
export function neighbors(cid, depth, untilCards) {
  return client.get('/graph/neighbors', { params: { cid, depth, untilCards } })
}

/** 图结构洞察：中心性 + 社区 + 体检。比 /graph 重（要跑迭代），别频繁调。
 *
 * @param {Object} [params]
 * @param {string} [params.category]
 * @param {string} [params.subject]
 * @returns {Promise<{ok:boolean, pagerank:Array, betweenness:Array,
 *                    communities:Array, coverage:Object}>}
 *  pagerank[]    : {id,label,type,value,degree,oneLine} 全局权威知识点
 *  betweenness[] : {id,label,value,...} 必经之路（关卡）
 *  communities[] : {size,members[]} Louvain 自动分块
 *  coverage      : {nodes,cards,edges,components,largest,coverage,
 *                   orphanCards,orphanRate,orphanList} 连通性体检
 */
export function graphInsight(params) {
  return client.get('/graph/insight', { params })
}

/** 社区摘要：AI 给每个 louvain 社区写一段「这是一块什么知识」。
 * @param {Object} [params]
 * @param {string} [params.category]
 * @param {string} [params.subject]
 * @param {string} [params.refresh] '=1' 强制重新生成（跑本地模型，几十秒）
 * @returns {Promise<{ok:boolean, available:boolean, cached?:boolean,
 *                    items:Array<{index,size,members,title,desc}>,
 *                    generatedAt?:string, msg?:string}>}
 *  available=false 是**状态不是故障**（AI 未启用/模型没吐对 JSON），
 *  拿 msg 渲一行提示，别当错误弹。
 */
export function graphCommunitySummary(params) {
  return client.get('/graph/community-summary', { params, timeout: 240000 })
}

/** 图推荐：以「我不会的卡」为种子的个性化 PageRank，每条带推荐理由。
 * @param {Object} [params]
 * @param {number} [params.limit] 1~30，默认 8
 * @param {string} [params.category]
 * @param {string} [params.subject]
 * @returns {Promise<{ok:boolean, items:Array, seeds:Array, algo:string,
 *                    seedCount:number, weakCount:number, note?:string}>}
 *  items[] : {id,label,oneLine,score,level,because[]} because 是种子卡 id 列表
 *  allDone : true 表示全部掌握，没东西可推（不是出错）
 */
export function graphRecommend(params) {
  return client.get('/graph/recommend', { params })
}

/** 两卡之间的最短学习路径（只沿 prereq）。
 * @param {string} src 起点卡 id
 * @param {string} dst 终点卡 id
 * @returns {Promise<{found:boolean, nodes:Array, edges:Array, hops:number, reason:string}>}
 *  found=false 是**正常答案**（两卡之间没有依赖链），不是错误，别弹错误提示
 */
export function graphPath(src, dst) {
  return client.get('/graph/path', { params: { src, dst } })
}

/** 批量查卡在图里的排名。给卡片详情页用。
 * @param {string|string[]} ids 卡片 id，数组会自动 join
 * @returns {Promise<{ok:boolean, ranks:Object, missing:string[]}>}
 *  missing 是查不到的 id —— 通常意味着传错了，静默吞掉会让「排名不显示」无法定位
 */
export function graphRank(ids) {
  const q = Array.isArray(ids) ? ids.join(',') : ids
  return client.get('/graph/rank', { params: { ids: q } })
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
