/* 文档域接口 —— 对应后端 `app/routers/docs.py`。
 *
 * 一份文档进来先由 `core/importer.parse_document()` 自动分章，
 * 再可以选择性地逐章调 AI 精读。docs[].aiDone / aiTotal 就是精读进度。
 */
import client from './client'

/** 文档列表（轻字段，不含章节正文）。
 * @returns {Promise<{ok:boolean, total:number, docs:Array<Object>}>}
 * 每项含 id / title / source / createdAt / stats{chapters,chars} / aiDone / aiTotal
 */
export function listDocs() {
  return client.get('/docs')
}

/** 文档详情：含全部章节与每章的精读结果。
 * @param {string} did 文档 id
 * @returns {Promise<{ok:boolean, doc:Object}>}
 */
export function getDoc(did) {
  return client.get('/docs/' + encodeURIComponent(did))
}

/** 导入整份文档：md / txt 可以给正文，PDF / Word(.docx) 走 dataB64。
 * @param {Object} body 见 `app/schemas.py:DocImportIn`
 * @returns {Promise<{ok:boolean, doc:Object}>}
 * timeout 放宽到 60 秒：base64 后的 PDF/Word 有好几 MB，
 * 大文档服务端解码 + 分章也要时间，全局 20 秒不够。
 */
export function importDoc(body) {
  return client.post('/import/doc', body, { timeout: 60000 })
}

/** 删除文档（连同它下面的草稿一并清掉）。
 * @param {string} did
 * @returns {Promise<{ok:boolean}>}
 */
export function removeDoc(did) {
  return client.delete('/docs/' + encodeURIComponent(did))
}

/** 重命名文档 = 重命名它的卡片组：级联改已发布卡和草稿里的 deck。
 * @param {string} did 文档 id（即 deckId）
 * @param {string} title 新组名（1-60 字）
 * @returns {Promise<{ok:boolean, title:string, cards:number, drafts:number}>}
 */
export function renameDoc(did, title) {
  return client.put('/docs/' + encodeURIComponent(did), { title })
}
