/* 学习域接口 —— 对应后端 `app/routers/learning.py`。
 *
 * 这里是整个 EduPath 最核心的一层：标记掌握度、算今日队列、看统计。
 * 现在跑的是 **SM-2 间隔重复 + 三档标记**，后续 BKT 掌握度会接进
 * `due_list` 的排序里 —— 前端不用改调用方式，只是队列顺序变了。
 *
 * level 的取值全项目统一，别在别处另立一套：
 *   0 = 未标记   1 = 不会   2 = 模糊   3 = 会
 *
 * ★ 本文件**只管发请求**：label / color 这些展示用的东西已经搬到
 * `@/config/theme`（levelLabel / levelColor）。从前这里有一份 LEVELS
 * 带着自己的颜色，与 theme.js 的 LEVEL_COLOR 冲突，同一档在两个页面
 * 是两种颜色；而且组件为了拿 label 直接 import 本文件，顺带破了
 * 「views 只调 store」那条铁律。
 */
import client from './client'

/** 全部学习进度。key 是卡片 id。
 * @returns {Promise<{ok:boolean, progress:Object<string,Object>}>}
 */
export function getProgress() {
  return client.get('/progress')
}

/** 标记某张卡的掌握程度。后端立刻按 SM-2 算出下次复习时间。
 * @param {string} cid   卡片 id
 * @param {number} level 1 不会 / 2 模糊 / 3 会
 * @returns {Promise<{ok:boolean, progress:Object}>}
 */
export function markCard(cid, level) {
  return client.put('/progress/' + encodeURIComponent(cid), { level })
}

/** 重置某张卡的进度（回到未标记）。
 * @param {string} cid
 * @returns {Promise<{ok:boolean}>}
 */
export function resetCard(cid) {
  return client.delete('/progress/' + encodeURIComponent(cid))
}

/** 今日复习队列。
 *
 * 排序规则在后端 `db.due_list()`：不会(1) → 模糊(2) → 未标记(0) → 会(3)，
 * 同档内按到期时间。**换存储后端不能改变这个顺序**（check.js 有对照),
 * 前端别再排一次，否则用户会看到跟 API 不一致的队列。
 *
 * @param {Object} [params]
 * @param {number} [params.limit] 最多几条
 * @param {string} [params.domain] 只看某领域
 * @param {string} [params.dirs]   学习方向 id，逗号分隔（data/directions.js）。
 *                                 后端**先按方向过滤全量到期卡，再截断 limit** ——
 *                                 方向卡不会被排在后面的基本卡挤出队列。
 * @param {string} [params.all]   '1' 时忽略到期时间，返回全部
 * @param {string} [params.pick]  '1' 时只回今日自选清单里的卡（清单空回空
 *                                 队列，不退化成普通队列；dirs/all 会让位于清单）
 * @returns {Promise<{ok:boolean, today:string, total:number, queue:Array<Object>}>}
 */
export function getDue(params) {
  return client.get('/review/due', { params })
}

/** 今日自选复习清单。
 *
 * 一天 311 张到期卡刷不完 —— 清单是用户自己点名「今天就刷这些」的那几十张。
 * 跨天自动作废（后端按存的日期判），所以永远是今天的口径。
 *
 * @returns {Promise<{ok:boolean, today:string, ids:string[], total:number}>}
 */
export function getPick() {
  return client.get('/review/pick')
}

/** 覆盖写今日清单（后端过滤不存在的 id、去重、截 100）。
 * @param {string[]} ids 卡片 id
 * @returns {Promise<{ok:boolean, ids:string[], total:number}>} 服务端回存后的那份
 */
export function putPick(ids) {
  return client.put('/review/pick', { ids })
}

/** 学习统计概览。
 * @returns {Promise<{ok:boolean, stats:Object}>}
 * stats 里除了计数，还有 domains / byCategory / bySubject 三个分布，大屏直接画。
 */
export function getStats() {
  return client.get('/stats')
}

/** BKT 掌握度汇总（brief=1：只回 summary + params，不回每张卡明细）。
 *
 * brief 是为驾驶舱加的：那里只画一条分布条，拉 400 张卡的 p 纯属浪费。
 * 需要逐卡掌握度（比如按 p 排选题）时不带 brief。
 * @returns {Promise<{ok:boolean, params:Object, summary:Object}>}
 */
export function getMasteryBrief() {
  return client.get('/mastery?brief=1')
}
