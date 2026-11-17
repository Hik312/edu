/* 卡片域状态。
 *
 * 筛选条件放在 store 里而不是组件里，是为了**从详情返回列表时不丢筛选**——
 * 用户翻到第 3 页点进一张卡，按返回键回来看见自己刚才的位置，这是最基本的体面。
 *
 * 详情页的全文（mechanism / diagram）体积不小，所以详情单独一套缓存，
 * 列表里只留轻字段。
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import * as cardsApi from '@/api/cards'

const FILTER_DEFAULTS = { category: '', subject: '', domain: '', deckId: '', q: '' }

/** 筛选条件刷新不丢：store 只活在内存里，上面注释说的「返回列表不丢筛选」
 *  挡得住返回键，挡不住刷新。读坏了就用默认值，绝不让坏数据拦住开页。 */
function loadFilters() {
  try {
    const s = JSON.parse(localStorage.getItem('edu.cardFilters') || '{}')
    const out = { ...FILTER_DEFAULTS }
    for (const k of Object.keys(FILTER_DEFAULTS)) {
      if (typeof s[k] === 'string') out[k] = s[k]
    }
    return out
  } catch {
    return { ...FILTER_DEFAULTS }
  }
}

export const useCardsStore = defineStore('cards', () => {
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)

  /** 分类树（导航菜单用）。整个会话变不了，取一次就够。 */
  const catalog = ref([])
  /** MOC 树（知识框架页面用），比 catalog 深一层到 topicPath。 */
  const outline = ref([])

  /** 单张卡详情缓存：{ [cardId]: card }。同一张卡第二次打开不再发请求。 */
  const details = ref({})

  // 筛选条件。改任一项都要调 fetchList() 才会生效 —— 刻意不让组件直接改 list
  // deckId = 卡片组（文件夹）：文档转出来的卡都挂在这份文档的 id 下
  // 组件可以直接改 filters.q（搜索框），所以持久化用 deep watch 兜住所有改法
  const filters = ref(loadFilters())
  watch(
    filters,
    v => {
      try {
        localStorage.setItem('edu.cardFilters', JSON.stringify(v))
      } catch {
        /* 忽略 */
      }
    },
    { deep: true }
  )

  const hasFilter = computed(() => {
    const f = filters.value
    return Boolean(f.category || f.subject || f.domain || f.deckId || f.q.trim())
  })

  async function fetchList() {
    loading.value = true
    try {
      const f = filters.value
      // ★ 固定要 brief=1：列表页只需要 id/title/oneLine/tags/level/deck，
      // 不带它时后端会把每张卡的 mechanism / scene / diagram 全吐出来。
      // 实测 67 张卡是 118KB，带 brief 只有 22KB —— 5.3 倍，
      // 而且详情页本来就会单独拉一次 /cards/{id} 拿全字段。
      const params = { brief: '1' }
      // 空串不发给后端：虽然后端容错，但 URL 里挂一串 &= 很难读
      if (f.category) params.category = f.category
      if (f.subject) params.subject = f.subject
      if (f.domain) params.domain = f.domain
      if (f.deckId) params.deckId = f.deckId
      if (f.q.trim()) params.q = f.q.trim()

      const r = await cardsApi.listCards(params)
      list.value = r.cards || []
      total.value = r.total || 0
    } finally {
      loading.value = false
    }
  }

  async function fetchCatalog() {
    if (catalog.value.length) return catalog.value
    const r = await cardsApi.getCatalog()
    catalog.value = r.catalog || []
    return catalog.value
  }

  async function fetchOutline() {
    if (outline.value.length) return outline.value
    const r = await cardsApi.getOutline()
    outline.value = r.tree || []
    return outline.value
  }

  /** 取详情。带缓存，force 用于「刚改完要立刻看到新内容」的场景。 */
  async function fetchDetail(cid, force = false) {
    if (!force && details.value[cid]) return details.value[cid]
    const r = await cardsApi.getCard(cid)
    details.value[cid] = r.card
    return r.card
  }

  function setFilter(key, value) {
    filters.value[key] = value
    // 换了科目但科目不属于新分类时清掉，否则筛出来是空的，用户以为数据没了
    if (key === 'category') filters.value.subject = ''
  }

  function resetFilter() {
    filters.value = { ...FILTER_DEFAULTS }
  }

  async function createCard(body) {
    await cardsApi.createCard(body)
    await fetchList()
  }

  async function updateCard(cid, body) {
    await cardsApi.updateCard(cid, body)
    delete details.value[cid]
    await fetchList()
  }

  async function removeCard(cid) {
    await cardsApi.removeCard(cid)
    delete details.value[cid]
    await fetchList()
  }

  return {
    list,
    total,
    loading,
    catalog,
    outline,
    details,
    filters,
    hasFilter,
    fetchList,
    fetchCatalog,
    fetchOutline,
    fetchDetail,
    setFilter,
    resetFilter,
    createCard,
    updateCard,
    removeCard
  }
})
