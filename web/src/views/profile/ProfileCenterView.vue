<script setup>
/* 个人中心 —— 学习效果闭环。
 *
 * 五个 Tab 对应「学了什么 / 哪里没会 / 会怎么忘 / 花了多少时间 / 我是谁」：
 *   概览      关键指标 + 连续学习天数 + 最近一次复习摘要
 *   错题本    按周期汇总「不会 / 模糊」的卡，支持周 / 月 / 全部
 *   遗忘曲线  单卡的 BKT 概率 p 随时间变化；整体看时画日均 p
 *   学习时长  日热力图 + 按领域分布 + 按卡片 Top 榜
 *   个人信息  显示名称可改；用户名 / 角色只读（见后端 db.update_user_profile）
 *
 * 数据全部来自后端 `app/routers/profile.py`（当前未实现时接口返回空结构）。
 * 页面拿到什么就画什么：后端没上线时显示占位提示，不显示「假数据」。
 *
 * ## 埋点
 * 复习页 `ReviewView` 在每张卡进入/离开时写一条记录到
 * `localStorage['edu.review.track']`。个人中心挂载时把它批量上报后端，
 * 成功后清空本地队列。后端 `/profile/review-sessions/batch` 落库。
 *
 * ## 配色
 * 全站统一牛皮纸，图表颜色用 `config/theme.js` 的语义色 + SEQ 序列色。
 * 不引入 ECharts 深色主题。
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useLearningStore } from '@/stores/learning'
import { useCardsStore } from '@/stores/cards'
import {
  getProfileOverview,
  getMistakeBook,
  getForgettingCurve,
  getReviewHeatmap,
  getStudyTime,
  getTrueRetention,
  batchReportReviewSessions
} from '@/api/profile'
import { levelColor, colorOf, INK, SEQ, chartBase } from '@/config/theme'
import EChart from '@/components/EChart.vue'

const router = useRouter()
const auth = useAuthStore()
const learning = useLearningStore()
const cards = useCardsStore()

// ---- Tab 管理 ----
const activeTab = ref('overview')

// ---- 概览 ----
const overview = ref(null)
const overviewLoading = ref(false)

// ---- 错题本 ----
const mistakePeriod = ref('week')
const mistakes = ref(null)
const mistakeLoading = ref(false)
const MISTAKE_PERIODS = [
  { value: 'week', label: '本周' },
  { value: 'month', label: '本月' },
  { value: 'all', label: '全部' }
]

// ---- 记忆保持率（True Retention）与复习热力图（2026-11-15 加） ----
const retention = ref(null)
const retentionLoading = ref(false)
const RET_RANGES = ['today', 'month', 'year', 'all']
const RET_RANGE_LABEL = { today: '今天', month: '本月', year: '今年', all: '全部' }
const heatYear = ref(new Date().getFullYear())
const heatmap = ref(null)
const heatmapLoading = ref(false)

// ---- 遗忘曲线 ----
const curveDays = ref(30)
const curveCardId = ref('')
const curve = ref(null)
const curveLoading = ref(false)
const CURVE_DAYS_OPTIONS = [
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
  { value: 90, label: '近 90 天' }
]

/** 可选卡片（取当前队列 + 详情缓存合并去重）。 */
const cardOptions = computed(() => {
  const map = new Map()
  ;(learning.queue || []).forEach(c => map.set(c.id, c))
  Object.values(cards.details || {}).forEach(c => map.set(c.id, c))
  return Array.from(map.values())
    .filter(c => c && c.title)
    .map(c => ({ value: c.id, label: c.title }))
    .slice(0, 50)
})

// ---- 学习时长 ----
const timePeriod = ref('week')
const studyTime = ref(null)
const timeLoading = ref(false)
const TIME_PERIODS = [
  { value: 'week', label: '本周' },
  { value: 'month', label: '本月' },
  { value: 'year', label: '全年' },
  { value: 'all', label: '全部' }
]

// ---- 个人信息 ----
const profileSaving = ref(false)
const profileForm = ref({ displayName: '' })

/** 把当前登录用户灌进表单。
 *  在切到该 tab 时调用 —— 表单初始值不能写死在 setup 顶层，
 *  刷新页面时 auth.user 是异步取回来的，顶层读到的是 null。 */
function syncProfileForm() {
  profileForm.value = { displayName: auth.user?.displayName || '' }
}

/** 保存个人信息。成功后 auth store 里的 user 就地更新（见 stores/auth.js），
 *  头部问候语跟着变，不用刷新页面。 */
async function saveProfile() {
  profileSaving.value = true
  try {
    await auth.updateProfile({ displayName: profileForm.value.displayName })
    // 回灌一次表单：留空保存时后端会回退成用户名（见 db.update_user_profile），
    // store 里已经是回退后的值，但输入框还挂着空串 —— 不回填就看着像「没保存上」。
    syncProfileForm()
    ElMessage.success('昵称已更新')
  } catch (e) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    profileSaving.value = false
  }
}

// ---- 上报复习埋点 ----
const TRACK_KEY = 'edu.review.track'

/** 读取本地埋点队列。
 *  条目形状：{ cardId, durationSeconds, level, ts, sessionId } */
function readTrackQueue() {
  try {
    const raw = JSON.parse(localStorage.getItem(TRACK_KEY) || '[]')
    return Array.isArray(raw) ? raw : []
  } catch {
    return []
  }
}

function writeTrackQueue(items) {
  try {
    if (!items.length) localStorage.removeItem(TRACK_KEY)
    else localStorage.setItem(TRACK_KEY, JSON.stringify(items.slice(-200)))
  } catch {
    /* 配额满就丢，不影响复习 */
  }
}

/** 批量上报埋点。失败时保留队列，下次进页面再试。 */
async function flushTrackQueue() {
  const items = readTrackQueue()
  if (!items.length) return
  try {
    await batchReportReviewSessions(items)
    writeTrackQueue([])
  } catch {
    // 保留本地队列，下次再报
  }
}

// ---- 加载各 Tab 数据 ----
async function loadOverview() {
  overviewLoading.value = true
  try {
    const r = await getProfileOverview()
    overview.value = r.data || null
  } catch {
    overview.value = null
  } finally {
    overviewLoading.value = false
  }
}

async function loadMistakes() {
  mistakeLoading.value = true
  try {
    const r = await getMistakeBook({ period: mistakePeriod.value })
    mistakes.value = r.data || null
    // 数据换了，滚动位置必须复位 —— 否则从「本周」切到「本月」，
    // 列表还是停在上次滚到的位置，看着像内容没换。
    resetScroll()
  } catch {
    mistakes.value = null
  } finally {
    mistakeLoading.value = false
  }
}

async function loadCurve() {
  curveLoading.value = true
  try {
    const params = { days: curveDays.value }
    if (curveCardId.value) params.cardId = curveCardId.value
    const r = await getForgettingCurve(params)
    curve.value = r.data || null
  } catch {
    curve.value = null
  } finally {
    curveLoading.value = false
  }
}

async function loadStudyTime() {
  timeLoading.value = true
  try {
    const r = await getStudyTime({ period: timePeriod.value })
    studyTime.value = r.data || null
  } catch {
    studyTime.value = null
  } finally {
    timeLoading.value = false
  }
}

async function loadRetention() {
  retentionLoading.value = true
  try {
    const r = await getTrueRetention()
    retention.value = r.data || null
  } catch {
    retention.value = null
  } finally {
    retentionLoading.value = false
  }
}

async function loadHeatmap() {
  heatmapLoading.value = true
  try {
    const r = await getReviewHeatmap({ year: heatYear.value })
    heatmap.value = r.data || null
  } catch {
    heatmap.value = null
  } finally {
    heatmapLoading.value = false
  }
}

function shiftYear(delta) {
  heatYear.value = Math.max(2000, Math.min(2100, heatYear.value + delta))
  loadHeatmap()
}

function onTabChange() {
  if (activeTab.value === 'overview' && !overview.value && !overviewLoading.value) loadOverview()
  if (activeTab.value === 'mistakes' && !mistakes.value && !mistakeLoading.value) loadMistakes()
  if (activeTab.value === 'curve' && !curve.value && !curveLoading.value) loadCurve()
  if (activeTab.value === 'time' && !studyTime.value && !timeLoading.value) loadStudyTime()
  if (activeTab.value === 'retention' && !retention.value && !retentionLoading.value) loadRetention()
  if (activeTab.value === 'profile') syncProfileForm()
}

onMounted(() => {
  flushTrackQueue()
  loadOverview()
  // 概览上的复习热力图：随页一起拉（张数口径，轻量聚合）
  loadHeatmap()
})

onUnmounted(() => {
  // 离开页面时尝试再报一次，避免丢数据
  flushTrackQueue()
})

// ===========================================================================
// 概览
// ===========================================================================

/** 概览指标卡。 */
const overviewMetrics = computed(() => {
  const d = overview.value
  if (!d) return []
  return [
    { key: 'totalReviews', label: '累计复习', value: d.totalReviews ?? 0, color: INK.accent },
    { key: 'totalCards', label: '掌握卡片', value: d.totalCards ?? 0, color: INK.known },
    { key: 'weakCards', label: '薄弱卡片', value: d.weakCards ?? 0, color: INK.weak },
    {
      key: 'avgMastery',
      label: '平均掌握度',
      value: d.avgMastery != null ? Math.round(d.avgMastery * 100) + '%' : '—',
      color: INK.fuzzy
    },
    { key: 'studyDays', label: '学习天数', value: d.studyDays ?? 0, color: '#c08a2e' },
    {
      key: 'totalMinutes',
      label: '总学习时长',
      value: d.totalMinutes != null ? Math.round(d.totalMinutes / 60) + 'h' : '—',
      color: '#3f8f6d'
    },
    { key: 'streakDays', label: '连续学习', value: (d.streakDays ?? 0) + ' 天', color: '#a8553f' }
  ]
})

// ===========================================================================
// 记忆保持率（True Retention）+ 复习热力图（2026-11-15 加）
// ===========================================================================

/** 保持率表的三行：young / mature / total。 */
const retentionRows = [
  { key: 'young', label: '新卡（间隔 <21 天）' },
  { key: 'mature', label: '成熟卡（间隔 ≥21 天）' },
  { key: 'total', label: '合计' }
]

/** 单元格文本：有样本 → 「94.2% (41/44)」；没样本 → 「—」。 */
function fmtCell(key, rng) {
  const c = retention.value?.[rng]?.[key]
  if (!c || !c.total) return '—'
  return Math.round((c.rate || 0) * 100) + '% (' + c.correct + '/' + c.total + ')'
}

/** 成熟卡记得率高 → 绿（好），低于新卡 → 赭黄（该警惕）。 */
function cellColor(key, rng) {
  const c = retention.value?.[rng]?.[key]
  if (!c || !c.total || c.rate == null) return null
  if (key === 'mature') return c.rate >= 0.85 ? INK.known : (c.rate >= 0.7 ? '#c08a2e' : INK.weak)
  if (key === 'young') return c.rate >= 0.75 ? '#3f8f6d' : INK.fuzzy
  return null
}

/** ECharts 日历热力图。颜色从纸色渐进到墨绿（与全站牛皮纸协调）。
 *  没有数据的日子补成 calendar 上缺席（ECharts 自己画空格）。 */
const HEAT_RAMP = ['#e8e2cf', '#c9d8a4', '#8fb573', '#5d8a54', '#2f5d3a']
const heatOption = computed(() => {
  const days = heatmap.value?.days || []
  const year = String(heatYear.value)
  const max = Math.max(1, ...days.map(d => d.count))
  return {
    tooltip: {
      formatter: (p) => {
        const v = Array.isArray(p.value) ? p.value : [null, 0]
        return `${v[0]}：刷了 ${v[1]} 张`
      }
    },
    visualMap: {
      min: 0, max, show: false,
      inRange: { color: HEAT_RAMP }
    },
    calendar: {
      range: year,
      cellSize: ['auto', 13],
      left: 36, right: 8, top: 14,
      splitLine: { show: false },
      itemStyle: { color: 'rgba(0,0,0,0.04)', borderWidth: 2, borderColor: 'transparent' },
      dayLabel: { color: '#8a8473', fontSize: 10 },
      monthLabel: { color: '#8a8473', fontSize: 10 },
      yearLabel: { show: false }
    },
    series: [{
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: days.map(d => [d.date, d.count])
    }]
  }
})

// ===========================================================================
// 错题本
// ===========================================================================

/** 按 level 分组的错题列表。
 *  后端返回 weakCards / fuzzyCards，前端按 level 排序。 */
const weakList = computed(() =>
  (mistakes.value?.weakCards || []).slice().sort((a, b) => (b.count || 0) - (a.count || 0))
)
const fuzzyList = computed(() =>
  (mistakes.value?.fuzzyCards || []).slice().sort((a, b) => (b.count || 0) - (a.count || 0))
)

/** 两个滚动容器的 DOM 引用（薄弱卡 / 模糊卡各自独立滚动）。 */
const weakBox = ref(null)
const fuzzyBox = ref(null)

/** 超过多少张才提示「可滚动」。
 *
 *  ★ 为什么要算这个而不是无条件显示：滚动容器的上限是 `clamp(180px, 42vh, 420px)`，
 *    一行卡片约 42px，所以**不超过 10~11 张根本不会溢出**。
 *    无条件写「可滚动 ↓」等于骗人——用户滚了发现没反应，下次就不信这个提示了。
 *    （这与「图表不能画出数据里没有的东西」是同一种诚实性。）
 */
const SCROLL_HINT_MIN = 11

/** 是否已经滚到底部。
 *
 *  ★ 为什么要判断这个：`.scroll-box` 用 mask-image 给内容底部加了渐隐，
 *    提示「下面还有」。但**滚到底之后**如果还留着渐隐，最后一行永远是淡的，
 *    看着像没加载完 / 有 bug。所以到底了就摘掉渐隐。
 *
 *  用 ±2px 容差：不同浏览器的 scrollTop 最大值会差1px，
 *  严格相等判断在某些浏览器上永远不成立，渐隐就摘不掉。
 */
function atScrollEnd(el) {
  if (!el) return false
  return el.scrollHeight - el.scrollTop - el.clientHeight <= 2
}

/** 切周期 / 切tab 后滚动位置要复位，否则第二次进来还停在上次的地方。 */
function resetScroll() {
  nextTick(() => {
    ;[weakBox.value, fuzzyBox.value].forEach(el => {
      if (el) el.scrollTop = 0
    })
  })
}

/** 错题本汇总条。 */
const mistakeSummary = computed(() => {
  const d = mistakes.value
  if (!d) return []
  return [
    { label: '复习总数', value: d.totalReviews ?? 0, color: INK.accent },
    { label: '薄弱卡', value: weakList.value.length, color: INK.weak },
    { label: '模糊卡', value: fuzzyList.value.length, color: INK.fuzzy }
  ]
})

/** 按日期分组的复习会话列表。 */
const reviewSessions = computed(() => mistakes.value?.reviewSessions || [])

// ===========================================================================
// 遗忘曲线
// ===========================================================================

/** 遗忘曲线图表配置。
 *  单卡：p 随时间折线 + 复习事件散点。
 *  整体：三档复习次数（堆叠柱，左轴）+ 平均掌握度趋势（折线，右轴）。
 *
 *  ★ 全图一条原则：**图表不能画出数据里没有的东西**。
 *    离散计数用柱状、掌握度用真实数据点的折线、
 *    没复习的日子给 null 让线断开 —— 绝不用 smooth 插值编造中间状态。*/
/** 把「有数据的那几天」补成连续日期序列。
 *
 * ★ 为什么必须补：后端只返回**有复习记录**的日期，直接当 xAxis 会让
 *   「09-29 → 10-01 → 10-08」紧挨在一起，视觉上像是连续的三天，
 *   而 10-02~10-07 这六天**根本没学**这件事被悄悄藏起来了。
 *   ——「哪天没学」和「学了多久」同样重要（连续学习天数就靠这个算）。
 *
 * @param {Array<{date:string}>} points 后端返回的点
 * @returns {{dates:string[], map:Object}} 补齐后的日期 + 原数据索引
 */
function fillDateGaps(points) {
  if (!points || !points.length) return { dates: [], map: {} }
  const map = {}
  points.forEach(p => {
    map[p.date] = p
  })
  const first = points[0].date
  const last = points[points.length - 1].date
  const dates = []
  const cur = new Date(first + 'T00:00:00')
  const end = new Date(last + 'T00:00:00')
  // 上限 400 天，防止日期异常导致死循环
  let guard = 0
  while (cur <= end && guard++ < 400) {
    const s = cur.toISOString().slice(0, 10)
    dates.push(s)
    cur.setDate(cur.getDate() + 1)
  }
  return { dates, map }
}

const curveOption = computed(() => {
  const base = chartBase()
  const d = curve.value
  if (!d || !d.points || !d.points.length) return null

  const isAggregate = !d.cardId
  const { dates, map } = fillDateGaps(d.points)

  if (isAggregate) {
    // 整体：三档堆叠柱（离散计数不该用平滑曲线）+ 平均掌握度折线
    const weak = dates.map(x => map[x]?.weakCount ?? 0)
    const mid = dates.map(x => map[x]?.midCount ?? 0)
    const strong = dates.map(x => map[x]?.strongCount ?? 0)
    // ★ avgP 用真实测点；没有复习的那天在**柱状图上是 0 高度**（那里确实没复习），
    //   折线用直线跨过（connectNulls:true + smooth:false）。
    //   区别见下面 series 里的注释 —— smooth 才是编数据，connectNulls 不是。
    const avgP = dates.map(x => {
      const v = map[x]?.avgP
      return v == null ? null : Number(v.toFixed(4))
    })
    return {
      ...base,
      tooltip: { ...base.tooltip, trigger: 'axis' },
      legend: {
        ...base.legend,
        show: true,
        bottom: 0,
        data: ['薄弱', '一般', '扎实', '平均掌握度']
      },
      grid: { left: 8, right: 16, top: 28, bottom: 40, containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#ddd1b6' } },
        axisTick: { show: false },
        axisLabel: { color: '#63543c', fontSize: 12 }
      },
      yAxis: [
        // 左轴：复习次数（整数）
        {
          type: 'value',
          name: '次数',
          nameTextStyle: { color: '#8a7a63', fontSize: 11, padding: [0, 0, 0, -18] },
          minInterval: 1,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#63543c', fontSize: 12 },
          splitLine: { lineStyle: { color: '#ddd1b6', type: 'dashed' } }
        },
        // 右轴：掌握度（0~1 概率），与左轴不同量纲 → 必须独立轴，
        // 否则两条线会互相拉偏量程（次数 5 和掌握度 0.5 差 10 倍）
        {
          type: 'value',
          name: '掌握度',
          min: 0,
          max: 1,
          nameTextStyle: { color: '#8a7a63', fontSize: 11 },
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#63543c', fontSize: 12, formatter: v => v.toFixed(1) },
          splitLine: { show: false }
        }
      ],
      series: [
        // ★ 用 bar（堆叠柱），不用 line+areaStyle。
        //   每天的「薄弱/一般/扎实」是**离散计数**，中间没有连续含义。
        //   画成平滑面积图（smooth+areaStyle）会让人误以为
        //   「10-09 到 10-08 之间也在平滑变化」——
        //   而那些天根本没有复习记录，曲线是 ECharts 插值编出来的。
        //   柱状图每个柱子只代表那天真实发生的事，不撒谎。
        {
          name: '薄弱',
          type: 'bar',
          stack: 'p',
          yAxisIndex: 0,
          data: weak,
          itemStyle: { color: INK.weak },
          barMaxWidth: 28
        },
        {
          name: '一般',
          type: 'bar',
          stack: 'p',
          yAxisIndex: 0,
          data: mid,
          itemStyle: { color: INK.fuzzy },
          barMaxWidth: 28
        },
        {
          name: '扎实',
          type: 'bar',
          stack: 'p',
          yAxisIndex: 0,
          data: strong,
          itemStyle: { color: INK.known },
          barMaxWidth: 28
        },
        // 掌握度趋势：细折线 + 小圆点，挂在右轴。
        //
        // ★★ connectNulls: true + smooth: false —— 这两个不是一回事，上一轮我搞混了：
        //   · smooth:true  = 用贝塞尔曲线**凭空造出**中间状态（真的在编数据）
        //   · connectNulls = 只是用**直线**跨过空档，连接两个**真实测点**
        //   实测踩过：设成 false 时，因为每两个有复习的日子中间都隔着没学的日子，
        //   所有线段全被切断 → 图上只剩一堆孤立的小圆点，完全看不出趋势。
        //   直线连接真实测点是时间序列的标准画法，不算插值编造；
        //   真正要防的是 smooth 那种「在两点之间画出模型没说过的东西」。
        //   保留下来的诚实性：没复习的日子**柱状图为 0 高度**（那里确实没复习），
        //   tooltip 也只显示真实测点的值。
        {
          name: '平均掌握度',
          type: 'line',
          yAxisIndex: 1,
          data: avgP,
          smooth: false,
          connectNulls: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: INK.accent },
          itemStyle: { color: INK.accent }
        }
      ]
    }
  }

  // 单卡：p 折线 + 复习事件散点
  // ★ 用补全后的 dates（gap 为 0），这样「哪天没复习」会显示成 p 掉到 0 的断点，
  //   而不是被悄悄跳过——「没学」和「学了但没进步」是两回事，必须能区分。
  const pValues = dates.map(x => map[x]?.p ?? 0)
  const reviewPoints = dates
    .map((x, i) => (map[x] && map[x].reviews > 0 ? [i, map[x].p ?? 0] : null))
    .filter(Boolean)

  return {
    ...base,
    tooltip: { ...base.tooltip, trigger: 'axis' },
    grid: { left: 8, right: 16, top: 18, bottom: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#ddd1b6' } },
      axisTick: { show: false },
      axisLabel: { color: '#63543c', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#63543c', fontSize: 12, formatter: v => Math.round(v * 100) + '%' },
      splitLine: { lineStyle: { color: '#ddd1b6', type: 'dashed' } }
    },
    series: [
      {
        name: '掌握概率 p',
        type: 'line',
        data: pValues,
        itemStyle: { color: INK.accent },
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15, color: INK.accent },
        smooth: true
      },
      {
        name: '复习事件',
        type: 'scatter',
        data: reviewPoints,
        symbolSize: 10,
        itemStyle: { color: INK.weak, borderColor: '#fff', borderWidth: 1 }
      }
    ]
  }
})

// ===========================================================================
// 学习时长
// ===========================================================================

/** 日学习时长柱状图。 */
const dailyTimeOption = computed(() => {
  const base = chartBase()
  const d = studyTime.value
  if (!d || !d.dailyMinutes || !d.dailyMinutes.length) return null
  const dates = d.dailyMinutes.map(x => x.date)
  const values = d.dailyMinutes.map(x => x.minutes || 0)
  const maxVal = Math.max(...values, 10)

  return {
    ...base,
    tooltip: {
      ...base.tooltip,
      trigger: 'axis',
      formatter: p => `${p[0].name}：${p[0].value} 分钟`
    },
    grid: { left: 8, right: 16, top: 18, bottom: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#ddd1b6' } },
      axisTick: { show: false },
      axisLabel: { color: '#63543c', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: maxVal + 5,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#63543c', fontSize: 12 },
      splitLine: { lineStyle: { color: '#ddd1b6', type: 'dashed' } }
    },
    series: [
      {
        type: 'bar',
        data: values.map(v => ({
          value: v,
          itemStyle: {
            color: v > 0 ? INK.accent : '#e0d6c0',
            borderRadius: v > 0 ? [3, 3, 0, 0] : 0
          }
        })),
        barWidth: '60%',
        label: { show: false }
      }
    ]
  }
})

/** 按领域分布的饼图。 */
const domainTimeOption = computed(() => {
  const base = chartBase()
  const d = studyTime.value
  if (!d || !d.byDomain || !d.byDomain.length) return null
  return {
    ...base,
    tooltip: { ...base.tooltip, formatter: '{b}：{c} 分钟（{d}%）' },
    legend: { ...base.legend, show: true, bottom: 0, type: 'scroll' },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '42%'],
        itemStyle: { borderRadius: 5, borderColor: '#f8f3e6', borderWidth: 2 },
        label: { color: '#63543c', fontSize: 12, formatter: '{b}\n{c} 分钟' },
        data: d.byDomain.map(x => ({
          name: x.domain || '未分类',
          value: x.minutes || 0,
          itemStyle: { color: colorOf(x.domain || '未分类', SEQ) }
        }))
      }
    ]
  }
})

/** 时长汇总指标。 */
const timeSummary = computed(() => {
  const d = studyTime.value
  if (!d) return []
  const totalH = Math.round((d.totalMinutes || 0) / 60)
  const avgPerDay =
    d.dailyMinutes && d.dailyMinutes.length
      ? Math.round(d.dailyMinutes.reduce((a, b) => a + (b.minutes || 0), 0) / d.dailyMinutes.length)
      : 0
  return [
    { label: '总时长', value: totalH + ' 小时', color: INK.accent },
    { label: '日均', value: avgPerDay + ' 分钟', color: INK.fuzzy },
    {
      label: '学习天数',
      value: (d.dailyMinutes || []).filter(x => x.minutes > 0).length + ' 天',
      color: INK.known
    }
  ]
})

/** 学习时长 Top 卡片榜。 */
const topCards = computed(() => (studyTime.value?.byCard || []).slice(0, 10))

/** 热力图数据（7 天 × 24 小时简化版：按天聚合）。 */
const heatmapData = computed(() => {
  const d = studyTime.value
  if (!d || !d.heatmap || !d.heatmap.length) return []
  return d.heatmap.slice(0, 30)
})

/** 格式化分钟数 → Xh Ym。 */
function fmtMinutes(m) {
  if (!m && m !== 0) return '—'
  if (m < 60) return m + ' 分钟'
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest ? `${h}h ${rest}m` : `${h}h`
}

/** 打开某张卡的详情（跳卡片页并带上 open 参数）。 */
function openCard(cardId) {
  router.push({ name: 'cards', query: { open: cardId } })
}
</script>

<template>
  <div class="profile">
    <!-- ===== 头部：用户信息 + 连续天数 ===== -->
    <section class="hero rise">
      <div class="hero-left">
        <div class="eyebrow">
          {{ greeting }}，{{ auth.user?.displayName || auth.user?.username }}
        </div>
        <div class="hero-title">个人中心</div>
        <p class="hero-sub">回顾你的学习轨迹 —— 哪些没记住、会怎么忘、花了多少时间。</p>
      </div>
      <div class="hero-right">
        <div class="streak-card">
          <span class="streak-num mono">{{ overview?.streakDays ?? 0 }}</span>
          <span class="streak-label">连续学习天数</span>
        </div>
      </div>
    </section>

    <!-- ===== Tab 切换 ===== -->
    <el-tabs v-model="activeTab" class="tabs" @tab-change="onTabChange">
      <!-- ========== 概览 ========== -->
      <el-tab-pane label="概览" name="overview">
        <section v-loading="overviewLoading" class="tab-body">
          <template v-if="overview">
            <div class="metrics">
              <div
                v-for="(m, i) in overviewMetrics"
                :key="m.key"
                class="metric rise"
                :style="{ animationDelay: i * 40 + 'ms' }"
              >
                <div class="m-label">{{ m.label }}</div>
                <div class="m-value mono" :style="{ color: m.color }">{{ m.value }}</div>
              </div>
            </div>

            <!-- 复习热力图（张数口径，2026-11-15 加）。学习时长 tab 的热力图
                 是分钟数（sessions 埋点），两个口径互补：刷 200 张秒过卡和
                 精读 3 章论文在分钟口径下完全不成比例，张数才看得出刷了多少。 -->
            <div class="panel rise">
              <header class="panel-head">
                <h3>复习热力</h3>
                <span class="hint">
                  {{ heatmap?.total ?? '—' }} 张 / {{ heatmap?.activeDays ?? '—' }} 天 ·
                  连续 {{ heatmap?.streak?.current ?? 0 }} 天（最长 {{ heatmap?.streak?.max ?? 0 }}）
                </span>
              </header>
              <div class="heat-toolbar">
                <button class="yr-btn" @click="shiftYear(-1)">‹</button>
                <span class="mono yr">{{ heatYear }}</span>
                <button class="yr-btn" :disabled="heatYear >= new Date().getFullYear()"
                        @click="shiftYear(1)">›</button>
              </div>
              <EChart v-if="heatOption" :option="heatOption" height="150" />
              <div v-else class="empty-block">还没有复习记录</div>
            </div>

            <!-- 最近一次复习摘要 -->
            <div v-if="overview.lastSession" class="panel rise">
              <header class="panel-head">
                <h3>最近一次复习</h3>
              </header>
              <div class="kv-grid">
                <div class="kv">
                  <span class="k">日期</span>
                  <span class="v mono">{{ overview.lastSession.date }}</span>
                </div>
                <div class="kv">
                  <span class="k">复习张数</span>
                  <span class="v mono">{{ overview.lastSession.count }}</span>
                </div>
                <div class="kv">
                  <span class="k">薄弱 / 模糊</span>
                  <span class="v">
                    <span :style="{ color: INK.weak }">{{ overview.lastSession.weak }}</span>
                    /
                    <span :style="{ color: INK.fuzzy }">{{ overview.lastSession.fuzzy }}</span>
                  </span>
                </div>
                <div class="kv">
                  <span class="k">用时</span>
                  <span class="v mono">{{ fmtMinutes(overview.lastSession.minutes) }}</span>
                </div>
              </div>
            </div>

            <div v-else class="empty-block">还没有学习记录</div>
          </template>
          <div v-else-if="!overviewLoading" class="empty-block">
            <p>概览数据加载中…</p>
          </div>
        </section>
      </el-tab-pane>

      <!-- ========== 错题本 ========== -->
      <el-tab-pane label="错题本" name="mistakes">
        <section class="tab-body">
          <!-- 周期切换 -->
          <div class="filter-bar">
            <el-radio-group v-model="mistakePeriod" @change="loadMistakes">
              <el-radio-button v-for="p in MISTAKE_PERIODS" :key="p.value" :value="p.value">
                {{ p.label }}
              </el-radio-button>
            </el-radio-group>
          </div>

          <div v-if="mistakeSummary.length" class="metrics">
            <div
              v-for="(m, i) in mistakeSummary"
              :key="m.label"
              class="metric rise"
              :style="{ animationDelay: i * 40 + 'ms' }"
            >
              <div class="m-label">{{ m.label }}</div>
              <div class="m-value mono" :style="{ color: m.color }">{{ m.value }}</div>
            </div>
          </div>

          <div v-loading="mistakeLoading" class="two-col">
            <!-- 薄弱卡 -->
            <div class="panel">
              <header class="panel-head">
                <h3>薄弱卡（不会）</h3>
                <span class="hint">
                  {{ weakList.length }} 张
                  <em v-if="weakList.length > SCROLL_HINT_MIN" class="scroll-tip">可滚动 ↓</em>
                </span>
              </header>
              <p v-if="!weakList.length" class="empty-sm">本周没有「不会」的卡</p>
              <ul
                v-else
                class="card-list scroll-box"
                :class="{ 'at-end': atScrollEnd(weakBox) }"
                ref="weakBox"
              >
                <li
                  v-for="c in weakList"
                  :key="c.cardId"
                  class="card-row"
                  @click="openCard(c.cardId)"
                >
                  <span class="dot" :style="{ background: levelColor(1) }" />
                  <div class="c-body">
                    <span class="c-title">{{ c.title }}</span>
                    <span class="c-meta">{{ c.domain || '未分类' }}</span>
                  </div>
                  <span class="chip">{{ c.count }} 次</span>
                </li>
              </ul>
            </div>

            <!-- 模糊卡 -->
            <div class="panel">
              <header class="panel-head">
                <h3>模糊卡</h3>
                <span class="hint">
                  {{ fuzzyList.length }} 张
                  <em v-if="fuzzyList.length > SCROLL_HINT_MIN" class="scroll-tip">可滚动 ↓</em>
                </span>
              </header>
              <p v-if="!fuzzyList.length" class="empty-sm">本周没有「模糊」的卡</p>
              <ul
                v-else
                class="card-list scroll-box"
                :class="{ 'at-end': atScrollEnd(fuzzyBox) }"
                ref="fuzzyBox"
              >
                <li
                  v-for="c in fuzzyList"
                  :key="c.cardId"
                  class="card-row"
                  @click="openCard(c.cardId)"
                >
                  <span class="dot" :style="{ background: levelColor(2) }" />
                  <div class="c-body">
                    <span class="c-title">{{ c.title }}</span>
                    <span class="c-meta">{{ c.domain || '未分类' }}</span>
                  </div>
                  <span class="chip">{{ c.count }} 次</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- 复习会话列表 -->
          <div v-if="reviewSessions.length" class="panel">
            <header class="panel-head">
              <h3>复习会话</h3>
            </header>
            <table class="tbl">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>张数</th>
                  <th>薄弱</th>
                  <th>模糊</th>
                  <th>用时</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(s, i) in reviewSessions" :key="i">
                  <td class="mono">{{ s.date }}</td>
                  <td class="mono">{{ s.count }}</td>
                  <td>
                    <span :style="{ color: INK.weak }">{{ s.weakCount }}</span>
                  </td>
                  <td>
                    <span :style="{ color: INK.fuzzy }">{{ s.fuzzyCount }}</span>
                  </td>
                  <td class="mono">{{ fmtMinutes(s.minutes) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </el-tab-pane>

      <!-- ========== 遗忘曲线 ========== -->
      <el-tab-pane label="遗忘曲线" name="curve">
        <section class="tab-body">
          <div class="filter-bar">
            <el-select
              v-model="curveCardId"
              placeholder="整体趋势"
              clearable
              style="width: 200px"
              @change="loadCurve"
            >
              <el-option
                v-for="c in cardOptions"
                :key="c.value"
                :value="c.value"
                :label="c.label"
              />
            </el-select>
            <el-radio-group v-model="curveDays" @change="loadCurve">
              <el-radio-button v-for="d in CURVE_DAYS_OPTIONS" :key="d.value" :value="d.value">
                {{ d.label }}
              </el-radio-button>
            </el-radio-group>
          </div>

          <div v-loading="curveLoading" class="panel">
            <header class="panel-head">
              <h3>{{ curveCardId ? '单卡掌握概率' : '整体掌握分布' }}</h3>
              <span class="hint">{{
                curveCardId
                  ? 'BKT p 值随时间变化 + 复习事件'
                  : '三档复习次数（左轴）+ 平均掌握度趋势（右轴）'
              }}</span>
            </header>
            <p v-if="!curve || !curve.points || !curve.points.length" class="empty-sm">
              暂无数据 —— 先去复习几张卡，这里就会出现曲线。
            </p>
            <EChart v-else :option="curveOption" height="320px" />
          </div>
        </section>
      </el-tab-pane>

      <!-- ========== 学习时长 ========== -->
      <el-tab-pane label="学习时长" name="time">
        <section class="tab-body">
          <div class="filter-bar">
            <el-radio-group v-model="timePeriod" @change="loadStudyTime">
              <el-radio-button v-for="p in TIME_PERIODS" :key="p.value" :value="p.value">
                {{ p.label }}
              </el-radio-button>
            </el-radio-group>
          </div>

          <!-- ★ 降级必须看得见（项目铁律）：
     后端 sessions 不可用时返回 sessionsAvailable=false（当前 PG 后端未实现该能力）。
     这时若只显示「暂无数据」，用户会以为自己没学过 —— 实际上是他学了但功能没接上。
     所以这里显式说明，不让「功能坏了」伪装成「你没学」。 -->
          <p v-if="studyTime && studyTime.sessionsAvailable === false" class="empty-sm">
            学习时长统计暂不可用：当前存储后端未启用该能力（复习记录不受影响）
          </p>

          <div v-if="timeSummary.length" class="metrics">
            <div
              v-for="(m, i) in timeSummary"
              :key="m.label"
              class="metric rise"
              :style="{ animationDelay: i * 40 + 'ms' }"
            >
              <div class="m-label">{{ m.label }}</div>
              <div class="m-value mono" :style="{ color: m.color }">{{ m.value }}</div>
            </div>
          </div>

          <div v-loading="timeLoading" class="two-col">
            <!-- 日时长柱状图 -->
            <div class="panel">
              <header class="panel-head">
                <h3>每日学习时长</h3>
                <span class="hint">分钟 / 天</span>
              </header>
              <p v-if="!dailyTimeOption" class="empty-sm">暂无数据</p>
              <EChart v-else :option="dailyTimeOption" height="260px" />
            </div>

            <!-- 领域分布饼图 -->
            <div class="panel">
              <header class="panel-head">
                <h3>按领域分布</h3>
                <span class="hint">分钟 / 领域</span>
              </header>
              <p v-if="!domainTimeOption" class="empty-sm">暂无数据</p>
              <EChart v-else :option="domainTimeOption" height="260px" />
            </div>
          </div>

          <!-- 热力图（简化版：按天） -->
          <div v-if="heatmapData.length" class="panel">
            <header class="panel-head">
              <h3>学习热力</h3>
              <span class="hint">近 30 天</span>
            </header>
            <div class="heatmap">
              <div
                v-for="(h, i) in heatmapData"
                :key="i"
                class="hm-cell"
                :style="{ background: hmColor(h.value) }"
                :title="`${h.date}：${h.value} 分钟`"
              />
            </div>
            <div class="hm-legend">
              <span>少</span>
              <span
                v-for="i in 5"
                :key="i"
                class="hm-cell"
                :style="{ background: hmColor(i * 20) }"
              />
              <span>多</span>
            </div>
          </div>

          <!-- Top 卡片榜 -->
          <div v-if="topCards.length" class="panel">
            <header class="panel-head">
              <h3>投入最多的卡片</h3>
              <span class="hint">Top {{ topCards.length }}</span>
            </header>
            <table class="tbl">
              <thead>
                <tr>
                  <th>卡片</th>
                  <th>领域</th>
                  <th>用时</th>
                  <th>复习次数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in topCards" :key="c.cardId" @click="openCard(c.cardId)">
                  <td class="c-title">{{ c.title }}</td>
                  <td>{{ c.domain || '未分类' }}</td>
                  <td class="mono">{{ fmtMinutes(c.minutes) }}</td>
                  <td class="mono">{{ c.reviews }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </el-tab-pane>

      <!-- ========== 记忆保持率（True Retention，2026-11-15 加） ========== -->
      <el-tab-pane label="记忆保持率" name="retention">
        <section v-loading="retentionLoading" class="tab-body">
          <template v-if="retention">
            <p class="tip-block">
              Anki 口径的 True Retention：把「刚学完就测」和「隔了三周再看」分开算 ——
              间隔排到 <b>21 天以上</b>再答对，才是复习系统真正的成绩。
              「模糊」在这里算记得（FSRS 问的是记不记得，与错题本的「掌握没」口径不同）。
            </p>
            <div class="panel">
              <header class="panel-head">
                <h3>记得率</h3>
                <span class="hint">单元格：记得率（记得 / 总次数）</span>
              </header>
              <table class="tbl">
                <thead>
                  <tr>
                    <th>口径</th>
                    <th>今天</th>
                    <th>本月</th>
                    <th>今年</th>
                    <th>全部</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in retentionRows" :key="row.key">
                    <td>{{ row.label }}</td>
                    <td v-for="rng in RET_RANGES" :key="rng" class="mono"
                        :style="{ color: cellColor(row.key, rng) }">
                      {{ fmtCell(row.key, rng) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="tip-block warn">
              成熟度按卡当前间隔近似（事件流里没存当时的间隔）：最近把卡推过
              21 天线的人，早前的成功复习也会被算成 mature —— 方向温和，
              但不是精确的历史口径，看趋势别抠小数。
            </p>
          </template>
          <div v-else-if="!retentionLoading" class="empty-block">还没有复习记录</div>
        </section>
      </el-tab-pane>

      <!-- ========== 个人信息 ========== -->
      <el-tab-pane label="个人信息" name="profile">
        <section class="tab-body">
          <div class="panel rise">
            <header class="panel-head">
              <h3>基本信息</h3>
              <span class="hint">用户名是登录凭据，不可修改</span>
            </header>
            <div class="profile-form">
              <div class="pf-row">
                <span class="pf-label">用户名</span>
                <span class="pf-readonly mono">{{ auth.user?.username }}</span>
              </div>
              <div class="pf-row">
                <span class="pf-label">昵称</span>
                <div class="pf-edit">
                  <el-input
                    v-model="profileForm.displayName"
                    class="pf-input"
                    maxlength="32"
                    show-word-limit
                    clearable
                    placeholder="留空则显示用户名"
                  />
                  <el-button
                    type="primary"
                    :loading="profileSaving"
                    class="pf-save"
                    @click="saveProfile"
                  >
                    保存
                  </el-button>
                </div>
              </div>
              <div class="pf-row">
                <span class="pf-label">角色</span>
                <span class="pf-readonly">{{
                  auth.user?.role === 'admin' ? '管理员' : '学习者'
                }}</span>
              </div>
              <div class="pf-row">
                <span class="pf-label">注册时间</span>
                <span class="pf-readonly mono">{{ auth.user?.createdAt || '—' }}</span>
              </div>
            </div>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
export default {
  computed: {
    greeting() {
      const h = new Date().getHours()
      if (h < 6) return '夜深了'
      if (h < 11) return '早上好'
      if (h < 14) return '中午好'
      if (h < 18) return '下午好'
      return '晚上好'
    }
  },
  methods: {
    hmColor(value) {
      // 0-100 → 纸色到靛蓝
      const v = Math.min(100, Math.max(0, value || 0))
      if (v === 0) return '#e8e0cc'
      const r = Math.round(248 - (248 - 31) * (v / 100))
      const g = Math.round(243 - (243 - 75) * (v / 100))
      const b = Math.round(230 - (230 - 107) * (v / 100))
      return `rgb(${r}, ${g}, ${b})`
    }
  }
}
</script>

<style scoped>
.profile {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 头部 ===== */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding: 24px 28px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background-color: var(--panel);
  background-image: radial-gradient(760px 300px at 6% -40%, var(--ac-glow), transparent 62%);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: var(--ac);
}
.hero-left {
  min-width: 0;
}
.hero-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 1px;
  margin: 4px 0 6px;
  color: var(--tx);
}
.hero-sub {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.7;
}
.hero-right {
  flex: none;
}
.streak-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 14px 24px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ac-dim);
  background: var(--ac-glow);
}
.streak-num {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--ac);
  font-variant-numeric: tabular-nums;
}
.streak-label {
  font-size: var(--fs-xs);
  color: var(--ac);
}

/* ===== Tabs ===== */
.tabs {
  margin: 0;
}
.tabs :deep(.el-tabs__header) {
  margin-bottom: 14px;
}
.tabs :deep(.el-tabs__item) {
  font-size: var(--fs-md);
  font-weight: 500;
  color: var(--mu);
}
.tabs :deep(.el-tabs__item.is-active) {
  color: var(--ac);
  font-weight: 600;
}

/* ===== Tab 内容 ===== */
.tab-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 指标卡 ===== */
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.metric {
  padding: 14px 16px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}
.m-label {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.m-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.3;
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* ===== 两列布局 ===== */
.two-col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  /* stretch（默认）而不是 start：让两栏 panel **等高**。
     配合 .scroll-box 的固定滚动高度，短的那栏底部留白由 panel 自身撑住，
     不会出现「左边卡片到头、右边还在滚」的那种参差感。 */
  align-items: stretch;
}
.two-col > .panel {
  /* grid 里子项默认不会因为内容少而塌陷，显式 stretch 让它撑满行高 */
  display: flex;
  flex-direction: column;
}
.two-col > .panel > .scroll-box {
  /* 面板是纵向 flex，滚动区跟着长；min-height:0 是 flex 子项能滚的前提
     （不加的话 flex 项不肯收缩到内容以下，overflow 就失效了） */
  flex: 1 1 auto;
  min-height: 0;
}
@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}

/* ===== 卡片列表 ===== */
/* ★ 错题本的「薄弱卡 / 模糊卡」各自独立滚动。
 *
 *   为什么两栏要**各自**滚而不是让整个页面滚：
 *   两个列表长度天然不等（弱的 2 张、模糊的 20 张）。
 *   共用一个滚动高度 → 短的那栏底部留一大片空白，且页面总高度被长的那栏撑走。
 *   各自滚 → 两栏**顶部对齐、等高**，视线不用来回找。
 *
 *   高度用 clamp()：内容少时不留空白（min 是下限），
 *   内容多时最多占多少屏幕可控（max 是上限），中间按内容自适应。
 */
.scroll-box {
  /* 6 行卡片再多也就 ~360px；clamp 让 1~2 张时自动收窄 */
  max-height: clamp(180px, 42vh, 420px);
  overflow-y: auto;
  overflow-x: hidden;
  /* 滚动条不占布局宽度，避免每次出现/消失导致卡片宽度跳动 */
  scrollbar-gutter: stable;
  /* 内容触顶/触底时的渐隐提示：告诉用户下面还有内容 */
  -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 24px), transparent 100%);
  mask-image: linear-gradient(to bottom, #000 calc(100% - 24px), transparent 100%);
}
/* 滚动到底时去掉渐隐（否则最后一行永远是淡的，看着像没加载完） */
.scroll-box.at-end {
  -webkit-mask-image: none;
  mask-image: none;
}
/* 悬停时把渐隐区收窄一点，让最后几行更清楚 */
.scroll-box:hover {
  -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 14px), transparent 100%);
  mask-image: linear-gradient(to bottom, #000 calc(100% - 14px), transparent 100%);
}

.card-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 「可滚动 ↓」提示：只在真的溢出时才出现（SCROLL_HINT_MIN 阈值以上） */
.scroll-tip {
  margin-left: 6px;
  padding: 1px 5px;
  border-radius: 8px;
  font-size: 11px;
  font-style: normal;
  color: #8a6a3f;
  background: rgba(196, 154, 82, 0.14);
  border: 1px solid rgba(196, 154, 82, 0.28);
}
.card-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.14s;
}
.card-row:hover {
  background: var(--ac-glow);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}
.c-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.c-title {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--tx);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.c-meta {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.chip {
  flex: none;
  font-size: var(--fs-xs);
  color: var(--dim);
  padding: 1px 8px;
  border-radius: 10px;
  border: 1px solid var(--line2);
  background: var(--panel2);
}

/* ===== 表格 ===== */
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}
.tbl th {
  text-align: left;
  padding: 8px 10px;
  font-weight: 600;
  color: var(--mu);
  border-bottom: 1px solid var(--line);
  font-size: var(--fs-xs);
}
.tbl td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  color: var(--tx);
}
.tbl tr:last-child td {
  border-bottom: none;
}
.tbl tbody tr {
  cursor: pointer;
  transition: background 0.14s;
}
.tbl tbody tr:hover {
  background: var(--ac-glow);
}

/* ===== KV 网格 ===== */
.kv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.kv .k {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.kv .v {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--tx);
}

/* ===== 热力图 ===== */
.heatmap {
  display: grid;
  grid-template-columns: repeat(30, 1fr);
  gap: 3px;
}
.hm-cell {
  aspect-ratio: 1;
  border-radius: 2px;
  min-height: 10px;
}
.hm-legend {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 8px;
  font-size: var(--fs-xs);
  color: var(--dim);
}
.hm-legend .hm-cell {
  width: 12px;
  height: 12px;
  min-height: 0;
}

/* ===== 空状态 ===== */
.empty-block {
  padding: 40px 20px;
  text-align: center;
  color: var(--dim);
  font-size: var(--fs-sm);
  border: 1px dashed var(--line2);
  border-radius: var(--radius);
  background: var(--panel2);
}

/* ===== True Retention 说明块 / 复习热力图工具条（2026-11-15 加） ===== */
.tip-block {
  padding: 10px 14px;
  border: 1px solid var(--line2);
  border-radius: var(--radius);
  background: var(--panel2);
  color: var(--mu);
  font-size: 12.5px;
  line-height: 1.7;
}
.tip-block.warn {
  border-left: 3px solid #c08a2e;
}
.tip-block b {
  color: var(--tx);
}
.heat-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin: 4px 0 2px;
}
.heat-toolbar .yr {
  font-size: 13px;
  color: var(--mu);
  min-width: 44px;
  text-align: center;
}
.yr-btn {
  width: 26px;
  height: 24px;
  border: 1px solid var(--line2);
  border-radius: 6px;
  background: transparent;
  color: var(--mu);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}
.yr-btn:hover:not(:disabled) {
  color: var(--ac);
  border-color: var(--ac);
}
.yr-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.empty-sm {
  padding: 20px;
  text-align: center;
  color: var(--dim);
  font-size: var(--fs-sm);
}

/* ===== 面板 ===== */
.panel {
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
  padding: 16px 18px;
}
.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.panel-head h3 {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--tx);
}
.panel-head .hint {
  font-size: var(--fs-xs);
  color: var(--dim);
}

/* ===== 个人信息 ===== */
.profile-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-width: 560px;
}
.pf-row {
  display: grid;
  grid-template-columns: 72px 1fr;
  align-items: center;
  gap: 12px;
}
.pf-label {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.pf-readonly {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--tx);
}
.pf-edit {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pf-input {
  max-width: 280px;
}
</style>
