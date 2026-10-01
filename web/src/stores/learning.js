/* 学习域状态：今日复习队列 + 掌握度标记 + 统计 + 今日学习设置。
 *
 * 一个刻意的产品决定：标记完一张卡**不重排队列**。
 * 队列顺序是后端按到期时间算好的，标一下就全部重排会让卡片在眼皮底下跳位置，
 * 用户会以为自己标错了。本地改掉这一条的状态就够了，下次进页面自然重排。
 *
 * ## 学习设置（每日目标 + 方向）存在后端档案，不在 localStorage
 *
 * 它决定「今天推哪些卡」，跟岗位、薄弱卡一样是**关于这个人的**数据 ——
 * 换台设备就没了会很莫名。写入走 PUT /api/agent/profile，字段
 * dailyTarget / directions（None = 不动，[] = 清空，语义在后端 save_profile）。
 *
 * ## 方向由 store 统一带进每一次取队列
 *
 * 复习页、驾驶舱滚动榜、今日路径取的是**同一批卡**：方向只在一处注入
 * （fetchDue），否则用户会看到「复习页推 Agent、路径页却是全库」的分裂。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as learningApi from '@/api/learning'
import { getProfile, putProfile } from '@/api/agent'
import { getDirections } from '@/api/system'
import { useCardsStore } from '@/stores/cards'

/** 每日目标从没设过时按这个值显示。定 20 而不是接口默认的 50：50 几乎等于
 *  全库（67 张），那不叫目标，叫「一次全看完」。 */
export const DAILY_DEFAULT = 20

/** 每日目标可调范围。和这里保持一致的还有设置条上的步进（±5）。 */
export const DAILY_MIN = 5
export const DAILY_MAX = 100

export const useLearningStore = defineStore('learning', () => {
  const queue = ref([])
  const total = ref(0)
  const today = ref('')
  const loading = ref(false)

  /** 正在等待后端的卡片 id 集合。用于只让那一张卡显示 loading，
   *  而不是整个页面转圈（要不然标一张卡闪一下全屏，很像卡死了）。 */
  const marking = ref({})

  const stats = ref(null)

  // ---- 今日学习设置（后端档案里的 dailyTarget / directions） ----
  /** 方向目录（data/directions.js，含每个方向的 count）。 */
  const directions = ref([])
  /** 每天学几张。拉到档案前先用默认值，档案里 0 也当没设过。 */
  const dailyTarget = ref(DAILY_DEFAULT)
  /** 选中的方向 id。空 = 全部方向（不过滤）。 */
  const pickedDirs = ref([])

  /** 方向名（档案里存的是 id，首页要显示中文名）。 */
  const dirNames = computed(() =>
    pickedDirs.value.map(id => (directions.value.find(d => d.id === id) || {}).name || id)
  )
  const dirText = computed(() => dirNames.value.join(' · '))

  /** 档案 + 方向目录只拉一次。失败也要 resolve —— 拿不到设置不该把
   *  复习队列也拖死（那时按默认值走，队列照常能取）。 */
  let settingsP = null
  function ensureSettings() {
    if (!settingsP) {
      settingsP = Promise.all([
        getProfile().catch(() => null),
        getDirections().catch(() => null)
      ]).then(([p, d]) => {
        if (p) {
          dailyTarget.value = p.dailyTarget || DAILY_DEFAULT
          pickedDirs.value = Array.isArray(p.directions) ? p.directions : []
        }
        if (d && Array.isArray(d.directions)) directions.value = d.directions
      })
    }
    return settingsP
  }

  /** 退出登录 / 换账号时调。
   *
   * ★ 为什么必须显式重置：`settingsP` 一旦 resolve 就永不再取档案，
   * 而登出只清了 auth store。同一 SPA 会话里换账号后，
   * `pickedDirs` 还是上一个人的方向，`fetchDue` 会把它注入**新用户**的队列；
   * `dailyTarget` 同理。刷新页面才会恢复 —— 这正是「换个人登录，怎么推的
   * 还是他的内容」那类说不清的 bug。AppLayout 的登出流程会调这里。 */
  function resetSettings() {
    settingsP = null
    directions.value = []
    dailyTarget.value = DAILY_DEFAULT
    pickedDirs.value = []
  }

  /** 改设置：写后端档案，成功后用**服务端返回的那份**回填本地
   *  （截断/去重在后端做，本地自己算一遍迟早跟它不一致）。 */
  async function saveSettings(patch) {
    const saved = await putProfile(patch)
    if (saved && saved.dailyTarget != null) {
      dailyTarget.value = saved.dailyTarget || DAILY_DEFAULT
    }
    if (saved && Array.isArray(saved.directions)) {
      pickedDirs.value = saved.directions
    }
    return saved
  }

  /** 队列里还剩几张没标过的。 */
  const unmarked = computed(() => queue.value.filter(c => !c.level).length)

  /** 三档分布，给大屏的饼图/胶囊图用。 */
  const distribution = computed(() => {
    const base = { known: 0, fuzzy: 0, weak: 0, unmarked: 0 }
    queue.value.forEach(c => {
      if (c.level === 3) base.known++
      else if (c.level === 2) base.fuzzy++
      else if (c.level === 1) base.weak++
      else base.unmarked++
    })
    return base
  })

  /** 并发取队列的序号。**后发先回的旧响应必须丢掉。**
   *
   * ★ 从前是 `queue.value = r.queue` 直接赋值，谁后回来谁赢。
   * 复习页快速连点「跳过」、路径页快速连点两个岗位时，旧请求晚于新请求
   * 返回，就会把新结果覆盖成旧岗位/旧队列的 —— 页面显示的内容和用户
   * 刚点的东西对不上。防抖只缩小窗口，并不保证顺序（这点注释里曾经
   * 写反了）。
   */
  let dueSeq = 0

  async function fetchDue(params) {
    await ensureSettings() // 方向没拿到之前先别取队列，否则取到的是全库
    const seq = ++dueSeq
    loading.value = true
    try {
      const p = Object.assign({}, params)
      // 方向是「今天学什么」的全局开关，每次取队列自动带上。
      // 显式传了 dirs 的调用方除外（比如调试时想看某个方向）。
      if (pickedDirs.value.length && p.dirs === undefined) {
        p.dirs = pickedDirs.value.join(',')
      }
      const r = await learningApi.getDue(p)
      // 已经有更新的请求发出去了，丢弃这份迟到的旧响应
      if (seq !== dueSeq) return
      queue.value = r.queue || []
      total.value = r.total || 0
      today.value = r.today || ''
    } finally {
      if (seq === dueSeq) loading.value = false
    }
  }

  /** 标记掌握度。失败要把本地状态改回去 —— 网络失败但界面显示成功了，
   *  用户刷新一看又变回去，是最让人不信应用的那种 bug。 */
  async function mark(cid, level) {
    const item = queue.value.find(c => c.id === cid)
    const old = item ? item.level : 0
    if (item) item.level = level
    // ★ 卡片列表里的同一张卡也必须跟着变。
    // `cards.list` 和 `queue` 是**两批不同的对象**（分别来自 /cards 和
    // /review/due）。从前只改了 queue 和详情缓存，于是「在抽屉里标了会、
    // 关掉抽屉，列表上那张卡还是未标记」，要重新筛选才更新。
    const cards = useCardsStore()
    const listItem = (cards.list || []).find(c => c.id === cid)
    const oldList = listItem ? listItem.level : undefined
    if (listItem) listItem.level = level
    marking.value[cid] = true
    try {
      await learningApi.markCard(cid, level)
      await fetchStats()
    } catch (e) {
      if (item) item.level = old
      if (listItem) listItem.level = oldList
      throw e
    } finally {
      delete marking.value[cid]
    }
  }

  async function reset(cid) {
    await learningApi.resetCard(cid)
    const item = queue.value.find(c => c.id === cid)
    if (item) {
      item.level = 0
      item.nextAt = null
      item.overdue = null
    }
    await fetchStats()
  }

  async function fetchStats() {
    const r = await learningApi.getStats()
    stats.value = r.stats
    return r.stats
  }

  return {
    queue,
    total,
    today,
    loading,
    marking,
    stats,
    unmarked,
    distribution,
    directions,
    dailyTarget,
    pickedDirs,
    dirNames,
    dirText,
    ensureSettings,
    resetSettings,
    saveSettings,
    fetchDue,
    mark,
    reset,
    fetchStats
  }
})
