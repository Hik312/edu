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
   *  上限 100 条 —— 会话历史不是存档，无限堆迟早顶穿 5MB 配额。 */
  function saveChat() {
    try {
      const slim = messages.value
        .filter(m => m.text && !m.streaming)
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

  restoreChat() // setup 期恢复：在下面的 watch 之前跑，不会误触发一次写盘
  watch(
    messages,
    () => {
      if (messages.value.some(m => m.streaming)) return // 流式生成中不落盘，结束那次再存
      saveChat()
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
    const m = { role: 'assistant', text: '', sources: [], streaming: true }
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
    sending.value = true

    if (mode.value === 'flow') {
      const m = pushAssistant()
      try {
        const r = await ask(q, 'flow', { history: hist, profile: prof, webSearch: webSearch.value })
        m.text = r.answer || ''
        m.sources = r.sources || []
      } catch (e) {
        m.text = '出错了：' + (e.message || e)
        m.sources = []
      } finally {
        m.streaming = false
        sending.value = false
      }
    } else {
      const m = pushAssistant()
      askStream(q, {
        history: hist,
        profile: prof,
        webSearch: webSearch.value,
        onText: t => {
          m.text = t
        },
        onSources: ids => {
          m.sources = ids || []
        },
        onDone: () => {
          m.streaming = false
          sending.value = false
        },
        onError: e => {
          m.text = '出错了：' + (e.message || e)
          m.streaming = false
          sending.value = false
        }
      })
    }
  }

  function clearChat() {
    messages.value = [] // watch 会把空数组写进 localStorage（等于清掉记忆）
  }

  return { messages, input, mode, webSearch, sending, profile, send, clearChat }
})
