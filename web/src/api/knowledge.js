/* 知识库接口 —— 对应后端 `app/routers/web/docs.py` 的 /api/knowledge/* 端点。
 *
 * 知识库复用文档数据（同一份 documents.json），只是入口不同：
 * - 知识库：自己建文件夹组织 + 原文阅读
 * - 文档与精读：转卡工具
 */
import client from './client'
import { getToken } from './client'

/** 知识库文档列表（含分类字段）。
 * @returns {Promise<{ok:boolean, total:number, docs:Array<Object>}>}
 * 每项含 id / title / category / domain / tags / rawFile / stats / createdAt
 */
export function listKnowledge() {
  return client.get('/docs')
}

/** 原始文件预览 URL（带 token，iframe 用）。
 * @param {string} did 文档 id
 * @returns {string} 可直接用于 <iframe src> 的 URL
 */
export function getFileUrl(did) {
  const t = getToken()
  return '/api/knowledge/file/' + encodeURIComponent(did) + (t ? '?t=' + encodeURIComponent(t) : '')
}

/** 导入文档（复用现有导入接口）。
 * @param {Object} body { title?, text?, filename?, dataB64? }
 * @returns {Promise<{ok:boolean, doc:Object}>}
 */
export function importKnowledge(body) {
  return client.post('/import/doc', body, { timeout: 60000 })
}

/** 删除文档。
 * @param {string} did
 * @returns {Promise<{ok:boolean}>}
 */
export function removeKnowledge(did) {
  return client.delete('/docs/' + encodeURIComponent(did))
}

/** 重命名文档。
 * @param {string} did
 * @param {string} title
 * @returns {Promise<{ok:boolean, title:string, cards:number, drafts:number}>}
 */
export function renameKnowledge(did, title) {
  return client.put('/docs/' + encodeURIComponent(did), { title })
}

/** 文档详情（含章节 + 精读结果）。
 * @param {string} did
 * @returns {Promise<{ok:boolean, doc:Object}>}
 */
export function getKnowledgeDoc(did) {
  return client.get('/docs/' + encodeURIComponent(did))
}

/** 重新解析：拿已存的原始文件重跑代码块识别/标题分层，就地修好旧文档。
 *  @param {string} did
 *  @returns {Promise<{ok:boolean, doc:Object}>}
 */
export function reparseDoc(did) {
  return client.post('/docs/' + encodeURIComponent(did) + '/reparse', {}, { timeout: 60000 })
}

/* ==================================================================
 * 文件夹树（PyCharm 式自建层级）
 *
 * ★ 树是**单例状态**，而且每次写操作都由服务端回传整棵 `tree` ——
 *   所以前端**永远不本地改树**，只拿响应里的 tree 覆盖本地。
 *   少这一步就会出现「界面上挪过去了、刷新又弹回来」，因为本地树
 *   和库里真树两份状态不一致（这一页其它地方踩过同类坑）。
 * ================================================================== */

/** 读整棵树。顶层是数组，没有虚拟根（「全部」由前端渲染）。 */
export function getKbTree() {
  return client.get('/kb/tree')
}

/** 新建文件夹。
 *  @param {string} name 文件夹名
 *  @param {string} [parentId] 父文件夹 id，''/undefined = 顶层
 *  @returns {Promise<{ok:boolean, node:Object, tree:Array}>}
 */
export function addKbFolder(name, parentId) {
  return client.post('/kb/tree/folder', { name, parentId: parentId || '' })
}

/** 重命名文件夹（只传 name，不传 collapsed —— 服务端按字段是否为空决定做哪个动作）。 */
export function renameKbFolder(fid, name) {
  return client.put('/kb/tree/folder/' + encodeURIComponent(fid), { name })
}

/** 折叠/展开。**持久化**到库里，重开页面记着。
 *  为什么不放 localStorage：树是多人共用的账号级数据，放本地会出现
 *  「我这边展开着，别人那边也是展开的」的错位。 */
export function collapseKbFolder(fid, collapsed) {
  return client.put('/kb/tree/folder/' + encodeURIComponent(fid), { collapsed: !!collapsed })
}

/** 删文件夹。
 *  @param {string} fid
 *  @param {'doc2root'|'delete'} [mode] doc2root=里面的文档挪回根（默认）；delete=文档留在原地只是脱离树
 *  @returns {Promise<{ok:boolean, moved:Array<string>, tree:Array}>}
 */
export function removeKbFolder(fid, mode = 'doc2root') {
  return client.delete(
    '/kb/tree/folder/' + encodeURIComponent(fid) + '?mode=' + encodeURIComponent(mode)
  )
}

/** 移动文件夹到新父级（'' = 顶层）。防环由服务端在写入前判。 */
export function moveKbFolder(id, parentId) {
  return client.post('/kb/tree/move', { id, parentId: parentId || '' })
}

/** 设置一份文档所属的文件夹。folderIds 为空 = 从所有文件夹移出（回到「未归档」）。 */
export function placeDoc(did, folderIds) {
  return client.post('/docs/' + encodeURIComponent(did) + '/move', {
    docId: did,
    folderIds: folderIds || []
  })
}

/* ==================================================================
 * 就这份文档提问（右下角 AI 问答，SSE 流式）
 *
 * ★ 为什么这里裸用 fetch 而不走 client.post：
 *   client 会把响应体 JSON.parse 掉，而 SSE 是**永远不结束**的流。
 *   解析它 = 界面一直卡在 loading。要逐字显示就必须自己读 ReadableStream。
 *   帧协议与 /api/agent/ask 一致（见 api/agent.js 同名函数），
 *   两处共用一套前端解析心智模型。
 * ================================================================== */

/** @param {string} did 文档 id
 * @param {string} question 问题
 * @param {Array<{question:string,answer:string}>} history 本会话历史
 * @param {{onText?:Function,onSources?:Function,onDone?:Function,onError?:Function}} cb */
export function askDocStream(did, question, history, cb = {}) {
  const token = getToken()
  return fetch('/api/docs/' + encodeURIComponent(did) + '/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {})
    },
    body: JSON.stringify({ question, history: history || [] })
  }).then(res => {
    // ⚠️ 别裸 res.json()：AI 没开时后端返回的是 {detail} 或空体，
    //   解析失败会把真正的原因盖掉，用户只看到一句语法错误。
    if (!res.ok) {
      return res.text().then(t => {
        let msg = ''
        try {
          const j = JSON.parse(t)
          msg = (j && (j.msg || j.detail)) || ''
        } catch {
          msg = ''
        }
        throw new Error(msg || 'HTTP ' + res.status + (t ? '：' + t.slice(0, 120) : ''))
      })
    }
    const reader = res.body.getReader()
    const dec = new TextDecoder('utf-8')
    let buf = ''
    let out = ''
    const pump = () =>
      reader.read().then(({ done, value }) => {
        if (done) {
          // 流自然结束但没收 done 帧：也收尾，否则界面一直转圈
          cb.onDone && cb.onDone(out)
          return
        }
        buf += dec.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const frame = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          let ev = 'message'
          const datas = []
          for (const ln of frame.split('\n')) {
            if (ln.startsWith('event:')) ev = ln.slice(6).trim()
            else if (ln.startsWith('data:')) datas.push(ln.slice(5).replace(/^ /, ''))
          }
          const payload = datas.join('\n')
          if (ev === 'message') {
            // 后端把换行转义成 \n
            out += payload.replace(/\\n/g, '\n')
            cb.onText && cb.onText(out)
          } else if (ev === 'sources') {
            try {
              cb.onSources && cb.onSources(JSON.parse(payload) || [])
            } catch {
              /* 半截帧忽略 */
            }
          } else if (ev === 'done') {
            cb.onDone && cb.onDone(out)
          } else if (ev === 'error') {
            cb.onError && cb.onError(payload)
          }
        }
        return pump()
      })
    return pump()
  })
}

/* ==================================================================
 * 论文翻译
 * ================================================================== */

/** 译文进度 + 已译内容 + 原文分段 + 术语表。
 *  一次拿全：页面刷新后要能恢复（翻译一小时，不能刷新就没）。
 *  @returns {Promise<{ok, status:{total,ok,warn,bad,done,pending},
 *    glossary:Array, segments:Array<{i,src}>,
 *    translations:Object<segI,{zh,status,score,missing}>,
 *    translatable:boolean}>}
 */
export function getTranslation(did) {
  return client.get('/docs/' + encodeURIComponent(did) + '/translate')
}

/** 开始/继续翻译（SSE）。
 * @param {string} did
 * @param {{mode?:string, verify?:boolean}} opt mode: run / redo / redo:N / limit:N
 * @param {{onTotal?:Function,onSeg?:Function,onDone?:Function,onError?:Function}} cb
 */
export function runTranslation(did, opt, cb = {}) {
  const token = getToken()
  const body = JSON.stringify({
    mode: (opt && opt.mode) || 'run',
    verify: !opt || opt.verify !== false
  })
  return fetch('/api/docs/' + encodeURIComponent(did) + '/translate/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {})
    },
    body
  }).then(res => {
    if (!res.ok) {
      // 别裸 res.json()：AI 没开时返回 {detail}，解析失败会盖掉真原因
      return res.text().then(t => {
        let msg = ''
        try {
          const j = JSON.parse(t)
          msg = (j && (j.msg || j.detail)) || ''
        } catch {
          msg = ''
        }
        throw new Error(msg || 'HTTP ' + res.status)
      })
    }
    const reader = res.body.getReader()
    const dec = new TextDecoder('utf-8')
    let buf = ''
    const pump = () =>
      reader.read().then(({ done, value }) => {
        if (done) {
          cb.onError && cb.onError('连接断开了（已译的部分不会丢，点继续接着翻）')
          return
        }
        buf += dec.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const frame = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          let ev = 'message'
          const datas = []
          for (const ln of frame.split('\n')) {
            if (ln.startsWith('event:')) ev = ln.slice(6).trim()
            else if (ln.startsWith('data:')) datas.push(ln.slice(5).replace(/^ /, ''))
          }
          const payload = datas.join('\n')
          if (ev === 'seg' || ev === 'total' || ev === 'done') {
            let j = {}
            try {
              j = JSON.parse(payload) || {}
            } catch {
              continue
            }
            if (ev === 'seg') cb.onSeg && cb.onSeg(j)
            else if (ev === 'total') cb.onTotal && cb.onTotal(j)
            else cb.onDone && cb.onDone(j)
          } else if (ev === 'error') {
            cb.onError && cb.onError(payload)
          }
        }
        return pump()
      })
    return pump()
  })
}

/** 重抽术语表（锁定的条目不会被覆盖）。 */
export function redoGlossary(did) {
  return client.post('/docs/' + encodeURIComponent(did) + '/translate/glossary', {}, { timeout: 180000 })
}

/** 手动加/改术语。locked 默认 true —— 手动录入的就是要压住自动抽取。 */
export function putGlossaryTerm(did, en, zh, locked) {
  return client.put('/docs/' + encodeURIComponent(did) + '/translate/glossary', {
    en, zh, locked: locked === undefined ? null : locked
  })
}

/** 删一条术语。 */
export function delGlossaryTerm(did, en) {
  return client.delete(
    '/docs/' + encodeURIComponent(did) + '/translate/glossary?en=' + encodeURIComponent(en)
  )
}

/** 清空译文（术语表保留）。 */
export function clearTranslation(did) {
  return client.delete('/docs/' + encodeURIComponent(did) + '/translate')
}

/* ==================================================================
 * 问答反馈 + 论文图片图注
 * ================================================================== */

/** 给一条文档问答打反馈（👍/👎），驱动自进化 RAG 纠错。
 *  @param {string} did
 *  @param {string} question 被反馈的那条问题原文（用于定位记忆）
 *  @param {boolean} good true=认可 false=不认可
 *  @param {string} [correction] 👎 时的修正说明
 */
export function feedbackQa(did, question, good, correction) {
  return client.post('/docs/' + encodeURIComponent(did) + '/qa/feedback', {
    question,
    good,
    correction: correction || null
  })
}

/** 视觉模型给论文里的图（架构图/示意图）写一句中文说明，best-effort。
 *  @param {string} did
 *  @param {string} name 图片名（与正文中 ![](media:name) 的 name 对应）
 *  @param {string} [context] 图片所在段落的少量上下文
 */
export function captionFigure(did, name, context) {
  return client.post(
    '/docs/' + encodeURIComponent(did) + '/figure/caption',
    { name, context: context || '' },
    { timeout: 90000 }
  )
}

/** 图片直链（带 token，<img> 用）。media 端点和 files 端点鉴权方式一致。
 *  @param {string} owner 文档 id
 *  @param {string} name 图片名
 */
export function getMediaUrl(owner, name) {
  const t = getToken()
  return (
    '/api/media/' +
    encodeURIComponent(owner) +
    '/' +
    encodeURIComponent(name) +
    (t ? '?t=' + encodeURIComponent(t) : '')
  )
}
