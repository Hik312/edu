/* 「全部转卡」一键流程 —— 从 DocsView 拆出来的旧链路（那边 max-lines 700 到顶了），
 * 和 docAgent.js 对称：一个管精读 + to-card，一个管 LangGraph 新链路。
 *
 * 两条边界，都是踩过坑才加的：
 * 1. 精读仍然一次一章 —— /llm/enrich 一次传多个 index 实测会把 A 章的内容
 *    安到 B 章（批量串味），慢一点是不可谈判的成本，循环必须写在调用方；
 * 2. 已精读的章跳过、已有草稿的章也跳过 —— 跑一半点了停止，再点一次是
 *    **断点续跑**，不会重复精读，更不会生成两条同 id 的重复草稿。
 * 单步失败只记账不断整轮：单章失败不该把整轮打断。
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDoc } from '@/api/docs'
import { enrich, toCard } from '@/api/ai'
import { listDrafts } from '@/api/imports'

export function makeDocAuto({ opened, llm, fetchList, agentBusy }) {
  /** 一键全量状态。按钮上直接显示进度（精读 3/12… / 转卡 2/10…），
   *  再点一次是请求停止 —— 长任务没有停止按钮的话用户只能刷新页面。 */
  const auto = ref({ on: false, stop: false, phase: 'enrich', i: 0, n: 0 })
  const autoLabel = computed(() => {
    const a = auto.value
    if (!a.on) return '全部转卡'
    const phase = a.phase === 'enrich' ? '精读 ' : '转卡 '
    return phase + a.i + '/' + a.n + (a.stop ? ' 停止中…' : '…')
  })

  async function toggleAuto() {
    if (auto.value.on) {
      auto.value.stop = true
      return
    }
    await runAuto()
  }

  /** 一键全量：逐章精读 → 逐章转草稿卡（生成的卡都挂当前文档的卡片组）。
   *  拆成两个阶段方法不是为了好看 —— 合在一起 eslint 复杂度 16 超了上限 15。 */
  async function runAuto() {
    if (!llm.value.ok) {
      ElMessage.warning('AI 未启用：' + (llm.value.msg || '没配置模型'))
      return
    }
    if (agentBusy()) return // 两条链互斥，别同时跑
    const docId = opened.value.id
    auto.value = { on: true, stop: false, phase: 'enrich', i: 0, n: 0 }
    const stat = { enriched: 0, made: 0, failed: 0 }
    try {
      await enrichAll(docId, stat)
      await convertAll(docId, stat)
      ElMessage.success(
        (auto.value.stop ? '已停止。' : '完成：') +
          `精读 ${stat.enriched} 章、生成 ${stat.made} 张草稿卡` +
          (stat.failed ? `、失败 ${stat.failed} 项` : '') +
          '。去「生成」页补齐 scene 后发布'
      )
    } finally {
      auto.value.on = false
      auto.value.stop = false
      const r = await getDoc(docId).catch(() => null)
      if (r) opened.value = r.doc
      await fetchList()
    }
  }

  /** 阶段一：逐章精读（正文 <20 字的纯标题章跳过）。 */
  async function enrichAll(docId, stat) {
    const need = (opened.value.chapters || [])
      .map((c, i) => ({ c, i }))
      .filter(x => (x.c.body || '').trim().length >= 20)
    auto.value.n = need.length
    for (let k = 0; k < need.length && !auto.value.stop; k++) {
      auto.value.i = k + 1
      const { c, i } = need[k]
      if (hasAi(c)) continue
      try {
        await enrich({ docId, index: i })
        stat.enriched++
      } catch {
        stat.failed++ // 单章失败不断整轮
      }
    }
  }

  /** 阶段二：把有精读结果、还没转过卡的章转成草稿。 */
  async function convertAll(docId, stat) {
    const r = await getDoc(docId)
    opened.value = r.doc
    auto.value.phase = 'convert'
    const drafts = (await listDrafts()).drafts || []
    // 已有草稿按「同组 + 同标题」认（llm.to_card 的标题截断到 60 字，跟着截）
    const have = new Set(
      drafts.filter(d => d.deckId === docId).map(d => String(d.title || '').slice(0, 60))
    )
    const targets = (opened.value.chapters || [])
      .map((c, i) => ({ c, i }))
      .filter(x => hasAi(x.c) && !have.has(String(x.c.title || '').slice(0, 60)))
    auto.value.n = targets.length
    auto.value.i = 0
    for (let k = 0; k < targets.length && !auto.value.stop; k++) {
      auto.value.i = k + 1
      try {
        await toCard(docId, targets[k].i)
        stat.made++
      } catch {
        stat.failed++
      }
    }
  }

  /** 这一章算不算「已精读」：enrich 落盘的 ai 至少要有结论或原理拆解。
   *  比单看 analogy 宽一点 —— 模型偶尔不给类比，但结果本身是可用的。 */
  function hasAi(c) {
    const a = c.ai || {}
    return Boolean(a.oneLine || a.analogy || (a.mechanism && a.mechanism.length))
  }

  return { auto, autoLabel, toggleAuto }
}
