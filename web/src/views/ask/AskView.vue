<script setup>
/* AI 问答页 —— 基于卡片知识库的问答入口。

两种模式（对应后端 /api/agent/ask 的 mode）：
- 知识库问答（flow）：固定「检索→回答→自检」流程，答案带 sources 溯源，可点开引用卡片。
- Agent（react）：模型自己决定调哪些工具，流式输出（SSE），生成结束补一个 sources 帧。

记忆分三层，各自存哪儿是这次改造的核心约定：
  L1 会话内多轮  chat store 持有（模块级，切页不断生成）→ 每次随请求发给后端，后端裁剪（不存会话）
  L2 检索上下文  后端 runtime 自己拼（retrieve 的 hits + 最近一句用户话）
  L3 长期档案    服务端 data/store/profiles.json，按登录用户存，本页挂载时读一次

设计上和 /generate、/docs 一样走 view→store→api 分层：本页只管渲染与交互，
取数全在 @/api/agent 和 @/api/cards。样式复用 tokens.css 的 :root 变量，不引入深色分支。
*/
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { getAgentStatus, getProfile, applyVerify, revertVerify } from '@/api/agent'
import * as cardsApi from '@/api/cards'
import { useChatStore } from '@/stores/chat'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

/* 会话状态全在 chat store（模块级）：问完切走页面，请求照样跑完写回，
 * 回来还在。本组件只剩渲染与视图态（滚动、抽屉、引用标题映射）。 */
const chat = useChatStore()
const { messages, input, mode, webSearch, sending, profile } = storeToRefs(chat)
const { send, clearChat } = chat

const cardMap = reactive({}) // id -> title，引用卡片展示用
const scrollEl = ref(null)
const status = ref({ ok: false, msg: '' })

const drawer = reactive({ open: false, card: null, loading: false })

// 生成中每来一段就滚一次。store 不碰 DOM，滚动是视图的活；
// 页面切走后 scrollEl 为 null，scrollToBottom 里有判断，不会炸。
watch(messages, () => scrollToBottom(), { deep: true })

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
    // getProfile() 已返回档案本身（解包在 api/agent.js）
    const p = await getProfile()
    profile.value = p && (p.role || (p.topics || []).length || (p.weak || []).length) ? p : null
  } catch {
    /* 档案拿不到就是没有，问答照常 */
  }
}

onMounted(() => {
  if (messages.value.length) scrollToBottom() // 恢复的历史也要滚到最新一条
  loadMeta()
})

function onSuggest(s) {
  input.value = s
  send()
}

function titleOf(id) {
  return cardMap[id] || id
}

/** 已知步骤是否全做完了。用来判断「步骤帧已到齐、但正文还没出字」的那段空窗，
 *  这时候要补一条不确定态的等待行，否则等待动画会断一下。 */
function allStepsDone(m) {
  return !!(m.steps && m.steps.length && m.steps.every(s => s.done))
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

/* ---- react 回答后的卡片校验（反问用户是否修正）----
 * 校验是 react 问答的内置环节：答完 → 拿联网资料核对引用到的卡 → 有错就
 * 挂一条 verify 建议到该条消息上（m.verify），在这里渲染「是否修正」。
 * 用户点「修正」才调 apply 落库，点「忽略」只收起 —— 绝不自动改知识库。 */
const FIELD_LABEL = {
  oneLine: '一句话结论',
  mechanism: '原理拆解',
  why: '为什么',
  analogy: '类比',
  scene: '使用场景',
  keywords: '关键词',
  interviewQ: '面试追问'
}

// 修正中 / 已处理的卡片 id：按钮置灰防重复点
const fixBusy = ref('')
const fixedIds = ref([])      // 已点过「修正」的卡
const ignoredIds = ref([])    // 已点过「忽略」的卡

function isFixed(id) {
  return fixedIds.value.includes(id)
}
function isIgnored(id) {
  return ignoredIds.value.includes(id)
}

async function applySuggestion(m, s) {
  if (!s || !s.card_id || fixBusy.value) return
  fixBusy.value = s.card_id
  try {
    await applyVerify({ card_id: s.card_id, patch: s.proposed_patch || {} })
    if (!fixedIds.value.includes(s.card_id)) fixedIds.value.push(s.card_id)
    ElMessage.success('已修正这张卡，检索/问答立即生效')
  } catch (e) {
    ElMessage.error('修正失败：' + (e && e.message ? e.message : e))
  } finally {
    fixBusy.value = ''
  }
}

function ignoreSuggestion(m, s) {
  if (!s || !s.card_id) return
  if (!ignoredIds.value.includes(s.card_id)) ignoredIds.value.push(s.card_id)
  ElMessage.info('已忽略本次建议，卡片保持原样')
}

async function revertSuggestion(m, s) {
  if (!s || !s.card_id || fixBusy.value) return
  fixBusy.value = s.card_id
  try {
    await revertVerify({ card_id: s.card_id })
    fixedIds.value = fixedIds.value.filter(x => x !== s.card_id)
    ElMessage.success('已还原为原始内容')
  } catch (e) {
    ElMessage.error('还原失败：' + (e && e.message ? e.message : e))
  } finally {
    fixBusy.value = ''
  }
}

// 一条建议里要展示的字段 diff（字段名 → 中文标签 + 建议新值）
function diffFields(s) {
  const p = (s && s.proposed_patch) || {}
  return Object.keys(p).map(k => ({ field: k, label: FIELD_LABEL[k] || k, val: p[k] }))
}
</script>

<template>
  <div class="ask">
    <!-- 顶栏：标题 + 模式切换 + 联网开关 + 档案 + AI 状态 -->
    <div class="head">
      <div class="head-l">
        <div class="seg">
          <button :class="{ on: mode === 'flow' }" @click="mode = 'flow'">知识库问答</button>
          <button :class="{ on: mode === 'react' }" @click="mode = 'react'">Agent（流式）</button>
        </div>
        <button
          class="ghost"
          :class="{ on: webSearch }"
          :title="
            webSearch
              ? '联网已开：回答会附带网页搜索结果（点击关闭）'
              : '点击开启联网：回答会附带网页搜索结果，适合问最新现状'
          "
          @click="webSearch = !webSearch"
        >
          联网{{ webSearch ? '·开' : '' }}
        </button>
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
              ? 'AI 已就绪 · ' +
                (mode === 'flow' ? '带引用' : '流式') +
                (webSearch ? ' · 联网' : '')
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
<!-- Agent 步骤条 / 等待态。
     ★ 规则：**一个字的正文都没出来时就显示等待提示；字一出来立刻收场。**
     - 出字前（本地 8B 要几十秒）：显示「在做什么」，解释为什么还在等。
     - 出字后：正文自己在滚，等待提示立刻消失。之前它不消失，
       用户看到「答案在滚、下面还有个圈转」，像卡住了。
     ★★ **绝不能出现「空气泡」**：发消息到第一个 step 帧到达之间有几十~几百 ms，
       此时 m.steps 还是空数组，如果只 v-for 遍历它，
       气泡会渲染出来但里面什么都没有 —— 用户看到一颗空白的胶囊，
       反而比没有动画更糟（实测截图就是这个）。所以下面必须有一条
       「还没收到任何步骤」的兜底行。 -->
<div v-if="m.streaming && !m.text" class="steps">
  <div v-for="(s, si) in m.steps" :key="si" class="step" :class="{ act: !s.done, fin: s.done }">
    <i class="sd" />{{ s.text }}
  </div>
  <!-- 兜底 A：一个步骤帧都还没到（网络/首帧延迟）→ 先给一句「正在思考」，
       避免出现空白气泡 -->
  <div v-if="!m.steps || !m.steps.length" class="step act">
    <i class="sd" />正在思考…
  </div>
  <!-- 兜底 B：已知步骤都做完了、正文还没出字 → 接住这段空窗 -->
  <div v-else-if="allStepsDone(m)" class="step act">
    <i class="sd" />正在组织回答…
  </div>
</div>
          <!-- 公式/代码/Markdown 渲染：MarkdownRenderer（KaTeX + marked + hljs） -->
          <MarkdownRenderer :text="m.text" class="body" />

          <div v-if="m.role === 'assistant' && m.sources && m.sources.length" class="srcs">
            <span class="src-label">引用卡片</span>
            <button v-for="id in m.sources" :key="id" class="chip" @click="openCard(id)">
              {{ titleOf(id) }}
            </button>
          </div>

          <!-- 后台核对（卡片校验）提示。
               ★ 刻意**不用转圈**，用呼吸点：这是后台增强，不是回答的必经环节，
               转圈会让人以为「答完了还在加载」（实测反馈过这个观感）。
               有建议时下面会直接出「是否修正」，没建议就自己淡出。 -->
          <div v-if="m.bgStep" class="bgstep">
            <i class="bdot" />{{ m.bgStep }}
          </div>

          <!-- react 答完后的卡片校验：拿联网资料核对引用卡，有错就反问是否修正 -->
          <div v-if="m.role === 'assistant' && m.verify && m.verify.length" class="vcheck">
            <div v-for="s in m.verify" :key="s.card_id" class="vcard">
              <div class="vcard-h">
                <span class="vcard-badge">校验发现可疑</span>
                <b>{{ s.title }}</b>
              </div>
              <p class="vcard-sum">{{ s.summary }}</p>
              <div v-for="(is, i) in s.issues || []" :key="i" class="vcard-issue">
                · [{{ FIELD_LABEL[is.field] || is.field }}] {{ is.why }}
              </div>
              <div v-for="d in diffFields(s)" :key="d.field" class="vcard-diff">
                <span class="vcard-dk">{{ d.label }}</span>
                <div class="vcard-dnew">{{ d.val }}</div>
              </div>
              <div class="vcard-act">
                <template v-if="isFixed(s.card_id)">
                  <span class="vcard-done">已修正 ✓</span>
                  <button class="ghost" :disabled="fixBusy === s.card_id" @click="revertSuggestion(m, s)">还原</button>
                </template>
                <template v-else-if="isIgnored(s.card_id)">
                  <span class="vcard-done">已忽略，卡片保持原样</span>
                </template>
                <template v-else>
                  <button class="send vbtn" :disabled="fixBusy === s.card_id" @click="applySuggestion(m, s)">
                    {{ fixBusy === s.card_id ? '修正中…' : '确认修正' }}
                  </button>
                  <button class="ghost" @click="ignoreSuggestion(m, s)">忽略</button>
                </template>
              </div>
            </div>
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
          <MarkdownRenderer :text="drawer.card.oneLine" class="d-one" />
          <div v-if="drawer.card.analogy" class="d-block">
            <span class="d-k">类比</span>
            <MarkdownRenderer :text="drawer.card.analogy" />
          </div>
          <div v-if="drawer.card.mechanism" class="d-block">
            <span class="d-k">原理</span>
            <div v-for="(s, k) in drawer.card.mechanism" :key="k" class="d-mech">
              <MarkdownRenderer :text="s" />
            </div>
          </div>
          <div v-if="drawer.card.scene" class="d-block">
            <span class="d-k">场景</span>
            <div v-for="(s, k) in drawer.card.scene" :key="k" class="d-scene">
              <MarkdownRenderer :text="s" />
            </div>
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
.head-l {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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
/* 联网开关的选中态：复用 .ghost 外壳，开着时填成主色（和 .seg button.on 一致） */
.ghost.on {
  background: var(--ac);
  border-color: var(--ac);
  color: #fdfaf3;
}
.ghost.on:hover {
  color: #fdfaf3;
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
  max-width: 82%;
  padding: 13px 16px;
  border-radius: 16px;
  font-size: var(--fs-md);
  line-height: 1.78;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--line);
  /* 纸面上的气泡要「浮」起来一点：极轻的双层阴影，够看出层次又不脏 */
  box-shadow:
    0 1px 2px rgba(58, 47, 33, 0.04),
    0 3px 10px -6px rgba(58, 47, 33, 0.14);
}
/* 用户气泡：靛蓝墨水。用极轻的纵向渐变代替纯色实心块 ——
   同样的靛蓝，但有了「墨从纸上洇开」的层次，不再是一块死蓝。 */
/* 用户气泡：**不再用实心深靛蓝**。
 * 实心深色块压在牛皮纸上像贴上去的色片，跟整页的"纸质"打架；
 * 而且深底对��比度再高，长句读起来也费劲（而且早期还有深底深字的 bug）。
 * 改成「淡靛蓝底+ 深靛蓝字 + 靛蓝细边」—— 同一色相族，
 * 仍然分得清谁说的话，但仍然属于这张纸。 */
.row.user .bubble {
  background: linear-gradient(168deg, color-mix(in srgb, var(--ac) 9%, var(--panel)) 0%,
    color-mix(in srgb, var(--ac) 14%, var(--panel2)) 100%);
  color: var(--ac-dim);
  border-color: color-mix(in srgb, var(--ac) 26%, var(--line));
  border-bottom-right-radius: 5px;
  box-shadow:
    0 1px 2px rgba(58, 47, 33, 0.04),
    0 3px 10px -7px rgba(31, 75, 107, 0.24);
}
.row.assistant .bubble {
  background: linear-gradient(180deg, #fbf7ec 0%, var(--panel) 100%);
  color: var(--tx);
  border-bottom-left-radius: 5px;
}
/* 助手气泡里的引用芯片在浅底上要压得住 */
.row.assistant .bubble .chip {
  background: var(--panel2);
}
/* ★ 气泡里的 Markdown 正文**必须关掉 pre-wrap**。
 * 之前 .bubble 上开着 white-space:pre-wrap，而正文由 MarkdownRenderer
 * 渲染成<p>/<ul>/<li> —— pre-wrap 让 HTML 里的换行/缩进**全部变成真实空白行**：
 * 一个 <p> 的 margin 之外还叠了三四个空行，长回答里像漏了一半内容。
 * Markdown 自己有块级元素提供间距，不需要保留源码换行；
 * pre-wrap 只留给「出错提示」那种纯文本（见 .err / .typing）。 */
.body {
  white-space: normal;
}
/* 用户提问是**纯文本**（没有 Markdown 结构），他打的换行是有意的
 * —— 多行提问要按原样显示。所以只给用户气泡恢复 pre-wrap。 */
.row.user .body {
  white-space: pre-wrap;
}
.body :deep(p) {
  margin: 0 0 8px;
  /* 段首缩进 2 字符 —— 中文排版的常规做法。模型输出是标准 Markdown，
   * 所有段落顶格会让长回答像一张清单，读起来"怪"。
   * 用 text-indent 只缩进**第一行**（第二行顶格才是对的），
   * 不要用 padding/margin-left，那会把整块都推走。 */
  text-indent: 2em;
}
.body :deep(p:last-child) {
  margin-bottom: 0;
}
/* 但下面这几种情况**不能缩进**，否则会跟它们自己的符号/缩进叠在一起：
 *  - 列表项里的段落：<li> 已经带项目符号和左缩进，再缩进两字会双重缩进
 *  - 引用块：缩进本身就是「引别人的话」的语义标记
 *  - 代码块：是 pre，压根不受 text-indent 影响 */
.body :deep(li p),
.body :deep(blockquote p) {
  text-indent: 0;
}
/* 用户提问语义上是一句话、不是段落，缩进只会怪。 */
.row.user .body :deep(p) {
  text-indent: 0;
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
/* 输入区：做成一个独立的圆角容器（不再是「一条线 + 两个控件」）。
   聚焦时整圈描边变靛蓝并浮起一点，像一张等着落笔的纸。 */
.bar {
  flex: none;
  display: flex;
  gap: 8px;
  align-items: flex-end;
  margin: 12px 4px 4px;
  padding: 8px 8px 8px 16px;
  background: var(--panel);
  border: 1px solid var(--line2);
  border-radius: 20px;
  box-shadow:
    0 1px 2px rgba(58, 47, 33, 0.04),
    0 6px 18px -10px rgba(58, 47, 33, 0.22);
  transition:
    border-color 0.18s,
    box-shadow 0.18s;
}
.bar:focus-within {
  border-color: var(--ac);
  box-shadow:
    0 1px 2px rgba(31, 75, 107, 0.1),
    0 6px 20px -8px rgba(31, 75, 107, 0.3);
}
.ta {
  flex: 1;
  resize: none;
  border: 0;
  background: transparent;
  color: var(--tx);
  font: inherit;
  font-size: var(--fs-md);
  padding: 8px 0;
  line-height: 1.65;
  outline: none;
}
.send {
  flex: none;
  height: 38px;
  padding: 0 20px;
  border: 0;
  border-radius: 14px;
  background: linear-gradient(168deg, #2a5a80 0%, var(--ac) 62%);
  color: #f6f1e6;
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 0 3px 10px -4px rgba(26, 64, 89, 0.5);
  transition:
    opacity 0.16s,
    transform 0.16s,
    box-shadow 0.16s;
}
.send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 5px 14px -5px rgba(26, 64, 89, 0.6);
}
.send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
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

/* react 回答后的卡片校验块（聊天气泡内） */
.vcheck {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--line2);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.vcard {
  border: 1px solid var(--line2);
  border-radius: var(--radius-sm);
  background: var(--bg);
  padding: 10px 12px;
}
.vcard-h {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-sm);
  color: var(--tx);
  margin-bottom: 6px;
}
.vcard-badge {
  flex: none;
  font-size: var(--fs-xs);
  color: #b4553f;
  border: 1px solid #b4553f;
  border-radius: 999px;
  padding: 1px 8px;
}
.vcard-sum {
  font-size: var(--fs-xs);
  color: var(--mu);
  line-height: 1.6;
  margin: 0 0 6px;
}
.vcard-issue {
  font-size: var(--fs-xs);
  color: var(--tx);
  line-height: 1.6;
  margin: 3px 0;
}
.vcard-diff {
  margin: 6px 0;
  padding: 6px 8px;
  border: 1px dashed var(--line2);
  border-radius: var(--radius-sm);
}
.vcard-dk {
  font-size: var(--fs-xs);
  color: var(--mu);
  font-weight: 600;
}
.vcard-dnew {
  white-space: pre-wrap;
  font-size: var(--fs-xs);
  color: var(--tx);
  line-height: 1.6;
  margin-top: 2px;
}
.vcard-act {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.vcard-done {
  font-size: var(--fs-xs);
  color: #2f7a4f;
}
.vbtn {
  height: 30px;
  padding: 0 14px;
  font-size: var(--fs-xs);
  border-radius: var(--radius-sm);
}

/* Agent 步骤条 */
.steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}
.step {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: var(--fs-xs);
  color: var(--mu);
  line-height: 1.6;
}
.step .sd {
  flex: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid var(--line2);
  position: relative;
}
.step.fin .sd {
  border-color: #2f7a4f;
  background: #2f7a4f;
}
.step.fin .sd::after {
  /* 勾 */
  content: '';
  position: absolute;
  left: 3.5px;
  top: 0.5px;
  width: 3px;
  height: 6px;
  border: solid #fdfaf3;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(43deg);
}

/* ===== 后台核对提示（卡片校验）=====
   ★ 呼吸点不是转圈：这个步骤发生在**答案已经显示之后**，
   转圈会让用户误以为「还没答完」，实测反馈过这个观感问题。
   呼吸点（透明度缓慢起伏）传达「在后台进行、但不影响你」。 */
.bgstep {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  font-size: var(--fs-xs);
  color: var(--dim);
}
.bdot {
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ac);
  animation: breathe 1.6s ease-in-out infinite;
}
@keyframes breathe {
  0%,
  100% {
    opacity: 0.28;
    transform: scale(0.82);
  }
  50% {
    opacity: 0.85;
    transform: scale(1);
  }
}
.step.act {
  color: var(--tx);
}
.step.act .sd {
  border-color: var(--ac);
  border-right-color: transparent;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ---- 代码块（豆包风格）：圆角 + 浅底 + 语言标签 + 等宽字体 ----
   回答正文是 v-html 渲染的，拿不到 scoped 的 data-v 属性，所以样式必须 :deep()。
   横向滚动（white-space:pre）而不是折行 —— 代码折行会让缩进对不上，反而更难读。 */
.body :deep(.code-block) {
  margin: 12px 0;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel2);
  overflow: hidden;
}
.body :deep(.code-head) {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: color-mix(in srgb, var(--line) 40%, transparent);
  border-bottom: 1px solid var(--line);
}
.body :deep(.code-lang) {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--dim);
}
.body :deep(.code-pre) {
  margin: 0;
  padding: 12px 14px;
  overflow-x: auto;
}
.body :deep(.code-pre code) {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  line-height: 1.7;
  color: var(--tx);
  white-space: pre;
}
</style>
