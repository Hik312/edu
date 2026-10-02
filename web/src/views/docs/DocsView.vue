<script setup>
/* 文档与精读 —— 本地 md/txt/pdf/docx 选文件（或粘贴）进来，自动分章，
 * 然后**逐章**过一遍 AI，最后可以一键全量转成草稿卡（卡片组）。
 *
 * ## 为什么必须逐章
 *
 * `/llm/enrich` 支持一次传多个 index（batch），但**实测会把 A 章的内容安到 B 章**。
 * 慢一点是不可谈判的成本 —— 错了的内容比没有内容更糟，因为不会被发现。
 * 所以这里一次只精读一章。「全部转卡」也是把循环写在前端逐章 await，
 * 不是把下标一把梭给批量接口。
 *
 * ## AI 是可选增强
 *
 * `/llm/status` 返回 ok:false **不是故障**。分章、阅读、上传都不依赖它，
 * 只有精读/转卡需要（没开模型时「全部转卡」直接提示，不降级 —— 降级切出来
 * 的卡缺类比缺场景，进了草稿池也是废的）。
 *
 * ## 长任务的现状
 *
 * 精读是同步请求，一份十几章的文档要点很多次 —— 「全部转卡」就是把这个循环
 * 交给代码跑并显示进度。这正是后期要改成「异步任务 + SSE 推送」的地方（E8），
 * 换的时候页面只需要把 await enrich 换成订阅进度。
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDoc, importDoc, listDocs, removeDoc } from '@/api/docs'
import { getLlmStatus, toCard } from '@/api/ai'
import { enrich } from '@/api/ai'
import { bodySegs, makeDocAgent, mediaSrc } from './docAgent'
import { makeDocAuto } from './docAuto'
import ParseReport from './ParseReport.vue'

const docs = ref([])
const loading = ref(false)
const llm = ref({ ok: false, provider: '', msg: '' })

const route = useRoute()

/** 当前展开阅读的文档 */
const opened = ref(null)
/** 正在精读的章节下标 */
const enriching = ref('')
/** 正在转卡的章节下标 */
const turning = ref('')

/** 导入面板是否展开 */
const showImport = ref(false)
const importForm = ref({ title: '', text: '' })
const importing = ref(false)

/** 两条一键流程都拆在旁边文件里（本文件 max-lines 到顶了）：
 *  auto = 旧链路（精读 + to-card，./docAuto.js），
 *  agent = LangGraph 新链路（定分章 + grounding，./docAgent.js）。
 *  两者互斥运行（busy / agentBusy 互相把关），按钮和进度各自独立，文案别混。
 *  两个闭包都是点击时才求值，声明顺序不用纠结谁先谁后。 */
const { auto, autoLabel, toggleAuto } = makeDocAuto({
  opened,
  llm,
  fetchList,
  agentBusy: () => agent.value.on
})
const { agent, agentLabel, toggleAgent, startAfterImport, parsing, runParseFlow, toggleKeep } =
  makeDocAgent({
    opened,
    llm,
    fetchList,
    busy: () => auto.value.on,
    openDoc
  })

onMounted(async () => {
  await Promise.all([fetchList(), fetchLlm()])
  // ?doc=<id> 直接展开某一份。这个地址可以贴给别人（「你看这份第 7 章的拆解」），
  // 也让截图脚本能抓到展开态 —— 纯点击是脚本进不去的场景。
  // 没带参数就恢复上次在读的那份（刷新不该把正在看的文档弹回列表）。
  const want = route.query.doc || localStorage.getItem('edu.doc') || ''
  if (want) {
    const hit = docs.value.find(d => String(d.id) === String(want))
    if (hit) await openDoc(hit)
    else localStorage.removeItem('edu.doc') // 文档被删了，清掉过期记忆
  }
})

async function fetchList() {
  loading.value = true
  try {
    docs.value = (await listDocs()).docs || []
  } finally {
    loading.value = false
  }
}

async function fetchLlm() {
  try {
    llm.value = await getLlmStatus()
  } catch {
    llm.value = { ok: false, provider: '', msg: '' }
  }
}

async function onImport() {
  const s = importForm.value.text.trim()
  if (!s) {
    ElMessage.warning('先粘一段内容')
    return
  }
  importing.value = true
  try {
    const r = await importDoc({
      title: importForm.value.title.trim() || undefined,
      text: s
    })
    ElMessage.success(`已导入《${r.doc?.title || ''}》，切成 ${r.doc?.stats?.chapters || 0} 章`)
    importForm.value = { title: '', text: '' }
    showImport.value = false
    await fetchList()
    await startAfterImport(r.doc) // 导完直接展开 + 自动出卡，不再让人手点「Agent 解析」
  } finally {
    importing.value = false
  }
}

async function openDoc(d) {
  opened.value = null
  const r = await getDoc(d.id)
  opened.value = r.doc
  localStorage.setItem('edu.doc', String(r.doc.id))
}

/** 支持的上传后缀。老 .doc 不收 —— 后端解析不了，先在前端就说清楚。 */
const OK_EXT = ['pdf', 'docx', 'md', 'markdown', 'txt']

/** 选本地文件 → 直接上传导入。PDF / Word 读 base64，文本类读原文。
 *  12MB 上限：base64 会膨胀 4/3，服务端请求体上限 16MB，留点余量。 */
async function onFile(ev) {
  const f = ev.target.files && ev.target.files[0]
  ev.target.value = '' // 同一个文件再选一次也要触发 change
  if (!f) return
  const ext = (f.name.split('.').pop() || '').toLowerCase()
  if (!OK_EXT.includes(ext)) {
    ElMessage.warning('只支持 PDF / Word(.docx) / md / txt（老 .doc 请另存为 .docx）')
    return
  }
  if (f.size > 12 * 1024 * 1024) {
    ElMessage.warning('文件超过 12MB，先拆小一点（或者只粘贴正文）')
    return
  }
  importing.value = true
  try {
    let body
    if (ext === 'pdf' || ext === 'docx') {
      body = { filename: f.name, dataB64: await readB64(f) }
    } else {
      body = { filename: f.name, text: await f.text() }
    }
    const t = importForm.value.title.trim()
    if (t) body.title = t
    const r = await importDoc(body)
    ElMessage.success(`已导入《${r.doc?.title || ''}》，切成 ${r.doc?.stats?.chapters || 0} 章`)
    importForm.value = { title: '', text: '' }
    showImport.value = false
    await fetchList()
    await startAfterImport(r.doc) // 同上：展开 + 自动出卡
  } finally {
    importing.value = false
  }
}

function readB64(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(String(fr.result).split(',')[1] || '')
    fr.onerror = () => reject(fr.error)
    fr.readAsDataURL(file)
  })
}

async function onRemove(d) {
  try {
    await ElMessageBox.confirm(
      `删除《${d.title}》？它的 {{ }} 章内容和精读结果都会一起删掉。`.replace(
        '{{ }}',
        String(d.stats?.chapters || 0)
      ),
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }
  await removeDoc(d.id)
  if (opened.value?.id === d.id) {
    opened.value = null
    localStorage.removeItem('edu.doc')
  }
  ElMessage.success('已删除')
  await fetchList()
}

/** 精读一章。一次只做一章 —— 见文件头。 */
async function onEnrich(idx) {
  if (!llm.value.ok) {
    ElMessage.warning('AI 未启用：' + (llm.value.msg || '没配置模型'))
    return
  }
  enriching.value = idx
  try {
    await enrich({ docId: opened.value.id, index: idx })
    // 重新拉一遍拿结果。不这么做的话要在本地拼 ai 字段，
    // 而 ai 的形状由后端决定，前端拼就容易对不上
    const r = await getDoc(opened.value.id)
    opened.value = r.doc
    await fetchList()
  } finally {
    enriching.value = ''
  }
}

async function onToCard(idx) {
  turning.value = idx
  try {
    await toCard(opened.value.id, idx)
    ElMessage.success('已生成草稿卡，去「生成」页补齐后发布')
  } finally {
    turning.value = ''
  }
}

const chapters = computed(() => opened.value?.chapters || [])

/** 文档有没有解析报告 —— 必须是本组件的 computed：docAgent 是模块级单例，
 *  它里面的 computed 会跨挂载残留旧的依赖追踪，回来以后判断会不准。 */
const hasParse = computed(() => Boolean(opened.value?.parse))

/** 精读进度百分比。没有 aiTotal 就是还没精读过任何一章。 */
function progress(d) {
  const t = d.aiTotal || 0
  if (!t) return 0
  return Math.round(((d.aiDone || 0) / t) * 100)
}

/** 结果字段存在返回值里，这里取一个统一切片。
 *  不同模型返回的字段名不完全一致，用空值兜住而不是让页面渲染 undefined。 */
function aiOf(c) {
  return c.ai || {}
}
</script>

<template>
  <div class="docs">
    <!-- ===== 列表 ===== -->
    <section class="panel">
      <header class="panel-head">
        <h3>
          文档 <span class="count">{{ docs.length }} 份</span>
        </h3>
        <button class="btn btn-ghost" @click="showImport = !showImport">
          <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
          导入
        </button>
      </header>

      <!-- AI 状态。未启用是正常状态，不是错误 -->
      <div class="row-between ai-state">
        <span class="chip" :class="{ accent: llm.ok }">
          AI 精读：{{ llm.ok ? '可用' : '未启用' }}
        </span>
        <span class="hint">{{
          llm.ok ? llm.provider + ' ' + (llm.model || '') : llm.msg || '分章、阅读、转卡都不依赖它'
        }}</span>
      </div>

      <div v-if="showImport" class="import-box">
        <div class="file-row">
          <label class="file-btn">
            <input type="file" accept=".pdf,.docx,.md,.markdown,.txt" @change="onFile" />
            选择文件上传
          </label>
          <span class="muted">PDF / Word(.docx) / md / txt，最大 12MB；也可以直接粘在下面</span>
        </div>
        <label class="field">
          <span class="lb">标题<em class="muted">留空自动从文中第一个标题推</em></span>
          <el-input v-model="importForm.title" placeholder="例如：MySQL 八股" />
        </label>
        <label class="field">
          <span class="lb"
            >正文<em class="muted">md / txt 均可，# 与「第X章」会被识别成章节</em></span
          >
          <el-input v-model="importForm.text" type="textarea" :rows="8" resize="vertical" />
        </label>
        <div class="row-between">
          <span class="muted">{{ importForm.text.length }} 字</span>
          <span>
            <button class="btn btn-ghost" @click="showImport = false">取消</button>
            <button class="btn btn-primary" :disabled="importing" @click="onImport">
              {{ importing ? '导入中…' : '导入并分章' }}
            </button>
          </span>
        </div>
      </div>

      <div class="dlist" v-loading="loading">
        <article
          v-for="d in docs"
          :key="d.id"
          class="doc"
          :class="{ on: opened?.id === d.id }"
          @click="openDoc(d)"
        >
          <div class="d-head">
            <h4 class="d-title">{{ d.title }}</h4>
            <span class="chip">{{ d.subject || d.category || '未分类' }}</span>
          </div>
          <p class="d-meta">
            {{ d.stats?.chapters ?? 0 }} 章 · {{ d.stats?.chars ?? 0 }} 字 · {{ d.createdAt }}
          </p>
          <div class="pbar">
            <i :style="{ width: progress(d) + '%' }" />
          </div>
          <p class="d-prog">
            精读 {{ d.aiDone ?? 0 }} / {{ d.aiTotal ?? 0 }}
            <span v-if="d.source" class="src">· {{ d.source }}</span>
            <button class="btn btn-bare danger" @click.stop="onRemove(d)">删除</button>
          </p>
        </article>
        <p v-if="!loading && !docs.length" class="empty">
          <span class="big">还没有文档</span>
          点右上角「导入」，把一份 md 或面经粘进来
        </p>
      </div>
    </section>

    <!-- ===== 章节 ===== -->
    <section class="panel reader">
      <header v-if="opened" class="panel-head">
        <h3>{{ opened.title }}</h3>
        <div class="hd-right">
          <span class="hint">{{ chapters.length }} 章</span>
          <button
            v-if="parsing || agent.on || (llm.ok && hasParse)"
            class="btn btn-ghost"
            :disabled="auto.on || parsing || (agent.on && agent.stop)"
            :title="
              hasParse
                ? '按解析报告逐章出卡（只跑保留的章，含图注+对齐自检）；再点一次可停止'
                : '内容解析进行中'
            "
            @click="toggleAgent"
          >
            {{ agentLabel }}
          </button>
          <button
            v-if="llm.ok"
            class="btn btn-ghost"
            :disabled="auto.on ? auto.stop : agent.on || parsing"
            :title="'逐章精读，再把每章转成草稿卡（挂到本卡片组）；再点一次可停止'"
            @click="toggleAuto"
          >
            {{ autoLabel }}
          </button>
        </div>
      </header>

      <p v-if="!opened" class="empty">
        <span class="big">选一份文档</span>
        左边点一下，这里会列出它的全部章节
      </p>

      <!-- 内容解析报告：出卡前的确认关卡（拆在 ./ParseReport.vue）：
           未解析 → 解析按钮；已解析 → 逐章勾选 + 出卡入口。 -->
      <ParseReport
        v-else
        :opened="opened"
        :parsing="parsing"
        :agent="agent"
        :agent-label="agentLabel"
        :busy-auto="auto.on"
        @run-parse="runParseFlow"
        @toggle-keep="toggleKeep"
        @toggle-agent="toggleAgent"
      />

      <ol v-if="opened" class="chapters">
        <li v-for="(c, i) in chapters" :key="i" class="chapter">
          <div class="c-head">
            <span class="c-idx mono">{{ String(i + 1).padStart(2, '0') }}</span>
            <h5 class="c-title">{{ c.title }}</h5>
            <div class="c-act">
              <button
                class="btn btn-ghost"
                :disabled="enriching === i || !llm.ok || auto.on"
                @click="onEnrich(i)"
              >
                {{ enriching === i ? '精读中…' : aiOf(c).analogy ? '重新精读' : 'AI 精读' }}
              </button>
              <button
                v-if="aiOf(c).analogy"
                class="btn btn-primary"
                :disabled="turning === i || auto.on"
                @click="onToCard(i)"
              >
                {{ turning === i ? '转换中…' : '转为草稿卡' }}
              </button>
            </div>
          </div>

          <!-- 正文预览：文字截 260 字，图片占位按原文位置插图（带 ?t= 登录态） -->
          <p class="c-text">
            <template v-for="(seg, si) in bodySegs(c.body)" :key="si">
              <img
                v-if="seg.img"
                class="c-img"
                :src="mediaSrc(opened?.id, seg.img)"
                :alt="seg.img"
                loading="lazy"
              />
              <span v-else>{{ seg.text }}</span>
            </template>
          </p>

          <!-- 精读结果 -->
          <div v-if="aiOf(c).analogy || aiOf(c).points?.length" class="ai">
            <div v-if="aiOf(c).analogy" class="ai-row">
              <span class="ai-k">类比</span>
              <span class="ai-v">{{ aiOf(c).analogy }}</span>
            </div>
            <div v-if="aiOf(c).points?.length" class="ai-row">
              <span class="ai-k">要点</span>
              <ul class="ai-v">
                <li v-for="(p, pi) in aiOf(c).points" :key="pi">{{ p }}</li>
              </ul>
            </div>
            <div v-if="aiOf(c).why" class="ai-row">
              <span class="ai-k">为什么</span>
              <span class="ai-v">{{ aiOf(c).why }}</span>
            </div>
          </div>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.docs {
  display: grid;
  grid-template-columns: minmax(300px, 400px) 1fr;
  gap: 16px;
  /* 撑满内容区高度，两栏**各自内部滚动**。
     文档页是个「阅读器」：左边文档数、右边章节数都不可控。
     之前是 align-items:start + 整页滚动 —— 读到第五章时左边那份文档早就
     滚出视野了，想换一份得先滚回顶部。
     高度取 100% 依赖 .content 是 flex item（高度确定）；万一哪天它变成
     auto，这里会退化成按内容高度，等于回到旧行为，不会更糟。 */
  height: 100%;
  min-height: 0;
  align-items: stretch;
}

/* panel 自己不滚，滚动条落在里面的列表上 —— 这样标题行始终钉在面板顶部 */
.docs .panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.docs .dlist,
.docs .chapters {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* overflow-y 一旦不是 visible，overflow-x 的 visible 也会被浏览器算成 auto
     —— 于是任何一点水平溢出都会在底部冒出一条横滚动条。
     这里显式压掉，滚动条只允许是竖的。 */
  overflow-x: hidden;
  /* 给滚动条留 6px 呼吸位，别贴着面板的圆角描边 */
  padding-right: 6px;
}
/* 空状态要占满剩余高度并居中，否则会贴在面板顶边 */
.docs .reader > .empty {
  flex: 1;
  align-content: center;
}
.count {
  font-size: var(--fs-xs);
  font-weight: 400;
  color: var(--dim);
}

.ai-state {
  padding: 9px 12px;
  margin-bottom: 12px;
  border-radius: var(--radius-sm);
  border: 1px dashed var(--line2);
  background: var(--panel2);
}
.ai-state .hint {
  font-size: var(--fs-xs);
  color: var(--dim);
}

.import-box {
  padding: 14px;
  margin-bottom: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line2);
  background: var(--panel2);
}
/* 文件选择行：按钮用虚线框，真正的 <input> 透明盖在上面，
   点文字任何位置都能拉起文件对话框（label 包 input 的标准做法） */
.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.file-btn {
  position: relative;
  overflow: hidden;
  display: inline-block;
  padding: 7px 14px;
  border: 1px dashed var(--ac);
  border-radius: 6px;
  color: var(--ac);
  font-size: 13.5px;
  cursor: pointer;
}
.file-btn:hover {
  background: var(--ac-glow);
}
.file-btn input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
.file-row .muted {
  font-size: 12.5px;
  color: var(--dim);
}
/* 右侧组：章数 + 全部转卡按钮钉在标题行右边 */
.hd-right {
  display: flex;
  align-items: center;
  gap: 10px;
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

.dlist {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.doc {
  padding: 13px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--panel2);
  cursor: pointer;
  transition:
    border-color 0.16s,
    background 0.16s;
}
.doc:hover {
  border-color: var(--line2);
}
.doc.on {
  border-color: var(--ac);
  background: var(--ac-glow);
}
.d-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.d-title {
  font-size: var(--fs-md);
  font-weight: 600;
}
.d-meta {
  margin: 4px 0 8px;
  font-size: var(--fs-xs);
  color: var(--dim);
}
.pbar {
  height: 4px;
  border-radius: 3px;
  background: var(--line);
  overflow: hidden;
}
.pbar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--ac-dim), var(--ac));
  transition: width 0.5s cubic-bezier(0.22, 0.7, 0.28, 1);
}
.d-prog {
  margin-top: 6px;
  font-size: var(--fs-xs);
  color: var(--mu);
  display: flex;
  align-items: center;
  gap: 6px;
}
.src {
  color: var(--dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.danger {
  margin-left: auto;
  color: var(--red);
}

/* ===== 章节 ===== */
.chapters {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.chapter {
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}
.chapter:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}
.c-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.c-idx {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.c-title {
  flex: 1;
  min-width: 200px;
  font-size: var(--fs-md);
  font-weight: 600;
}
.c-act {
  display: flex;
  gap: 8px;
}
.c-text {
  margin: 8px 0 0;
  padding-left: 30px;
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.8;
  white-space: pre-wrap;
}
/* 文档里的配图（docx/pdf 抠出来的）：小图预览，点不开也不挡文字 */
.c-img {
  display: block;
  max-width: 260px;
  max-height: 180px;
  margin: 8px 0 4px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
}

.ai {
  margin: 12px 0 0 30px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  border-left: 2px solid var(--ac);
  background: var(--ac-glow);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-row {
  display: flex;
  gap: 12px;
  font-size: var(--fs-sm);
}
.ai-k {
  flex: none;
  width: 42px;
  font-weight: 600;
  color: var(--ac);
}
.ai-v {
  flex: 1;
  min-width: 0;
  line-height: 1.8;
}
.ai-v ul {
  margin: 0;
  padding-left: 18px;
}
.ai-v li {
  margin-bottom: 3px;
}

@media (max-width: 1080px) {
  .docs {
    grid-template-columns: 1fr;
    /* 单列时回到自然高度：两栏各占半屏会被压成两条窄缝 */
    height: auto;
  }
  .docs .dlist,
  .docs .chapters {
    overflow: visible;
    padding-right: 0;
  }
}
</style>
