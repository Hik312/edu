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

/** 非流式问答（flow 模式用，能拿到 sources 溯源）。 */
export function ask(question, mode = 'flow', opts = {}) {
  return client.post('/agent/ask', {
    question,
    mode,
    stream: false,
    history: opts.history || [],
    profile: opts.profile || undefined
  })
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
  s = s.replace(/(?:卡\s*片?\s*id\s*[:：为]?\s*|id\s*[:：]\s*)[A-Za-z][A-Za-z0-9_-]{1,60}/gi, '')
  s = s.replace(/\n{3,}/g, '\n\n')
  return s.trim()
}

/**
 * 流式问答（react 模式走 SSE）。
 * @param {string} question
 * @param {Object} [opts]
 * @param {Array<{role:string,content:string}>} [opts.history] L1 会话历史
 * @param {Object} [opts.profile]  L3 长期档案，不传则用服务端存的
 * @param {(text:string)=>void} [opts.onText]   累计全文（已清洗）
 * @param {(ids:string[])=>void} [opts.onSources] 引用卡片 id，可能为空数组
 * @param {(res:{answer:string})=>void} [opts.onDone]
 * @param {(err:Error)=>void} [opts.onError]
 */
export function askStream(question, opts = {}) {
  const { history = [], profile, onText, onSources, onDone, onError } = opts
  const token = getToken()
  const body = JSON.stringify({
    question,
    mode: 'react',
    stream: true,
    history,
    profile: profile || undefined
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
