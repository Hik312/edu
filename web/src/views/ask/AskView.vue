<script setup>
/* AI 问答页 —— 基于卡片知识库的问答入口。

两种模式（对应后端 /api/agent/ask 的 mode）：
- 知识库问答（flow）：固定「检索→回答→自检」流程，答案带 sources 溯源，可点开引用卡片。
- Agent（react）：模型自己决定调哪些工具，流式输出（SSE），生成结束补一个 sources 帧。

记忆分三层，各自存哪儿是这次改造的核心约定：
  L1 会话内多轮  前端持有（本页 messages）→ 每次随请求发给后端，后端裁剪（不存会话）
  L2 检索上下文  后端 runtime 自己拼（retrieve 的 hits + 最近一句用户话）
  L3 长期档案    服务端 data/store/profiles.json，按登录用户存，本页挂载时读一次

设计上和 /generate、/docs 一样走 view→store→api 分层：本页只管渲染与交互，
取数全在 @/api/agent 和 @/api/cards。样式复用 tokens.css 的 :root 变量，不引入深色分支。
*/
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ask, askStream, getAgentStatus, getProfile } from '@/api/agent'
import * as cardsApi from '@/api/cards'

const messages = ref([]) // {role, text, sources, streaming}
const input = ref('')
const mode = ref('flow') // 'flow' | 'react'
const sending = ref(false)
const status = ref({ ok: false, msg: '' })
const cardMap = reactive({}) // id -> title，引用卡片展示用
const scrollEl = ref(null)
const profile = ref(null) // L3 长期档案 {role, topics, weak}，拿不到就是 null

const drawer = reactive({ open: false, card: null, loading: false })

const SUGGESTS = [
  'JVM 内存模型是怎么划分的',
  '今天该复习什么',
  'Spring Boot 自动装配是怎么跑起来的',
  'TCP 三次握手为什么是三次'
]

function scrollToBottom() {
  nextTick(() => {
    const el = scrollEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadMeta() {
  try {
    const s = await getAgentStatus()
    status.value = { ok: Boolean(s.ok), msg: s.msg || '可用' }
  } catch {
    status.value = { ok: false, msg: '状态获取失败' }
  }
  try {
    // brief=1：这里只是要一张 id → 标题 的映射，用来把回答里的引用渲染成
    // 可点的卡片名。不带它的话后端会回整库正文（实测 118KB vs 22KB）——
    // 每次打开问答页都白下载一遍所有卡片的 mechanism/scene。
    const r = await cardsApi.listCards({ brief: '1' })
    ;(r.cards || []).forEach(c => {
      cardMap[c.id] = c.title || c.id
    })
  } catch {
    /* 引用卡片标题拿不到就退化显示 id，不影响问答 */
  }
  try {
    const p = await getProfile()
    profile.value = p && (p.role || (p.topics || []).length || (p.weak || []).length) ? p : null
  } catch {
    /* 档案拿不到就是没有，问答照常 */
  }
}

onMounted(loadMeta)

/** L1：把页面上的对话压成后端要的形状。
 *  只取 role/content —— sources / streaming 是本页的渲染态，不该进历史。 */
function historyOf() {
  return messages.value
    .filter(m => m.text && !m.streaming)
    .map(m => ({ role: m.role, content: m.text }))
}

function clearChat() {
  messages.value = []
}

function pushUser(text) {
  messages.value.push({ role: 'user', text })
}

function pushAssistant() {
  const m = reactive({ role: 'assistant', text: '', sources: [], streaming: true })
  messages.value.push(m)
  return m
}

async function send() {
  const q = input.value.trim()
  if (!q || sending.value) return
  input.value = ''
  // **先**取历史再 push 这条问题 —— 顺序反了会把当前问题重复发给后端
  const hist = historyOf()
  const prof = profile.value
  pushUser(q)
  sending.value = true
  scrollToBottom()

  if (mode.value === 'flow') {
    const m = pushAssistant()
    try {
      const r = await ask(q, 'flow', { history: hist, profile: prof })
      m.text = r.answer || ''
      m.sources = r.sources || []
    } catch (e) {
      m.text = '出错了：' + (e.message || e)
      m.sources = []
    } finally {
      m.streaming = false
      sending.value = false
      scrollToBottom()
    }
  } else {
    const m = pushAssistant()
    askStream(q, {
      history: hist,
      profile: prof,
      onText: t => {
        m.text = t
        scrollToBottom()
      },
      onSources: ids => {
        m.sources = ids || []
      },
      onDone: () => {
        m.streaming = false
        sending.value = false
        scrollToBottom()
      },
      onError: e => {
        m.text = '出错了：' + (e.message || e)
        m.streaming = false
        sending.value = false
      }
    })
  }
}

function onSuggest(s) {
  input.value = s
  send()
}

function titleOf(id) {
  return cardMap[id] || id
}

async function openCard(id) {
  drawer.loading = true
  drawer.open = true
  drawer.card = null
  try {
    const r = await cardsApi.getCard(id)
    drawer.card = r.card
  } catch {
    ElMessage.error('卡片加载失败')
  } finally {
    drawer.loading = false
  }
}

function closeDrawer() {
  drawer.open = false
}
</script>

<template>
  <div class="ask">
    <!-- 顶栏：标题 + 模式切换 + 档案 + AI 状态 -->
    <div class="head">
      <div class="seg">
        <button :class="{ on: mode === 'flow' }" @click="mode = 'flow'">知识库问答</button>
        <button :class="{ on: mode === 'react' }" @click="mode = 'react'">Agent（流式）</button>
      </div>
      <div class="head-r">
        <span v-if="profile" class="prof" :title="'这轮问答会带上你的长期档案'">
          档案 · {{ profile.role || '未设岗位'
          }}<template v-if="profile.weak && profile.weak.length">
            · {{ profile.weak.length }} 张薄弱</template
          >
        </span>
        <button v-if="messages.length" class="ghost" @click="clearChat">清空对话</button>
        <div class="status" :class="{ bad: !status.ok }">
          <span class="dot" />
          {{
            status.ok
              ? 'AI 已就绪 · ' + (mode === 'flow' ? '带引用' : '流式')
              : 'AI 未启用 · ' + status.msg
          }}
        </div>
      </div>
    </div>

    <!-- 消息流 -->
    <div ref="scrollEl" class="stream">
      <div v-if="!messages.length" class="empty">
        <p class="empty-t">向卡片知识库提问</p>
        <p class="empty-s">
          flow 模式会给出答案并标注引用卡片；Agent 模式模型自行调用工具检索。
          对话带着上文，「那第二个呢」这种指代也听得懂。
        </p>
        <div class="sugs">
          <button v-for="s in SUGGESTS" :key="s" class="sug" @click="onSuggest(s)">{{ s }}</button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="row" :class="m.role">
        <div class="bubble">
          <span v-if="m.streaming && !m.text" class="typing">思考中…</span>
          <span class="body">{{ m.text }}</span>

          <div v-if="m.role === 'assistant' && m.sources && m.sources.length" class="srcs">
            <span class="src-label">引用卡片</span>
            <button v-for="id in m.sources" :key="id" class="chip" @click="openCard(id)">
              {{ titleOf(id) }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入条 -->
    <div class="bar">
      <textarea
        v-model="input"
        class="ta"
        rows="2"
        placeholder="问点什么…（Enter 发送，Shift+Enter 换行）"
        @keydown.enter.exact.prevent="send"
      />
      <button class="send" :disabled="sending || !input.trim()" @click="send">
        {{ sending ? '发送中' : '发送' }}
      </button>
    </div>

    <!-- 引用卡片详情抽屉 -->
    <div v-if="drawer.open" class="mask" @click.self="closeDrawer">
      <aside class="drawer">
        <button class="x" @click="closeDrawer">×</button>
        <div v-if="drawer.loading" class="d-loading">加载中…</div>
        <template v-else-if="drawer.card">
          <h3 class="d-title">{{ drawer.card.title }}</h3>
          <p class="d-one">{{ drawer.card.oneLine }}</p>
          <div v-if="drawer.card.analogy" class="d-block">
            <span class="d-k">类比</span>{{ drawer.card.analogy }}
          </div>
          <div v-if="drawer.card.mechanism" class="d-block">
            <span class="d-k">原理</span>
            <div v-for="(s, k) in drawer.card.mechanism" :key="k" class="d-mech">{{ s }}</div>
          </div>
          <div v-if="drawer.card.scene" class="d-block">
            <span class="d-k">场景</span>
            <div v-for="(s, k) in drawer.card.scene" :key="k" class="d-scene">{{ s }}</div>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.ask {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* 顶栏 */
.head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 4px 14px;
}
.seg {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--panel);
}
.seg button {
  border: 0;
  background: transparent;
  padding: 7px 14px;
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--mu);
  cursor: pointer;
  transition:
    background 0.16s,
    color 0.16s;
}
.seg button + button {
  border-left: 1px solid var(--line);
}
.seg button.on {
  background: var(--ac);
  color: #fdfaf3;
}
.head-r {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.prof {
  font-size: var(--fs-xs);
  color: var(--ac);
  background: var(--ac-glow);
  border-radius: 999px;
  padding: 4px 10px;
}
.ghost {
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--mu);
  border-radius: var(--radius-sm);
  padding: 5px 10px;
  font-size: var(--fs-xs);
  cursor: pointer;
  transition:
    border-color 0.16s,
    color 0.16s;
}
.ghost:hover {
  border-color: var(--ac);
  color: var(--ac);
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: var(--fs-sm);
  color: var(--ac);
}
.status.bad {
  color: var(--dim);
}
.status .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ac);
}
.status.bad .dot {
  background: var(--dim);
}

/* 消息流 */
.stream {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 4px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.empty {
  margin: auto;
  text-align: center;
  color: var(--dim);
  max-width: 460px;
}
.empty-t {
  font-family: var(--font-title);
  font-size: var(--fs-xl);
  color: var(--tx);
  margin: 0 0 6px;
}
.empty-s {
  font-size: var(--fs-sm);
  margin: 0 0 18px;
  line-height: 1.7;
}
.sugs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.sug {
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--mu);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: var(--fs-sm);
  cursor: pointer;
  transition:
    border-color 0.16s,
    color 0.16s;
}
.sug:hover {
  border-color: var(--ac);
  color: var(--ac);
}

.row {
  display: flex;
}
.row.user {
  justify-content: flex-end;
}
.row.assistant {
  justify-content: flex-start;
}
.bubble {
  max-width: 78%;
  padding: 12px 14px;
  border-radius: 14px;
  font-size: var(--fs-md);
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--line);
}
.row.user .bubble {
  background: var(--ac);
  color: #fdfaf3;
  border-color: var(--ac);
  border-bottom-right-radius: 4px;
}
.row.assistant .bubble {
  background: var(--panel);
  color: var(--tx);
  border-bottom-left-radius: 4px;
}
.body {
  white-space: pre-wrap;
}
.typing {
  color: var(--dim);
  font-style: italic;
}

.srcs {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--line2);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.src-label {
  font-size: var(--fs-xs);
  color: var(--dim);
  letter-spacing: 1px;
}
.chip {
  border: 1px solid var(--line2);
  background: var(--bg);
  color: var(--ac);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: var(--fs-xs);
  cursor: pointer;
  transition:
    border-color 0.16s,
    background 0.16s;
}
.chip:hover {
  border-color: var(--ac);
  background: var(--panel);
}

/* 输入条 */
.bar {
  flex: none;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 12px 4px 4px;
  border-top: 1px solid var(--line2);
}
.ta {
  flex: 1;
  resize: none;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--tx);
  font: inherit;
  font-size: var(--fs-md);
  padding: 10px 12px;
  line-height: 1.6;
  outline: none;
}
.ta:focus {
  border-color: var(--ac);
}
.send {
  flex: none;
  height: 42px;
  padding: 0 20px;
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--ac);
  color: #fdfaf3;
  font-size: var(--fs-md);
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.16s;
}
.send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 抽屉 */
.mask {
  position: fixed;
  inset: 0;
  background: rgba(40, 33, 22, 0.32);
  display: flex;
  justify-content: flex-end;
  z-index: 50;
}
.drawer {
  width: min(420px, 92vw);
  height: 100%;
  background: var(--bg);
  background-image: var(--tex);
  border-left: 1px solid var(--line2);
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.12);
  padding: 22px 22px 30px;
  overflow-y: auto;
  position: relative;
}
.x {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 50%;
  background: var(--panel);
  color: var(--mu);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.d-loading {
  color: var(--dim);
  padding-top: 40px;
  text-align: center;
}
.d-title {
  font-family: var(--font-title);
  font-size: var(--fs-lg);
  color: var(--tx);
  margin: 6px 30px 10px 0;
  line-height: 1.4;
}
.d-one {
  font-size: var(--fs-md);
  color: var(--ac);
  margin: 0 0 14px;
  line-height: 1.7;
}
.d-block {
  margin-bottom: 14px;
  font-size: var(--fs-sm);
  line-height: 1.7;
  color: var(--tx);
}
.d-k {
  display: inline-block;
  min-width: 42px;
  font-weight: 600;
  color: var(--mu);
  margin-right: 6px;
}
.d-mech,
.d-scene {
  margin: 3px 0 3px 48px;
  color: var(--tx);
}
</style>
