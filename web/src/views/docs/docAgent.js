/* 卡片 Agent 三阶段流程 —— 从 DocsView 拆出来的（那边 max-lines 700 到顶了）。
 *
 *   1. structure —— LLM 看规则初切的章节清单定切分点，修「分章不准」。
 *      refined:false 是正常结果（没装模型/方案不合法），提示后按原分章继续。
 *   2. parse     —— 规则预判 + AI 判定每章有用/没用，出**内容解析报告**。
 *      报告是**终点**：用户确认/勾选之后才出卡（导入后不会自动出卡）。
 *   3. chapter   —— 只对报告里「保留」的章逐章跑「图注 → 生成 → 对齐自检」，
 *      全部落草稿。幂等由后端按草稿 id 保证：已有草稿返回 skipped，
 *      所以中途停止再点一次就是断点续跑。
 *
 * 顺序不能反：structure 重切章节会改变下标，报告必须在它之后。
 *
 * 和「全部转卡」旧链路（DocsView 里的 runAuto）互斥运行，但进度、
 * 文案、按钮各自独立 —— 换链路的人不该分不清自己在跑哪条。
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDoc } from '@/api/docs'
import { cardsChapter, cardsStructure, parseDoc, putParseKeeps } from '@/api/agent'
import { getToken } from '@/api/client'

/** 正文里的图片占位（和后端 docparse.MEDIA_TOKEN 同形，改了要两边同步）。 */
const MEDIA_RE = /!\[\]\(media:([A-Za-z0-9_.\- ]+)\)/g

export function makeDocAgent({ opened, llm, fetchList, busy, openDoc }) {
  const agent = ref({ on: false, stop: false, phase: 'draft', i: 0, n: 0 })
  const parsing = ref(false) // structure+parse 串行中（报告还没出来）

  const hasParse = computed(() => Boolean(opened.value?.parse))

  const agentLabel = computed(() => {
    const a = agent.value
    if (parsing.value) return '内容解析中…'
    if (a.on) return `出卡 ${a.i}/${a.n}` + (a.stop ? ' 停止中…' : '…')
    return '开始出卡'
  })

  async function toggleAgent() {
    if (agent.value.on) {
      agent.value.stop = true
      return
    }
    if (parsing.value || busy() || !opened.value) return
    if (!llm.value.ok) {
      ElMessage.warning('AI 未启用：' + (llm.value.msg || '没配置模型'))
      return
    }
    if (!hasParse.value) {
      ElMessage.info('先跑「AI 解析内容」，确认报告后再出卡')
      return
    }
    await runAgent()
  }

  async function runAgent() {
    if (agent.value.on || parsing.value || !opened.value) return // 自动触发和手点共用这个闸
    const docId = opened.value.id
    agent.value = { on: true, stop: false, phase: 'draft', i: 0, n: 0 }
    const stat = { made: 0, skipped: 0, watch: 0, failed: 0, dropped: 0 }
    try {
      // structure 不在这里跑：解析流程已经跑过（报告基于它的下标），
      // 再跑一次会重切章节、让报告的下标错位。
      await draftPhase(docId, stat)
      const parts = [`生成 ${stat.made} 张`]
      if (stat.dropped) parts.push(`跳过 ${stat.dropped} 章（报告剔除）`)
      if (stat.skipped) parts.push(`跳过 ${stat.skipped} 章（已有草稿）`)
      if (stat.watch) parts.push(`需人工把关 ${stat.watch} 章`)
      if (stat.failed) parts.push(`失败 ${stat.failed} 章`)
      ElMessage.success(
        (agent.value.stop ? '已停止。' : '完成：') +
          parts.join('、') +
          '。去「生成」页补齐 scene 后发布'
      )
    } catch (e) {
      // 可预期失败（没装 langgraph → 503、模型错 → 502）在这里给一次人话；
      // 单章失败在 draftPhase 里记账，不断整轮
      ElMessage.error(e?.message || '卡片 Agent 执行失败')
    } finally {
      agent.value.on = false
      agent.value.stop = false
      const r = await getDoc(docId).catch(() => null)
      if (r) opened.value = r.doc
      await fetchList()
    }
  }

  /** 阶段三：逐章出卡。只跑报告里「保留」的章。
   *  ok:false = 重写到上限也没对齐，落了草稿但要人工把关。 */
  async function draftPhase(docId, stat) {
    agent.value.phase = 'draft'
    const r = await getDoc(docId) // 分章/报告可能变过，重新拉
    opened.value = r.doc
    const parse = r.doc.parse
    const keeps = parse
      ? new Set((parse.chapters || []).filter(x => x.keep).map(x => x.index))
      : null
    if (parse) stat.dropped = (parse.chapters || []).filter(x => !x.keep).length
    const need = (r.doc.chapters || [])
      .map((c, i) => ({ c, i }))
      .filter(x => (x.c.body || '').trim().length >= 20 && (!keeps || keeps.has(x.i)))
    agent.value.n = need.length
    agent.value.i = 0
    for (let k = 0; k < need.length && !agent.value.stop; k++) {
      agent.value.i = k + 1
      try {
        const out = await cardsChapter(docId, need[k].i)
        if (out.skipped) stat.skipped++
        else {
          stat.made++
          if (!out.ok) stat.watch++
        }
      } catch {
        stat.failed++ // 单章失败不断整轮
      }
    }
  }

  /** 结构精修，失败不打断 —— 精修是增强不是地基，失败按现有分章继续。 */
  async function refineFirst(docId) {
    try {
      const s = await cardsStructure(docId)
      if (s.refined && s.doc && opened.value?.id === docId) {
        opened.value = s.doc // 新分章直接上屏
        ElMessage.success('分章已精修：' + (s.msg || `${s.chapters} 章`))
      } else if (!s.refined && s.msg) {
        ElMessage.warning('分章保持原样（' + s.msg + '）')
      }
    } catch (e) {
      ElMessage.warning('结构精修失败（' + (e.message || e) + '），按现有分章解析')
    }
  }

  /** 解析流程 = 结构精修（定分章点）→ 内容解析（有用/没用报告）。
   *  两步必须串行且顺序不能反：精修会重切章节，报告要基于最终下标。
   *  跑完**停住** —— 报告是终点，出卡等人确认后手动点。
   *  不 await 调用方：结构精修+判定可能要一两分钟，进度显示在按钮上。 */
  async function runParseFlow() {
    if (parsing.value || agent.value.on || !opened.value) return
    const docId = opened.value.id
    parsing.value = true
    try {
      await refineFirst(docId)
      const r = await parseDoc(docId)
      if (opened.value?.id === docId) opened.value = r.doc
      if (r.modelOk === false) {
        ElMessage.warning(
          'AI 判定没跑成（' + (r.msg || '模型不可用') + '），已用规则初筛，可手动勾选'
        )
      } else {
        ElMessage.success('解析完成 —— 看一眼报告，确认后再出卡')
      }
    } catch (e) {
      ElMessage.error(e?.message || '内容解析失败')
    } finally {
      parsing.value = false
      await fetchList()
    }
  }

  /** 报告页勾选：乐观更新（勾选框即时响应），保存失败回滚。 */
  async function toggleKeep(index, keep) {
    const docId = opened.value?.id
    const row = (opened.value?.parse?.chapters || []).find(r => r.index === index)
    if (!docId || !row) return
    const old = row.keep
    row.keep = keep
    try {
      const r = await putParseKeeps(docId, { [String(index)]: keep })
      if (opened.value?.id === docId) opened.value = r.doc
    } catch (e) {
      row.keep = old
      ElMessage.error('勾选保存失败：' + (e.message || e))
    }
  }

  /** 导入成功后自动开跑：展开文档 → 精修分章 → 内容解析 → **停在报告**。
   *  出卡不自动 —— 解析结果就是终点，什么时候出卡用户说了算。
   *  模型没启用也照跑：规则初筛照样能剔封面/目录，提示在返回值里。
   *  不 await：跑完报告为止可能要一两分钟，导入对话框不该陪着等。 */
  async function startAfterImport(doc) {
    if (!doc) return
    await openDoc(doc)
    const n = (doc.chapters || []).length || (doc.stats && doc.stats.chapters) || 0
    if (!n) return
    runParseFlow()
  }

  return {
    agent,
    agentLabel,
    toggleAgent,
    startAfterImport,
    parsing,
    hasParse,
    runParseFlow,
    toggleKeep
  }
}

/** 图片占位 → <img> 地址。鉴权带 ?t= token：浏览器 <img> 不发
 *  Authorization 头，逐张 fetch 转 blob 又要管一堆加载状态。 */
export function mediaSrc(docId, name) {
  const t = getToken()
  return `/api/media/${docId}/${encodeURIComponent(name)}${t ? '?t=' + t : ''}`
}

/** 正文切段：文字（预览截到 260 字）+ 图片，按原文顺序。
 *  直接 {{ body }} 会把 ![](media:x) 当字面量显示，图永远出不来。 */
export function bodySegs(body) {
  const out = []
  const s = body || ''
  const CAP = 260
  let used = 0
  let last = 0
  let m
  MEDIA_RE.lastIndex = 0 // 共享正则，先归零再遍历
  while ((m = MEDIA_RE.exec(s)) && used < CAP) {
    const txt = s.slice(last, m.index)
    if (txt) {
      const cut = txt.slice(0, CAP - used)
      out.push({ text: cut })
      used += cut.length
    }
    if (used < CAP) out.push({ img: m[1] }) // 图不吃预览预算
    last = m.index + m[0].length
  }
  const tail = s.slice(last)
  if (used < CAP) {
    const cut = tail.slice(0, CAP - used)
    if (cut) out.push({ text: cut })
    if (tail.length > cut.length) out.push({ text: '…' })
  }
  return out
}
