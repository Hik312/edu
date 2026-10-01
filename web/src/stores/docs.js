/* 文档域状态：文档列表 + 当前打开的文档详情。
 *
 * 详情是「一次打开一份」，所以只留一个 current，不做缓存 map。
 * 章节正文几百 KB 一份，缓存多了内存先崩，而用户在同一会话里反复
 * 横跳多份文档的概率并不高。
 *
 * ⚠️ 现状：**这个 store 目前没有任何页面引用**（全仓 grep useDocsStore
 * 只命中本文件的定义）。DocsView.vue 自己在页面里直接调 api/docs 和
 * api/ai，把这里的职责重写了一遍 —— 所以下面这两处契约错误长期没有
 * 暴露的机会（已经修好，但根因还在）。
 * 真要收口，应该让 DocsView 改调本 store；那是一次独立重构，别顺手做。
 * 在那之前，**改文档相关接口时记得两边都看**。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as docsApi from '@/api/docs'
import * as aiApi from '@/api/ai'

export const useDocsStore = defineStore('docs', () => {
  const list = ref([])
  const loading = ref(false)
  const current = ref(null)

  /** AI 精读可用性。ok:false 不算故障，只是「没开」。 */
  const llm = ref({ ok: false, msg: '' })

  /** 当前文档已精读的章节下标集合，用来在章节列表上打勾。 */
  const enriched = ref([])

  async function fetchDocs() {
    loading.value = true
    try {
      const r = await docsApi.listDocs()
      list.value = r.docs || []
    } finally {
      loading.value = false
    }
  }

  async function openDoc(did) {
    const r = await docsApi.getDoc(did)
    current.value = r.doc
    // ★ 后端没有 aiEnriched 这个字段。
    // 已精读的章节是「chapter 自己带 ai 字段」，进度是 doc.aiDone / aiTotal。
    // 从前读 r.doc.aiEnriched 恒为 undefined → enriched 永远是空数组 →
    // 章节列表上的「已精读」勾一个都打不出来。
    enriched.value = ((r.doc && r.doc.chapters) || [])
      .map((ch, i) => (ch && ch.ai ? i : -1))
      .filter(i => i >= 0)
    return r.doc
  }

  async function importDoc(body) {
    const r = await docsApi.importDoc(body)
    await fetchDocs()
    return r.doc
  }

  async function removeDoc(did) {
    await docsApi.removeDoc(did)
    if (current.value && current.value.id === did) current.value = null
    await fetchDocs()
  }

  async function fetchLlmStatus() {
    const r = await aiApi.getLlmStatus()
    llm.value = {
      ok: Boolean(r.ok),
      msg: r.msg || '',
      provider: r.provider || '',
      model: r.model || ''
    }
    return llm.value
  }

  /** 逐章精读。batch 默认 1 —— 批量会把不同章节的内容串味，别改大。
   *
   *  ★ 返回值：传了 docId 时后端走 `_enrich_doc`，回的是
   *  `{ok, done, failed, skipped, doc}` —— **没有 ai 字段**（只有不带
   *  docId、直接精读一段文字时才回 `ai`）。从前这里 `return r.ai` 恒为
   *  undefined，调用方拿到空值还会以为精读没生效。
   *  这里从回填后的 doc 里取这一章的 ai。
   */
  async function enrichChapter(docId, index) {
    const r = await aiApi.enrich({ docId, index, batch: 1 })
    if (r && r.doc) current.value = r.doc
    if (!enriched.value.includes(index)) enriched.value.push(index)
    await fetchDocs()
    const chs = (r && r.doc && r.doc.chapters) || []
    return (chs[index] && chs[index].ai) || null
  }

  const currentChapters = computed(() => (current.value && current.value.chapters) || [])

  return {
    list,
    loading,
    current,
    llm,
    enriched,
    currentChapters,
    fetchDocs,
    openDoc,
    importDoc,
    removeDoc,
    fetchLlmStatus,
    enrichChapter
  }
})
