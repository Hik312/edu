<script setup>
/* 岗位知识地图 —— 今日路径页的上半屏。
 *
 * 选岗位（或自己勾科目）→ 后端 /api/plan 拿技能组对账 → 缺哪条考考点说哪条。
 * 选中的岗位写进长期档案（L3，服务端 profiles.json）+ localStorage，
 * 这样问答页也认得「你在准备什么岗位」。
 *
 * 从 PathView 拆出来是因为它和「今日队列」是两件事：地图回答「我该学什么」，
 * 队列回答「今天先学哪个」，同页只是省一次跳转，代码上不该搅在一起。
 */
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { levelColor } from '@/config/theme'
import { getRoles, getPlan, catalog } from '@/api/system'
import { getProfile, putProfile } from '@/api/agent'

const router = useRouter()

const roles = ref([])
const roleOpts = ref([]) // 自定义模式的科目选项 [{value,label}]
const mapRole = ref('') // 当前选中的岗位 id
const customOn = ref(false) // true = 不用预置岗位，自己勾科目
const picked = ref([]) // 自定义勾选的科目 id
const plan = ref(null)
const mapLoading = ref(false)
const savedRole = ref('') // 服务端档案里的岗位名（用来显示"已存"）

/** 自定义勾选的科目也记下来 —— 勾了十个科目然后刷新就没了，是最直接的劝退。
 *  勾选状态和岗位选择分开存：岗位那份在「存进我的档案」时才写（要进 L3）。 */
function savePathSel() {
  try {
    localStorage.setItem(
      'edu.pathSubs',
      JSON.stringify({ customOn: customOn.value, picked: picked.value })
    )
  } catch {
    /* 忽略 */
  }
}
watch([customOn, picked], savePathSel, { deep: true })

async function loadMap() {
  try {
    const [r, c] = await Promise.all([getRoles(), catalog()])
    roles.value = r.roles || []
    roleOpts.value = flatSubjects(c)
  } catch {
    ElMessage.error('岗位列表加载失败')
  }
  try {
    // getProfile() 已返回档案本身（解包在 api/agent.js）
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

/** 上次选的岗位记住（localStorage，不占后端）；没记过就默认第一个。
 *  自定义勾选优先恢复 —— 用户上次明确勾过科目，就不该被塞回预置岗位。 */
function restoreLast() {
  try {
    const s = JSON.parse(localStorage.getItem('edu.pathSubs') || 'null')
    if (s && s.customOn && Array.isArray(s.picked) && s.picked.length) {
      customOn.value = true
      picked.value = s.picked
      loadPlan()
      return
    }
  } catch {
    /* 坏数据当作没存过 */
  }
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

/** 取知识地图。**后发先回的旧响应必须丢掉**。
 *
 * ★ 和 stores/learning.js 的 dueSeq 同一个道理：loadPlan 有 4 个触发点
 *   （切岗位 / 切自定义 / 点科目 / 恢复上次），每个都是「改一个选中态就重取」，
 *   用户连点三个岗位就会发出三个请求。网络不保证返回顺序，
 *   慢的那次晚回来就赢 —— 于是**高亮的是岗位 C，地图画的是岗位 A**。
 *   mapLoading 只挡 UI 不挡竞态，防抖也只缩小窗口、不保证顺序。
 */
let planSeq = 0

async function loadPlan() {
  if (customOn.value && !picked.value.length) {
    plan.value = null
    return
  }
  const seq = ++planSeq
  mapLoading.value = true
  try {
    const r = customOn.value
      ? await getPlan({ subjects: picked.value.join(',') })
      : await getPlan({ role: mapRole.value })
    if (seq !== planSeq) return          // 已有更新的请求，丢弃这份旧结果
    plan.value = r.plan || null
  } catch (e) {
    if (seq !== planSeq) return
    plan.value = null
    ElMessage.error('知识点地图算不出来：' + (e.message || e))
  } finally {
    if (seq === planSeq) mapLoading.value = false
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

onMounted(loadMap)
</script>

<template>
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
</template>

<style scoped>
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
</style>
