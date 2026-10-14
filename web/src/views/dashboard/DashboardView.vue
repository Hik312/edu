<script setup>
/* 学习驾驶舱 —— 首页。
 *
 * ## 版式（2026-10-12 改版，仿「介绍 + 数据」双段式首页）
 *
 * 别的页面是「读」，这一页是「扫」。改版后整页从上到下五段：
 *   1. **介绍横幅**：左边是产品介绍（价值主张 + 行动按钮 + 三个小数据），
 *      右边一张浮动预览卡（今天接下来要复习的那张卡）。这是一眼要看到的东西。
 *   2. **四张数据卡**：待复习 / 已掌握 / 文档 / 笔记，带图标、可点击直达对应页。
 *   3. **左右分栏**：左「今日队列」列表（可切 tab），右「常用功能 + 学习指南」。
 *   4. **图表行**：领域分布 / 自评档位 / BKT 掌握度。
 *   5. **状态条**：卡片构成 + 运行状态。
 * 上一版把「总卡数」当唯一主角的大数字排版已废弃 —— 现在首页既要有
 * 「这个产品是干什么的」（介绍），也要有「我的数据长什么样」（展示）。
 *
 * ## 数据全部来自 /api/stats
 *
 * 没有一个数是前端算的 —— 掌握度、分布都在后端 `db.stats()` 里。
 * 前端只负责「画」，不负责「定义」，否则换存储后端时口径会对不上
 * （check.js 里就有 JSON / MySQL 两版统计对照）。
 *
 * ## 图表走 EChart 组件，不走 echarts.init
 *
 * 见 components/EChart.vue 的文件头：dispose、容器 resize、notMerge 三件事
 * 集中在一个地方做。这里只需要提供 option。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EChart from '@/components/EChart.vue'
import { useAuthStore } from '@/stores/auth'
import { useLearningStore } from '@/stores/learning'
import { useCardsStore } from '@/stores/cards'
import { storage, getAlgo } from '@/api/system'
import { getLlmStatus } from '@/api/ai'
import { getMasteryBrief } from '@/api/learning'
import { CHART_BG, INK, chartBase, colorOf, levelColor, levelLabel, SEQ } from '@/config/theme'

const router = useRouter()
const auth = useAuthStore()
const learning = useLearningStore()
const cards = useCardsStore()

/** 纸面主题是唯一主题，所以这些是个常量，不再按页取。 */
const base = chartBase()

/** 内联线性图标（24×24，stroke 风格）。集中一处是为了**换图标只改这里** ——
 *  散在模板里各写一个 svg，粗细/圆角/尺寸迟早不一致。
 *  图标只是「扫一眼认出是哪类」的记号，不做装饰细节。 */
const ICONS = {
  calendar:
    '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/></svg>',
  check:
    '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M8.5 12.2l2.5 2.5 4.5-5"/></svg>',
  doc: '<svg viewBox="0 0 24 24"><path d="M6 3.5h8l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 5 20V5A1.5 1.5 0 0 1 6 3.5z"/><path d="M13.5 3.8V8H18M8.5 12.5h7M8.5 16h7"/></svg>',
  note: '<svg viewBox="0 0 24 24"><path d="M5 4.5h14v11l-4 4H5z"/><path d="M15 19.5v-4h4M8.5 9h7M8.5 12.5h5"/></svg>',
  upload:
    '<svg viewBox="0 0 24 24"><path d="M12 15V4m0 0L8 8m4-4l4 4"/><path d="M4.5 15v3.5A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5V15"/></svg>',
  spark:
    '<svg viewBox="0 0 24 24"><path d="M11 3l1.7 4.8L17.5 9.5l-4.8 1.7L11 16l-1.7-4.8L4.5 9.5l4.8-1.7z"/><path d="M18 15l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/></svg>',
  route:
    '<svg viewBox="0 0 24 24"><path d="M6 20V4.5A1.5 1.5 0 0 1 7.5 3H17l-2.2 3.8L17 10.5H7.5"/><path d="M6 20h5"/></svg>',
  graph:
    '<svg viewBox="0 0 24 24"><circle cx="6" cy="7" r="2.5"/><circle cx="18" cy="8" r="2.5"/><circle cx="12" cy="17.5" r="2.5"/><path d="M8.4 8l7.2-.2M7.5 9.3l3.3 6M16.6 10.3l-3.5 5.2"/></svg>'
}

/** subject id → 中文名，**从 catalog 派生**（不硬编码一份）。
 *
 * ★ 为什么必须从 catalog 取：科目名是数据（`data/catalog.js` 里能改），
 *   前端再写一份映射就是「两个真相源」—— 改了 catalog 这份就过期，
 *   表现是「领域分布显示旧科目名」而没有任何报错。
 *   这与「domain字段和 subject 各写各的」是同一类错误。
 */
const subjectLabel = computed(() => {
  const map = {}
  for (const cat of cards.catalog || []) {
    for (const sub of cat.subjects || []) map[sub.id] = sub.name
  }
  return map
})

const storeInfo = ref(null)
/* BKT 掌握度汇总。和 /api/stats 的三档计数**不是一回事**：
 * stats 的 known/fuzzy/weak 是用户自评的三档（粗糙、只有三档），
 * 这里的 weak/mid/strong 是 BKT 从复习事件回放出的连续概率 p 分的档。
 * 两者并存是有意的：自评快、但区分不出「模糊」的轻重；p 慢但细。 */
const mastery = ref(null)
/* 当前间隔调度算法（sm2/fsrs/hlr/bkt）。ALGO 改配置就换算法，
 * 而界面上看不出来 —— 徽标就是补这个信息缺口。 */
const algoInfo = ref(null)
/* AI 可用性**必须问 /api/llm/status**，不能读 /api/health 的 llm 字段。
 *
 * health.llm 的定义是 `bool(os.environ['LLM_API_KEY'])` —— 它只表示
 * 「配了云端 key」，本机跑 Ollama 时它就是 false。照它来判断的话，
 * 本机明明有 qwen3:8b 能精读，驾驶舱却写「未启用」，而生成页（读
 * llm/status）写着「可用」—— 同一套系统两个页面自相矛盾。
 * 所以这里跟生成页用同一个接口，判断依据只留一处。 */
const llmInfo = ref(null)

onMounted(async () => {
  // 领域分布要用 subject id → 中文名，名字在 catalog 里。
  // 不取的话SUBJECT_LABEL 全是空，图上会显示原始 id（algorithm/middleware…）。
  cards.fetchCatalog()
  // 今日队列列表比旧滚动榜（8 行）要长一些，多取几条供列表内滚动。
  learning.fetchDue({ limit: 20 })
  learning.fetchStats()
  // ★ 两个请求各自 try/catch。
  // 从前它们共用一个 try，`/api/health` 超时会把**已经拿到的** storeInfo
  // 一起清成 null，于是存储后端那一整块显示成「-」，看起来像数据库没了，
  // 实际只是另一个请求慢了一下。
  // 另外这里本来还取了 health() 存进 healthInfo，但模板里一处都没读 ——
  // 白拉一个请求，已删（版本号那个字段后端也不返回，见 SystemView）。
  try {
    storeInfo.value = (await storage()).storage
  } catch {
    // 系统状态拿不到不影响这一页的主功能，留空即可 —— 别弹错挡住整屏
    storeInfo.value = null
  }
  try {
    llmInfo.value = await getLlmStatus()
  } catch {
    // ok:false 是正常状态（可选能力没开），拿不到就当未启用
    llmInfo.value = null
  }
  // 同样各自 try/catch：这两个都是「有则锦上添花」的信息，
  // 任何一个失败都不该影响驾驶舱的主功能（数字 + 图表 + 队列）。
  try {
    const r = await getMasteryBrief()
    mastery.value = r.summary || null
  } catch {
    // 算法库不可用 / 未登录。少一条分布条而已，不报错。
    mastery.value = null
  }
  try {
    algoInfo.value = (await getAlgo()).current
  } catch {
    algoInfo.value = null
  }
})

const s = computed(() => learning.stats || {})

/** ★ 今天实际要学几张 = min(后端到期总数, 我的每日目标)。
 *
 *  后端 `dueToday` = 学过但排期到了的（dueLearned）+ 从没背过的新卡（fresh），
 *  400 张库里 398 张没标过 → dueToday=400。但复习页只取 `dailyTarget`（默认 20）张，
 *  所以**界面报 400、进去只有 20**，是同一套系统的两个矛盾口径。
 *  这里统一成「今天要做多少」，跟侧栏角标、复习页三处一致。
 */
const dueToday = computed(() => {
  const total = s.value.dueToday ?? 0
  return Math.min(total, learning.dailyTarget || 0)
})

/** 积压 = 到期总数 - 今天要学的。积压不是失败，是「按每日目标排队」的正常结果，
 *  所以文案是「排队」而不是「欠债」—— 后者会让人有挫败感然后弃用。 */
const dueBacklog = computed(() => Math.max((s.value.dueToday ?? 0) - dueToday.value, 0))

/** 一句话说明「400 到底是什么意思」。只在真有积压时出现。 */
const dueBacklogText = computed(() => {
  const learned = s.value.dueLearned ?? 0
  const fresh = s.value.fresh ?? 0
  if (!dueBacklog.value) return ''
  const parts = []
  if (learned > 0) parts.push(`到期 ${learned}`)
  if (fresh > 0) parts.push(`新卡 ${fresh}`)
  return `${parts.join(' · ')}，按每日 ${learning.dailyTarget} 张排队`
})

/** 库里一张卡都没有 —— 空驾驶舱的判据。
 *
 *  这个状态**必须单独设计**，不能当成"有数据但数字是 0"来渲染：
 *  之前 0 张卡时，页面照样画四个 0 的指标卡、一张空环形图，
 *  图表区还大片留白 —— 新用户看到的是「这里什么都没有」，
 *  而不是「该去导入/生成第一批卡」。空驾驶舱是这个产品最容易劝退人的第一屏。 */
const isEmpty = computed(() => (s.value.total ?? 0) === 0)

/** 今天的日期，写成「9月24日 周三」这种一眼能认的形式。 */
const todayText = computed(() => {
  const d = new Date()
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${d.getMonth() + 1}月${d.getDate()}日 ${week}`
})

/** 四张数据卡（仿参考首页的「图标 + 数字 + 标签」小卡）。
 *
 *  每张都可点击直达对应页面 —— 数据卡不是图表的重复，是**入口**：
 *  「今日待复习 12」点进去就是那 12 张。
 *  四个颜色必须**色相各不相同**，否则四张并排的卡会被人当成两组。
 *  文档 / 笔记 不用语义色，它们不是「掌握程度」，借用语义色会误导。 */
const metrics = computed(() => {
  const v = s.value
  return [
    {
      key: 'due',
      label: '今日待复习',
      value: dueToday.value,
      color: INK.accent,
      icon: 'calendar',
      to: 'review'
    },
    {
      key: 'known',
      label: '已掌握',
      value: v.known ?? 0,
      color: INK.known,
      icon: 'check',
      to: 'cards'
    },
    { key: 'docs', label: '文档', value: v.docs ?? 0, color: '#c08a2e', icon: 'doc', to: 'docs' },
    {
      key: 'notes',
      label: '笔记',
      value: v.notes ?? 0,
      color: '#6a5aa8',
      icon: 'note',
      to: 'notes'
    }
  ]
})

/** 掌握度环形图。中间放总数不放百分比 ——
 *  百分比会跟上面「已掌握」那张卡说同一件事，重复信息是密度的主要敌人。 */
const masteryOption = computed(() => {
  const v = s.value
  const data = [
    { name: '会', value: v.known ?? 0, itemStyle: { color: INK.known } },
    { name: '模糊', value: v.fuzzy ?? 0, itemStyle: { color: INK.fuzzy } },
    { name: '不会', value: v.weak ?? 0, itemStyle: { color: INK.weak } },
    { name: '未标记', value: v.unmarked ?? 0, itemStyle: { color: INK.unmarked } }
  ].filter(d => d.value > 0)
  const total = data.reduce((a, b) => a + b.value, 0)

  return {
    ...base,
    tooltip: { ...base.tooltip, formatter: '{b}：{c} 张（{d}%）' },
    series: [
      {
        type: 'pie',
        // 半径 / 圆心：上一版是 ['56%','80%'] + center '52%'，外圈底边落到 92%，
        // 单档数据的标签被挤到环的下沿、糊成一团（20 张全部未标记时就是这个样子）。
        // 现在环收到 76% 并垂直居中，底边 88%，配合下面"单档不画标签"一起解决。
        radius: ['54%', '76%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        label: {
          // 只有一档时**不画标签**（比如 20 张全部未标记）。
          // 整圈一个颜色，标签给不出任何可区分的信息，却一定会贴在环上
          // 把画面搅乱；总数已经写在圆心了。两档以上才需要标出每块是谁。
          show: data.length > 1,
          color: CHART_BG.label,
          fontSize: 13,
          // ★ 占比过小的扇区也不标。「会 99.5% / 模糊 0.5%」这种分布下，
          // 那条 0.5% 的标签会被挤到环的正上方、还带着一根几乎看不见的
          // 引线，读的人会先看到它再去找它指哪块。0.5% 的人数为 2 张，
          // 悬停 tooltip 一样能查出来，没必要写在图面上。
          formatter: p => (p.percent < 3 ? '' : `${p.name}\n${p.percent}%`),
          lineHeight: 18
        },
        // ⚠️ 别给极小的扇区加圆角。
        // 0.75% 的扇区在环上只有约 3° 的弧长，两端各 5px 的 borderRadius
        // 正好把它整段抹掉 —— 加上纸色描边，视觉上就是**环上开了个白口子**，
        // 看起来像渲染坏了（2026-10-03 用户就指着这个图问是不是坏了）。
        // 圆角是给「有面积的扇区」做视觉柔化的，对一根线来说它是灾难。
        // 同理，<3% 的扇区描边也收窄到 1px，避免描边占掉的宽度超过它本身。
        itemStyle: p => ({
          borderColor: CHART_BG.paper,
          borderWidth: p.percent < 3 ? 1 : 2,
          borderRadius: p.percent < 3 ? 0 : 5,
          color: p.data.itemStyle.color
        }),
        labelLine: { length: 10, length2: 12, lineStyle: { color: CHART_BG.line } },
        data
      }
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '43%',
        style: {
          text: String(total),
          fill: CHART_BG.text,
          fontSize: 30,
          fontWeight: 600,
          fontFamily: 'Microsoft YaHei, sans-serif'
        }
      },
      {
        type: 'text',
        left: 'center',
        top: '56%',
        style: {
          text: '张卡片',
          fill: CHART_BG.label,
          fontSize: 13,
          fontFamily: 'Microsoft YaHei, sans-serif'
        }
      }
    ]
  }
})

/** 领域分布：横向条。
 *领域名可能较长，横向条能给文字留位置；
 * 纵向的话标签会互相挤成斜排或者直接被省略掉。
 *
 * ★★ 这里用的是 `bySubject` 而不是 `domains`（2026-10-09 改）：
 *   `domains` 读的是卡片上的 `domain` **旧字段**，它没有 catalog 约束、
 *   各写各的，实际出现过四种口径分裂：
 *     ·同名不同写：`Java后端`170 和 `求职·Java`10 是同一个领域两行
 *     · 迁移不同步：middleware 76 张只改了 subject，domain 还留着
 *       `Java后端` → 中间件在首页被显示成「Java后端」
 *     · 粒度不一：有的值是科目、有的是主题（`操作系统`）、还有 `待归类`
 *   而 `bySubject` 的 key 是有 catalog 约束的 `category/subject`，
 *   单一数据源不可能再分裂。
 *   （根因：两个字段都存「分类信息」却各自维护。domain 只能是派生值。）
 */
const domainOption = computed(() => {
  const rows = Object.entries(s.value.bySubject || {})
    .map(([k, v]) => {
      // key 形如 'work/algorithm'，取末段 subject id 再翻成中文名
      const id = String(k).split('/').pop()
      return { id, name: subjectLabel.value[id] || id, value: v }
    })
    .sort((a, b) => b.value - a.value)
  if (!rows.length) return null
  return {
    ...base,
    // 右边必须留出数字的位置。原来 right:26 只够放两位数，
    // 「170」这种三位数会被条形压住半个 —— 数值标签压在条上是这页最刺眼的一处。
    grid: { left: 8, right: 46, top: 8, bottom: 4, containLabel: true },
    tooltip: { ...base.tooltip, formatter: '{b}：{c} 张' },
    xAxis: { type: 'value', show: false, max: Math.max(...rows.map(r => r.value), 1) },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map(r => r.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: CHART_BG.label, fontSize: 13, fontWeight: 500 }
    },
    series: [
      {
        type: 'bar',
        barWidth: 15,
        data: rows.map(r => ({
          value: r.value,
          itemStyle: { color: colorOf(r.id, SEQ), borderRadius: [0, 4, 4, 0] }
        })),
        label: {
          show: true,
          position: 'right',
          color: CHART_BG.text,
          fontSize: 12.5,
          formatter: '{c}'
        },
        showBackground: true,
        // 未填满的那段用比纸略深的底，而不是半透明白 ——
        // 纸底上叠白会发灰，看着像脏了
        backgroundStyle: { color: CHART_BG.paper2, borderRadius: 4 }
      }
    ]
  }
})

/** 内置 / 自建的堆叠条。回答的是「我的库里多少是自己加的」。 */
const composeOption = computed(() => {
  const v = s.value
  const custom = v.custom ?? 0
  const builtin = Math.max((v.total ?? 0) - custom, 0)
  return {
    ...base,
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { show: false, max: Math.max(v.total ?? 0, 1) },
    yAxis: { show: false, type: 'category', data: [''] },
    series: [
      {
        type: 'bar',
        stack: 'a',
        barHeight: 20,
        data: [{ value: builtin, itemStyle: { color: INK.accent, borderRadius: [4, 0, 0, 4] } }],
        label: {
          show: builtin > 0,
          position: 'insideLeft',
          // 靛蓝是深色，所以标签用纸白，不是墨色
          color: '#fdfaf3',
          fontSize: 12,
          fontWeight: 600,
          formatter: `内置 ${builtin}`
        }
      },
      {
        type: 'bar',
        stack: 'a',
        barHeight: 20,
        data: [{ value: custom, itemStyle: { color: INK.known, borderRadius: [0, 4, 4, 0] } }],
        label: {
          show: custom > 0,
          position: 'insideRight',
          color: '#fdfaf3',
          fontSize: 12,
          fontWeight: 600,
          formatter: `自建 ${custom}`
        }
      }
    ]
  }
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

/** 横幅右侧的预览卡：今天接下来要复习的那张卡。
 *  参考首页在横幅右侧放「示例岗位」，这里放**真实的下一张卡** ——
 *  比任何插图都有用：它就是用户下一步要点的东西。 */
const heroCard = computed(() => learning.queue[0] || null)

/** 今日队列的 tab。仿参考首页「最新岗位」的分类切换。
 *  「全部 / 未标记 / 已标记」对应复习的三种扫视需求：
 *  看总量、找没看过的、找之前标过要再巩固的。 */
const queueTabs = [
  { k: 'all', n: '全部' },
  { k: 'unmarked', n: '未标记' },
  { k: 'marked', n: '已标记' }
]
const queueTab = ref('all')

const queueRows = computed(() => {
  const q = learning.queue
  if (queueTab.value === 'unmarked') return q.filter(c => !c.level)
  if (queueTab.value === 'marked') return q.filter(c => c.level)
  return q
})

/** 常用功能宫格。**是入口不是装饰** —— 每格直达对应页面，
 *  相当于把侧栏最常用的六个入口搬到首屏，少一次「去侧栏找」。 */
const quickLinks = [
  { icon: 'upload', label: '导入文档', desc: 'PDF / Word / Markdown', to: 'docs' },
  { icon: 'spark', label: 'AI 生成卡片', desc: '给个方向批量造卡', to: 'generate' },
  { icon: 'calendar', label: '开始复习', desc: '今日到期队列', to: 'review' },
  { icon: 'route', label: '今日路径', desc: '按目标排今天学什么', to: 'path' },
  { icon: 'graph', label: '知识图谱', desc: '卡片之间的关联', to: 'graph' },
  { icon: 'note', label: '笔记', desc: '随手记与摘录', to: 'notes' }
]

/** 学习指南。三句话说清「这系统怎么用」，每条直达对应页面 ——
 *  新用户前五分钟的动线就靠它，不用去翻文档。 */
const guideTips = [
  { n: '1', t: '导入一份 PDF / Word，自动按标题分章，一键转成卡片', to: 'docs' },
  { n: '2', t: '每天到期一批卡，标一下掌握度，算法安排下一次复习', to: 'review' },
  { n: '3', t: '模糊、不会的卡会被自动加急，不用自己排复习计划', to: 'path' }
]

/** 存储状态一句话。**降级必须说清楚** —— 悄悄回退到文件存储是最坏的情况：
 *  用户以为在写数据库，其实写进 JSON 了。 */
const storeText = computed(() => {
  const st = storeInfo.value
  if (!st) return ''
  if (st.degraded) return `⚠ 降级运行 · ${st.store}`
  return st.store === 'mysql' ? 'MySQL' : '文件存储'
})

/** 调度算法徽标。刻意只显示**名字**，不显示 needs 那一长串 ——
 *  「FSRS-4.5（记忆稳定性模型）」够了；数据需求写在系统状态页，
 *  驾驶舱是「扫一眼」的页面，塞长句会破坏它的节奏。 */
const algoName = computed(() => algoInfo.value?.label || '')

/** 掌握度分布条的三段。computed=0（没练过）时前端不画 ——
 *  那时每张卡的 p 都等于先验，画出来是一条三等分的假分布。 */
const bktBars = computed(() => {
  const m = mastery.value
  if (!m || !m.computed) return []
  return [
    { key: 'weak', name: '薄弱', value: m.weak, color: INK.weak },
    { key: 'mid', name: '一般', value: m.mid, color: INK.fuzzy },
    { key: 'strong', name: '扎实', value: m.strong, color: INK.known }
  ]
})

/** 平均掌握度 → 百分比字符串。p 是 0~1 的概率，不是分数。 */
const bktAvg = computed(() => {
  const p = mastery.value?.avgP
  return typeof p === 'number' ? `${Math.round(p * 100)}%` : ''
})
</script>

<template>
  <div class="dash">
    <!-- ===== 介绍横幅：左边产品介绍 + 行动按钮 + 三个小数据，右边浮动预览卡 ===== -->
    <section class="hero rise" :class="{ blank: isEmpty }">
      <div class="hero-left">
        <div class="eyebrow">
          <span class="brand-tag">智径 · AI 自适应学习平台</span>
          <span>{{ greeting }}，{{ auth.user?.displayName || auth.user?.username }}</span>
          <span class="dot" />
          <span>{{ todayText }}</span>
        </div>
        <h1 class="hero-title">把散落的资料，<em>变成记得住的知识</em></h1>
        <p class="hero-desc">
          导入文档或让 AI 生成卡片，间隔算法按你的掌握情况安排复习 —— 学得快，忘得慢。
        </p>
        <div class="hero-cta">
          <!-- 零状态：今天没有到期卡时**别再用主色召唤「开始复习」** ——
               那是个死路（队列是空的），点了只会让人以为页面坏了。
               主色让位给「生成卡片」，这才是此刻真正该做的事。 -->
          <button v-if="isEmpty" class="go" @click="router.push({ name: 'generate' })">
            生成第一批卡片
            <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
          <button v-else-if="dueToday > 0" class="go" @click="router.push({ name: 'review' })">
            开始复习（{{ dueToday }} 张）
            <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
          <button v-else class="go" @click="router.push({ name: 'cards' })">
            去学新卡
            <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
          <button v-if="isEmpty" class="go ghost" @click="router.push({ name: 'docs' })">
            导入文档
          </button>
          <button v-else class="go ghost" @click="router.push({ name: 'path' })">今日路径</button>
        </div>

        <!-- 横幅底部三个小数据（仿参考首页「617 个在招职位 / 15 份我的简历」那行） -->
        <div v-if="!isEmpty" class="hero-stats">
          <div class="hs">
            <b class="mono">{{ s.total ?? 0 }}</b>
            <span>张卡片</span>
          </div>
          <div class="hs">
            <b class="mono">{{ dueToday }}</b>
            <span>今日待复习</span>
          </div>
          <div class="hs">
            <b class="mono">{{ s.known ?? 0 }}</b>
            <span>已掌握</span>
          </div>
        </div>

        <!-- 状态徽标行：积压解释 / 学习方向 / 存储 / 算法。
             积压解释是**必须**的 —— 不解释的话用户会以为系统只挑了 20 张给他，
             或者以为数据丢了。 -->
        <div v-if="!isEmpty" class="hero-chips">
          <span
            v-if="dueBacklogText"
            class="chip"
            :title="`后端到期 ${s.dueToday} 张（含没学过的）`"
          >
            还有 {{ dueBacklog }} 张排队 · {{ dueBacklogText }}
          </span>
          <span v-if="learning.dirText" class="chip dir">{{ learning.dirText }}</span>
          <span v-if="storeText" class="chip">{{ storeText }}</span>
          <span
            v-if="algoName"
            class="chip dashed"
            title="复习间隔由哪个算法计算（config.local.json 的 ALGO）"
          >
            {{ algoName }}
          </span>
        </div>
      </div>

      <!-- 右侧浮动预览卡。三态：空库引导 / 今天的下一张卡 / 今天没到期 -->
      <aside class="preview">
        <template v-if="heroCard">
          <div class="pv-top">
            <span class="pv-tag">今日推荐</span>
            <span class="pv-level" :style="{ color: levelColor(heroCard.level) }">
              ● {{ levelLabel(heroCard.level) }}
            </span>
          </div>
          <div class="pv-title">{{ heroCard.title }}</div>
          <p class="pv-desc">
            {{ heroCard.oneLine || '这张卡还没有一句话简介，打开卡片可以补写。' }}
          </p>
          <div class="pv-tags">
            <span v-if="heroCard.domain" class="pv-domain">{{ heroCard.domain }}</span>
            <span class="pv-more">队列共 {{ learning.total }} 张</span>
          </div>
          <button class="go sm" @click="router.push({ name: 'review' })">
            开始复习
            <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
        </template>
        <template v-else-if="isEmpty">
          <div class="pv-top">
            <span class="pv-tag">从一份资料开始</span>
          </div>
          <div class="pv-title">你的卡片库还是空的</div>
          <p class="pv-desc">
            把讲义、论文、笔记丢进来，系统自动分章、转成卡片，之后就交给复习算法。
          </p>
          <button class="go sm" @click="router.push({ name: 'docs' })">
            导入第一份文档
            <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
        </template>
        <template v-else>
          <div class="pv-top">
            <span class="pv-tag">今日队列</span>
          </div>
          <div class="pv-title">今天没有到期的卡片</div>
          <p class="pv-desc">排期都照顾到了。可以去卡片库挑几张新的学，按每日目标推进就好。</p>
          <button class="go sm" @click="router.push({ name: 'cards' })">
            去学新卡
            <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
        </template>
      </aside>
    </section>

    <!-- ===== 空库：给一屏引导，而不是四个 0 + 五张空图 ===== -->
    <section v-if="isEmpty" class="blank-panel rise">
      <div class="bp-steps">
        <div class="bp">
          <div class="bp-n">1</div>
          <div class="bp-t">导入一份文档</div>
          <div class="bp-d">Markdown / PDF / Word 丢进来，自动按标题分章，再转成卡片</div>
          <button class="go ghost sm" @click="router.push({ name: 'docs' })">去导入</button>
        </div>
        <div class="bp">
          <div class="bp-n">2</div>
          <div class="bp-t">或让 AI 生成</div>
          <div class="bp-d">给一个方向，本地模型按大纲批量造卡，生成后先进草稿箱</div>
          <button class="go ghost sm" @click="router.push({ name: 'generate' })">去生成</button>
        </div>
        <div class="bp">
          <div class="bp-n">3</div>
          <div class="bp-t">开始复习</div>
          <div class="bp-d">每天到期一批，算法会按你的掌握情况安排下一次</div>
          <button class="go ghost sm" @click="router.push({ name: 'review' })">看队列</button>
        </div>
      </div>
    </section>

    <!-- 以下全部是「有卡之后才成立」的内容。空库时整块撤掉，
         只留上面那三步引导 —— 摆四个 0 和五张空图只会让人以为坏了。 -->
    <template v-if="!isEmpty">
      <!-- ===== 四张数据卡（带图标，点击直达） ===== -->
      <section class="metrics">
        <button
          v-for="(m, i) in metrics"
          :key="m.key"
          class="metric rise"
          :style="{ animationDelay: i * 55 + 'ms' }"
          @click="router.push({ name: m.to })"
        >
          <span class="m-ico" :style="{ color: m.color, background: m.color + '1c' }">
            <span class="mi" v-html="ICONS[m.icon]" />
          </span>
          <span class="m-body">
            <span class="m-value mono" :style="{ color: m.color }">{{ m.value }}</span>
            <span class="m-label">{{ m.label }}</span>
          </span>
        </button>
      </section>

      <!-- ===== 左右分栏：今日队列 + 常用功能/学习指南 =====
         仿参考首页「最新岗位 + 常用功能/求职指南」的分栏。
         列表 7 列、右栏 5 列：队列行有标题+简介+领域标签，需要宽度；
         右栏是宫格和短句，窄一点反而整齐。每行必须凑满 12。 -->
      <section class="grid">
        <div class="panel span-7 rise" :style="{ animationDelay: '80ms' }">
          <header class="panel-head">
            <h3>今日队列</h3>
            <div class="q-tabs">
              <button
                v-for="t in queueTabs"
                :key="t.k"
                class="q-tab"
                :class="{ on: queueTab === t.k }"
                @click="queueTab = t.k"
              >
                {{ t.n }}
              </button>
              <button class="link" @click="router.push({ name: 'review' })">查看全部 →</button>
            </div>
          </header>
          <div v-if="queueRows.length" class="q-list">
            <button
              v-for="c in queueRows"
              :key="c.id"
              class="q-row"
              @click="router.push({ name: 'review' })"
            >
              <span class="q-dot" :style="{ background: levelColor(c.level) }" />
              <span class="q-main">
                <span class="q-title">{{ c.title }}</span>
                <span class="q-sub">{{ c.oneLine || '' }}</span>
              </span>
              <span class="q-domain">{{ c.domain || '' }}</span>
              <span class="q-level" :style="{ color: levelColor(c.level) }">
                {{ levelLabel(c.level) }}
              </span>
            </button>
          </div>
          <p v-else class="empty">
            {{
              queueTab === 'all'
                ? '今天没有到期的卡片 —— 先去「卡片」页挑几张新的吧'
                : '这个筛选下没有卡片'
            }}
          </p>
        </div>

        <div class="span-5 side">
          <div class="panel rise" :style="{ animationDelay: '105ms' }">
            <header class="panel-head">
              <h3>常用功能</h3>
              <span class="hint">一键直达</span>
            </header>
            <div class="quick">
              <button
                v-for="q in quickLinks"
                :key="q.to"
                class="qk"
                @click="router.push({ name: q.to })"
              >
                <span class="qk-ico"><span class="mi" v-html="ICONS[q.icon]" /></span>
                <span class="qk-t">{{ q.label }}</span>
                <span class="qk-d">{{ q.desc }}</span>
              </button>
            </div>
          </div>

          <div class="panel rise" :style="{ animationDelay: '130ms' }">
            <header class="panel-head">
              <h3>学习指南</h3>
              <span class="hint">怎么用这个系统</span>
            </header>
            <div class="guide">
              <button
                v-for="g in guideTips"
                :key="g.n"
                class="gd"
                @click="router.push({ name: g.to })"
              >
                <span class="gd-n">{{ g.n }}</span>
                <span class="gd-t">{{ g.t }}</span>
                <svg class="gd-arrow" viewBox="0 0 24 24">
                  <path d="M5 12h13M13 6l6 6-6 6" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- ===== 图表行 =====
         栅格分配的依据是**每块图表要放多少字**，不是"看起来匀"。
         · 领域分布 5 列：横向条的左边要放得下「求职·AI工程」这种长领域名，
           给 4 列时标签和条会挤在一起（原来就是这样）；
         · 自评档位 3 列：环形图本身不需要宽，多给的列只是把图撑稀；
         · BKT 4 列：三段条 + 一段说明文字，比环形图需要更多的行内空间。
         ⚠️ 每行必须凑满 12（7+5 / 5+3+4 / 12）。
         原「科目构成」玫瑰图已撤：它和领域分布是同一份 bySubject 数据的
         两种画法，改版后页面以列表为主，重复图形不再值得占一整块。 -->
        <div class="panel span-5 rise" :style="{ animationDelay: '155ms' }">
          <header class="panel-head">
            <h3>领域分布</h3>
            <span class="hint">卡片按知识领域统计</span>
          </header>
          <EChart :option="domainOption" height="252px" />
        </div>

        <div class="panel span-3 rise" :style="{ animationDelay: '180ms' }">
          <header class="panel-head">
            <!-- 原先这里叫「掌握度分布」，但它画的是 users 自评的三档标记，
             不是掌握度。名字和内容对不上比不写更糟 —— 会让人以为
             系统已经算出了真实的掌握程度。改成「自评档位」，
             真正的掌握度挪到右边那张 BKT 卡（那是真的 p）。 -->
            <h3>自评档位</h3>
            <span class="hint">三档标记</span>
          </header>
          <EChart :option="masteryOption" height="252px" />
        </div>

        <div class="panel span-4 rise" :style="{ animationDelay: '205ms' }">
          <header class="panel-head">
            <h3>BKT 掌握度</h3>
            <span class="hint">
              {{ bktBars.length ? `已练 ${mastery.computed} 张 · 均值 ${bktAvg}` : '尚无数据' }}
            </span>
          </header>
          <!-- 用 CSS 条而不是 ECharts：这里只有三段，引入一个图表实例
             去画三段 div 完全不划算（这一页已经有 3 个 ECharts 实例了）。
             没数据时**不留 252px 的空框**（见 .bkt-empty）：一块纯文字却
             占着跟环形图一样高，是这一页最明显的「像坏了」的地方。 -->
          <div v-if="bktBars.length" class="bkt">
            <div class="bkt-bar">
              <i
                v-for="b in bktBars"
                :key="b.key"
                :style="{ flexGrow: b.value, background: b.color }"
              />
            </div>
            <div class="bkt-legend">
              <span v-for="b in bktBars" :key="b.key">
                <i :style="{ background: b.color }" />{{ b.name }} {{ b.value }}
              </span>
            </div>
            <p class="bkt-note">
              由复习事件回放出的概率 p 划档，比左边三档自评细 ——
              能看出「模糊」里有多少其实快忘了。没练过的卡不算在内。
            </p>
          </div>
          <div v-else class="bkt-empty">
            <p class="bkt-empty-t">还没有可算的掌握度</p>
            <p class="bkt-empty-d">
              BKT 要靠复习事件回放概率 p。去
              <button class="link" @click="router.push({ name: 'review' })">复习页</button>
              标几张卡，这里就会出现分布。
            </p>
          </div>
        </div>
      </section>

      <!-- ===== 底部状态条 =====
         「卡片构成 + 系统状态」横贯整行。这行本来就是收尾，
         不该再跟上面的图表抢注意力。 -->
      <section class="statusbar rise">
        <div class="sb-compose">
          <div class="sb-head">
            <h3>卡片构成</h3>
            <span class="hint"
              >内置 {{ Math.max((s.total ?? 0) - (s.custom ?? 0), 0) }} · 自建
              {{ s.custom ?? 0 }}</span
            >
          </div>
          <EChart :option="composeOption" height="44px" />
          <div class="legend-row">
            <span><i :style="{ background: INK.accent }" />内置</span>
            <span><i :style="{ background: INK.known }" />自建</span>
          </div>
        </div>

        <div class="sb-sep" />

        <!-- ⚠️ 拿不到时**写「检测中」而不是 `-`**：一个孤零零的横杠
           读起来像「坏了/没有」，而真相是「这个请求还没回来」。
           这三格是 per-request 拉的，页面刚打开的那一瞬间必然是空的。 -->
        <div class="sb-cell">
          <span class="dim">存储后端</span>
          <span class="mono">{{ storeInfo?.store || '检测中' }}</span>
        </div>
        <div class="sb-cell">
          <span class="dim">内置卡 / 库内</span>
          <span class="mono">
            {{
              storeInfo
                ? (storeInfo?.builtin?.inFile ?? '-') +
                  ' / ' +
                  (storeInfo?.builtin?.inDb ?? '未同步')
                : '检测中'
            }}
          </span>
        </div>
        <div class="sb-cell">
          <span class="dim">AI 精读</span>
          <span>{{ llmInfo === null ? '检测中' : llmInfo?.ok ? '可用' : '未启用' }}</span>
        </div>
        <button class="link sb-more" @click="router.push({ name: 'admin-system' })">
          运行状态 →
        </button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 空库引导 =====
 * 空驾驶舱不是「数据为 0 的驾驶舱」，是另一个页面。所以：
 *   - 横幅主按钮让位给「生成第一批卡片」（压线是「数据在这」的信号，空库去掉）；
 *   - 指标卡与图表区整块 v-if 撤掉（摆四个 0 和五张空图只会像坏了）；
 *   - 给三步「导入 / 生成 / 复习」，每步都带一个真的能点的按钮。 */
.hero.blank::before {
  display: none;
}
.blank-panel {
  padding: 8px 4px 4px;
}
.bp-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.bp {
  padding: 20px 20px 18px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.bp-n {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--ac);
  color: #fdfaf3;
  font-size: var(--fs-sm);
  font-weight: 600;
  line-height: 26px;
  text-align: center;
  margin-bottom: 12px;
}
.bp-t {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--tx);
  margin-bottom: 6px;
}
.bp-d {
  font-size: var(--fs-sm);
  line-height: 1.65;
  color: var(--mu);
  margin-bottom: 14px;
}
@media (max-width: 900px) {
  .bp-steps {
    grid-template-columns: 1fr;
  }
}

/* ===== 介绍横幅 =====
 * 左边：小标签 + 大标题 + 一句介绍 + 行动按钮 + 三个小数据。
 * 右边：浮动预览卡（今天接下来要复习的那张卡）。
 * 顶上一道靛蓝压线是整页唯一的重色 —— 「主角在这儿」的信号。
 * 参考页横幅是浅绿渐变，这里用靛蓝淡晕保持全站牛皮纸一致性。 */
.hero {
  display: flex;
  /* 垂直居中而不是拉伸：预览卡保持**内容高度**浮在右侧。
     拉伸时它会被撑到和左边文字一样高，卡下半截一大片空白
     （参考页的浮卡就是紧凑的一张）。 */
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  flex-wrap: wrap;
  padding: 30px 32px 26px;
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
  flex: 1 1 420px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: var(--fs-sm);
  color: var(--mu);
}
/* 产品小标签：仿参考页横幅左上角那行小字。主色描边，是「品牌」不是「状态」 */
.brand-tag {
  font-size: var(--fs-xs);
  padding: 3px 11px;
  border-radius: 20px;
  border: 1px solid var(--ac-dim);
  background: var(--ac-glow);
  color: var(--ac);
  font-weight: 600;
}
.hero-title {
  font-size: var(--fs-hero);
  font-weight: 700;
  line-height: 1.22;
  margin: 14px 0 10px;
  color: var(--tx);
}
/* 标题后半句用主色 —— 仿参考页「职业机会」那半句的处理，
 * 一眼看出这产品的价值落在哪几个字上。 */
.hero-title em {
  font-style: normal;
  color: var(--ac);
}
.hero-desc {
  font-size: var(--fs-md);
  line-height: 1.75;
  color: var(--mu);
  max-width: 560px;
}
.hero-cta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 20px;
}

/* 横幅底部三个小数据：仿参考页「617 个 / 15 份 / 400 个」那行。
 * 数字大、标签小，竖分隔线隔开 —— 这是「介绍」到「数据」的过渡。 */
.hero-stats {
  display: flex;
  gap: 26px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px dashed var(--line2);
  width: 100%;
}
.hs {
  display: flex;
  align-items: baseline;
  gap: 7px;
}
.hs b {
  font-size: 26px;
  font-weight: 700;
  color: var(--tx);
  font-variant-numeric: tabular-nums;
}
.hs span {
  font-size: var(--fs-xs);
  color: var(--dim);
}

.hero-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.chip {
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--line2);
  color: var(--dim);
}
/* 积压说明用**中性描边**而不是警示色 —— 积压不是错误，
   400 张库里只学 20 张是「按计划排队」，标成橙色会让人以为坏了。 */
.chip.dir {
  border-color: var(--ac-dim);
  background: var(--ac-glow);
  color: var(--ac);
}
/* 调度算法是**配置**而不是内容状态，虚线描边跟其它徽标再区分一档 */
.chip.dashed {
  border-style: dashed;
}

/* ===== 浮动预览卡 =====
 * 仿参考页横幅右侧的「示例岗位」卡：小标签 + 标题 + 简介 + 底部行动。
 * 用比面板更强的投影「浮」起来，是横幅里唯一立体的东西。 */
.preview {
  flex: 0 1 330px;
  min-width: 280px;
  padding: 20px 22px 18px;
  border-radius: var(--radius);
  border: 1px solid var(--line2);
  background: var(--panel);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.pv-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}
.pv-tag {
  font-size: var(--fs-xs);
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 20px;
  background: var(--ac-glow);
  color: var(--ac);
}
.pv-level {
  font-size: var(--fs-xs);
  font-weight: 600;
}
.pv-title {
  font-size: var(--fs-lg);
  font-weight: 700;
  line-height: 1.45;
  color: var(--tx);
  margin: 12px 0 6px;
}
.pv-desc {
  font-size: var(--fs-sm);
  line-height: 1.7;
  color: var(--mu);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pv-tags {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0 14px;
}
.pv-domain {
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--line2);
  color: var(--mu);
}
.pv-more {
  font-size: var(--fs-xs);
  color: var(--dim);
}

/* 主按钮用平涂的靛蓝，不做渐变 —— 渐变是屏幕语言，
   纸面上的墨是平的。这一处克制了，整页的"纸质"才立得住 */
.go {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ac);
  font-size: var(--fs-md);
  font-weight: 600;
  font-family: var(--font);
  color: #fdfaf3;
  background: var(--ac);
  cursor: pointer;
  transition:
    background 0.16s,
    border-color 0.16s;
}
.go:hover {
  background: var(--ac-dim);
  border-color: var(--ac-dim);
}
.go svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.go.ghost {
  color: var(--tx);
  background: var(--panel2);
  border-color: var(--line2);
}
.go.ghost:hover {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--panel2);
}
.go.sm {
  padding: 8px 16px;
  font-size: var(--fs-sm);
}

/* ===== 四张数据卡 =====
 * 仿参考页「图标 + 数字 + 标签」小卡。button 元素自带的外观全清掉，
 * 只留 hover 抬升 —— 整张卡就是入口。 */
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.metric {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
  font-family: var(--font);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s,
    transform 0.18s,
    box-shadow 0.18s;
}
.metric:hover {
  /* 抬升 + 描边转主色：光靠 2px 位移在截图里几乎看不出来，
     「可点击」的暗示不够。描边变靛蓝是最明确的「这是入口」信号。 */
  border-color: var(--ac-dim);
  transform: translateY(-3px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.62),
    var(--shadow);
}
/* 图标底盘：圆角方块 + 各卡自己的淡色底，仿参考页的圆形图标底 */
.m-ico {
  flex: none;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
}
.mi {
  display: inline-flex;
}
/* 图标是 v-html 注入的（无 scope 属性），要用 :deep 才够得着 */
.m-ico :deep(svg),
.qk-ico :deep(svg) {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.m-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.m-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.15;
  /* 等宽数字：四卡并排时，20 / 0 / 0 / 0 的字宽一致才像一张表。
     比例数字（1 有宽、0 窄）会让并排的列看着在抖。 */
  font-variant-numeric: tabular-nums;
}
.m-label {
  font-size: var(--fs-sm);
  color: var(--mu);
  letter-spacing: 0.2px;
}

/* ===== 图表网格 =====
 * 12 栅格，按信息复杂度分配列数，**不要平均** ——
 * 平均分配的结果就是六块一样大的方块，眼睛找不到重点。
 * ⚠️ 每一行的 span 之和必须等于 12：7+5 / 5+3+4。
 * .panel / .panel-head 用 tokens.css 里的全局类，这里只写栅格。 */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 14px;
}
.span-3 {
  grid-column: span 3;
}
.span-4 {
  grid-column: span 4;
}
.span-5 {
  grid-column: span 5;
}
.span-7 {
  grid-column: span 7;
}

/* 右栏：常用功能 + 学习指南上下两块 */
.side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.side .panel {
  flex: 1;
}

/* ===== 今日队列 ===== */
.q-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
}
.q-tab {
  padding: 3px 11px;
  border-radius: 20px;
  border: 1px solid transparent;
  background: none;
  font-family: var(--font);
  font-size: var(--fs-xs);
  color: var(--mu);
  cursor: pointer;
  transition:
    color 0.15s,
    background 0.15s,
    border-color 0.15s;
}
.q-tab:hover {
  color: var(--ac);
}
.q-tab.on {
  color: var(--ac);
  background: var(--ac-glow);
  border-color: var(--ac-dim);
  font-weight: 600;
}
.q-list {
  display: flex;
  flex-direction: column;
  max-height: 300px;
  overflow-y: auto;
}
/* 行按钮：色点 + 标题/简介 + 领域 + 档位。整行可点进复习。
 * 行间用淡分隔线，不用卡片套卡片 —— 一张纸上的清单。 */
.q-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 6px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: none;
  font-family: var(--font);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}
.q-row:last-child {
  border-bottom: 0;
}
.q-row:hover {
  background: var(--panel2);
}
.q-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.q-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.q-title {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--tx);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.q-sub {
  font-size: var(--fs-xs);
  color: var(--dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.q-domain {
  flex: none;
  max-width: 120px;
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--line2);
  color: var(--mu);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.q-level {
  flex: none;
  width: 44px;
  text-align: right;
  font-size: var(--fs-xs);
  font-weight: 600;
}

/* ===== 常用功能宫格 =====
 * 2×3 六格，仿参考页「常用功能」。格子是入口：图标 + 名字 + 一句说明。 */
.quick {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 4px 2px 6px;
}
.qk {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 13px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--panel2);
  font-family: var(--font);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.qk:hover {
  border-color: var(--ac-dim);
  background: var(--panel);
}
.qk-ico {
  color: var(--ac);
  margin-bottom: 2px;
}
.qk-t {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--tx);
}
.qk-d {
  font-size: var(--fs-xs);
  color: var(--dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* ===== 学习指南 =====
 * 三行「怎么用」，编号 + 一句话 + 箭头。仿参考页「求职指南」。 */
.guide {
  display: flex;
  flex-direction: column;
  padding: 2px 0 4px;
}
.gd {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 6px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: none;
  font-family: var(--font);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}
.gd:last-child {
  border-bottom: 0;
}
.gd:hover {
  background: var(--panel2);
}
.gd-n {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--ac-glow);
  color: var(--ac);
  font-size: var(--fs-xs);
  font-weight: 600;
  line-height: 22px;
  text-align: center;
}
.gd-t {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: var(--mu);
}
.gd-arrow {
  flex: none;
  width: 15px;
  height: 15px;
  fill: none;
  stroke: var(--dim);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.gd:hover .gd-arrow {
  stroke: var(--ac);
}

/* ===== BKT 掌握度分布 =====
 * 三段条用 flex-grow 分配宽度（值由 wxml/模板传进来），某段为 0 时
 * flex-grow:0 → 自然不占宽，不用额外写隐藏判断。 */
.bkt {
  display: flex;
  flex-direction: column;
  height: 252px;
  padding: 18px 2px 0;
}
/* 无数据状态：**不撑高**。
 * 之前用 `.empty`（height:100%）放在 252px 的面板里，一段纯文字
 * 独占一整块竖直空间，跟旁边的环形图齐平 —— 视觉上像"图加载失败"。
 * 现在改成从上往下排的一段短文字，块里留白是版式的呼吸，不是缺东西。 */
.bkt-empty {
  padding: 22px 2px 0;
}
.bkt-empty-t {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--mu);
  margin-bottom: 8px;
}
.bkt-empty-d {
  font-size: var(--fs-sm);
  line-height: 1.75;
  color: var(--dim);
}
/* 说明文字里的按钮要跟正文基线对齐，且不能有自己的下边框残留 */
.bkt-empty-d .link {
  font-size: var(--fs-sm);
  vertical-align: baseline;
}
.bkt-bar {
  display: flex;
  height: 16px;
  border-radius: 999px;
  overflow: hidden; /* 段间不留缝，靠圆角裁出连续的条 */
}
.bkt-bar i {
  flex-basis: 0;
}
.bkt-legend {
  display: flex;
  gap: 18px;
  margin-top: 16px;
  font-size: var(--fs-xs);
  color: var(--mu);
}
.bkt-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.bkt-legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}
.bkt-note {
  margin: auto 0 0;
  font-size: var(--fs-xs);
  line-height: 1.7;
  color: var(--dim);
}

.empty {
  height: 100%;
  min-height: 120px;
  display: grid;
  place-items: center;
  text-align: center;
  font-size: var(--fs-sm);
  color: var(--dim);
  padding: 0 20px;
}

.legend-row {
  display: flex;
  gap: 18px;
  font-size: var(--fs-xs);
  color: var(--mu);
  padding: 4px 2px 12px;
}
.legend-row span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend-row i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

/* ===== 底部状态条 =====
 * 「卡片构成 + 运行状态」横贯整行的一条。
 * 用 grid 而不是 flex：flex + 三格 + 一个按钮，宽度分配全靠 flex-grow
 * 猜，而这里每格内容长度差别很大（"mysql" vs "未同步"），得按内容定量。 */
.statusbar {
  display: grid;
  grid-template-columns: minmax(260px, 1.4fr) 1px repeat(3, minmax(120px, 1fr)) auto;
  align-items: center;
  gap: 18px;
  padding: 16px 22px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}
/* 竖分隔线：只把"构成"和"运行状态"分开，三格状态之间不隔 ——
 * 它们是同一组信息，格子之间加线会让人以为是三件独立的事。 */
.sb-sep {
  align-self: stretch;
  background: var(--line);
}
.sb-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}
.sb-head h3 {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--tx);
}
.sb-head .hint {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.sb-compose .legend-row {
  padding: 6px 0 0;
}
.sb-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  font-size: var(--fs-sm);
}
/* 标签在上、值在下：横向排的话「存储后端」四个字 + "mysql"
 * 在 150px 里会顶到同一行然后折行，值和标签就错位了。 */
.sb-cell .dim {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.sb-cell .mono {
  color: var(--tx);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sb-more {
  align-self: center;
  white-space: nowrap;
}
@media (max-width: 1100px) {
  /* 窄屏时状态条的四列排不下，退回两行两列。
   * 不能靠 flex-wrap：那样第一格会把整行宽度吃掉，第二行只剩一个按钮。 */
  .statusbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 20px;
  }
  .sb-sep {
    display: none;
  }
  .sb-compose {
    grid-column: 1 / -1;
  }
  .sb-more {
    justify-self: start;
  }
}

.link {
  align-self: flex-start;
  margin-top: 2px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--ac);
  font-size: var(--fs-sm);
  font-family: var(--font);
  cursor: pointer;
  white-space: nowrap;
}
.link:hover {
  text-decoration: underline;
}

@media (max-width: 1240px) {
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .span-3,
  .span-4,
  .span-5,
  .span-7 {
    grid-column: span 12;
  }
  /* 图表全部拉满宽之后，252px 的定高对 BKT 偏矮，
   * 但 ECharts 高度是 prop 写死的，这里只把 CSS 容器放开。 */
  .bkt {
    height: 288px;
  }
}
@media (max-width: 900px) {
  .hero {
    padding: 24px 22px;
  }
  .hero-title {
    font-size: var(--fs-2xl);
  }
  .preview {
    flex-basis: 100%;
  }
  .metrics {
    grid-template-columns: 1fr;
  }
}
</style>
