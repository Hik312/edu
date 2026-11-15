<script setup>
/* 论文双语对照 —— 左：原 PDF 文档（真实渲染，等比缩小）；右：中文译文。
 *
 * ## 为什么左边是「PDF 原件」而不是「抽取出来的英文文本」
 * 用户要的是「原文」，而双栏论文的抽取文本是残缺的（左右栏交错、
 * 公式图表丢失、页码混进正文）。原件渲染出来的版面才是真正的原文。
 * 右侧给「附英文」开关：需要时把干净抽取段贴在译文上方，方便逐句核对
 * （PDF 文本层糊掉的时候这一行比 PDF 本身还准）。
 *
 * ## 左右两个独立滚动容器，不再强求逐段对齐
 * PDF 的页是排版单位，译文是阅读单位，两者没法 1:1 对齐；
 * 强行对齐只会让某一边滚动时错位、抖动。
 * 所以这里就是「左 PDF + 右译文」两个并排面板，各自滚动，
 * 用户读译文时随时瞟一眼左边的原件 —— 这正是纸质对照读物的体验。
 *
 * ## 译文从哪来
 * 译文由后端逐段落库（可断点续译），这里永远从服务端读，
 * 本地只存一份增量覆盖。理由：翻译要跑将近半小时，用户可能刷新、
 * 关页面、换设备 —— 本地状态一丢就是几十分钟白跑。
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import PdfViewer from './PdfViewer.vue'
import {
  getTranslation,
  getTranslateStatus,
  runTranslation,
  stopTranslation,
  redoGlossary,
  putGlossaryTerm,
  delGlossaryTerm,
  getMediaUrl,
  captionFigure
} from '@/api/knowledge'

const props = defineProps({
  docId: { type: String, default: '' },
  /** 该文档有没有留抽取文本（纯扫描版 PDF 翻不了） */
  hasText: { type: Boolean, default: false }
})

/* ---------------- 阅读字体 / 字号（用户可在工具条切换） ---------------- */
/* ★ 译文默认用衬线（思源宋体/Noto Serif SC 之类）—— 长段中文用衬线比黑体更像
 *   一本书、读久了不累眼；英文原文用衬线（Source Serif / Georgia）更有论文味。
 *   不习惯衬线可一键切黑体（思源黑体/Noto Sans SC）。
 *   字体走「Web 字体优先 + 系统字体兜底」：离线时自动落到本机宋体/黑体，不会变丑。 */
const fontMode = ref('serif')          // 'serif' | 'sans'
const fontSize = ref(16)               // 译文基准字号(px)
function stepFont(d) {
  fontSize.value = Math.min(21, Math.max(13, fontSize.value + d))
}

/* ---------------- 状态 ---------------- */
const loading = ref(false)
const running = ref(false)
/** 后端返回的全量：{status, segments, translations, glossary, translatable} */
const data = ref(null)
/** 本地覆盖：segI -> {zh,status,...}。翻完的段直接塞这里，界面即时更新。 */
const overlay = ref({})
/** 右侧译文上方是否附上英文原文段（核对用） */
const showSrc = ref(false)

const status = computed(() => data.value?.status || { total: 0, done: 0, ok: 0, warn: 0, bad: 0, pending: 0 })
const pct = computed(() => (status.value.total ? Math.round((status.value.done / status.value.total) * 100) : 0))

/** 合起来看：本地覆盖优先。 */
const merged = computed(() => {
  const out = {}
  for (const k in data.value?.translations || {}) out[k] = data.value.translations[k]
  for (const k in overlay.value) out[k] = overlay.value[k]
  return out
})

/** 段列表 + 每段译文。segments 一定存在（后端一起返回），translations 可能为空。 */
const rows = computed(() =>
  (data.value?.segments || []).map(s => ({
    i: s.i,
    src: s.src,
    zh: (merged.value[s.i]?.zh || '').trim(),
    status: merged.value[s.i]?.status || '',
    score: merged.value[s.i]?.score ?? null,
    missing: merged.value[s.i]?.missing || [],
    translate: s.translate !== false,   // false = 公式/参考文献/图片，原样保留不译
    type: s.type || 'body'
  }))
)

/** 原样保留段的提示文案（公式/参考文献/图片/图内文字/表格/附录不翻译，明确告诉用户）。 */
function keepBadge(r) {
  if (r.translate) return ''
  if (r.type === 'figure') return figInterpreted(r) ? '图片·已中文解读' : '图片·保留原图'
  return { equation: '公式·保留原文', bibliography: '参考文献·保留原文',
           figure: '图片·保留原图', figtext: '图内文字·保留原文',
           table: '表格·保留原文', appendix: '附录·保留原文',
           keep: '保留原文' }[r.type] || '保留原文'
}

/* ---------------- 图表解读卡（2026-11-15） ----------------
 * figure 段的译文（zh）有两种可能：mode=vlm 跑过 → 是「中文解读卡」文本；
 * 没跑过 → 与原文相同（media token）。区别就在 zh 是否等于 src。
 * ★ 解读是**持久化**的（存在译文表），刷新不丢 —— 以前 VLM 图注存前端内存，
 *   一刷新就没，等于白识别。 */
const MEDIA_NAME_RE = /!\[\]\(media:([^)]+)\)/

function figName(src) {
  const m = String(src || '').match(MEDIA_NAME_RE)
  return m ? m[1] : ''
}

function figInterpreted(r) {
  const zh = (r.zh || '').trim()
  return !!zh && zh !== (r.src || '').trim()
}

function figLines(zh) {
  return String(zh || '').split('\n').map(s => s.trim()).filter(Boolean)
}

/** 解读文本 → 结构化三段（2026-11-15 用户反馈：标注对照要用**表格**形式，
 *  bullets 散文式对照读起来不知道谁对谁）。
 *  VLM 输出固定三段：【图】题 / `- 英文 → 中文` 标注对照 / 解读：……
 *  返回 { title, table: [[en, zh]...], summary }。 */
function figParts(zh) {
  const lines = figLines(zh)
  const out = { title: '', table: [], summary: '' }
  for (const ln of lines) {
    if (ln.startsWith('【图】')) { out.title = ln.replace(/^【图】/, '').trim(); continue }
    if (ln.startsWith('解读')) { out.summary = ln.replace(/^解读[:：]?/, '').trim(); continue }
    const m = ln.match(/^[-•·]\s*(.+?)\s*→\s*(.+)$/)
    if (m) { out.table.push([m[1].trim(), m[2].trim()]); continue }
    // 非标准行归入对照表第一列，不丢内容
    if (out.table.length || (ln.includes('→'))) out.table.push([ln, ''])
  }
  return out
}

/** 有多少张图还没解读（工具条按钮上的角标）。 */
const vlmPending = computed(() =>
  rows.value.filter(r => r.type === 'figure' && !figInterpreted(r)).length)
const hasFigures = computed(() => rows.value.some(r => r.type === 'figure'))

/* 标题段识别：编号段（1 / Introduction、4.1 / ...）或孤立的章节词（Abstract/
 * Conclusion/References…）渲染成「小节标题」而非正文，结构才立得起来、好看。 */
const HEADING_WORDS = /^(abstract|introduction|related work|conclusion|references|appendix|acknowledg|background|method|results|discussion|overview|preliminaries)/i
function isHeading(r) {
  const src = (r.src || '').trim()
  if (!src) return false
  if (/^\d+(\.\d+)*\s*\/?\s*\S/.test(src) && src.length < 72) return true
  if (HEADING_WORDS.test(src) && src.length < 40) return true
  return false
}

/* ---------------- 加载 ---------------- */
async function load() {
  if (!props.docId) return
  loading.value = true
  try {
    const r = await getTranslation(props.docId)
    data.value = r
    overlay.value = {}
  } catch (e) {
    ElMessage.error('译文加载失败：' + (e?.message || e))
  } finally {
    loading.value = false
  }
  // ★ 刷新恢复（2026-11-15）：内容拉完了，再查一次「任务还在不在跑」。
  //   在跑 → running=true + 轮询接管；不在跑 → 保持 false，按钮回到可点。
  checkRunning()
}

/* ---------------- 翻译任务状态（2026-11-15）：刷新不丢、可停止 ----------------
 * ★ 以前刷新页面后 running=false，用户再点一次就起了第二个并行翻译线程
 *   （后端没注册表，谁都不知道在跑）。现在：load() 后查 status，
 *   服务端说在跑 → running=true + 3s 轮询接管进度；run 端点 409（已有任务）
 *   也转入同一条接管路径。轮询期间 progress 条由 status 驱动，
 *   任务结束自动 load() 拉全量。
 *
 * ★★ 声明顺序教训（2026-11-15 浏览器验证抓出）：watch(immediate) 必须放在
 *   `let pollTimer` **之后** —— immediate 回调在 setup 期间同步执行，
 *   回调里 stopPoll() 碰到还没初始化的 pollTimer 就是 TDZ ReferenceError，
 *   被 Vue 的 errorHandler 静默吞掉 → **挂载时的 load() 一次都不跑**，
 *   面板永远空态；而切文档的后续触发（setup 已完成）正常，恰好掩盖了它。
 *   后端日志（对照页 mount 后零 /translate 请求）是唯一可靠证据。 */
let pollTimer = null
const runInfo = ref({ running: false, startedAt: null, cancelRequested: false })
const vlmInfo = ref({ vlm: false, vlmModel: '' })

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    try {
      const r = await getTranslateStatus(props.docId)
      runInfo.value = r
      if (r.status && data.value) data.value = { ...data.value, status: r.status }
      if (!r.running) {
        stopPoll()
        running.value = false
        ElMessage.success(r.cancelRequested
          ? '翻译已停止（已完成的段落都保留）'
          : '后台翻译已完成（刷新前跑的那次）')
        load()
      }
    } catch {
      // 任务端点都没了（服务重启 / 文档被删）：别再空转
      stopPoll()
      running.value = false
    }
  }, 3000)
}

async function checkRunning() {
  try {
    const r = await getTranslateStatus(props.docId)
    runInfo.value = r
    vlmInfo.value = { vlm: !!r.vlm, vlmModel: r.vlmModel || '' }
    if (r.running) {
      running.value = true
      startPoll()
    }
  } catch {
    /* 404（文档没了）/ 网络抖动：静默，正常加载不受影响 */
  }
}

async function onStop() {
  try {
    const r = await stopTranslation(props.docId)
    ElMessage.info(r.wasRunning
      ? '已请求停止：当前段翻完就断，已完成段落都保留'
      : (r.msg || '当前没有翻译在跑'))
  } catch (e) {
    ElMessage.error('停止失败：' + (e?.message || e))
  }
}

onUnmounted(stopPoll)

// ★ watch 必须在 pollTimer 声明之后（见上面的声明顺序教训）
watch(() => props.docId, () => { stopPoll(); load() }, { immediate: true })

/* ---------------- 翻译 ---------------- */
const lastMode = ref('run')
async function start(mode = 'run', verify = true) {
  if (running.value || !props.docId) return
  lastMode.value = mode
  running.value = true
  const t0 = Date.now()
  let n = 0
  try {
    await runTranslation(props.docId, { mode, verify }, {
      onSeg: seg => {
        // ★ 逐段落库，所以每收到一段就已经安全了 —— 用户随时可以关页面。
        overlay.value = { ...overlay.value, [seg.i]: seg }
        n++
      },
      onDone: () => {
        const dt = ((Date.now() - t0) / 1000).toFixed(0)
        ElMessage.success(mode === 'vlm'
          ? `图注解读完成（${n} 张图），刷新也不会丢`
          : `本次翻了 ${n} 段，用了 ${dt}s`)
        // 跑完重新拉一次，让 status/glossary 与服务端完全一致
        load()
      },
      onCancelled: () => {
        ElMessage.info('翻译已停止（已完成的段落都保留）')
        load()
      },
      onError: msg => ElMessage.warning(msg)
    })
  } catch (e) {
    const msg = String(e?.message || e)
    if (msg.includes('已有翻译在跑') || msg.includes('409')) {
      // 409 = 别的会话/刷新前的那次还在跑 → 转入接管：轮询它的进度
      ElMessage.info('已接管正在进行的翻译任务（可随时点停止）')
      await checkRunning()
    } else {
      ElMessage.error('翻译失败：' + msg)
    }
  } finally {
    // 接管路径 checkRunning 会重新把 running 置回 true，这里先归零没关系
    if (!runInfo.value.running) running.value = false
  }
}

/* ---------------- 术语表 ---------------- */
const showGlossary = ref(false)
const gBusy = ref(false)

async function rebuildGlossary() {
  gBusy.value = true
  try {
    const r = await redoGlossary(props.docId)
    data.value = { ...data.value, glossary: r.glossary }
    ElMessage.success(`术语表 ${r.count} 条（你手动改过的没被覆盖）`)
  } catch (e) {
    ElMessage.error('术语表抽取失败：' + (e?.message || e))
  } finally {
    gBusy.value = false
  }
}

async function saveTerm(en, zh, locked) {
  try {
    const r = await putGlossaryTerm(props.docId, en, zh, locked)
    data.value = { ...data.value, glossary: r.glossary }
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.message || e))
  }
}

async function dropTerm(en) {
  try {
    const r = await delGlossaryTerm(props.docId, en)
    data.value = { ...data.value, glossary: r.glossary }
  } catch (e) {
    ElMessage.error('删除失败：' + (e?.message || e))
  }
}

/* ---------------- 质量标记 ---------------- */
function flagText(r) {
  if (!r.zh) return r.status === 'bad' ? '失败' : ''
  if (r.missing?.length) return '数字缺失'
  if (r.status === 'warn') return '待核'
  return ''
}

function flagTitle(r) {
  if (r.missing?.length) {
    return '原文里的第 ' + r.missing.join('、') + ' 处数字/公式没能在译文里找到，' +
      '点「全部重翻」可以再试一次'
  }
  if (r.status === 'warn' && r.score != null) {
    return '回译校验分 ' + r.score.toFixed(2) + '（偏低），建议对照原文复核'
  }
  if (r.status === 'bad') return '这一段翻译失败，点「继续翻译」会重试'
  return ''
}

/* ---------------- 图片 / 架构图：保留原图 + 标注，不翻译 ---------------- */
/* ★ 论文里的图本就不该被「翻译」成文字：原文以 `![](media:name)` 内联，
 *   翻译管道已把它当占位符保护（见 core/translate.py），译文里仍是原 token。
 *   这里把它渲染回图片，并明确标「原文图片·未译」，让人一眼知道这是图不是译文。
 *   用户想理解图，可点「用 AI 识别这张图」调视觉模型写一句中文说明（best-effort）。 */

/** name -> {cap, busy}：图注是按需拉取的，别在渲染译文时顺手轰视觉模型。 */
const caps = ref({})

/** 把一段译文拆成 [文字, 图片, 文字, ...]，图片是 {type:'img', name}。 */
function partsOf(r) {
  const zh = r.zh || ''
  const out = []
  let last = 0
  const RE = /!\[\]\(media:([^)]+)\)/g
  let m
  while ((m = RE.exec(zh))) {
    if (m.index > last) out.push({ type: 'text', text: zh.slice(last, m.index) })
    out.push({ type: 'img', name: m[1] })
    last = m.index + m[0].length
  }
  if (last < zh.length) out.push({ type: 'text', text: zh.slice(last) })
  return out
}

function capOf(name) {
  return caps.value[name] || { cap: '', busy: false }
}

async function describe(p) {
  if (caps.value[p.name]?.busy) return
  caps.value = { ...caps.value, [p.name]: { cap: caps.value[p.name]?.cap || '', busy: true } }
  try {
    const r = await captionFigure(props.docId, p.name, '')
    if (r.ok && r.caption) {
      caps.value = { ...caps.value, [p.name]: { cap: r.caption, busy: false } }
    } else {
      caps.value = { ...caps.value, [p.name]: { cap: '', busy: false } }
      ElMessage.info('视觉模型没开或没识别出来，图片保留原样')
    }
  } catch (e) {
    caps.value = { ...caps.value, [p.name]: { cap: '', busy: false } }
    ElMessage.warning('识别失败：' + (e?.message || e))
  }
}
</script>

<template>
  <div
    class="bi"
    :style="{
      '--rd-fs': fontSize + 'px',
      '--rd-zh': fontMode === 'serif'
        ? 'var(--ff-zh-serif)'
        : 'var(--ff-zh-sans)'
    }"
  >
    <!-- 工具条 -->
    <div class="bi-bar">
      <span class="bi-mode">论文对照</span>
      <span class="grow" />

      <span v-if="loading" class="dim">载入中…</span>
      <template v-else>
        <button class="btn btn-bare" :class="{ on: showSrc }" @click="showSrc = !showSrc">
          附英文
        </button>
        <span class="bi-font">
          <button
            class="btn btn-bare"
            :class="{ on: fontMode === 'serif' }"
            title="译文用衬线（书卷感，长文更耐读）"
            @click="fontMode = 'serif'"
          >衬线</button>
          <button
            class="btn btn-bare"
            :class="{ on: fontMode === 'sans' }"
            title="译文用黑体（屏幕感，更清晰）"
            @click="fontMode = 'sans'"
          >黑体</button>
          <span class="bi-fs">
            <button class="btn btn-bare sq" :disabled="fontSize <= 13" @click="stepFont(-1)">A−</button>
            <span class="bi-fs-val">{{ fontSize }}</span>
            <button class="btn btn-bare sq" :disabled="fontSize >= 21" @click="stepFont(1)">A+</button>
          </span>
        </span>
        <button class="btn btn-bare" @click="showGlossary = !showGlossary">
          术语表 {{ data?.glossary?.length || 0 }}
        </button>
        <button v-if="!running" class="btn btn-ghost" :disabled="!hasText" @click="start('run', true)">
          {{ status.done ? '继续翻译' : '开始翻译' }}
        </button>
        <template v-else>
          <button class="btn btn-ghost"
                  :title="runInfo.startedAt ? '从 ' + runInfo.startedAt + ' 起在跑（刷新页面后接管）' : ''">
            翻译中… {{ pct }}%
          </button>
          <!-- 协作式停止：当前段翻完就断，已完成的段落都在库里 -->
          <button class="btn btn-bare" title="当前段翻完就断（3~8s 内），已完成的段落都保留"
                  @click="onStop">停止</button>
        </template>
        <button
          v-if="vlmInfo.vlm && hasFigures && !running"
          class="btn btn-ghost"
          title="给还没解读的图跑本地 VLM：中文图题 + 图内标注对照 + 一句话解读。结果持久保存，刷新不丢"
          @click="start('vlm', false)"
        >
          图注解读<template v-if="vlmPending">（{{ vlmPending }} 张待解读）</template>
        </button>
        <button
          v-else-if="running && lastMode === 'vlm'"
          class="btn btn-ghost">解读中… {{ pct }}%</button>
        <button
          v-if="status.done"
          class="btn btn-bare"
          :disabled="running"
          title="把所有段重翻一遍（术语表保留）"
          @click="start('redo', true)"
        >
          全部重翻
        </button>
      </template>
    </div>

    <!-- 进度条：只在翻过东西之后出现，没开始时不占地方 -->
    <div v-if="status.total && (status.done || running)" class="bi-prog">
      <div class="bar"><i :style="{ width: pct + '%' }" /></div>
      <span class="dim">
        已译 {{ status.done }} / {{ status.total }}（{{ pct }}%）
        <template v-if="status.warn"> · {{ status.warn }} 段待核</template>
        <template v-if="status.bad"> · {{ status.bad }} 段失败</template>
      </span>
    </div>

    <!-- 空态 -->
    <div v-if="!loading && !data?.translatable" class="bi-empty">
      <span class="big">这份文档没有可翻译的正文</span>
      纯扫描版 PDF（没有文字层）或已经是中文了 —— 翻译需要能读出来的文字
    </div>
    <div v-else-if="!loading && !status.done && !running" class="bi-empty">
      <span class="big">还没有译文</span>
      点「开始翻译」，左边是原 PDF、右边会逐段长出中文译文；<br />
      本地模型约 6 秒一段，一篇论文半小时左右，中途关掉也不会丢
      <div class="bi-why">
        <p>翻译时做了三件保准确性的事：</p>
        <ul>
          <li><b>数字/公式/引用</b>先被抽出来占位，译完原样填回 —— 这一环不经过模型，不会错</li>
          <li><b>术语表</b>全文统一，同一个词只允许一个译法</li>
          <li>每段翻完<b>回译回英文比对</b>，偏差大的标成「待核」让你复核</li>
        </ul>
      </div>
    </div>

    <!-- ★ 左右两栏：左 PDF 原件（等比缩小），右中文译文，各自滚动 -->
    <div v-else class="bi-body">
      <!-- 左：原 PDF 文档。占 54%（比译文略大），PdfViewer 按容器宽度铺满即等比缩小。 -->
      <div class="bi-left">
        <PdfViewer :doc-id="docId" :mini="true" />
      </div>

      <!-- 右：中文译文。独立滚动，不做左右同步（PDF 页与段无法 1:1 对齐）。 -->
      <div class="bi-right">
        <div
          v-for="r in rows"
          :key="r.i"
          class="t-row"
          :class="{ warn: r.status === 'warn', bad: r.status === 'bad', heading: isHeading(r) }"
        >
          <span class="t-no">{{ r.i + 1 }}</span>
          <div class="t-body">
            <div v-if="showSrc && r.src" class="t-src">{{ r.src }}</div>
            <span class="t-keep" v-if="!r.translate" :title="keepBadge(r) + '：这类内容按你的要求原样保留，不送模型翻译'">{{ keepBadge(r) }}</span>
            <template v-if="r.zh">
              <span class="t-flag" v-if="flagText(r)" :title="flagTitle(r)">{{ flagText(r) }}</span>
              <!-- figure 段专用渲染（2026-11-15）：原图永远保留；跑过 mode=vlm 的
                   段，译文列是「中文解读卡」（图题+标注对照+解读），持久保存 -->
              <template v-if="r.type === 'figure'">
                <div class="t-img">
                  <img :src="getMediaUrl(docId, figName(r.src))" :alt="figName(r.src)" loading="lazy" />
                  <div class="t-img-cap">
                    <span class="badge" :class="{ 'badge-ok': figInterpreted(r) }">
                      {{ figInterpreted(r) ? '已生成中文解读（持久保存）' : '原文图片 · 未译（保留原图）' }}
                    </span>
                    <span class="fig-cap-src">{{ r.src.replace(MEDIA_NAME_RE, '').trim() }}</span>
                  </div>
                  <div v-if="figInterpreted(r)" class="fig-card">
                    <div v-if="figParts(r.zh).title" class="fig-line fig-title">
                      【图】{{ figParts(r.zh).title }}
                    </div>
                    <table v-if="figParts(r.zh).table.length" class="fig-table">
                      <tbody>
                        <tr v-for="(row, ri) in figParts(r.zh).table" :key="ri">
                          <td class="mono">{{ row[0] }}</td>
                          <td>{{ row[1] }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-if="figParts(r.zh).summary" class="fig-line fig-summary">
                      解读：{{ figParts(r.zh).summary }}
                    </div>
                  </div>
                </div>
              </template>
              <template v-else>
                <template v-for="(p, pi) in partsOf(r)" :key="pi">
                  <span v-if="p.type === 'text'" class="t-zh">{{ p.text }}</span>
                  <div v-else class="t-img">
                    <img :src="getMediaUrl(docId, p.name)" :alt="p.name" loading="lazy" />
                    <div class="t-img-cap">
                      <span class="badge">原文图片 · 未译（保留原图）</span>
                      <button class="link" :disabled="capOf(p.name).busy" @click="describe(p)">
                        {{
                          capOf(p.name).cap
                            ? 'AI 图注：' + capOf(p.name).cap
                            : (capOf(p.name).busy ? '识别中…' : '用 AI 识别这张图')
                        }}
                      </button>
                    </div>
                  </div>
                </template>
              </template>
            </template>
            <span v-else class="t-todo">未译</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 术语表抽屉 -->
    <div v-if="showGlossary" class="gl">
      <div class="gl-head">
        <b>术语表</b>
        <span class="dim">锁定的条目在「重抽术语表」时不会被覆盖</span>
        <span class="grow" />
        <button class="btn btn-bare" :disabled="gBusy" @click="rebuildGlossary">
          {{ gBusy ? '抽取中…' : '重抽术语表' }}
        </button>
        <button class="btn btn-bare" @click="showGlossary = false">收起</button>
      </div>
      <div class="gl-list">
        <div v-for="g in data?.glossary || []" :key="g.en" class="gl-row">
          <span class="gl-en">{{ g.en }}</span>
          <input
            class="gl-zh"
            :value="g.zh"
            @change="saveTerm(g.en, $event.target.value, g.locked)"
          />
          <span class="gl-lock" :class="{ on: g.locked }" :title="g.locked ? '已锁定' : '自动抽取'">
            {{ g.locked ? '🔒' : '·' }}
          </span>
          <button class="gl-del" @click="dropTerm(g.en)">×</button>
        </div>
        <div v-if="!data?.glossary?.length" class="dim" style="padding: 10px">
          还没有术语表
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Web 字体优先，离线自动落到本机宋体/黑体（不会变丑） */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap');

.bi {
  --ff-en-serif: 'Source Serif 4', Georgia, 'Times New Roman', 'Noto Serif SC', serif;
  --ff-zh-serif: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  --ff-zh-sans: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', 'Source Han Sans SC', system-ui, sans-serif;
  --ff-en-sans: 'Inter', 'Segoe UI', system-ui, 'PingFang SC', sans-serif;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: var(--panel2);
}
.bi-bar {
  flex: none;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 7px 12px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
}
/* 字号 / 字体切换一组，做成连贯的小控件 */
.bi-font {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
  margin-left: 2px;
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.bi-font .btn.on {
  color: var(--ac);
  background: var(--ac-glow);
  border-color: var(--ac-dim);
}
.bi-fs {
  display: inline-flex;
  align-items: center;
  gap: 1px;
  margin-left: 3px;
  padding-left: 5px;
  border-left: 1px solid var(--line);
}
.bi-fs .sq {
  min-width: 22px;
  padding: 0 5px;
  font-size: 11px;
}
.bi-fs-val {
  min-width: 22px;
  text-align: center;
  font-size: 11px;
  color: var(--mu);
  font-variant-numeric: tabular-nums;
}
.bi-mode {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--mu);
}
.grow {
  flex: 1;
}
/* 「附英文」开关做成 toggle 态，明确它现在是开还是关 */
.btn.on {
  color: var(--ac);
  background: var(--ac-glow);
  border-color: var(--ac-dim);
}

.bi-prog {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  font-size: var(--fs-xs);
  border-bottom: 1px solid var(--line);
}
.bi-prog .bar {
  flex: 1;
  height: 3px;
  background: var(--line2);
  border-radius: 2px;
  overflow: hidden;
}
.bi-prog .bar i {
  display: block;
  height: 100%;
  background: var(--ac);
  transition: width 0.25s;
}

.bi-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  text-align: center;
  color: var(--dim);
  font-size: var(--fs-sm);
  line-height: 1.7;
}
.bi-empty .big {
  font-size: var(--fs-md);
  color: var(--mu);
}
.bi-why {
  margin-top: 12px;
  max-width: 480px;
  text-align: left;
  font-size: var(--fs-xs);
  line-height: 1.8;
  color: var(--dim);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}
.bi-why p {
  margin: 0 0 6px;
  color: var(--mu);
}
.bi-why ul {
  margin: 0;
  padding-left: 18px;
}

/* ★ 左右两栏：左 PDF、右译文。两列都用 flex 占满高度，
   内部各自处理自己的纵向滚动 —— 谁也不听谁的，对齐靠视觉分栏即可。 */
.bi-body {
  flex: 1;
  min-height: 0;
  display: flex;
}
/* 左列固定 54%（比右栏译文略大），PDF 按这个宽度铺满即等比缩小（PdfViewer 内部按容器宽渲染）。
   ★ 不给具体像素：窗口变宽时 PDF 跟着变大、变窄时跟着变小，
   始终占满左列又不会挤到右列。右栏 .bi-right 用 flex:1 自动占剩余 46%。 */
.bi-left {
  flex: 0 0 58%;
  min-width: 0;
  display: flex;
  border-right: 1px solid var(--line);
  background: var(--panel2);
}
/* PdfViewer 根节点是 .pdfv，它本身 flex:1 + min-height:0，
   作为 .bi-left 的 flex 子项会被拉伸填满左列。 */
.bi-left :deep(.pdfv) {
  flex: 1;
}

/* 右列：译文。独立滚动。 */
.bi-right {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 8px 0 80px;
}
.t-row {
  display: flex;
  gap: 12px;
  padding: 11px 18px;
  border-left: 2px solid transparent;
  border-bottom: 1px solid var(--line);
}
.t-row:hover {
  background: var(--panel);
}
.t-row.warn {
  background: color-mix(in srgb, var(--ac) 5%, transparent);
}
.t-row.bad {
  background: color-mix(in srgb, #d9534f 7%, transparent);
}
/* 标题段：像书的章节名，拉开与正文的呼吸感 */
.t-row.heading {
  padding-top: 22px;
  padding-bottom: 6px;
  border-left-color: var(--ac-dim);
}
.t-row.heading + .t-row:not(.heading) {
  border-top: none;
}
.t-no {
  flex: none;
  width: 26px;
  text-align: right;
  font-size: 10px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
  line-height: 1.9;
}
.t-row.heading .t-no {
  line-height: 1.5;
  font-size: 11px;
  color: var(--ac);
}
.t-body {
  flex: 1;
  min-width: 0;
  max-width: 52em;        /* 控制每行字数，太宽反而累眼 */
}
.t-src {
  font-family: var(--ff-en-serif);
  font-size: 13.5px;
  color: color-mix(in srgb, var(--mu) 88%, var(--dim));
  line-height: 1.75;
  margin-bottom: 4px;
  padding-left: 9px;
  border-left: 2px solid var(--line2);
  font-style: italic;
}
.t-zh {
  font-family: var(--rd-zh);
  font-size: var(--rd-fs);
  line-height: 1.95;
  letter-spacing: 0.01em;
  color: var(--tx);
  white-space: pre-wrap;
  word-break: break-word;
  text-align: justify;
  text-justify: inter-ideograph;
}
.t-row.heading .t-zh {
  font-size: calc(var(--rd-fs) + 5px);
  font-weight: 700;
  line-height: 1.5;
  letter-spacing: 0.02em;
  color: var(--mu);
  margin: 2px 0;
}
.t-todo {
  font-size: var(--fs-xs);
  color: var(--line2);
  line-height: 1.85;
}
.t-flag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  height: 16px;
  line-height: 14px;
  border-radius: 8px;
  background: var(--line2);
  color: var(--mu);
  margin-right: 6px;
  vertical-align: 1px;
  font-weight: 500;
}
.t-row.warn .t-flag {
  background: var(--ac-glow);
  color: var(--ac);
}
.t-row.bad .t-flag {
  background: #d9534f;
  color: #fff;
}
/* 「公式/参考文献/图片·保留原文」：原样不译的段，给一个明确的浅色标识，
   让用户一眼知道这是「故意不译」而不是「还没翻」。 */
.t-keep {
  display: inline-block;
  font-size: 10px;
  padding: 1px 8px;
  height: 16px;
  line-height: 14px;
  border-radius: 8px;
  margin: 0 6px 4px 0;
  vertical-align: 1px;
  font-weight: 600;
  letter-spacing: .3px;
  background: color-mix(in srgb, #3a7afe 14%, transparent);
  color: color-mix(in srgb, #3a7afe 78%, var(--tx));
  border: 1px solid color-mix(in srgb, #3a7afe 32%, transparent);
}

/* 图片 / 架构图：保留原图，明确标「未译」，不把它塞进译文正文 */
.t-img {
  margin: 10px 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--panel2);
  box-shadow: 0 1px 4px color-mix(in srgb, #000 8%, transparent);
}
.t-img img {
  display: block;
  max-width: 100%;
  height: auto;
  background: #fff;
}
.t-img-cap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 10px;
  border-top: 1px solid var(--line);
}
.t-img-cap .badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 9px;
  background: color-mix(in srgb, #8a6d3b 20%, transparent);
  color: var(--mu);
  border: 1px solid color-mix(in srgb, #8a6d3b 38%, transparent);
  font-weight: 500;
}
.t-img-cap .link {
  font-size: var(--fs-xs);
  color: var(--ac);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.t-img-cap .link:disabled {
  color: var(--dim);
  cursor: default;
}
.t-img-cap .badge-ok {
  background: color-mix(in srgb, #3f8f6d 18%, transparent);
  color: #3f8f6d;
  border-color: color-mix(in srgb, #3f8f6d 40%, transparent);
}
.t-img-cap .fig-cap-src {
  font-size: 11px;
  color: var(--dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

/* ---- VLM 中文解读卡（2026-11-15）：图题 + 标注对照 + 解读，三段式 ---- */
.fig-card {
  padding: 8px 12px;
  border-top: 1px dashed var(--line);
  background: color-mix(in srgb, #3f8f6d 5%, transparent);
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.fig-line {
  font-size: 12.5px;
  color: var(--tx);
  line-height: 1.65;
}
.fig-line.fig-title {
  font-weight: 700;
  color: #3f8f6d;
  font-size: 13px;
}
.fig-line.fig-summary {
  margin-top: 2px;
}
/* 标注对照两列表格：英文原文 / 中文译法，谁对谁一目了然 */
.fig-table {
  width: 100%;
  border-collapse: collapse;
  margin: 2px 0;
}
.fig-table td {
  padding: 3px 8px;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  line-height: 1.5;
  vertical-align: top;
}
.fig-table td:first-child {
  color: var(--mu);
  width: 46%;
  word-break: normal;
  overflow-wrap: anywhere;
}
.fig-table tr:last-child td {
  border-bottom: none;
}

/* 术语表 */
.gl {
  flex: none;
  max-height: 42%;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--line);
  background: var(--panel);
}
.gl-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: var(--fs-xs);
  border-bottom: 1px solid var(--line);
}
.gl-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}
.gl-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 1px 0;
}
.gl-en {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-xs);
  color: var(--mu);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gl-zh {
  width: 130px;
  padding: 2px 6px;
  font-size: var(--fs-xs);
  color: var(--tx);
  background: var(--panel2);
  border: 1px solid var(--line2);
  border-radius: 4px;
  outline: none;
}
.gl-zh:focus {
  border-color: var(--ac);
}
.gl-lock {
  width: 16px;
  text-align: center;
  font-size: 10px;
  color: var(--dim);
}
.gl-lock.on {
  color: var(--ac);
}
.gl-del {
  width: 18px;
  height: 18px;
  font-size: 13px;
  line-height: 1;
  color: var(--dim);
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.gl-del:hover {
  color: #d9534f;
  background: var(--panel2);
}
</style>
