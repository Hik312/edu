/* 导入域接口 —— 对应后端 `app/routers/imports.py`。
 *
 * 流程是单向的：**粘贴文本 → 草稿 →（补齐字段）→ 发布成正式卡**。
 * 草稿单独一张表，不进正式卡列表，所以页面上「草稿」和「卡片」是两个区域，
 * 别指望划线 ⟲ 发布后草稿还留着 —— 发布了就没了，少 deletes 一次只 acknowledging 一步。
 */
import client from './client'

/** 粘贴文本切成草稿卡。
 * @param {Object} body 见 `app/schemas.py:ImportTextIn`
 * @param {string} body.text   原文
 * @param {boolean} [body.useLLM] true 时先走大模型抽取，失败自动退回本地规则
 * @returns {Promise<{ok:boolean, drafts:Array<Object>}>}
 */
export function importText(body) {
  return client.post('/import', body)
}

/** 草稿列表。
 * @returns {Promise<{ok:boolean, drafts:Array<Object>}>}
 */
export function listDrafts() {
  return client.get('/drafts')
}

/** 补齐草稿字段（主要是 scene 至少 2 条，不满足发布不了）。
 * @param {string} did  草稿 id
 * @param {Object} body 见 `app/schemas.py:DraftPatch`
 * @returns {Promise<{ok:boolean, draft:Object}>}
 */
export function patchDraft(did, body) {
  return client.put('/drafts/' + encodeURIComponent(did), body)
}

/** 发布草稿 → 正式卡。发布成功后端会删掉这条草稿。
 * @param {string} did 草稿 id
 * @returns {Promise<{ok:boolean, card:Object}>}
 */
export function publishDraft(did) {
  return client.post('/drafts/publish', { id: did })
}

/** 丢弃单条草稿。
 * @param {string} did
 * @returns {Promise<{ok:boolean}>}
 */
export function dropDraft(did) {
  return client.delete('/drafts/' + encodeURIComponent(did))
}

/** 清空全部草稿。
 * @returns {Promise<{ok:boolean}>}
 */
export function clearDrafts() {
  return client.delete('/drafts')
}

/** ===== 题库导入（2026-11-15）：确定性解析，不走 AI =====
 *  两步走：preview 解析预览 → 勾选后 commit 入草稿。
 *  资料清单与格式适配建议见 docs/资料来源.md。
 */

/** 解析预览（不落库）。
 * @param {Object} body 见 `app/schemas.py:ImportQaIn`
 * @param {string} body.text    题库原文（多文件在客户端拼接后传一份）
 * @param {string} [body.fmt]   'md-qa'（默认）| 'anki-txt' | 'obsidian-sr'
 * @param {number} [body.qLevel] md-qa：第几级标题算题面，默认 3
 * @param {string} [body.deck]  卡片组名
 * @param {string} [body.source] 资料来源（溯源/署名）
 * @returns {Promise<{ok:boolean, fmt:string, cards:Array, skipped:Array, count:number}>}
 */
export function importQaPreview(body) {
  return client.post('/import/qa', body)
}

/** 勾选的卡批量存为草稿。服务端**重新解析**再按 id 过滤 —— 只信 id。
 * @param {Object} body 同 preview，外加 body.ids 勾选的卡 id 列表
 * @returns {Promise<{ok:boolean, count:number, missing:number}>}
 */
export function importQaCommit(body) {
  return client.post('/import/qa/commit', body)
}
