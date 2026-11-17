/* AI 补齐的批量队列 —— 「AI 补齐全部」一次排队跑完所有草稿。
 *
 * 放模块级（和 docs/docAuto.js 同一理由）：生成页切走，队列照跑，回来进度还在。
 * 刷新页面会断 —— 本地会话级的排队没必要落库，断了重跑一遍即可（补齐是幂等的）。
 *
 * 为什么是串行不是并发：本地 8B 一次只吃得下一路生成，并发几路只会互相抢
 * 显存、谁都不快；队列还保证了页面上「正在补第几张」的进度是真实的。
 */
import { ref } from 'vue'
import { fillDraft } from '@/api/ai'

/** { running, total, done, currentId, currentTitle, failed:[{title,msg}] } */
export const job = ref(null)

let cancelled = false

/** 取消：等当前这张补完就停（已经在模型里的那张不打断，避免半截 JSON 落盘）。 */
export function cancelFill() {
  cancelled = true
}

/**
 * 逐张补齐。单张失败不中断整队（一张 Ollama 抽风不该让后面的都不跑）。
 *
 * @param {Array<{id: string, title: string}>} drafts 取快照后的清单（循环期间
 *   列表刷新不影响它，靠 after 钩子把最新数据刷回视图）
 * @param {{start?:(id:string)=>void, after?:(id:string, ok:boolean)=>void}} hooks
 *   start：每张开始前（视图拿它标 busy）；after：每张结束后（刷新列表/表单）
 * @returns {Promise<{ok:number, empty:number, failed:Array<{title:string,msg:string}>}>}
 *   ok=补出新内容的张数；empty=跑了但没变化；failed=报错的
 */
export async function runFillAll(drafts, hooks = {}) {
  if (job.value && job.value.running) {
    return { ok: 0, empty: 0, failed: [], skipped: true }
  }
  cancelled = false
  job.value = {
    running: true,
    total: drafts.length,
    done: 0,
    currentId: '',
    currentTitle: '',
    failed: []
  }
  const res = { ok: 0, empty: 0, failed: [] }
  try {
    for (const d of drafts) {
      if (cancelled) break
      job.value.currentId = d.id
      job.value.currentTitle = d.title || ''
      hooks.start && hooks.start(d.id)
      let ok = false
      try {
        const r = await fillDraft(d.id)
        if ((r.changed || []).length) res.ok++
        else res.empty++
        ok = true
      } catch (e) {
        res.failed.push({ title: d.title || d.id, msg: e?.message || '失败' })
        job.value.failed = res.failed
      } finally {
        hooks.after && hooks.after(d.id, ok)
        job.value.done++
      }
    }
  } finally {
    job.value.running = false
    job.value.currentId = ''
    job.value.currentTitle = ''
  }
  return res
}
