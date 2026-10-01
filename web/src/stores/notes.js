/* 笔记域状态。
 *
 * 后端是「带 id 就是更新，不带就是新建」的单一 save 接口，
 * 这里刻意保留同样的写法 —— 前端再拆成 create/update 两个方法，
 * 反而要多维护一处「到底该调谁」的判断。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as notesApi from '@/api/notes'

export const useNotesStore = defineStore('notes', () => {
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)

  /** 搜索词。跟卡片列表一样放在 store 里，返回列表时不丢。 */
  const keyword = ref('')
  /** 按卡片过滤：从某张卡详情点「我的理解」进来时用。 */
  const cardFilter = ref('')

  async function fetchNotes() {
    loading.value = true
    try {
      const params = {}
      if (keyword.value.trim()) params.q = keyword.value.trim()
      if (cardFilter.value) params.cardId = cardFilter.value
      const r = await notesApi.listNotes(params)
      list.value = r.notes || []
      total.value = r.total || 0
    } finally {
      loading.value = false
    }
  }

  /** 新建或更新。返回后端给的笔记对象（含 id）。 */
  async function save(body) {
    const r = await notesApi.saveNote(body)
    await fetchNotes()
    return r.note
  }

  async function remove(nid) {
    await notesApi.removeNote(nid)
    // 只在本地剔掉这一条，不整页重取：删一条笔记把输入框里的草稿也刷掉太糟心
    list.value = list.value.filter(n => n.id !== nid)
    total.value = Math.max(0, total.value - 1)
  }

  /** 某张卡下挂了几条笔记。卡片详情底部显示用。 */
  function notesOfCard(cid) {
    return list.value.filter(n => n.cardId === cid)
  }

  const isFiltered = computed(() => Boolean(keyword.value.trim()) || Boolean(cardFilter.value))

  return {
    list,
    total,
    loading,
    keyword,
    cardFilter,
    isFiltered,
    fetchNotes,
    save,
    remove,
    notesOfCard
  }
})
