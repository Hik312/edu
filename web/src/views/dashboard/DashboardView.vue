<script setup>
/* 学习驾驶舱 —— 数据总览。
 *
 * ## 它跟别的页面有什么不一样
 *
 * 别的页面是「读」，这一页是「扫」：用户进来只为三件事 ——
 * 库里一共有多少卡（这一页的主角）、今天待复习几张、以及确认数据存到哪了。
 * 所以整页只留一个大数字（总卡数），其余都当配角，靠字号和位置分主次。
 * 今日待复习没消失，它降到四张指标卡里当第一张 —— 总量是「资产」，
 * 待复习是「今天的活儿」，前者才是这一页要一眼看到的东西。
 *
 * 曾经这一页是全站唯一的深色页，靠深底把图表托起来。现在全站统一牛皮纸，
 * 图表的对比度靠**压低颜色饱和度 + 描边**来保证，不靠底色深浅 ——
 * 纸底上把颜色调深就够读了，反而更省眼睛。
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
import { storage, getAlgo } from '@/api/system'
import { getLlmStatus } from '@/api/ai'
import { getMasteryBrief } from '@/api/learning'
import { CHART_BG, INK, chartBase, colorOf, levelColor, SEQ } from '@/config/theme'

const router = useRouter()
const auth = useAuthStore()
const learning = useLearningStore()

/** 纸面主题是唯一主题，所以这些是个常量，不再按页取。 */
const base = chartBase()

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
  learning.fetchDue({ limit: 8 })
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

/** 四张顶指标。bar 是视觉占比，分母统一用卡片总数 ——
 *  用各自的极值会让四条杠看起来差不多长，占比图就失去意义了。
 *
 *  四个颜色必须**色相各不相同**，否则四张并排的卡会被人当成两组。
 *  文档 / 笔记 不用语义色，它们不是「掌握程度」，借用语义色会误导。 */
const metrics = computed(() => {
  const v = s.value
  const total = Math.max(v.total ?? 0, 1)
  return [
    {
      key: 'due',
      label: '今日待复习',
      value: dueToday.value,
      color: INK.accent,
      ratio: dueToday.value / total
    },
    {
      key: 'known',
      label: '已掌握',
      value: v.known ?? 0,
      color: INK.known,
      ratio: (v.known ?? 0) / total
    },
    {
      key: 'docs',
      label: '文档',
      value: v.docs ?? 0,
      color: '#c08a2e',
      ratio: (v.docs ?? 0) / Math.max(total / 4, 1)
    },
    {
      key: 'notes',
      label: '笔记',
      value: v.notes ?? 0,
      color: '#6a5aa8',
      ratio: (v.notes ?? 0) / Math.max(total / 4, 1)
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
          formatter: (p) => (p.percent < 3 ? '' : `${p.name}\n${p.percent}%`),
          lineHeight: 18
        },
        // ⚠️ 别给极小的扇区加圆角。
        // 0.75% 的扇区在环上只有约 3° 的弧长，两端各 5px 的 borderRadius
        // 正好把它整段抹掉 —— 加上纸色描边，视觉上就是**环上开了个白口子**，
        // 看起来像渲染坏了（2026-10-03 用户就指着这个图问是不是坏了）。
        // 圆角是给「有面积的扇区」做视觉柔化的，对一根线来说它是灾难。
        // 同理，<3% 的扇区描边也收窄到 1px，避免描边占掉的宽度超过它本身。
        itemStyle: (p) => ({
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
 * 领域名可以很长（「求职·AI工程」），横向条能给文字留位置；
 * 纵向的话标签会互相挤成斜排或者直接被省略掉。 */
const domainOption = computed(() => {
  const rows = Object.entries(s.value.domains || {}).sort((a, b) => b[1] - a[1])
  return {
    ...base,
    // 右边必须留出数字的位置。原来 right:26 只够放两位数，
    // 「170」这种三位数会被条形压住半个 —— 数值标签压在条上是这页最刺眼的一处。
    grid: { left: 8, right: 46, top: 8, bottom: 4, containLabel: true },
    tooltip: { ...base.tooltip, formatter: '{b}：{c} 张' },
    xAxis: { type: 'value', show: false, max: Math.max(...rows.map(r => r[1]), 1) },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map(r => r[0]),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: CHART_BG.label, fontSize: 13, fontWeight: 500 }
    },
    series: [
      {
        type: 'bar',
        barWidth: 15,
        data: rows.map(r => ({
          value: r[1],
          itemStyle: { color: colorOf(r[0], SEQ), borderRadius: [0, 4, 4, 0] }
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

/** 科目构成：玫瑰图。同一份数据换一种图形不是凑数 ——
 *  饼图只看角度，科目多的时候很难分辨谁多；玫瑰图让半径也编码数值，
 *  面积差异被放大，一眼就能看出「明显多的那一个」。 */
const subjectOption = computed(() => {
  const rows = Object.entries(s.value.bySubject || {}).sort((a, b) => b[1] - a[1])
  return {
    ...base,
    tooltip: { ...base.tooltip, formatter: '{b}：{c} 张' },
    legend: { ...base.legend, show: true, bottom: 0, type: 'scroll' },
    series: [
      {
        type: 'pie',
        radius: [18, 92],
        center: ['50%', '44%'],
        roseType: 'area',
        itemStyle: { borderRadius: 6, borderColor: CHART_BG.paper, borderWidth: 2 },
        label: { color: CHART_BG.label, fontSize: 12.5, formatter: '{b} {c}' },
        data: rows.map(r => ({
          name: r[0],
          value: r[1],
          itemStyle: { color: colorOf(r[0], SEQ) }
        }))
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

/** DataV 滚动榜。**行里不放太多字段** —— 榜的作用是「一眼扫到标题」，
 *  塞进 oneLine 会让每行变成三行字，滚起来根本看不清。
 *
 *  ⚠️ DataV 这套组件的底色/字色默认值是**给深色大屏**的（文字写死 #fff，
 *  表头是亮青）。所以这里必须逐项覆盖背景，字色则在样式里用 :deep 覆盖
 *  （见 <style> 里那段注释）—— 漏掉任何一项，纸上就会出现一片看不见的白字。 */
const boardOption = computed(() => {
  const rows = learning.queue
    .slice(0, 8)
    .map(c => [
      `<span style="color:${levelColor(c.level)}">●</span> ${escapeHtml(c.title)}`,
      escapeHtml(c.domain || '')
    ])
  return {
    header: ['待办卡片', '领域'],
    data: rows.length ? rows : [['暂无待复习卡片', '']],
    rowNum: Math.min(rows.length || 1, 8),
    headerBGC: 'rgba(31, 75, 107, 0.09)',
    oddRowBGC: 'rgba(58, 47, 33, 0.035)',
    evenRowBGC: 'transparent',
    headerHeight: 36,
    rowHeight: 30,
    columnWidth: [340, 130],
    align: ['left', 'right'],
    index: false,
    waitTime: 2600,
    // ★ 刻意**关掉自动翻页**（carousel: 'page' → ''）。
    // 滚动榜是用来展示「看不完的量」的，而今日队列最多 8 条 ——
    // 让它自己滚，读的人就得盯着等下一行，一行标题都读不完整。
    // 8 条一次摊开（rowNum 8 + rowHeight 30 = 240px，刚好落进 252px 的框），
    // 想上下扫自己滚就够了。数据量真涨到几十条时再把翻页开回来。
    carousel: '',
    hoverPause: true
  }
})

/** 滚动榜是按 innerHTML 渲染的，标题里的尖括号会被当成标签。
 *  这当然不是 XSS 的第一道防线（后端也该清洗），但至少别让它把自己渲染坏。 */
function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

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
    <!-- ===== 卷宗题头：总卡数是这一页唯一的主角 ===== -->
    <section class="hero rise" :class="{ blank: isEmpty }">
      <div class="hero-left">
        <template v-if="isEmpty">
          <!-- 空库：不显示「0 张卡片」这个大号 0。大号 0 在这里是
               最糟的排版 —— 它把「你还没开始」渲染成了「你什么都没有」，
               而这其实是**这个产品最容易劝退人的第一屏**。改成邀请。 -->
          <div class="eyebrow">{{ greeting }}，{{ auth.user?.displayName || auth.user?.username }}</div>
          <div class="hero-title">还没有卡片</div>
          <div class="hero-sub">
            <span>这个产品的一切都从卡片开始 —— 导入一份文档，或让 AI 生成第一批</span>
          </div>
        </template>
        <template v-else>
          <div class="eyebrow">
            {{ greeting }}，{{ auth.user?.displayName || auth.user?.username }}
          </div>
          <div class="hero-num">
            <span class="num mono">{{ s.total ?? 0 }}</span>
            <span class="unit">张卡片</span>
          </div>
        </template>
        <div class="hero-sub" v-if="!isEmpty">
          <span>{{ todayText }}</span>
          <span class="dot" />
          <span>今日待复习 {{ dueToday }} 张</span>
          <!-- 积压解释：为什么库里 400 张、今天只学 20 张。
               这一行是**必须**的 —— 不解释的话用户会以为系统只挑了 20 张给他，
               或者以为数据丢了。 -->
          <template v-if="dueBacklogText">
            <span class="dot" />
            <span class="backlog" :title="`后端到期 ${s.dueToday} 张（含没学过的）`">
              还有 {{ dueBacklog }} 张排队 · {{ dueBacklogText }}
            </span>
          </template>
          <template v-if="learning.dirText">
            <span class="dot" />
            <span class="dir">{{ learning.dirText }}</span>
          </template>
          <template v-if="storeText">
            <span class="dot" />
            <span class="store">{{ storeText }}</span>
          </template>
          <template v-if="algoName">
            <span class="dot" />
            <span class="algo" title="复习间隔由哪个算法计算（config.local.json 的 ALGO）">
              {{ algoName }}
            </span>
          </template>
        </div>
      </div>
      <div class="hero-right">
        <!-- 零状态：今天没有到期卡时**别再用主色召唤「开始复习」** ——
             那是个死路（队列是空的），点了只会让人以为页面坏了。
             主色让位给「去学新卡」，这才是此刻真正该做的事。 -->
        <button v-if="isEmpty" class="go" @click="router.push({ name: 'generate' })">
          生成第一批卡片
          <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
        </button>
        <button v-else-if="dueToday > 0" class="go" @click="router.push({ name: 'review' })">
          开始复习
          <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
        </button>
        <button v-else class="go" @click="router.push({ name: 'cards' })">
          去学新卡
          <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
        </button>
        <button class="go ghost" @click="router.push({ name: 'path' })">今日路径</button>
        <button v-if="isEmpty" class="go ghost" @click="router.push({ name: 'docs' })">
          导入文档
        </button>
      </div>
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
         只留上面那三步引导 —— 摆 four 个 0 和五张空图只会让人以为坏了。 -->
    <template v-if="!isEmpty">
    <!-- ===== 四张指标 ===== -->
    <section class="metrics">
      <div
        v-for="(m, i) in metrics"
        :key="m.key"
        class="metric rise"
        :style="{ animationDelay: i * 55 + 'ms' }"
      >
        <div class="m-label">{{ m.label }}</div>
        <div class="m-value mono" :style="{ color: m.color }">{{ m.value }}</div>
        <div class="m-bar">
          <i :style="{ width: Math.min(m.ratio * 100, 100) + '%', background: m.color }" />
        </div>
      </div>
    </section>

    <!-- ===== 图表区 =====
         栅格分配的依据是**每块图表要放多少字**，不是"看起来匀"。
         · 领域分布 5 列：横向条的左边要放得下「求职·AI工程」这种长领域名，
           给 4 列时标签和条会挤在一起（原来就是这样）；
         · 自评档位 3 列：环形图本身不需要宽，多给的列只是把图撑稀；
         · BKT 4 列：三段条 + 一段说明文字，比环形图需要更多的行内空间。
         ⚠️ 每行必须凑满 12（5+3+4 / 7+5 / 12）。之前是 4+4+4 / 4+7 / 5，
         右边永远缺一块，页面看着是"没排完"而不是"排好了"。 -->
    <section class="grid">
      <div class="panel span-5 rise" :style="{ animationDelay: '80ms' }">
        <header class="panel-head">
          <h3>领域分布</h3>
          <span class="hint">卡片按知识领域统计</span>
        </header>
        <EChart :option="domainOption" height="252px" />
      </div>

      <div class="panel span-3 rise" :style="{ animationDelay: '105ms' }">
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

      <div class="panel span-4 rise" :style="{ animationDelay: '130ms' }">
        <header class="panel-head">
          <h3>BKT 掌握度</h3>
          <span class="hint">
            {{ bktBars.length ? `已练 ${mastery.computed} 张 · 均值 ${bktAvg}` : '尚无数据' }}
          </span>
        </header>
        <!-- 用 CSS 条而不是 ECharts：这里只有三段，引入一个图表实例
             去画三段 div 完全不划算（这一页已经有 4 个 ECharts 实例了）。
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

      <!-- 宽度分布：**图表 7 / 滚动榜 5**。
     试过对调（队列 7、图 5）想让队列标题不被截断，实测反而更糟：
     科目构成的扇区外标签和图例一起被挤到省略号（"work/ai 1…"、"k mayo…"），
     而队列那点多出来的宽度只够多显示两三个字。
     两边都是「标签放不下」，但图表的标签是**外置引线**的，截断更像坏了。 -->
      <div class="panel span-7 rise" :style="{ animationDelay: '180ms' }">
        <header class="panel-head">
          <h3>科目构成</h3>
          <span class="hint">扇区半径与面积同时编码数量</span>
        </header>
        <EChart :option="subjectOption" height="288px" />
      </div>

      <div class="panel span-5 rise" :style="{ animationDelay: '230ms' }">
        <header class="panel-head">
          <h3>今日队列</h3>
          <span class="hint">共 {{ learning.total }} 张</span>
        </header>
        <div class="board">
          <DvScrollBoard v-if="learning.queue.length" :config="boardOption" />
          <p v-else class="empty">今天没有到期的卡片 —— 先去「卡片」页挑几张新的吧</p>
        </div>
      </div>
    </section>

    <!-- ===== 底部状态条 =====
         原来「卡片构成」和「系统状态」挤在同一个 span-5 的窄面板里，
         堆叠条只有 64px 高、下面拖着三行小字，右侧空 7 列。
         改成一条**横贯整行**的状态条：左边是构成条，右边三格是运行状态。
         信息量没变，但 12 列的宽度正好够 —— 这行本来就是收尾，
         不该再跟上面的图表抢注意力。 -->
    <section class="statusbar rise">
      <div class="sb-compose">
        <div class="sb-head">
          <h3>卡片构成</h3>
          <span class="hint">内置 {{ Math.max((s.total ?? 0) - (s.custom ?? 0), 0) }} · 自建 {{ s.custom ?? 0 }}</span>
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
              ? (storeInfo?.builtin?.inFile ?? '-') + ' / ' + (storeInfo?.builtin?.inDb ?? '未同步')
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
 *   - hero 的大号 0 换成一句邀请（.blank 去掉靛蓝压线，压线是「数据在这」的信号）；
 *   - 指标卡与图表区整块 v-if 撤掉（摆四个 0 和五张空图只会像坏了）；
 *   - 给三步「导入 / 生成 / 复习」，每步都带一个真的能点的按钮。 */
.hero.blank::before {
  display: none;
}
.hero-title {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.15;
  margin: 8px 0 6px;
  color: var(--tx);
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
.go.sm {
  margin-top: auto;
  padding: 7px 14px;
  font-size: var(--fs-sm);
}
@media (max-width: 900px) {
  .bp-steps {
    grid-template-columns: 1fr;
  }
}

/* ===== 卷宗题头 =====
 * 顶上一道靛蓝压线 + 纸面本色。压线是整页唯一的重色，
 * 它就是「主角在这儿」的信号，不需要再做发光或渐变。 */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding: 26px 28px;
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
.hero-num {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 6px 0 8px;
}
.num {
  font-size: 54px;
  font-weight: 700;
  line-height: 1;
  color: var(--ac);
  /* 等宽数字：四个指标卡并排时，20 / 0 / 0 / 0 的字宽一致才像一张表。
     比例数字（1 有宽、0 窄）会让右对齐的列看着在抖 —— 这是"廉价感"最常见的来源。 */
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.5px;
}
.unit {
  font-size: var(--fs-md);
  color: var(--mu);
}
.hero-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: var(--fs-sm);
  color: var(--mu);
}
.dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--line2);
}
.store {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--line2);
  color: var(--dim);
}
/* 学习方向：回答「今天在学什么」，比存储徽标重要一档 —— 用主色点出来 */
.dir {
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--ac-dim);
  background: var(--ac-glow);
  color: var(--ac);
}
/* 积压说明。用**中性描边**而不是警示色 —— 积压不是错误，
   400 张库里只学 20 张是「按计划排队」，标成橙色会让人以为坏了。 */
.backlog {
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--line2);
  color: var(--dim);
}
/* 调度算法：也是「系统在替你做什么」的说明，但它是**配置**而不是
 * 内容状态，所以用中性描边（不抢主色的戏）。title 里给全称。 */
.algo {
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px dashed var(--line2);
  color: var(--dim);
}

.hero-right {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
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

/* ===== 指标卡 ===== */
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.metric {
  position: relative;
  padding: 16px 18px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
  transition:
    border-color 0.18s,
    transform 0.18s,
    box-shadow 0.18s;
}
.metric:hover {
  border-color: var(--line2);
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.62),
    var(--shadow);
}
.m-label {
  font-size: var(--fs-sm);
  color: var(--mu);
  /* 标签给一点点字距：纯中文标签不能给（会糊），但这个字号下
     0.2px 的紧排能让四张卡的标签左边缘看起来是一条直线 */
  letter-spacing: 0.2px;
}
.m-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.25;
  /* 同 .num：等宽数字，四卡并排不抖 */
  font-variant-numeric: tabular-nums;
  margin-top: 2px;
}
.m-bar {
  height: 4px;
  margin-top: 8px;
  border-radius: 3px;
  background: var(--line);
  overflow: hidden;
}
.m-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.22, 0.7, 0.28, 1);
}

/* ===== 图表网格 =====
 * 12 栅格，按信息复杂度分配列数，**不要平均** ——
 * 平均分配的结果就是六块一样大的方块，眼睛找不到重点。
 * ⚠️ 每一行的 span 之和必须等于 12：4+4+4 / 4+7 / 5 这种排法右边
 * 永远缺一块，页面读起来像「没排完」。现在是 5+3+4 / 7+5 / 12（全宽条）。
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

.board {
  height: 252px;
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

/* DataV 滚动榜的文字色写死在它自己的 CSS 里（.dv-scroll-board{color:#fff}），
   那是给深色大屏用的 —— 在纸面上等于看不见。:deep 会编成
   `[data-v-xxx] .dv-scroll-board`，特异性高过它，与引入顺序无关。
   ⚠️ 别把这段搬去 tokens.css：那样它是全局规则，会连带影响以后别处
   可能用到的 DataV 组件，而且一旦失效很难想到是这里。 */
.board :deep(.dv-scroll-board) {
  color: var(--tx);
}
.board :deep(.dv-scroll-board .header) {
  color: var(--mu);
  font-weight: 600;
}
.board :deep(.dv-scroll-board .row-item) {
  font-size: var(--fs-sm);
  line-height: 2;
}

.empty {
  height: 100%;
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
 * 「卡片构成 + 运行状态」从原来那个 span-5 的窄面板改成横贯整行的一条。
 * 动机有两条，缺一不可：
 *   1. **填满栅格**。原来这行只占了 5 列，右边空 7 列。
 *   2. **宽度要够放三格状态**。「存储后端 / 内置卡 / AI 精读」挤在
 *      半屏里时每格都得折行，现在每格分到 200px 上下，一行放得下。
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
  cursor: pointer;
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
  /* 图表全部拉满宽之后，252px 的定高对「今日队列」和 BKT 都偏矮，
   * 但 ECharts 高度是 prop 写死的，这里只把 CSS 容器放开。 */
  .board,
  .bkt {
    height: 288px;
  }
}
</style>
