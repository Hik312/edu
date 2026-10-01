/* 学习域接口 —— 对应后端 `app/routers/learning.py`。
 *
 * 这里是整个 EduPath 最核心的一层：标记掌握度、算今日队列、看统计。
 * 现在跑的是 **SM-2 间隔重复 + 三档标记**，后续 BKT 掌握度会接进
 * `due_list` 的排序里 —— 前端不用改调用方式，只是队列顺序变了。
 *
 * level 的取值全项目统一，别在别处另立一套：
 *   0 = 未标记   1 = 不会   2 = 模糊   3 = 会
 */
import client from './client'

/** 三档标记的含义与各档颜色。放这里是想让「0/1/2/3 到底哪个是不会」
 * 有个唯一答案 —— 散落在各页面里迟早会写反。
 */
export const LEVELS = {
  0: { label: '未标记', color: '#7a8699', rank: 2 },
  1: { label: '不会', color: '#ff6b81', rank: 0 },
  2: { label: '模糊', color: '#ffb454', rank: 1 },
  3: { label: '会', color: '#4fe0b0', rank: 3 }
}

/** 取 level 的展示文案，容错非数字输入。 */
export function levelLabel(level) {
  const hit = LEVELS[level]
  return hit ? hit.label : '未标记'
}

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
 * @returns {Promise<{ok:boolean, today:string, total:number, queue:Array<Object>}>}
 */
export function getDue(params) {
  return client.get('/review/due', { params })
}

/** 学习统计概览。
 * @returns {Promise<{ok:boolean, stats:Object}>}
 * stats 里除了计数，还有 domains / byCategory / bySubject 三个分布，大屏直接画。
 */
export function getStats() {
  return client.get('/stats')
}
