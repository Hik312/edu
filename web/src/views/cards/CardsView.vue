<script setup>
/* 卡片页 —— 学习区的门面，也是旧版最核心的一页。
 *
 * 三个交互决定：
 *
 * 1. **搜索防抖 320ms**。每敲一个字母就发一次请求，在「Java」四个字母上
 *    会打四次，返回顺序还不保证 —— 最后显示的可能是「J」的结果。
 * 2. **筛选条件存在 store 里**，不放在本组件。这样翻到第 3 页点进一张卡，
 *    按返回回来还在原位（用户最基本的体面）。
 * 3. **详情另开抽屉，列表不卸载**。这样关掉抽屉时滚动位置、筛选、
 *    甚至加载状态全都在，不用重新拉一遍。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCardsStore } from '@/stores/cards'
import { useLearningStore } from '@/stores/learning'
import { levelLabel } from '@/api/learning'
import { getPlan } from '@/api/system'
import CardItem from '@/components/CardItem.vue'
import CardBody from '@/components/CardBody.vue'
import LevelPicker from '@/components/LevelPicker.vue'

const cards = useCardsStore()
const learning = useLearningStore()
const route = useRoute()

const drawer = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const saving = ref(false)

/** 按岗位筛选：从 PathView 存的岗位 id 反查它的卡 id 集合，客户端过滤。
 *  放客户端而不是多发几个 /cards?subject= 请求：岗位就 3-4 个科目，
 *  分四次请求换一次「筛得准」不划算；卡片列表本来就整页拉回来了。 */
const roleIds = ref(null) // Set<string>，null = 没开岗位筛选
const roleName = ref('')
const shown = computed(() =>
  roleIds.value ? cards.list.filter(c => roleIds.value.has(c.id)) : cards.list
)

/** 分类 chips：全部 + catalog 里的每个一级分类。 */
const cats = computed(() => [{ id: '', name: '全部' }, ...cards.catalog])

/** 当前分类下的二级科目。没选分类时不给选科目 —— 跨分类的科目名会重。 */
const subs = computed(() => {
  if (!cards.filters.category) return []
  const hit = cards.catalog.find(c => c.id === cards.filters.category)
  return hit ? hit.subjects || [] : []
})

/** 卡片组（文件夹）选项：文档转出来的卡带 deck/deckId，攒成 chips。
 *  只在**没开组筛选**时刷新：开了之后列表只剩这一组的卡，
 *  再刷新选项会把其它组挤没，就切不回去了。 */
const deckOpts = ref([])
watch(
  () => cards.list,
  list => {
    if (cards.filters.deckId) return
    const m = new Map()
    for (const c of list) if (c.deckId && c.deck) m.set(c.deckId, c.deck)
    deckOpts.value = [...m].map(([id, name]) => ({ id, name }))
  }
)

function pickDeck(id) {
  cards.setFilter('deckId', id)
  cards.fetchList()
}

const levelOf = computed(() => (detail.value ? (detail.value.level ?? 0) : 0))

/** 上一张 / 下一张：按**当前显示的列表**走，翻回去还在原来的位置。 */
const stepIdx = computed(() =>
  detail.value ? shown.value.findIndex(c => c.id === detail.value.id) : -1
)

async function loadRoleFilter() {
  const rid = localStorage.getItem('edu.role') || ''
  if (!rid) return
  try {
    const r = await getPlan({ role: rid })
    const plan = r.plan || {}
    roleName.value = plan.name || ''
    roleIds.value = new Set((plan.skills || []).flatMap(g => (g.cards || []).map(c => c.id)))
  } catch {
    /* 拿不到岗位就当没开筛选 */
  }
}

onMounted(async () => {
  await Promise.all([cards.fetchCatalog(), cards.fetchList(), learning.fetchStats()])
  loadRoleFilter()
  // ?open=xxx：从路径页 / 问答页点引用跳过来时直接开详情
  const open = route.query.open
  if (open) openCard({ id: open })
})

// 连续点两个 ?open 的链接时（抽屉已开、路由又变）也要跟着换卡
watch(
  () => route.query.open,
  v => {
    if (v) openCard({ id: v })
  }
)

/** 搜索防抖。敲字时不发请求，停手 320ms 才发。 */
let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => cards.fetchList(), 320)
}
onUnmounted(() => clearTimeout(searchTimer))

function pickCat(id) {
  cards.setFilter('category', id)
  cards.fetchList()
}

function pickSub(id) {
  // 再点一次同一个科目就取消，省得用户找不到「取消筛选」的按钮
  cards.setFilter('subject', cards.filters.subject === id ? '' : id)
  cards.fetchList()
}

async function openCard(card) {
  drawer.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await cards.fetchDetail(card.id)
    syncOpen(card.id)
  } finally {
    detailLoading.value = false
  }
}

/** 打开关联卡：换一张卡继续看，抽屉不关。
 *  不关是刻意的 —— 顺着前置关系往下走时，反复开关抽屉很打断思路。 */
async function openRelated(id) {
  detailLoading.value = true
  try {
    detail.value = await cards.fetchDetail(id)
  } finally {
    detailLoading.value = false
  }
}

/** 上一张 / 下一张。到头就停在原地，不做循环 —— 循环会让人失去「读到哪了」。 */
async function step(dir) {
  if (stepIdx.value < 0) return
  const next = shown.value[stepIdx.value + dir]
  if (!next) return
  await openRelated(next.id)
  syncOpen(next.id)
}

/** 换卡时把 ?open= 同步到地址栏：复制链接、F5 刷新都还停在这张卡上。
 *  只用 replaceState 改地址，不动路由对象 —— 动路由会触发上面那个 watch，转一圈回来。 */
function syncOpen(id) {
  history.replaceState(null, '', '/cards?open=' + encodeURIComponent(id))
}

/** 关掉抽屉就把 ?open= 摘掉 —— 否则刷新又会把抽屉弹开。 */
function onDrawerClose() {
  detail.value = null
  history.replaceState(null, '', '/cards')
}

function toggleRole() {
  if (roleIds.value) roleIds.value = null
  else loadRoleFilter()
}

async function mark(level) {
  if (!detail.value) return
  saving.value = true
  try {
    await learning.mark(detail.value.id, level)
    detail.value.level = level
  } finally {
    saving.value = false
  }
}

/* 下面两个清筛选的动作写成方法，不在模板里写 `a = ''; b()` ——
 * Vue 的模板表达式只收**单个**表达式，分号语句序列编译不过。
 * （lint 的自动换行会把这个错误变得特别明显：一换行就直接语法报错。） */

/** 只清搜索词。跟 clearAll 分开：多数时候用户想回到「本分类的全部卡」，
 *  而不是把刚选的科目也一起丢掉。 */
function clearSearch() {
  cards.filters.q = ''
  cards.fetchList()
}

/** 清掉全部筛选条件。 */
function clearAll() {
  cards.resetFilter()
  cards.fetchList()
}
</script>

<template>
  <div class="cards-page">
    <!-- ===== 工具栏 ===== -->
    <div class="bar rise">
      <label class="search">
        <svg viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="6.4" />
          <path d="m16 16 4.5 4.5" />
        </svg>
        <input
          v-model="cards.filters.q"
          placeholder="搜标题、类比、原理…（空格分隔要全部命中）"
          @input="onSearchInput"
        />
        <button v-if="cards.filters.q" class="clear" @click="clearSearch">×</button>
      </label>

      <div class="cats">
        <button
          v-for="c in cats"
          :key="c.id"
          class="cat"
          :class="{ on: cards.filters.category === c.id }"
          @click="pickCat(c.id)"
        >
          {{ c.name }}
        </button>
        <button
          v-if="roleName"
          class="cat rolef"
          :class="{ on: !!roleIds }"
          title="只显示当前目标岗位覆盖到的卡"
          @click="toggleRole"
        >
          岗位 · {{ roleName }}
        </button>
      </div>
    </div>

    <!-- 子科目只在选了分类后出现 -->
    <div v-if="subs.length" class="subs rise">
      <button
        v-for="s in subs"
        :key="s.id"
        class="sub"
        :class="{ on: cards.filters.subject === s.id }"
        @click="pickSub(s.id)"
      >
        {{ s.name }}
      </button>
    </div>

    <!-- 卡片组（文件夹）：只有文档转出来的卡才有组 -->
    <div v-if="deckOpts.length" class="subs rise">
      <span class="deck-lb">卡片组</span>
      <button class="sub" :class="{ on: !cards.filters.deckId }" @click="pickDeck('')">全部</button>
      <button
        v-for="d in deckOpts"
        :key="d.id"
        class="sub"
        :class="{ on: cards.filters.deckId === d.id }"
        :title="`只看《${d.name}》里的卡`"
        @click="pickDeck(d.id)"
      >
        {{ d.name }}
      </button>
    </div>

    <div class="count">
      <span v-if="cards.loading">加载中…</span>
      <template v-else>
        共 <b>{{ shown.length }}</b> 张
        <span v-if="roleIds" class="resetting" @click="roleIds = null">· 已按岗位筛选</span>
        <span v-if="cards.hasFilter" class="resetting" @click="clearAll">· 清除筛选</span>
      </template>
    </div>

    <!-- ===== 列表 ===== -->
    <div v-if="shown.length" class="grid">
      <CardItem
        v-for="(c, i) in shown"
        :key="c.id"
        :card="c"
        class="rise"
        :style="{ animationDelay: Math.min(i, 9) * 40 + 'ms' }"
        @open="openCard"
      />
    </div>
    <div v-else-if="!cards.loading" class="empty">
      <p v-if="cards.hasFilter || roleIds">没有匹配的卡。换个词，或者清除筛选。</p>
      <p v-else>还没有卡片。</p>
    </div>

    <!-- ===== 详情抽屉 ===== -->
    <el-drawer
      v-model="drawer"
      size="620px"
      :with-header="false"
      class="card-drawer"
      @closed="onDrawerClose"
    >
      <div v-if="detailLoading" class="d-loading">读取中…</div>

      <article v-else-if="detail" class="d">
        <header class="d-head">
          <div class="d-path">
            <span v-for="(p, i) in detail.topicPath || []" :key="i">{{ p }}</span>
          </div>
          <h2>{{ detail.title }}</h2>
          <div class="d-meta">
            <span class="d-domain">{{ detail.domain }}</span>
            <span class="d-level">当前：{{ levelLabel(levelOf) }}</span>
            <span class="d-nav">
              <button class="nb" :disabled="stepIdx <= 0" @click="step(-1)">← 上一张</button>
              <span class="nb-n mono">{{ stepIdx + 1 }} / {{ shown.length }}</span>
              <button
                class="nb"
                :disabled="stepIdx < 0 || stepIdx >= shown.length - 1"
                @click="step(1)"
              >
                下一张 →
              </button>
            </span>
          </div>
        </header>

        <CardBody :card="detail" @open-related="openRelated" />

        <footer class="d-foot">
          <span class="d-foot-label">这张卡会了吗？</span>
          <LevelPicker :model-value="levelOf" :loading="saving" @pick="mark" />
        </footer>
      </article>
    </el-drawer>
  </div>
</template>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.search {
  flex: 1;
  min-width: 260px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 13px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  box-shadow: var(--shadow);
  transition: border-color 0.18s;
}
.search:focus-within {
  border-color: var(--ac-dim);
}
.search svg {
  width: 16px;
  height: 16px;
  flex: none;
  fill: none;
  stroke: var(--dim);
  stroke-width: 1.8;
  stroke-linecap: round;
}
.search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--tx);
  font-family: inherit;
  font-size: 14.5px;
}
.search input::placeholder {
  color: var(--dim);
}
.clear {
  flex: none;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  background: var(--line);
  color: var(--mu);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
}

.cats {
  display: flex;
  gap: 6px;
}
.cat {
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--panel);
  color: var(--mu);
  font-size: 14px;
  cursor: pointer;
  transition:
    color 0.16s,
    border-color 0.16s,
    background 0.16s;
}
.cat:hover {
  color: var(--tx);
}
.cat.on {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.cat.rolef::before {
  content: '◆ ';
  font-size: 10px;
  opacity: 0.7;
}

.subs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-left: 2px;
}
.sub {
  padding: 4px 12px;
  border: 1px dashed var(--line2);
  border-radius: 6px;
  background: transparent;
  color: var(--mu);
  font-size: 13.5px;
  cursor: pointer;
  transition:
    color 0.16s,
    border-color 0.16s;
}
.sub:hover {
  color: var(--tx);
}
.sub.on {
  color: var(--ac);
  border-color: var(--ac);
  border-style: solid;
}
/* 组行的前缀标签：不做成按钮，只是说明这一行筛的是什么 */
.deck-lb {
  align-self: center;
  font-size: 12.5px;
  color: var(--dim);
  padding-right: 2px;
}

.count {
  font-size: 13.5px;
  color: var(--dim);
  margin-bottom: 14px;
}
.count b {
  color: var(--tx);
  font-family: var(--font-mono);
}
.resetting {
  color: var(--ac);
  cursor: pointer;
  border-bottom: 1px dashed currentColor;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 13px;
}

.empty {
  padding: 60px 0;
  text-align: center;
  color: var(--dim);
  font-size: 14.5px;
}

.d-loading {
  color: var(--dim);
  font-size: 14px;
  padding: 20px 0;
}

.d {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.d-head {
  padding-bottom: 16px;
  border-bottom: 2px solid var(--line2);
}
.d-path {
  display: flex;
  gap: 8px;
  font-size: var(--fs-xs);
  color: var(--dim);
  margin-bottom: 8px;
}
.d-path span + span::before {
  content: '/';
  margin-right: 8px;
  color: var(--line2);
}
.d-head h2 {
  font-family: var(--font-title);
  font-size: 23px;
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}
.d-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.d-domain {
  color: var(--mu);
}
.d-level {
  color: var(--ac);
}
.d-nav {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.nb {
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--mu);
  border-radius: var(--radius-sm);
  padding: 4px 9px;
  font-size: var(--fs-xs);
  cursor: pointer;
  transition:
    border-color 0.16s,
    color 0.16s;
}
.nb:hover:not(:disabled) {
  border-color: var(--ac);
  color: var(--ac);
}
.nb:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.nb-n {
  font-size: var(--fs-xs);
  color: var(--dim);
}

.d-foot {
  position: sticky;
  bottom: -20px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 14px 0 18px;
  margin-top: 4px;
  background: linear-gradient(180deg, transparent, var(--panel) 26%);
  border-top: 1px dashed var(--line);
}
.d-foot-label {
  font-size: 14px;
  color: var(--mu);
}
</style>

<style>
/* 抽屉是 teleport 到 <body> 的，scoped 够不着，所以用全局选择器。
 *
 * 颜色不用再写一遍：主题变量挂在 <html> 上，body 是它的子元素，
 * 抽屉自然继承到当前这套。如果哪天抽屉要跨主题（在数据页里弹出纸色面板），
 * 再在这里单独声明变量覆盖不迟 —— 现在写等于把主题钉死了。 */
.card-drawer .el-drawer__body {
  padding: 26px 28px;
  background: var(--panel);
  background-image: var(--tex);
}
</style>
