/* 卡片域接口 —— 对应后端 `app/routers/cards.py` 与 `app/routers/system.py`。
 *
 * 本文件只做三件事：拼参数、发请求、把响应原样返回。**不在这里加工数据**
 * （比如把 cards 数组按科目分组），那属于 store 或 view 的职责。
 * 一旦这里开始加工，同一个接口在不同页面上就会拿到不同形状的数据。
 *
 * 所有响应体都包了一层 `{ok: true, ...}`，字段形状以本文档注释为准。
 */
import client from './client'

/** 关联卡的关系类型。kind 只许这三种（后端 importer.validate 也按这个校），
 *  中文名集中放这里 —— 散在各页面写，迟早出现「前置」和「先修」两个说法。 */
export const RELATIONS = {
  prereq: { label: '前置', hint: '看不懂这张，先去看它' },
  extends: { label: '延伸', hint: '这张懂了，接着看它' },
  compare: { label: '对比', hint: '跟它成对出现，容易混' }
}

/** 取关系类型的中文说明，遇到没见过的 kind 兜底显示原值而不是空白。 */
export function relationOf(kind) {
  return RELATIONS[kind] || { label: kind || '关联', hint: '' }
}

/** 卡片列表 / 搜索。
 * @param {Object} [params]
 * @param {string} [params.category] 一级分类 id
 * @param {string} [params.subject]  二级科目 id
 * @param {string} [params.domain]   领域名，如「求职·AI工程」
 * @param {string} [params.q]        关键词，空格分隔表示全部命中
 * @param {string} [params.brief]    '1' 时只回轻字段，列表页用
 * @returns {Promise<{ok:boolean, total:number, cards:Array<Object>}>}
 */
export function listCards(params) {
  return client.get('/cards', { params })
}

/** 单张卡详情（含 mechanism / diagram / interviewQ 等全部字段）。
 * @param {string} cid 卡片 id
 * @returns {Promise<{ok:boolean, card:Object}>}
 */
export function getCard(cid) {
  return client.get('/cards/' + encodeURIComponent(cid))
}

/** 新建自定义卡。字段见 `app/schemas.py:CardIn`；校验失败 400。
 * @param {Object} body 卡片内容，scene 至少 2 条
 * @returns {Promise<{ok:boolean, card:Object}>}
 */
export function createCard(body) {
  return client.post('/cards', body)
}

/** 修改自定义卡（内置卡改不动，会返回错误）。
 * @param {string} cid
 * @param {Object} body 要改的字段
 * @returns {Promise<{ok:boolean, card:Object}>}
 */
export function updateCard(cid, body) {
  return client.put('/cards/' + encodeURIComponent(cid), body)
}

/** 删除自定义卡。
 * @param {string} cid
 * @returns {Promise<{ok:boolean}>}
 */
export function removeCard(cid) {
  return client.delete('/cards/' + encodeURIComponent(cid))
}

/** 分类树：category → subject 两级，含每张 Art 的数量。导航菜单靠它渲染。
 * @returns {Promise<{ok:boolean, catalog:Array<{id,name,desc,subjects:Array}>}>}
 */
export function getCatalog() {
  return client.get('/catalog')
}

/** 知识框架（MOC 树）：category → subject → topicPath 各层，叶子节点是卡。
 * @returns {Promise<{ok:boolean, tree:Array<Object>}>}
 */
export function getOutline() {
  return client.get('/outline')
}

/* getGraph / getNeighbors 2026-10-03 删。
 *
 * 两个问题叠在一起，留着比删掉更危险：
 *   1. **零调用**——图谱页 import 的是 api/system.js 的 graph()/neighbors()。
 *      这两个是 2026-09 早期加的，从没被接过。
 *   2. **字段名是错的**——jsdoc 写 `{nodes, links}`，后端实际返回
 *      `{nodes, edges}`。哪天有人照着它 import，edges 会是 undefined，
 *      图渲染成一片孤点，而且没有任何报错提示 —— 契约不一致最阴的就是这个。
 * 图谱相关的接口统一去 api/system.js。 */
