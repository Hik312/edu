/* 笔记域接口 —— 对应后端 `app/routers/notes.py`。
 *
 * 笔记有两种形态，后端是一张表，靠 `cardId` 区分：
 *   - 独立笔记：cardId 为空，就是普通笔记本
 *   - 卡片理解：挂在某张卡下面，显示在卡片详情底部
 */
import client from './client'

/** 笔记列表。
 * @param {Object} [params]
 * @param {string} [params.category] 一级分类
 * @param {string} [params.subject]  二级科目
 * @param {string} [params.cardId]   只看某张卡下面的理解
 * @param {string} [params.q]        搜标题 / 正文 / 标签
 * @returns {Promise<{ok:boolean, total:number, notes:Array<Object>}>}
 */
export function listNotes(params) {
  return client.get('/notes', { params })
}

/** 单条笔记。
 * @param {string} nid
 * @returns {Promise<{ok:boolean, note:Object}>}
 */
export function getNote(nid) {
  return client.get('/notes/' + encodeURIComponent(nid))
}

/** 新建或更新笔记。**带 id 就是更新，不带就是新建**（后端靠 id 判断）。
 * @param {Object} body 见 `app/schemas.py:NoteIn`
 * @returns {Promise<{ok:boolean, note:Object}>}
 */
export function saveNote(body) {
  return client.post('/notes', body)
}

/** 删除笔记。
 * @param {string} nid
 * @returns {Promise<{ok:boolean}>}
 */
export function removeNote(nid) {
  return client.delete('/notes/' + encodeURIComponent(nid))
}
