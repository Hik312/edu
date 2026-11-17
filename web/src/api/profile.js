/* 个人中心接口 —— 对应后端 `app/routers/profile.py`（待实现）。
 * 目前前端先按约定字段定好接口，后端实现时对齐即可。 */
import client from './client'

/** 获取个人中心概览数据。
 * @returns {Promise<{ok:boolean, data:Object}>}
 * data: {
 *   totalReviews: number,        // 累计复习次数
 *   totalCards: number,          // 掌握卡片数
 *   weakCards: number,           // 薄弱卡片数
 *   avgMastery: number,          // 平均掌握度 0-1
 *   studyDays: number,           // 学习天数
 *   totalMinutes: number,        // 总学习分钟数
 *   streakDays: number,          // 连续学习天数
 *   weeklyReport: Object,        // 本周复盘数据
 *   monthlyReport: Object        // 本月复盘数据
 * } */
export function getProfileOverview() {
  return client.get('/profile/overview')
}

/** 获取错题本/复盘数据。
 * @param {Object} [params]
 * @param {string} [params.period] 'week' | 'month' | 'all'
 * @param {string} [params.start]  开始日期 YYYY-MM-DD
 * @param {string} [params.end]    结束日期 YYYY-MM-DD
 * @returns {Promise<{ok:boolean, data:Object}>}
 * data: {
 *   period: string,
 *   totalReviews: number,
 *   weakCards: Array<{cardId, title, domain, level, count, lastReviewed}>,
 *   fuzzyCards: Array<{cardId, title, domain, level, count, lastReviewed}>,
 *   reviewSessions: Array<{date, count, weakCount, fuzzyCount, duration}>
 * } */
export function getMistakeBook(params) {
  return client.get('/profile/mistakes', { params })
}

/** 获取遗忘曲线数据（单张卡或整体）。
 * @param {Object} [params]
 * @param {string} [params.cardId]  指定卡片，不传返回整体聚合
 * @param {number} [params.days]    回溯天数，默认 30
 * @returns {Promise<{ok:boolean, data:Object}>}
 * data: {
 *   cardId?: string,
 *   points: Array<{date, p, nextAt, level, reviews}>,
 *   // 整体聚合时额外返回：
 *   aggregate?: Array<{date, avgP, weakCount, midCount, strongCount}>
 * } */
export function getForgettingCurve(params) {
  return client.get('/profile/forgetting-curve', { params })
}

/** 获取学习时长统计。
 * @param {Object} [params]
 * @param {string} [params.period] 'week' | 'month' | 'year' | 'all'
 * @param {string} [params.start]
 * @param {string} [params.end]
 * @returns {Promise<{ok:boolean, data:Object}>}
 * data: {
 *   period: string,
 *   totalMinutes: number,
 *   dailyMinutes: Array<{date, minutes, sessions}>,
 *   heatmap: Array<{date, value}>,
 *   byDomain: Array<{domain, minutes, percentage}>,
 *   byCard: Array<{cardId, title, minutes, reviews}>
 * } */
export function getStudyTime(params) {
  return client.get('/profile/study-time', { params })
}

/** 上报单次复习会话时长（前端埋点调用）。
 * @param {Object} payload
 * @param {string} payload.cardId
 * @param {number} payload.durationSeconds
 * @param {number} payload.level 标记后的等级
 * @param {string} [payload.sessionId] 会话 ID（可选，用于去重）
 * @returns {Promise<{ok:boolean}>} */
export function reportReviewSession(payload) {
  return client.post('/profile/review-session', payload)
}

/** 批量上报复习会话（页面关闭/离开时批量发送）。
 * @param {Array<Object>} sessions
 * @returns {Promise<{ok:boolean, saved:number}>} */
export function batchReportReviewSessions(sessions) {
  return client.post('/profile/review-sessions/batch', { sessions })
}

/** True Retention（Anki 口径记忆保持率，2026-11-15 加）。
 * young（间隔 <21 天）/ mature（≥21 天）分开算「记得率」，四档时间窗。
 * @returns {Promise<{ok:boolean, data:Object}>}
 * data: { [today|month|year|all]: {
 *   young:  {correct, total, rate},   // rate 为 null 表示这个窗口还没有样本
 *   mature: {correct, total, rate},
 *   total:  {correct, total, rate} } } */
export function getTrueRetention() {
  return client.get('/profile/true-retention')
}

/** 复习热力图：一年里「每天刷了几张」（学习时长热力图量的是分钟，互补）。
 * @param {Object} [params]
 * @param {number} [params.year] 不传 = 今年
 * @returns {Promise<{ok:boolean, data:Object}>}
 * data: { year:number, days: Array<{date,count,weak,good}>,
 *         total:number, activeDays:number,
 *         streak: {current:number, max:number} } */
export function getReviewHeatmap(params) {
  return client.get('/profile/review-heatmap', { params })
}
