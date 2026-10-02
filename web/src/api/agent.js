/* AI 问答接口 —— 对应后端 `app/routers/agent.py`。

三条硬规矩（和 ai.js 同源，别破坏）：
  1. `/agent/status` 返回 ok:false 是正常状态，不是故障。AI 是可选增强，
     关掉后背卡、复习照常。页面要显示「未启用」而不是报错红条。
  2. 错误响应体是 {ok:false, msg}，msg 是给人看的中文。
  3. **回答里不许出现卡片 id / 【xxx】标记 / JSON** —— 这是用户明确反馈过的问题。
     后端有两道（提示词 + runtime.clean_answer），这里是第三道兜底，
     `cleanAnswer()` 必须对 flow 和 react 两种模式都生效。

流式走 SSE，但 EventSource 只支持 GET，这里是 POST，所以必须用 fetch 自己读流。
后端 SSE 帧格式（改了必须两边同步）：
  `data: <文本增量>`           正文，换行被转义成 \\n
  `event: sources` + data      这次引用到的卡片 id，JSON 数组（生成结束后才有）
  `event: done`                正文流结束
  `event: error`               出错
*/
import client from './client'
import { getToken } from './client'

/** 可用性（模型在不在 / langchain 装没装）。 */
export function getAgentStatus() {
  return client.get('/agent/status')
}

/* ---- cards Agent（文档 → 卡片，LangGraph）----
 * 两个阶段分开调，中间前端要拿 structure 的结果刷新章节列表再逐章跑 ——
 * 合成一个端点就没法在「结构变了」之后把新分章显示出来了。
 * timeout 各自放宽：本地 8B 结构分析 20~60s、一章出卡（含看图）可能到分钟级，
 * 全局 20s 会在模型慢一点时把正常请求掐断。 */

/** 阶段一：LLM 看规则初切的清单定切分点，合法才重切落库（返回 {refined,msg,doc}）。 */
export function cardsStructure(docId) {
  return client.post('/agent/cards/structure', { docId }, { timeout: 300000 })
}

/** 阶段二：一章跑完整张图（图注 → 生成 → 对齐自检），落一张草稿。
 *  幂等：已有同章草稿返回 {skipped:true}（断点续跑）。 */
export function cardsChapter(docId, index, force = false) {
  return client.post('/agent/cards/chapter', { docId, index, force }, { timeout: 600000 })
}

/** 内容解析：规则预判 + AI 判定每章有用/没用，报告落库（出卡前的确认关卡）。
 *
 * timeout 放宽到 5 分钟：判定要读完整份章节清单，大文档比结构精修还慢；
 * 而且它在 structure 之后串行调，等的是两段模型时间。 */
export function parseDoc(docId) {
  return client.post('/agent/cards/parse', { docId }, { timeout: 300000 })
}

/** 保存报告页的勾选调整。keeps: {章节下标(字符串): 是否保留} */
export function putParseKeeps(docId, keeps) {
  return client.put('/agent/cards/parse', { docId, keeps })
}

/** 非流式问答（flow 模式用，能拿到 sources 溯源）。
 *
 * timeout 单独放宽到 2 分钟：带多轮 history 的 flow 实测 31 秒
 * （单轮也要 17 秒），全局 20 秒会把正常问答掐成
 * 「timeout of 20000ms exceeded」—— 表现就是「问答不出来了」。 */
export function ask(question, mode = 'flow', opts = {}) {
  return client.post(
    '/agent/ask',
    {
      question,
      mode,
      stream: false,
      history: opts.history || [],
      profile: opts.profile || undefined,
      webSearch: Boolean(opts.webSearch)
    },
    { timeout: 120000 }
  )
}

/** 长期档案（L3）：跟着登录用户走，服务端存一份。
 * @returns {Promise<{role:string, topics:string[], weak:string[]}>} */
export function getProfile() {
  return client.get('/agent/profile')
}

/** 合并更新长期档案（只覆盖发上去的字段）。 */
export function putProfile(patch) {
  return client.put('/agent/profile', patch)
}

/**
 * 清洗回答正文（第三道兜底，后端 clean_answer 的前端镜像）。
 *
 * 为什么前后端都要做：流式模式下正文是**边生成边渲染**的，
 * 后端只能在生成完之后再清洗，那时用户已经看见 id 了。
 *
 * @param {string} text
 * @returns {string}
 */
export function cleanAnswer(text) {
  if (!text) return ''
  let s = String(text)
  const lines = []
  for (const raw of s.split('\n')) {
    let ln = raw.trim()
    if (ln.startsWith('【')) {
      const close = ln.indexOf('】')
      if (close > 0 && close <= 60) ln = ln.slice(close + 1).replace(/^[\s：:]+/, '')
    }
    if (/^(引用卡片|引用[：:]|来源[：:])/.test(ln)) continue
    if (ln) lines.push(ln)
  }
  s = lines.join('\n')
  s = s.replace(/【\s*[A-Za-z][A-Za-z0-9_-]{1,60}\s*】/g, '')
  s = s.replace(/\{[^{}]*"id"\s*:\s*"[^"]+"[^{}]*\}/g, '')
  // ★ `id\s*[:：]` 这两个分支必须带词边界 \b：
  // 没有它时，任何以 id 结尾的英文词后面跟冒号都会被吃掉一段 ——
  // `valid: true` 变成 `val`、`solid: …`、`grid: …`、`void: …` 同理。
  // 中英混排的技术回答里这类词很常见，属于「清洗把答案改坏了」。
  // 后端 agent/qa/runtime.py 是同一份正则，两边必须一起改。
  s = s.replace(/(?:卡\s*片?\s*id\s*[:：为]?\s*|\bid\s*[:：]\s*)[A-Za-z][A-Za-z0-9_-]{1,60}/gi, '')
  // 「（参考《xxx》…）」这类括号出处标注：正文里读着突兀（用户反馈）。
  // 出处走 sources 引用条，不靠正文括注。只删括号包住且以参考/参见/引自/
  // 出自开头的 —— 正常引用《手册》安装不带这个开头，不会误伤。
  // back_study/agent/qa/runtime.py 的 clean_answer 是同一份正则，两边必须一起改。
  s = s.replace(/[（(]\s*(?:参考|参见|引自|出自|出处\s*[:：])[^（()）]{0,100}[）)]/g, '')
  s = s.replace(/\n{3,}/g, '\n\n')
  return s.trim()
}

/**
 * 流式问答（react 模式走 SSE）。
 * @param {string} question
 * @param {Object} [opts]
 * @param {Array<{role:string,content:string}>} [opts.history] L1 会话历史
 * @param {Object} [opts.profile]  L3 长期档案，不传则用服务端存的
 * @param {boolean} [opts.webSearch] 联网开关：资料追加【网页】搜索结果
 * @param {(text:string)=>void} [opts.onText]   累计全文（已清洗）
 * @param {(ids:string[])=>void} [opts.onSources] 引用卡片 id，可能为空数组
 * @param {(res:{answer:string})=>void} [opts.onDone]
 * @param {(err:Error)=>void} [opts.onError]
 */
export function askStream(question, opts = {}) {
  const { history = [], profile, webSearch = false, onText, onSources, onDone, onError } = opts
  const token = getToken()
  const body = JSON.stringify({
    question,
    mode: 'react',
    stream: true,
    history,
    profile: profile || undefined,
    webSearch
  })
  fetch('/api/agent/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {})
    },
    body
  })
    .then(res => {
      if (!res.ok) {
        return res.json().then(j => {
          throw new Error((j && j.msg) || 'HTTP ' + res.status)
        })
      }
      const reader = res.body.getReader()
      const dec = new TextDecoder('utf-8')
      let buf = ''
      let raw = '' // 未清洗的累计（清洗是正则级的，逐块做会切坏标记）
      let stopped = false // 收到 error 帧就不再读了，免得 onError 之后还 onDone
      const flush = () => {
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
            if (payload === '[DONE]') continue
            raw += payload.replace(/\\n/g, '\n') // 后端把换行转义成 \\n
            onText && onText(cleanAnswer(raw))
          } else if (ev === 'sources') {
            try {
              onSources && onSources(JSON.parse(payload) || [])
            } catch {
              /* 半截帧不致命，忽略 */
            }
          } else if (ev === 'error') {
            stopped = true
            onError && onError(new Error(payload || '流式输出出错'))
            return
          }
          // done 帧不在这里触发 onDone —— 等 reader 真正读完，
          // 否则后端还没 flush 完就回调，最后几个字会丢
        }
      }
      const pump = () => {
        if (stopped) return
        reader
          .read()
          .then(({ done, value }) => {
            if (done) {
              flush()
              onDone && onDone({ answer: cleanAnswer(raw) })
              return
            }
            buf += dec.decode(value, { stream: true })
            flush()
            pump()
          })
          .catch(e => onError && onError(e))
      }
      pump()
    })
    .catch(e => onError && onError(e))
}
