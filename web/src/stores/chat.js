/* AI 问答会话 —— 状态放 store 而不是组件里，为的是「后台继续回答」。
 *
 * 用户问完一句就切走页面是常态（去看卡、看文档）。请求若挂在组件上，
 * 组件一销毁，回答就写进了一块没人要的内存 —— 回来只剩自己问的那句。
 * 放 store（模块级单例）里：页面切走，axios/SSE 照样跑完、照样写回；
 * 切回来，正在生成的回答还挂在屏幕上。
 *
 * 记忆分三层（和 AskView 头注释同一份约定，改这里要同步那边）：
 *   L1 会话内多轮 —— 本 store 持有 + localStorage(edu.chat) 兜刷新
 *   L2 检索上下文 —— 后端 runtime 自己拼（retrieve 的 hits + 最近一句用户话）
 *   L3 长期档案   —— 服务端存，AskView 挂载时读一次写进 profile
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { ask, askStream } from '@/api/agent'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([]) // {role, text, sources, streaming}
  const input = ref('')
  const mode = ref('flow') // 'flow' | 'react'
  const webSearch = ref(false) // 联网开关：true 时资料追加【网页】搜索结果
  const sending = ref(false)
  const profile = ref(null) // L3 长期档案 {role, topics, weak}，拿不到就是 null

  /** L1 刷新不丢：整段对话存 localStorage（只存 role/text/sources，渲染态不存）。
   *  上限 100 条 —— 会话历史不是存档，无限堆迟早顶穿 5MB 配额。

   *  ★ 连「生成中」的消息也存：从前的守卫是「有streaming 就不落盘」，
   *    想避免存半截。但 react 流式动辄几十秒，用户很可能**在生成途中就刷新**——
   *    守卫一旦命中，整条正在生成的对话在刷新后**全部消失**（实测踩过）。
   *    半截文本也比空屏好：用户看到的是「已经出的那部分」，和刷新前一致。 */
  function saveChat() {
    try {
      const slim = messages.value
        .filter(m => m.text)
        .slice(-100)
        .map(m => ({ role: m.role, text: m.text, sources: m.sources || [] }))
      localStorage.setItem('edu.chat', JSON.stringify(slim))
    } catch {
      /* 配额满了就不存，不能把页面搞崩 */
    }
  }

  function restoreChat() {
    try {
      const raw = JSON.parse(localStorage.getItem('edu.chat') || '[]')
      if (Array.isArray(raw)) {
        messages.value = raw
          .filter(m => m && (m.role === 'user' || m.role === 'assistant') && m.text)
          .map(m => ({
            role: m.role,
            text: String(m.text),
            sources: m.sources || []
          }))
      }
    } catch {
      /* 坏数据当作没存过 */
    }
  }

  /* ---- 按钮选项（模式 / 联网开关）也要持久化 ----
   * 用户诉求：「刷新后问答还在，但答案没显示，而且那些按钮选项也改变了，都要持久化」。
   * mode / webSearch 之前没存，刷新一律回默认（flow + 不联网）。
   * 单独放一个 key：它是「偏好」，不是「对话」，清空对话时不该被重置。 */
  const PREFS_KEY = 'edu.chat.prefs'
  function savePrefs() {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify({ mode: mode.value, webSearch: webSearch.value }))
    } catch {
      /* 忽略 */
    }
  }
  function restorePrefs() {
    try {
      const p = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}')
      if (p.mode === 'flow' || p.mode === 'react') mode.value = p.mode
      if (typeof p.webSearch === 'boolean') webSearch.value = p.webSearch
    } catch {
      /* 坏数据当作默认 */
    }
  }

  restoreChat() // setup 期恢复：在下面的 watch 之前跑，不会误触发一次写盘
  restorePrefs()
  watch([mode, webSearch], savePrefs)
  // 节流落盘：流式时每个 token 都会触发 watch，不节流会把 localStorage 写爆。
  let saveTimer = null
  watch(
    messages,
    () => {
      if (saveTimer) return
      saveTimer = setTimeout(() => {
        saveTimer = null
        saveChat()
      }, 600)
    },
    { deep: true }
  )

  /** 压成后端要的形状。只取 role/content —— sources/streaming 是渲染态。 */
  function historyOf() {
    return messages.value
      .filter(m => m.text && !m.streaming)
      .map(m => ({ role: m.role, content: m.text }))
  }

  function pushUser(text) {
    messages.value.push({ role: 'user', text })
  }

  function pushAssistant() {
    const m = { role: 'assistant', text: '', sources: [], streaming: true, verify: null, steps: [], bgStep: '' }
    messages.value.push(m)
    return m
  }

  /** 问一句。不依赖任何组件状态：发送方（组件）卸载后照样跑完写回。
   *  滚动由 AskView 的 watch 负责 —— store 不碰 DOM。 */
  async function send() {
    const q = input.value.trim()
    if (!q || sending.value) return
    input.value = ''
    // **先**取历史再 push 这条问题 —— 顺序反了会把当前问题重复发给后端
    const hist = historyOf()
    const prof = profile.value
    pushUser(q)
    // 问题一发出就**立即**落盘，不等节流：用户可能答还没生成完就刷新/切页，
    // 那时至少「问了什么」还在（丢答案比丢问题轻）。节流只留给流式正文。
    saveChat()
    sending.value = true

    // ★ 两个模式**都走 SSE 流式**，只有 mode 参数不同。
// 以前 flow 用 ask() 一次性等全文 —— 本地 8B 要 20~40 秒，
// 屏幕整段空白，用户只能猜是不是坏了（实测这才是「等待动画显得没用」的根源）。
// 现在后端 flow 也支持 token sink（agent/qa/runtime.py:stream_flow）。
const m = pushAssistant()
askStream(q, {
  mode: mode.value,
  history: hist,
  profile: prof,
  webSearch: webSearch.value,
  onText: t => {
    m.text = t
  },
  onStep: s => {
    // 「到哪一步」进度帧：{text} 新增一步（自动把上一步标记完成），
    // {done:true} 只收尾 —— 每个新增步骤都必须有一次收尾，否则那个转圈停不下来。
    // kind:'bg' 的是**后台增强**（卡片校验），不属于回答流程 —— 它不该占步骤条
    // 让人以为「答完了还在加载」，单独放 bgStep 渲染成一行轻提示。
    if (s && s.kind === 'bg') {
      if (s.done) m.bgStep = ''
      else m.bgStep = s.text
      return
    }
    if (!m.steps) m.steps = []
    const last = m.steps[m.steps.length - 1]
    if (s && s.done) {
      if (last && !last.done) last.done = true
    } else if (s && s.text) {
      if (last && !last.done) last.done = true
      m.steps.push({ text: s.text, done: false })
    }
  },
  onSources: ids => {
    m.sources = ids || []
  },
  onVerify: list => {
    // react 答完后校验引用卡的结果；有错卡才推过来，前端渲染「是否修正」
    m.verify = list && list.length ? list : null
  },
  onDone: () => {
    m.streaming = false
    sending.value = false
    // 兜底：万一某个版本漏发收尾帧，500ms 后无论如何把进行中的那步标记完成。
    // （正常路径后端 done 帧后已经补了收尾，这里只是防御）
    setTimeout(() => {
      const last = (m.steps || [])[m.steps.length - 1]
      if (last && !last.done) last.done = true
    }, 500)
    saveChat() // 答完立即落盘，别等节流窗口
  },
  onError: e => {
    m.text = '出错了：' + (e.message || e)
    m.streaming = false
    sending.value = false
    m.bgStep = ''
    const last = (m.steps || [])[m.steps.length - 1]
    if (last && !last.done) last.done = true
    saveChat()
  }
})
  }

  function clearChat() {
    messages.value = [] // watch 会把空数组写进 localStorage（等于清掉记忆）
  }

  return { messages, input, mode, webSearch, sending, profile, send, clearChat }
})
