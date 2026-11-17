<script setup>
/* 布局壳：侧栏 + 顶栏 + 内容区。
 *
 * 它要解决的问题只有三个：
 *
 * 1. **一眼知道自己在哪**。侧栏按「总览 / 学习 / 内容 / 工具 / 管理」分组，
 *    分组小标题做成卷宗的分栏线样式，比一排等价的图标好找得多。
 *
 * 2. **导航不用 el-menu**。它的样式覆盖是无底洞（选中态要穿透三层 class），
 *    而且要的东西它不提供：左侧指示条、分组小标题、待建角标。
 *    自己写几十行 CSS 比覆盖它八十行更短，也更好懂。
 *
 * 3. **字号不写死 px，走 tokens 的 --fs-***。「字体看不清」的根因通常是
 *    小字号 + 轻字重 + 过宽字距三件套，集中到一处才好调。
 *
 * 侧栏的「待建」标记从路由表 meta.ready 推出来，不另外维护清单 ——
 * 手写两份必然有一天对不上。搬完一页，改 router/index.js 的 ready 即可。
 *
 * ⚠️ 这里**不定义主题**。变量全在 tokens.css 的 :root 上，本组件只消费。
 * 早先版本按当前页切深/浅色，已随「全站统一牛皮纸」一起删除；
 * 谁要加回来，先看 router/index.js 里那段注释。
 */
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useLearningStore } from '@/stores/learning'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const learning = useLearningStore()

/** 图标用内联 SVG 的 innerHTML —— 比引一整个图标库省 200KB，
 *  而且这几个形状简单到不值得为它装依赖。viewBox 统一 0 0 24 24。
 *  线宽、圆角这些统一在 .ico 里给，这里只管形状 ——
 *  「图标后期要不要换样式」就变成改一处 CSS 的事。 */
const ICON = {
  dashboard: '<path d="M4 4h7v7H4zM13 4h7v4h-7zM13 11h7v9h-7zM4 14h7v6H4z"/>',
  path: '<path d="M4 19.5 9.5 12l4 3L20 5.5"/><path d="M15.5 5.5H20v4.5"/>',
  review:
    '<path d="M4 7h16M4 12h16M4 17h9"/><circle cx="17.5" cy="17" r="3"/><path d="M17.5 15.6v1.6l1.1.7"/>',
  cards:
    '<rect x="4" y="5.5" width="16" height="13" rx="2.2"/><path d="M4 10.5h16"/><path d="M8 14.4h5"/>',
  docs: '<path d="M6.5 3.5h7l4.5 4.5v12.5h-11.5z"/><path d="M13.5 3.5V8H18"/><path d="M9.5 12.5h5M9.5 16h3.5"/>',
  knowledge:
    '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H11v18H5.5A1.5 1.5 0 0 1 4 19.5z"/><path d="M20 4.5A1.5 1.5 0 0 0 18.5 3H13v18h5.5A1.5 1.5 0 0 0 20 19.5z"/>',
  graph:
    '<circle cx="6.5" cy="7" r="2.4"/><circle cx="18" cy="6" r="2"/><circle cx="12" cy="18" r="2.6"/><path d="M8.3 8.4 10.7 15.7M16.6 7.4 13.6 15.9M8.9 7 16 6.2"/>',
  notes:
    '<path d="M8 5.5h11M8 10.5h11M8 15.5h7"/><circle cx="4.6" cy="5.5" r="1"/><circle cx="4.6" cy="10.5" r="1"/><circle cx="4.6" cy="15.5" r="1"/>',
  generate: '<path d="M12 3.2 14.5 9.5 20.8 12l-6.3 2.5L12 20.8l-2.5-6.3L3.2 12 9.5 9.5z"/>',
  ask: '<path d="M4 5.5h16v10.5H9.5L5.2 20v-4H4z"/><path d="M8 9.2h8M8 12.4h5.5"/>',
  profile: '<circle cx="12" cy="8" r="5"/><path d="M12 16v8M4 20c0-4 3.5-6 8-6s8 2 8 6"/>',
  users:
    '<circle cx="9" cy="8" r="3.4"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><path d="M16.2 5.2a3.4 3.4 0 0 1 0 5.9M17.5 14.9c2 .7 3.5 2.6 3.5 5.1"/>',
  server:
    '<rect x="3.5" y="4" width="17" height="6" rx="1.8"/><rect x="3.5" y="14" width="17" height="6" rx="1.8"/><path d="M7 7h.01M7 17h.01"/><path d="M10.5 7h4M10.5 17h4"/>'
}

/** 导航分组。**管理那一组只对管理员显示** —— 普通学习者看到一堆自己
 *  点不开的入口，只会觉得这产品做得糙。 */
/* 分组的排法有两条原则，都是踩出来的：
 *
 * 1. **按「多久用一次」排，不按「功能像不像」排。** 复习队列排在今日路径
 *    前面 —— 每天要做的是前者，路径是有了队列之后才需要看的东西。
 *    「AI 问答 / 生成」原来埋在「工具」组第 3、4 位，而它们恰恰是这个
 *    项目跟「一个静态卡片列表」拉开差距的地方。现在独立成组、放在内容之后。
 * 2. **管理组垫底，且非管理员看不见**（admin: true）。
 */
const NAV = [
  { group: '总览', items: [{ name: 'dashboard', label: '学习驾驶舱' }] },
  {
    group: '学习',
    items: [
      // badge: 'due' —— 侧栏直接显示今天有几张卡到期，**不用点进去才知道**。
      // 数字取 /api/stats 的 dueToday（驾驶舱本来就在拉，零新增请求）。
      { name: 'review', label: '复习队列', badge: 'due' },
      { name: 'path', label: '今日路径' }
    ]
  },
  {
    group: '内容',
    items: [
      { name: 'cards', label: '卡片' },
      { name: 'docs', label: '文档与精读' },
      { name: 'knowledge', label: '知识库' }
    ]
  },
  {
    group: 'AI 助手',
    items: [
      { name: 'ask', label: 'AI 问答' },
      { name: 'generate', label: '生成' }
    ]
  },
  {
    group: '工具',
    items: [
      { name: 'graph', label: '知识图谱' },
      { name: 'notes', label: '笔记' }
    ]
  },
  {
    group: '个人',
    items: [{ name: 'profile', label: '个人中心' }]
  },
  {
    group: '管理',
    admin: true,
    items: [
      { name: 'admin-users', label: '用户管理' },
      { name: 'admin-system', label: '运行状态' }
    ]
  }
]

const visibleNav = computed(() => NAV.filter(g => !g.admin || auth.user?.role === 'admin'))

/** 到期总数（后端按全库算的口径）。
 *
 *  取 `/api/stats` 的 `dueToday` 而不是 `learning.total`：
 *  total 是**当前已加载队列**的长度，用户在别的页签筛过方向/自选清单后
 *  它会变成另一个数，拿它当「今天要复习几张」会骗人。
 *
 *  ⚠️ 这个数**会大得离谱**：`due_list` 把「从没背过」的卡也算到期，
 *  而新卡从不自动 `nextAt`，所以 400 张库里 398 张没标过 → dueToday=400。
 *  直接把它当角标显示，用户看到的就是「99+」，而复习页实际只会给
 *  dailyTarget（默认 20）张 —— **角标在吓人，而产品一次就要他学 99 张**。
 */
const dueTotal = computed(() => learning.stats?.dueToday ?? 0)

/** 角标真正该显示的数：**今天实际要学几张**，不是库里积了多少。
 *
 *  上限是 `dailyTarget`（用户自己设的每日目标，5~100，档案里存着）。
 *  这个上限本来就在复习页生效（`fetchDue({limit: dailyTarget})`），
 *  角标却没跟它对齐 —— 于是同一套系统里出现两个矛盾的「今天要做多少」：
 *  侧栏说 99+，复习页说 1/20。
 *
 *  dailyTarget 拿不到时**退回 0 而不是退回 dueTotal**：拿不到设置就干脆
 *  不显示角标，好过显示一个必然错的大数。真到那一步用户点进去也还是
 *  默认值 20。
 */
const dueTodayPlan = computed(() => {
  const target = learning.dailyTarget
  if (!target) return 0
  return Math.min(dueTotal.value, target)
})

/** 积压总数（今天学不完的那部分）。用于角标的 title 提示。 */
const dueBacklog = computed(() => Math.max(dueTotal.value - dueTodayPlan.value, 0))

/** 角标文案。**带积压时不加任何视觉噪音**（徽标位置塞不下），
 *  完整信息放 title —— 鼠标悬停能看全，不悬停也不干扰扫视。 */
const dueBadgeText = computed(() => {
  const n = dueTodayPlan.value
  return n > 99 ? '99+' : String(n)
})
const dueBadgeTitle = computed(() => {
  if (!dueTotal.value) return '今天没有到期的卡片'
  if (dueBacklog.value) {
    return (
      `今天要学 ${dueTodayPlan.value} 张（每日目标 ${learning.dailyTarget}）· ` +
      `另有 ${dueBacklog.value} 张积压，做不完会顺延到明天`
    )
  }
  return `今天要学 ${dueTodayPlan.value} 张`
})

/** 顺带在布局里补拉 stats + 每日目标：驾驶舱之外的页面往往还没拉过，
 *  没有这次补拉，角标在非驾驶舱页面上是空的（一个"只在某页有效"的角标
 *  等于没有角标）。两者都很轻，且和驾驶舱共用同一个 store，不算浪费。 */
onMounted(() => {
  if (!learning.stats) learning.fetchStats()
  learning.ensureSettings()
})

const readyNames = computed(() => {
  const root = router.options.routes.find(r => r.path === '/')
  const set = new Set()
  ;(root?.children || []).forEach(c => {
    if (c.meta && c.meta.ready) set.add(c.name)
  })
  return set
})

/** 当前页所属分组的名字，显示在顶栏标题左边。
 *  它替代的是一句「你在哪」—— 分组名比面包屑短，比什么都不放清楚。 */
const groupLabel = computed(() => {
  const g = NAV.find(x => x.items.some(i => i.name === route.name))
  return g ? g.group : ''
})

/** 顶栏右上角的档号。用今天的日期，而不是编一个流水号 ——
 *  **编出来的号看着更专业，但它是假的**，而且每天都不变，看第二眼就露。 */
const dno = computed(() => {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
})

const displayName = computed(() => auth.user?.displayName || auth.user?.username || '未登录')
/** 头像里的字：中文取姓，英文取首字母。空值给个占位免得圈里什么都没有。 */
const initial = computed(() => (displayName.value || '?').trim().charAt(0).toUpperCase())

function onLogout() {
  auth.logout()
  // ★ 业务 store 里还留着上一个人的状态，必须一起清。
  // learning 的 settingsP 一旦 resolve 就永不再取档案（每日目标 / 学习方向），
  // 而这里从前只清 auth —— 同一 SPA 会话换账号后，新用户会被套上上一个人的
  // 方向和每日目标，刷新页面才恢复。属于「换个人登录，推的还是他的内容」。
  learning.resetSettings()
  ElMessage.success('已退出登录')
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <!-- 标记：一条折线加一个终点，就是「径」的意思 -->
        <svg class="mark" viewBox="0 0 32 32" aria-hidden="true">
          <path d="M6 25 13.5 15l5 4.2L26 7" />
          <circle cx="26" cy="7" r="3.1" />
        </svg>
        <div class="brand-txt">
          <span class="brand-cn">智径</span>
          <span class="brand-en">EduPath</span>
        </div>
      </div>

      <nav class="nav">
        <div v-for="(g, gi) in visibleNav" :key="g.group" class="group">
          <div class="group-label">{{ g.group }}</div>
          <button
            v-for="(it, ii) in g.items"
            :key="it.name"
            class="item rise"
            :class="{ on: route.name === it.name }"
            :style="{ animationDelay: (gi * 4 + ii) * 34 + 60 + 'ms' }"
            @click="router.push({ name: it.name })"
          >
            <svg class="ico" viewBox="0 0 24 24" v-html="ICON[it.name]" />
            <span class="txt">{{ it.label }}</span>
            <span
              v-if="it.badge === 'due' && dueTodayPlan > 0"
              class="badge"
              :title="dueBadgeTitle"
              >{{ dueBadgeText }}</span
            >
            <span v-if="!readyNames.has(it.name)" class="soon">待建</span>
          </button>
        </div>
      </nav>

      <div class="me">
        <span class="avatar">{{ initial }}</span>
        <div class="me-txt">
          <span class="me-name">{{ displayName }}</span>
          <span class="me-role">{{ auth.user?.role === 'admin' ? '管理员' : '学习者' }}</span>
        </div>
        <button class="out" title="退出登录" @click="onLogout">
          <svg viewBox="0 0 24 24">
            <path d="M15 17l5-5-5-5" />
            <path d="M20 12H9" />
            <path d="M12 20H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6" />
          </svg>
        </button>
      </div>
    </aside>

    <div class="main">
      <header class="top">
        <div class="crumb">
          <span v-if="groupLabel" class="group-tag">{{ groupLabel }}</span>
          <h1 class="page-title">{{ route.meta.title || '' }}</h1>
          <span v-if="route.meta.note" class="note">{{ route.meta.note }}</span>
        </div>
        <div class="top-right">
          <span class="dno">{{ dno }}</span>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100%;
  background: var(--bg);
  background-image: var(--tex);
}

/* ============ 侧栏 ============ */
.side {
  width: var(--side-w);
  flex: none;
  display: flex;
  flex-direction: column;
  /* 封皮比内页深一档。做成同色的话，侧栏和内容区只能靠一根 1px 线分开，
     纸的层次就没了 */
  background: var(--bg2);
  position: relative;
}

/* 装订边：一条深线 + 一条紧贴的亮线。卷宗是装订起来的，
   两条并排才有「这里订着」的感觉；单线看过去只是隔断 */
.side::after {
  content: '';
  position: absolute;
  inset: 0 -1px 0 auto;
  width: 1px;
  background: var(--line2);
  box-shadow: 1px 0 0 rgba(255, 255, 255, 0.5);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 16px;
}
.mark {
  width: 30px;
  height: 30px;
  flex: none;
  fill: none;
  stroke: var(--ac);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.brand-txt {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
/* 品牌名用宋体 + 拉开字距。这是全站唯一允许大字距的地方 ——
   只有两个字，不会糊 */
.brand-cn {
  font-family: var(--font-title);
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 3px;
  color: var(--tx);
}
.brand-en {
  font-size: var(--fs-xs);
  letter-spacing: 1.6px;
  color: var(--dim);
  text-transform: uppercase;
}

.nav {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px 12px;
}
.group + .group {
  margin-top: 16px;
}
/* 分组小标题：宋体 + 一条拉到头的细线，就是卷宗的分栏。
   比一个灰色加粗小字更能分隔区域，也比画整个框省地方 */
.group-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-title);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--dim);
  padding: 0 4px 8px;
}
.group-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line2);
}

.item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px 10px 12px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  /* 导航不是正文，用 500 就够压住；中文 400 在浅底上会明显发虚 */
  color: var(--mu);
  font-size: var(--fs-md);
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  position: relative;
  transition:
    background 0.18s,
    color 0.18s,
    transform 0.18s;
}

/* 左侧指示条：默认收成看不见，选中时长成一根亮条。
   比整块背景变色更克制，也不会把文字衬得发灰。 */
.item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 2px;
  height: 0;
  border-radius: 2px;
  background: var(--ac);
  transform: translateY(-50%);
  transition: height 0.22s cubic-bezier(0.22, 0.7, 0.28, 1);
}

.item:hover {
  background: var(--panel);
  color: var(--tx);
  transform: translateX(2px);
}
.item.on {
  background: var(--panel);
  color: var(--ac);
  font-weight: 600;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.item.on::before {
  height: 18px;
}

.ico {
  width: 18px;
  height: 18px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.85;
}
.item.on .ico {
  opacity: 1;
}

.txt {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 待建角标：虚线小胶囊。用虚线是因为它表达「还没成型」，
   实线边框会让人以为是可点的按钮 */
.soon {
  flex: none;
  font-size: var(--fs-xs);
  line-height: 1;
  padding: 3px 6px;
  border-radius: 4px;
  color: var(--dim);
  border: 1px dashed var(--line2);
}

/* 今日待复习角标。用实心靛蓝而不用虚线描边（.soon 那个）：
 * 「待建」是状态说明，不该吸引注意；「今天有 12 张要复习」是**待办**，
 * 是整个侧栏里唯一需要被余光扫到的东西，所以给它实心 + 白字。 */
.badge {
  flex: none;
  min-width: 20px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--ac);
  color: #fdfaf3;
  font-size: var(--fs-xs);
  font-weight: 600;
  line-height: 18px;
  text-align: center;
  font-variant-numeric: tabular-nums; /* 数字等宽，跳动时不抖 */
}

.me {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 12px 14px;
  padding: 11px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--panel);
}
.avatar {
  width: 32px;
  height: 32px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-family: var(--font-title);
  font-size: var(--fs-lg);
  font-weight: 700;
  color: #fdfaf3;
  background: var(--ac);
}
.me-txt {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}
.me-name {
  font-size: var(--fs-sm);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.me-role {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.out {
  flex: none;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--mu);
  cursor: pointer;
  transition:
    background 0.16s,
    color 0.16s;
}
.out:hover {
  background: var(--panel2);
  color: var(--red);
}
.out svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* ============ 顶栏 ============ */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.top {
  min-height: var(--top-h);
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 24px;
  background: var(--panel);
  /* 页眉用双线收口（一根 real 边框 + 一根 box-shadow 假线），
     跟卷宗的页眉一道杠一个道理。单线在纸色上太轻，撑不住整页 */
  border-bottom: 1px solid var(--line2);
  box-shadow: 0 1px 0 var(--line);
}
.crumb {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
  flex-wrap: wrap;
}

/* 分组标签：朱砂小框，标这一页在全站里的归属。
   这是页面上唯一的印章式元素，别再多加第二个 */
.group-tag {
  flex: none;
  font-family: var(--font-title);
  font-size: var(--fs-xs);
  font-weight: 700;
  letter-spacing: 2px;
  padding: 2px 8px;
  border: 1px solid var(--red);
  border-radius: 4px;
  color: var(--red);
  opacity: 0.9;
}

.page-title {
  font-size: var(--fs-xl);
  font-weight: 700;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 一句话说明这页是干什么的。放在标题右边而不是副标题位置，
   是为了让 note 长度变化时标题不上下跳 */
.note {
  font-size: var(--fs-sm);
  color: var(--dim);
  border-left: 2px solid var(--line2);
  padding-left: 10px;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 26px 28px 40px;
}

/* ============ 窄屏 ============
 * 侧栏横过来贴顶。窄屏没有空间给竖向侧栏 ——
 * 留着它，内容区就只剩很窄一条。 */
@media (max-width: 980px) {
  .shell {
    flex-direction: column;
  }
  .side {
    width: 100%;
    flex-direction: row;
    align-items: center;
    border-bottom: 1px solid var(--line2);
    padding: 0 8px;
  }
  .side::after {
    display: none;
  }
  .brand {
    padding: 10px 12px 10px 6px;
  }
  .brand-txt {
    display: none;
  }
  .nav {
    display: flex;
    gap: 4px;
    padding: 6px 0;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .group {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .group + .group {
    margin-top: 0;
  }
  .group-label,
  .soon {
    display: none;
  }
  .item {
    width: auto;
    white-space: nowrap;
    padding: 7px 11px;
  }
  .item::before {
    display: none;
  }
  .me {
    margin: 0 8px 0 4px;
    padding: 6px;
  }
  .me-txt {
    display: none;
  }
  .top {
    padding: 10px 14px;
  }
  .note {
    display: none;
  }
  .content {
    padding: 16px 14px 30px;
  }
}
</style>
