<script setup>
/* 今日路径 —— 上半屏是「岗位知识地图」，下半屏是「今日队列」。

 上：选岗位（或自己勾科目）→ 后端 /api/plan 拿技能组对账 → 缺哪条考考点说哪条。
     选中的岗位写进长期档案（L3，服务端 profiles.json）+ localStorage，
     这样问答页也认得「你在准备什么岗位」。
 下：今日队列保持原样 —— 后端 /api/review/due 已经排好序，本页只分段 + 给理由。

 两块为什么放在一页：地图回答「我该学什么」，队列回答「今天先学哪个」。
 拆成两页的话，选完岗位还得自己跳过去找队列。
*/
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useLearningStore } from '@/stores/learning'
import { levelColor } from '@/config/theme'
import { getRoles, getPlan, catalog } from '@/api/system'
import { getProfile, putProfile } from '@/api/agent'

const router = useRouter()
const learning = useLearningStore()

onMounted(() => {
  // all=1：今天没到期也要能看到内容，否则新用户进来是空的，
  // 会以为这一页坏了。真正的「到期才复习」约束在复习页体现
  learning.fetchDue({ all: '1' })
  learning.fetchStats()
  loadMap()
})

// ---------------------------------------------------------------------------
// 上：岗位知识地图
// ---------------------------------------------------------------------------
const roles = ref([])
const roleOpts = ref([]) // 自定义模式的科目选项 [{value,label}]
const mapRole = ref('') // 当前选中的岗位 id
const customOn = ref(false) // true = 不用预置岗位，自己勾科目
const picked = ref([]) // 自定义勾选的科目 id
const plan = ref(null)
const mapLoading = ref(false)
const savedRole = ref('') // 服务端档案里的岗位名（用来显示"已存"）

async function loadMap() {
  try {
    const [r, c] = await Promise.all([getRoles(), catalog()])
    roles.value = r.roles || []
    roleOpts.value = flatSubjects(c)
  } catch {
    ElMessage.error('岗位列表加载失败')
  }
  try {
    const p = await getProfile()
    savedRole.value = (p && p.role) || ''
  } catch {
    /* 没档案就空着 */
  }
  restoreLast()
}

/** catalog 的 category → subject 摊平成下拉选项（自定义模式用）。 */
function flatSubjects(c) {
  const flat = []
  for (const cat of c.catalog || []) {
    for (const s of cat.subjects || []) {
      flat.push({ value: s.id, label: (cat.name || '') + ' · ' + (s.name || s.id) })
    }
  }
  return flat
}

/** 上次选的岗位记住（localStorage，不占后端）；没记过就默认第一个。 */
function restoreLast() {
  const last = localStorage.getItem('edu.role') || ''
  if (last && roles.value.some(x => x.id === last)) {
    mapRole.value = last
  } else if (roles.value.length) {
    mapRole.value = roles.value[0].id
  }
  if (mapRole.value) loadPlan()
}

function pickRole(id) {
  mapRole.value = id
  customOn.value = false
  loadPlan()
}

function toggleCustom() {
  customOn.value = !customOn.value
  if (customOn.value) loadPlan()
}

function toggleSubject(sid) {
  const i = picked.value.indexOf(sid)
  if (i >= 0) picked.value.splice(i, 1)
  else picked.value.push(sid)
  loadPlan()
}

async function loadPlan() {
  if (customOn.value && !picked.value.length) {
    plan.value = null
    return
  }
  mapLoading.value = true
  try {
    const r = customOn.value
      ? await getPlan({ subjects: picked.value.join(',') })
      : await getPlan({ role: mapRole.value })
    plan.value = r.plan || null
  } catch (e) {
    plan.value = null
    ElMessage.error('知识点地图算不出来：' + (e.message || e))
  } finally {
    mapLoading.value = false
  }
}

/** 存进长期档案（L3）—— 问答页会读它，「薄弱」用当前标过「不会」的卡。 */
async function saveRole() {
  if (!plan.value) return
  try {
    const weak = (plan.value.skills || []).flatMap(g =>
      (g.cards || []).filter(c => c.level === 1).map(c => c.id)
    )
    await putProfile({ role: plan.value.name, weak })
    savedRole.value = plan.value.name
    localStorage.setItem('edu.role', customOn.value ? '' : mapRole.value)
    ElMessage.success('已存进档案，AI 问答会带着这个岗位')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.message || e))
  }
}

function openCard(cid) {
  router.push({ path: '/cards', query: { open: cid } })
}

/** 三段的定义。order 用来保证段顺序稳定 ——
 *  依赖对象遍历顺序的地方迟早会乱（不同后端的返回顺序可能不同）。 */
const SEGMENTS = [
  {
    key: 'fix',
    step: 1,
    label: '补牢',
    levels: [1],
    color: 'weak',
    why: '标记了「不会」的先过一遍 —— 这些是最容易在面试里当场卡住的地方'
  },
  {
    key: 'firm',
    step: 2,
    label: '巩固',
    levels: [2],
    color: 'fuzzy',
    why: '「模糊」说明骨架有了、细节没定，再看一次通常就能钉死'
  },
  {
    key: 'push',
    step: 3,
    label: '推进',
    levels: [0],
    color: 'accent',
    why: '剩下的新内容。可以慢慢推，但别一次开太多 —— 半途而废比慢更贵'
  }
]

const segments = computed(() =>
  SEGMENTS.map(s => ({
    ...s,
    items: learning.queue.filter(c => s.levels.includes(c.level || 0))
  })).filter(s => s.items.length)
)

/** 已掌握的单独拎出来展示成「今天不用管」，而不是混在路径里。
 *  放进路径会让用户觉得「还得再看一遍」，跟事实相反。 */
const doneCount = computed(() => learning.stats?.known ?? 0)

const total = computed(() => learning.queue.length)

/** 今天完成了多少（队列里已经标过、且不是"不会"的）。 */
const finished = computed(() => learning.queue.filter(c => [2, 3].includes(c.level)).length)

const percent = computed(() => (total.value ? Math.round((finished.value / total.value) * 100) : 0))
</script>

<template>
  <div class="path stack" v-loading="learning.loading">
    <!-- ===== 岗位知识地图 ===== -->
    <section class="panel map" v-loading="mapLoading">
      <header class="panel-head">
        <h3>岗位知识地图</h3>
        <span class="hint">先定方向，再排今天</span>
      </header>

      <div class="roles">
        <button
          v-for="r in roles"
          :key="r.id"
          class="role"
          :class="{ on: !customOn && mapRole === r.id }"
          :title="r.desc"
          @click="pickRole(r.id)"
        >
          {{ r.name }}
        </button>
        <button class="role custom" :class="{ on: customOn }" @click="toggleCustom">
          自定义科目
        </button>
        <button v-if="plan" class="save" @click="saveRole">
          {{ savedRole === plan.name ? '已存进档案' : '存进我的档案' }}
        </button>
      </div>

      <div v-if="customOn" class="subs">
        <button
          v-for="s in roleOpts"
          :key="s.value"
          class="sub"
          :class="{ on: picked.includes(s.value) }"
          @click="toggleSubject(s.value)"
        >
          {{ s.label }}
        </button>
        <span v-if="!picked.length" class="sub-hint">勾几个科目，右侧会立刻算覆盖</span>
      </div>

      <template v-if="plan">
        <div class="sum">
          <div class="sum-top">
            <span class="sum-num mono">{{ plan.summary.percent }}%</span>
            <span class="sum-lb"
              >技能点覆盖 · {{ plan.summary.covered }}/{{ plan.summary.keywords }}</span
            >
            <span class="sum-lb dim"
              >库内 {{ plan.summary.cards }} 张卡 · 已掌握 {{ plan.summary.mastered }}</span
            >
          </div>
          <div class="sum-bar"><i :style="{ width: plan.summary.percent + '%' }" /></div>
        </div>

        <div v-for="g in plan.skills" :key="g.subject" class="grp">
          <div class="grp-head">
            <b>{{ g.name }}</b>
            <span class="mono">{{ g.mastered }}/{{ g.count }} 掌握</span>
          </div>
          <div class="kws">
            <span v-for="k in g.covered" :key="'c' + k" class="kw ok">{{ k }}</span>
            <span
              v-for="k in g.missing"
              :key="'m' + k"
              class="kw miss"
              title="库里还没有这块的卡 —— 这就是缺口"
              >{{ k }} 缺</span
            >
          </div>
          <div class="cards">
            <button
              v-for="c in g.cards"
              :key="c.id"
              class="ccard"
              :class="{ weak: c.level === 1, done: c.level === 3 }"
              @click="openCard(c.id)"
            >
              <span class="cdot" :style="{ background: levelColor(c.level || 0) }" />
              <span class="ct">{{ c.title }}</span>
            </button>
          </div>
        </div>
      </template>
      <p v-else-if="!mapLoading" class="map-empty">
        选一个岗位看缺口；或者点「自定义科目」自己勾组合。
      </p>
    </section>

    <!-- ===== 概览 ===== -->
    <section class="panel hero">
      <div class="hero-txt">
        <div class="eyebrow">今日路径</div>
        <div class="hero-num">
          <span class="num mono">{{ percent }}%</span>
          <span class="unit">已完成 {{ finished }} / {{ total }} 张</span>
        </div>
        <p class="hero-sub">
          顺序不是随机的：先看没掌握的，再看模糊的，最后才是新的。
          <template v-if="doneCount">另有 {{ doneCount }} 张已掌握，今天不用管。</template>
        </p>
      </div>
      <div class="hero-bar">
        <i :style="{ width: percent + '%' }" />
      </div>
      <div class="hero-act">
        <button class="btn btn-primary" @click="router.push({ name: 'review' })">
          按顺序复习
          <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
        </button>
      </div>
    </section>

    <!-- ===== 分段路径 ===== -->
    <section v-for="seg in segments" :key="seg.key" class="panel seg">
      <header class="panel-head">
        <h3>
          <span class="step mono">{{ seg.step }}</span>
          {{ seg.label }}
          <span class="count">{{ seg.items.length }} 张</span>
        </h3>
        <span class="hint">{{ seg.key === 'fix' ? '优先级最高' : '' }}</span>
      </header>
      <p class="why">{{ seg.why }}</p>

      <ol class="steps">
        <li v-for="(c, i) in seg.items" :key="c.id" class="step-row">
          <span class="dot" :style="{ borderColor: levelColor(c.level || 0) }" />
          <div class="s-body">
            <span class="s-idx mono">{{ String(i + 1).padStart(2, '0') }}</span>
            <div class="s-main">
              <span class="s-title">{{ c.title }}</span>
              <span class="s-line">{{ c.oneLine }}</span>
            </div>
            <span class="chip">{{ c.domain }}</span>
          </div>
        </li>
      </ol>
    </section>

    <p v-if="!learning.loading && !segments.length" class="empty">
      <span class="big">今天没有要安排的卡片</span>
      去「卡片」页给几张卡标一下掌握度，路径会自动从这里算出来
    </p>
  </div>
</template>

<style scoped>
/* ===== 岗位知识地图 ===== */
.roles {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.role {
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--mu);
  border-radius: 999px;
  padding: 6px 13px;
  font-size: var(--fs-sm);
  cursor: pointer;
  transition:
    border-color 0.16s,
    color 0.16s,
    background 0.16s;
}
.role:hover {
  border-color: var(--ac);
  color: var(--ac);
}
.role.on {
  background: var(--ac);
  border-color: var(--ac);
  color: #fdfaf3;
}
.role.custom {
  border-style: dashed;
}
.save {
  margin-left: auto;
  border: 1px solid var(--ac);
  background: transparent;
  color: var(--ac);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: var(--fs-sm);
  cursor: pointer;
  transition: background 0.16s;
}
.save:hover {
  background: var(--ac-glow);
}
.subs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px;
  margin-bottom: 12px;
  border: 1px dashed var(--line2);
  border-radius: var(--radius-sm);
}
.sub {
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--mu);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.sub.on {
  background: var(--ac-dim, var(--ac));
  border-color: var(--ac);
  color: var(--ac);
}
.sub-hint {
  font-size: var(--fs-xs);
  color: var(--dim);
  align-self: center;
}
.sum {
  margin-bottom: 14px;
}
.sum-top {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.sum-num {
  font-size: 30px;
  font-weight: 700;
  color: var(--ac);
  line-height: 1;
}
.sum-lb {
  font-size: var(--fs-sm);
  color: var(--tx);
}
.sum-lb.dim {
  color: var(--dim);
}
.sum-bar {
  height: 7px;
  border-radius: 4px;
  background: var(--line);
  overflow: hidden;
}
.sum-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--ac-dim), var(--ac));
  transition: width 0.5s cubic-bezier(0.22, 0.7, 0.28, 1);
}
.grp {
  padding: 12px 0;
  border-top: 1px solid var(--line2);
}
.grp-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}
.grp-head b {
  font-size: var(--fs-md);
  font-weight: 600;
}
.grp-head .mono {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.kws {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.kw {
  font-size: var(--fs-xs);
  border-radius: 999px;
  padding: 3px 9px;
}
.kw.ok {
  background: var(--ac-glow);
  color: var(--ac);
}
.kw.miss {
  background: transparent;
  border: 1px dashed #c0603f;
  color: #c0603f;
}
.cards {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ccard {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 100%;
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  font-size: var(--fs-sm);
  color: var(--tx);
  cursor: pointer;
  transition: border-color 0.16s;
}
.ccard:hover {
  border-color: var(--ac);
}
.ccard.done {
  color: var(--dim);
}
.ccard.done .ct {
  text-decoration: line-through;
  text-decoration-color: var(--line2);
}
.ccard.weak {
  border-color: #d08a5c;
}
.cdot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.ct {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.map-empty {
  font-size: var(--fs-sm);
  color: var(--dim);
  padding: 8px 0 4px;
}

.hero {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  background-image: radial-gradient(760px 240px at 8% -30%, var(--ac-glow), transparent 62%);
}
.hero-txt {
  flex: 1;
  min-width: 240px;
}
.hero-num {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 4px 0 6px;
}
.num {
  font-size: 44px;
  font-weight: 700;
  line-height: 1;
  color: var(--ac);
}
.unit {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.hero-sub {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.7;
}
.hero-bar {
  flex: 1;
  min-width: 180px;
  height: 7px;
  border-radius: 4px;
  background: var(--line);
  overflow: hidden;
}
.hero-bar i {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--ac-dim), var(--ac));
  transition: width 0.6s cubic-bezier(0.22, 0.7, 0.28, 1);
}
.hero-act {
  flex: none;
}

.seg .step {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  margin-right: 8px;
  border-radius: 50%;
  background: var(--ac-glow);
  color: var(--ac);
  font-size: var(--fs-xs);
  font-weight: 700;
  vertical-align: 2px;
}
.count {
  margin-left: 8px;
  font-size: var(--fs-xs);
  font-weight: 400;
  color: var(--dim);
}
.why {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.75;
  margin-bottom: 12px;
  padding-left: 34px;
  border-left: 2px solid var(--line);
}

.steps {
  list-style: none;
  display: flex;
  flex-direction: column;
}
.step-row {
  display: flex;
  gap: 12px;
  position: relative;
  padding: 0 0 14px 0;
}
/* 竖线：把同一段里的步骤串起来。
   最后一项用 :last-child 断掉，否则会拖出一根悬空的尾巴 */
.step-row::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 16px;
  bottom: -2px;
  width: 1px;
  background: var(--line2);
}
.step-row:last-child::before {
  display: none;
}
.step-row:last-child {
  padding-bottom: 0;
}
.dot {
  flex: none;
  width: 9px;
  height: 9px;
  margin-top: 7px;
  border-radius: 50%;
  border: 2px solid var(--ac);
  background: var(--panel);
  position: relative;
  z-index: 1;
}
.s-body {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.s-idx {
  flex: none;
  font-size: var(--fs-xs);
  color: var(--dim);
}
.s-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.s-title {
  font-size: var(--fs-md);
  font-weight: 500;
}
.s-line {
  font-size: var(--fs-sm);
  color: var(--mu);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 860px) {
  .hero-bar {
    order: 3;
    width: 100%;
  }
  .s-body {
    flex-wrap: wrap;
  }
  .s-line {
    white-space: normal;
  }
}
</style>
