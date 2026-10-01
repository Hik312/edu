/* 文档域状态：文档列表 + 当前打开的文档详情。
 *
 * 详情是「一次打开一份」，所以只留一个 current，不做缓存 map。
 * 章节正文几百 KB 一份，缓存多了内存先崩，而用户在同一会话里反复
 * 横跳多份文档的概率并不高。
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
    enriched.value = (r.doc && r.doc.aiEnriched) || []
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

  /** 逐章精读。batch 默认 1 —— 批量会把不同章节的内容串味，别改大。 */
  async function enrichChapter(docId, index) {
    const r = await aiApi.enrich({ docId, index, batch: 1 })
    if (!enriched.value.includes(index)) enriched.value.push(index)
    await fetchDocs()
    return r.ai
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
