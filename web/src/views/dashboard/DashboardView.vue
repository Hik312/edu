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
import { storage } from '@/api/system'
import { getLlmStatus } from '@/api/ai'
import { CHART_BG, INK, chartBase, colorOf, levelColor, SEQ } from '@/config/theme'

const router = useRouter()
const auth = useAuthStore()
const learning = useLearningStore()

/** 纸面主题是唯一主题，所以这些是个常量，不再按页取。 */
const base = chartBase()

const storeInfo = ref(null)
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
})

const s = computed(() => learning.stats || {})

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
      value: v.dueToday ?? 0,
      color: INK.accent,
      ratio: (v.dueToday ?? 0) / total
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
        // 描边用纸面本色而不是深色：扇区之间靠"露出的纸"分开，
        // 在浅底上比画黑缝干净
        itemStyle: { borderColor: CHART_BG.paper, borderWidth: 2, borderRadius: 5 },
        label: {
          // 只有一档时**不画标签**（比如 20 张全部未标记）。
          // 整圈一个颜色，标签给不出任何可区分的信息，却一定会贴在环上
          // 把画面搅乱；总数已经写在圆心了。两档以上才需要标出每块是谁。
          show: data.length > 1,
          color: CHART_BG.label,
          fontSize: 13,
          formatter: '{b}\n{d}%',
          lineHeight: 18
        },
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
    grid: { left: 8, right: 26, top: 8, bottom: 4, containLabel: true },
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
    rowNum: Math.min(rows.length || 1, 6),
    headerBGC: 'rgba(31, 75, 107, 0.09)',
    oddRowBGC: 'rgba(58, 47, 33, 0.035)',
    evenRowBGC: 'transparent',
    headerHeight: 36,
    columnWidth: [340, 130],
    align: ['left', 'right'],
    index: false,
    waitTime: 2600,
    carousel: 'page',
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
</script>

<template>
  <div class="dash">
    <!-- ===== 卷宗题头：总卡数是这一页唯一的主角 ===== -->
    <section class="hero rise">
      <div class="hero-left">
        <div class="eyebrow">
          {{ greeting }}，{{ auth.user?.displayName || auth.user?.username }}
        </div>
        <div class="hero-num">
          <span class="num mono">{{ s.total ?? 0 }}</span>
          <span class="unit">张卡片</span>
        </div>
        <div class="hero-sub">
          <span>{{ todayText }}</span>
          <span class="dot" />
          <span>今日待复习 {{ s.dueToday ?? 0 }} 张</span>
          <template v-if="learning.dirText">
            <span class="dot" />
            <span class="dir">{{ learning.dirText }}</span>
          </template>
          <template v-if="storeText">
            <span class="dot" />
            <span class="store">{{ storeText }}</span>
          </template>
        </div>
      </div>
      <div class="hero-right">
        <button class="go" @click="router.push({ name: 'review' })">
          开始复习
          <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
        </button>
        <button class="go ghost" @click="router.push({ name: 'path' })">今日路径</button>
      </div>
    </section>

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

    <!-- ===== 图表区 ===== -->
    <section class="grid">
      <div class="panel span-4 rise" :style="{ animationDelay: '80ms' }">
        <header class="panel-head">
          <h3>掌握度分布</h3>
          <span class="hint">按三档标记统计</span>
        </header>
        <EChart :option="masteryOption" height="252px" />
      </div>

      <div class="panel span-4 rise" :style="{ animationDelay: '130ms' }">
        <header class="panel-head">
          <h3>领域分布</h3>
          <span class="hint">卡片按知识领域统计</span>
        </header>
        <EChart :option="domainOption" height="252px" />
      </div>

      <div class="panel span-4 rise" :style="{ animationDelay: '180ms' }">
        <header class="panel-head">
          <h3>今日队列</h3>
          <span class="hint">共 {{ learning.total }} 张</span>
        </header>
        <div class="board">
          <DvScrollBoard v-if="learning.queue.length" :config="boardOption" />
          <p v-else class="empty">今天没有到期的卡片 —— 先去「卡片」页挑几张新的吧</p>
        </div>
      </div>

      <div class="panel span-7 rise" :style="{ animationDelay: '230ms' }">
        <header class="panel-head">
          <h3>科目构成</h3>
          <span class="hint">扇区半径与面积同时编码数量</span>
        </header>
        <EChart :option="subjectOption" height="288px" />
      </div>

      <div class="panel span-5 rise" :style="{ animationDelay: '280ms' }">
        <header class="panel-head">
          <h3>卡片构成</h3>
          <span class="hint">内置 / 自建</span>
        </header>
        <EChart :option="composeOption" height="64px" />
        <div class="legend-row">
          <span><i :style="{ background: INK.accent }" />内置</span>
          <span><i :style="{ background: INK.known }" />自建</span>
        </div>

        <!-- 系统状态摘要。
             放在这里是刻意的：degraded 藏在管理页里没人会去看，
             而它直接决定「我写的东西到底存到哪了」。 -->
        <div class="sys">
          <div class="sys-row">
            <span class="dim">存储后端</span>
            <span class="mono">{{ storeInfo?.store || '-' }}</span>
          </div>
          <div class="sys-row">
            <span class="dim">内置卡 / 库内</span>
            <span class="mono">
              {{ storeInfo?.builtin?.inFile ?? '-' }} / {{ storeInfo?.builtin?.inDb ?? '未同步' }}
            </span>
          </div>
          <div class="sys-row">
            <span class="dim">AI 精读</span>
            <span>{{ llmInfo?.ok ? '可用' : '未启用' }}</span>
          </div>
          <button class="link" @click="router.push({ name: 'admin-system' })">
            查看运行状态 →
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  padding: 16px 18px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
  transition:
    border-color 0.18s,
    transform 0.18s;
}
.metric:hover {
  border-color: var(--line2);
  transform: translateY(-2px);
}
.m-label {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.m-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.25;
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
 * .panel / .panel-head 用 tokens.css 里的全局类，这里只写栅格。 */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 14px;
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

.sys {
  border-top: 1px solid var(--line);
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sys-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: var(--fs-sm);
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
  .span-4,
  .span-5,
  .span-7 {
    grid-column: span 12;
  }
}
</style>
