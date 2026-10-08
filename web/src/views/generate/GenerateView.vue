<script setup>
/* 生成 —— 粘贴一大段文字，切成草稿卡，补齐字段后发布。
 *
 * ## 为什么中间要有一层草稿
 *
 * 机器切出来的卡**永远差一口气**：title 是原文第一句、scene 是占位符、
 * analogy 压根没有。直接入库的结果是库里混进一批半成品，
 * 而用户往往要等很久才会发现某张卡是残的 —— 那时已经用它复习过了。
 *
 * 所以流程是单向的：文本 → 草稿 →（人工或 AI 补齐）→ 发布。
 * 草稿单独一张表，不出现在正式卡列表里。
 *
 * ## 发布门槛
 *
 * 后端要求 scene（应用场景）至少 2 条非空、非占位。
 * 这不是刁难：一张没有场景的技术卡，背下来也不知道什么时候该说。
 * 前端在这里把门槛讲清楚，而不是等接口报 400 才让用户猜。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  clearDrafts,
  dropDraft,
  importText,
  listDrafts,
  patchDraft,
  publishDraft
} from '@/api/imports'
import { fillDraft, getLlmStatus } from '@/api/ai'
import { getToken } from '@/api/client'
import { job as fillJob, runFillAll, cancelFill } from './fillJob'

/** 草稿配图地址 + 登录态（<img> 不发 Authorization 头，token 走 ?t=）。 */
function imgSrc(im) {
  const sep = String(im.src || '').includes('?') ? '&' : '?'
  const t = getToken()
  return (im.src || '') + (t ? sep + 't=' + encodeURIComponent(t) : '')
}

/** 贴了一半的正文刷新不该没：setup 期直接从 localStorage 起。
 *  截 1MB —— localStorage 总配额才 5MB，整份文件塞进来是给别人的数据腾地方。 */
const text = ref(localStorage.getItem('edu.genText') || '')
const useLLM = ref(false)
const splitting = ref(false)
const drafts = ref([])
/** 正在编辑的草稿 id。同时只展开一条 —— 全展开会让页面变成一堆表单。 */
const editing = ref('')
const busy = ref({})

const llm = ref({ ok: false, provider: '', msg: '' })

/** 表单缓存。key 是草稿 id，value 是正在编辑的字段。
 *  不直接改 drafts 里的对象：发布失败了要能原样退回去 */
const form = ref({})

function saveText() {
  try {
    if (text.value && text.value.length < 1024 * 1024) {
      localStorage.setItem('edu.genText', text.value)
    } else localStorage.removeItem('edu.genText') // 空或超大都不留
  } catch {
    /* 配额满了就不存 */
  }
}

/** 展开中的表单连着编辑进度一起存；关掉/保存后清掉（editing 变空即触发）。 */
function saveForm() {
  try {
    if (editing.value && form.value[editing.value]) {
      localStorage.setItem(
        'edu.genForm',
        JSON.stringify({ editing: editing.value, form: form.value })
      )
    } else localStorage.removeItem('edu.genForm')
  } catch {
    /* 忽略 */
  }
}

watch(text, saveText)
watch([editing, form], saveForm, { deep: true })

/** 占位符识别：`（待补充...）` 这类文本不算真正补齐。
 *  不判断的话用户原样提交占位符也能发布，门槛就形同虚设。 */
function isFilled(s) {
  const t = String(s ?? '').trim()
  return t.length >= 4 && !t.startsWith('（待补充')
}

const llmTip = computed(() => {
  if (!llm.value.ok) return 'AI 抽词未启用，将使用本地规则切分'
  return `AI 抽词可用：${llm.value.provider || ''} ${llm.value.model || ''}`.trim()
})

onMounted(async () => {
  // 恢复上次没写完的编辑框；草稿可能已被发布/丢弃，对着不存在的草稿
  // 展开表单没有意义，拉完列表对不上就直接清
  try {
    const saved = JSON.parse(localStorage.getItem('edu.genForm') || 'null')
    if (saved && saved.editing && saved.form && saved.form[saved.editing]) {
      editing.value = saved.editing
      form.value = saved.form
    }
  } catch {
    /* 坏数据不恢复 */
  }
  await Promise.all([fetchDrafts(), fetchLlm()])
  if (editing.value && !drafts.value.some(d => d.id === editing.value)) {
    editing.value = ''
    form.value = {}
  }
})

async function fetchDrafts() {
  drafts.value = (await listDrafts()).drafts || []
}

async function fetchLlm() {
  try {
    llm.value = await getLlmStatus()
  } catch {
    // AI 状态拿不到就按未启用处理：它是可选增强，不该拖垮整页
    llm.value = { ok: false, provider: '', msg: '' }
  }
}

async function onSplit() {
  const t = text.value.trim()
  if (t.length < 12) {
    ElMessage.warning('至少贴进来十几个字才切得出东西')
    return
  }
  splitting.value = true
  try {
    const r = await importText({ text: t, useLLM: useLLM.value && llm.value.ok })
    await fetchDrafts()
    ElMessage.success(`切出 ${r.drafts?.length || 0} 条草稿`)
    text.value = ''
  } finally {
    splitting.value = false
  }
}

function startEdit(d) {
  editing.value = d.id
  syncForm(d.id)
}

/** 草稿 → 表单缓存（新建或覆盖）。startEdit 和「AI 补齐」共用：
 *  补齐会改字段，正在编辑的表单不同步就会把刚补上的内容盖回旧的。 */
function syncForm(did) {
  const d = drafts.value.find(x => x.id === did)
  if (!d) return
  form.value[did] = {
    title: d.title || '',
    oneLine: d.oneLine || '',
    scene: (d.scene || []).join('\n'),
    keywords: (d.keywords || []).join(', '),
    interviewQ: (d.interviewQ || []).join('\n')
  }
}

function cancelEdit(did) {
  editing.value = ''
  delete form.value[did]
}

/** 这条草稿离发布还差什么。**返回空数组就是可以发布了**。
 *  把「为什么不能发布」讲出来，比让接口甩一个 400 友好得多。 */
function blockers(d) {
  const out = []
  const real = (d.scene || []).filter(isFilled)
  if (real.length < 2) out.push(`场景还差 ${2 - real.length} 条`)
  if (!String(d.title || '').trim()) out.push('缺标题')
  return out
}

function ready(d) {
  return blockers(d).length === 0
}

async function onSave(d) {
  const f = form.value[d.id]
  if (!f) return
  busy.value[d.id] = 'save'
  try {
    await patchDraft(d.id, {
      title: f.title,
      oneLine: f.oneLine,
      scene: f.scene
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean),
      keywords: f.keywords
        .split(/[,，]/)
        .map(s => s.trim())
        .filter(Boolean),
      interviewQ: f.interviewQ
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean)
    })
    await fetchDrafts()
    cancelEdit(d.id)
    ElMessage.success('已保存')
  } finally {
    delete busy.value[d.id]
  }
}

async function onPublish(d) {
  busy.value[d.id] = 'publish'
  try {
    await publishDraft(d.id)
    ElMessage.success(`《${d.title}》已发布为正式卡`)
    await fetchDrafts()
  } finally {
    delete busy.value[d.id]
  }
}

/** AI 补齐：整张卡通读一遍 —— 缺的补上、占位/偏薄的重写（后端尽力找回原文，
 *  有原文时事实以原文为准）。单张跑：一次只补这一张，结果报「补了什么」。 */
async function onFill(d) {
  if (!llm.value.ok) {
    ElMessage.warning('AI 未启用：' + (llm.value.msg || '没配置模型'))
    return
  }
  busy.value[d.id] = 'fill'
  try {
    const r = await fillDraft(d.id)
    await fetchDrafts()
    if (editing.value === d.id) syncForm(d.id) // 正在编辑就同步进表单，别盖回旧值
    const names = {
      title: '标题',
      oneLine: '一句话',
      analogy: '类比',
      why: '为什么',
      mechanism: '原理步骤',
      keywords: '关键词',
      scene: '场景',
      interviewQ: '追问'
    }
    const what = (r.changed || []).map(k => names[k] || k)
    if (what.length) ElMessage.success(`已补齐：${what.join('、')}`)
    // changed 空 = 模型没给任何可更新的值（字段名对不上 / 内容没变）。
    // 从前这里报成功，用户明明看到表单没变，读起来就是「补齐是空的」
    else ElMessage.warning('AI 通读后没有补出新内容，试试「手工补齐」')
  } catch (e) {
    ElMessage.error(e?.message || 'AI 补齐失败')
  } finally {
    delete busy.value[d.id]
  }
}

/** AI 补齐（全部）：逐张排进 fillJob 队列 —— 页面切走队列照跑，单张失败不
 *  断队。串行是刻意的：本地 8B 一次只跑一路，并发只是互相抢显存。 */
async function onFillAll() {
  if (!llm.value.ok) {
    ElMessage.warning('AI 未启用：' + (llm.value.msg || '没配置模型'))
    return
  }
  if (!drafts.value.length || (fillJob.value && fillJob.value.running)) return
  const list = drafts.value.map(d => ({ id: d.id, title: d.title }))
  const sum = await runFillAll(list, {
    start: id => {
      busy.value[id] = 'fill'
    },
    // 每张跑完刷新一次：用户看着字段一张张被补上，正在编辑的表单同步新值
    after: async id => {
      delete busy.value[id]
      await fetchDrafts()
      if (editing.value === id) syncForm(id)
    }
  })
  if (sum.skipped) return
  if (sum.failed.length) {
    const f = sum.failed[0]
    ElMessage.error(
      `补齐完成 ${sum.ok}/${list.length}：${sum.failed.length} 张失败（${f.title}：${f.msg}）`
    )
  } else if (sum.ok) {
    ElMessage.success(`补齐完成：${sum.ok} 张有新内容${sum.empty ? `，${sum.empty} 张没变化` : ''}`)
  } else ElMessage.warning('AI 通读后没有补出新内容，试试「手工补齐」')
}

async function onDrop(d) {
  try {
    await ElMessageBox.confirm('丢弃这条草稿？', '确认', {
      type: 'warning',
      confirmButtonText: '丢弃',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  await dropDraft(d.id)
  await fetchDrafts()
}

async function onClear() {
  if (!drafts.value.length) return
  try {
    await ElMessageBox.confirm(`清空全部 ${drafts.value.length} 条草稿？清空后不能恢复。`, '确认', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  await clearDrafts()
  await fetchDrafts()
  ElMessage.success('已清空')
}
</script>

<template>
  <div class="gen">
    <!-- ===== 左：输入 ===== -->
    <section class="panel">
      <header class="panel-head">
        <h3>粘贴文本</h3>
        <span class="hint">按空行分段</span>
      </header>

      <el-input
        v-model="text"
        type="textarea"
        :rows="12"
        resize="vertical"
        placeholder="把笔记、面经、文档里的一段粘进来。空行会被切成不同的 mechanism 步骤。"
      />

      <div class="row-between" style="margin-top: 14px">
        <span class="counter" :class="{ over: text.length > 4000 }"> {{ text.length }} 字 </span>
        <span class="muted">建议 200–4000 字，太短切不出结构、太长会切成一堆碎片</span>
      </div>

      <div class="opt">
        <label class="switch">
          <el-switch v-model="useLLM" :disabled="!llm.ok" />
          <span class="sw-txt">用 AI 抽 title / oneLine<em v-if="!llm.ok">（不可用）</em></span>
        </label>
        <span class="tip">{{ llmTip }}</span>
      </div>

      <button class="btn btn-primary block" :disabled="splitting" @click="onSplit">
        <svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h13" /></svg>
        {{ splitting ? '切分中…' : '切成草稿' }}
      </button>
    </section>

    <!-- ===== 右：草稿 ===== -->
    <section class="panel">
      <header class="panel-head">
        <h3>
          草稿 <span class="count">{{ drafts.length }} 条</span>
        </h3>
        <div class="head-acts">
          <span v-if="fillJob?.running" class="fill-prog">
            补齐中 {{ fillJob.done }}/{{ fillJob.total }}
          </span>
          <button v-if="fillJob?.running" class="btn btn-bare" @click="cancelFill">取消</button>
          <button
            v-else-if="drafts.length"
            class="btn btn-ghost"
            :disabled="!llm.ok"
            :title="llm.ok ? '逐张通读排队补齐，可以切去别的页面，回来看进度' : llmTip"
            @click="onFillAll"
          >
            AI 补齐全部
          </button>
          <button
            v-if="drafts.length"
            class="btn btn-bare"
            :disabled="fillJob?.running"
            @click="onClear"
          >
            清空
          </button>
        </div>
      </header>

      <p v-if="!drafts.length" class="empty">
        <span class="big">还没有草稿</span>
        左边粘一段文字，点「切成草稿」
      </p>

      <div v-else class="dlist">
        <article v-for="d in drafts" :key="d.id" class="draft" :class="{ on: editing === d.id }">
          <header class="d-head">
            <div class="d-title-wrap">
              <h4 class="d-title">{{ d.title }}</h4>
              <span class="chip">{{ d.domain || '待归类' }}</span>
              <span v-if="d._from === 'llm'" class="chip accent">AI 抽词</span>
              <span v-if="d._from === 'agent-cards'" class="chip accent">Agent 出卡</span>
              <!-- 卡片组：这份草稿来自哪份上传的文档 -->
              <span v-if="d.deck" class="chip" :title="`来自《${d.deck}》`">《{{ d.deck }}》</span>
            </div>
            <div class="d-act">
              <template v-if="editing === d.id">
                <button class="btn btn-ghost" @click="cancelEdit(d.id)">取消</button>
                <button class="btn btn-primary" :disabled="busy[d.id]" @click="onSave(d)">
                  保存
                </button>
              </template>
              <template v-else>
                <button
                  class="btn btn-ghost"
                  :disabled="busy[d.id] || fillJob?.running"
                  @click="onFill(d)"
                >
                  {{ busy[d.id] === 'fill' ? 'AI 补齐中…' : 'AI 补齐' }}
                </button>
                <button class="btn btn-ghost" @click="startEdit(d)">手工补齐</button>
                <button
                  class="btn btn-primary"
                  :disabled="!ready(d) || busy[d.id]"
                  @click="onPublish(d)"
                >
                  {{ busy[d.id] === 'publish' ? '发布中…' : '发布' }}
                </button>
                <button class="btn btn-danger" @click="onDrop(d)">丢弃</button>
              </template>
            </div>
          </header>

          <!-- 未就绪时明说缺什么，而不是禁用了事 -->
          <p v-if="!ready(d)" class="blockers">
            <svg viewBox="0 0 24 24">
              <path d="M12 8v5M12 16.5v.01" />
              <circle cx="12" cy="12" r="9" />
            </svg>
            还不能发布：{{ blockers(d).join('、') }}
          </p>

          <p class="d-oneline">{{ d.oneLine }}</p>

          <!-- Agent 出的卡带原文配图：发布前先在这看一眼图和图注对不对 -->
          <div v-if="d.images?.length" class="d-imgs">
            <figure v-for="(im, i) in d.images" :key="i">
              <img :src="imgSrc(im)" :alt="im.name || '配图'" loading="lazy" />
              <figcaption v-if="im.caption">{{ im.caption }}</figcaption>
            </figure>
          </div>

          <details class="d-more">
            <summary>切出的 {{ (d.mechanism || []).length }} 个步骤</summary>
            <ol class="mech">
              <li v-for="(m, i) in d.mechanism || []" :key="i">{{ m }}</li>
            </ol>
          </details>

          <!-- 编辑区 -->
          <div v-if="editing === d.id" class="edit">
            <label class="field">
              <span class="lb">标题</span>
              <el-input v-model="form[d.id].title" />
            </label>
            <label class="field">
              <span class="lb">一句话说明</span>
              <el-input v-model="form[d.id].oneLine" />
            </label>
            <label class="field">
              <span class="lb"
                >应用场景<em class="muted">每行一条，至少 2 条 —— 缺了发不了</em></span
              >
              <el-input
                v-model="form[d.id].scene"
                type="textarea"
                :rows="3"
                placeholder="在慢查询治理中用来定位回表开销&#10;面试被问到「MySQL 5.6 之后有哪些优化」时举例"
              />
            </label>
            <label class="field">
              <span class="lb">面试追问<em class="muted">每行一条</em></span>
              <el-input v-model="form[d.id].interviewQ" type="textarea" :rows="2" />
            </label>
            <label class="field">
              <span class="lb">关键词<em class="muted">逗号分隔</em></span>
              <el-input v-model="form[d.id].keywords" />
            </label>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gen {
  display: grid;
  grid-template-columns: minmax(320px, 420px) 1fr;
  gap: 16px;
  align-items: start;
}

/* 宽屏：两列各自独立滚动 —— 滚左列不动右列。
   原理：.content 是 flex:1（definite 高），根容器 height:100% 正好占满它，
   列 stretch 撑满后内部各自 overflow-y:auto，页面本身就不再滚了。
   align-items 必须从 start 改回 stretch：start 会让列按内容高度、整页一起滚。
   窄屏（≤1080px）单列堆叠，留在整页滚，不做独立滚动。 */
@media (min-width: 1081px) {
  .gen {
    height: 100%;
    align-items: stretch;
  }
  .gen > .panel {
    min-height: 0;
    overflow-y: auto;
  }
}

.counter {
  font-size: var(--fs-sm);
  color: var(--mu);
  font-variant-numeric: tabular-nums;
}
.counter.over {
  color: var(--amber);
}

.opt {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 14px 0 16px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  border: 1px dashed var(--line2);
  background: var(--panel2);
}
.switch {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
.sw-txt {
  font-size: var(--fs-sm);
  font-weight: 500;
}
.sw-txt em {
  font-style: normal;
  color: var(--dim);
}
.tip {
  font-size: var(--fs-xs);
  color: var(--dim);
}

.block {
  width: 100%;
  justify-content: center;
}

.dlist {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.draft {
  padding: 14px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--panel2);
  transition: border-color 0.16s;
}
.draft:hover {
  border-color: var(--line2);
}
.draft.on {
  border-color: var(--ac);
  background: var(--ac-glow);
}
.d-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}
.d-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.d-title {
  font-size: var(--fs-md);
  font-weight: 600;
}
.d-act {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.count {
  font-size: var(--fs-xs);
  font-weight: 400;
  color: var(--dim);
}

/* 标题行右侧的批量操作：进度 + 取消 / 补齐全部 / 清空 */
.head-acts {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.fill-prog {
  font-size: var(--fs-xs);
  color: var(--ac);
  font-variant-numeric: tabular-nums;
}

.blockers {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0;
  font-size: var(--fs-sm);
  color: var(--amber);
}
.blockers svg {
  width: 15px;
  height: 15px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}

.d-oneline {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.7;
  margin: 8px 0;
}

/* 草稿配图：横排小缩略图，图注在下。发布前肉眼校验图和图注对不对 */
.d-imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 6px 0;
}
.d-imgs figure {
  margin: 0;
  max-width: 220px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.d-imgs img {
  max-width: 100%;
  max-height: 140px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--bg2);
}
.d-imgs figcaption {
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--dim);
}

.d-more {
  font-size: var(--fs-sm);
}
.d-more summary {
  cursor: pointer;
  color: var(--ac);
  padding: 4px 0;
  user-select: none;
}
.mech {
  margin: 6px 0 0 18px;
  color: var(--mu);
  line-height: 1.75;
}
.mech li {
  margin-bottom: 4px;
}

.edit {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.lb {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--mu);
}
.lb em {
  font-style: normal;
  font-weight: 400;
  margin-left: 6px;
}

@media (max-width: 1080px) {
  .gen {
    grid-template-columns: 1fr;
  }
}
</style>
