<script setup>
/* 复习队列 —— 抽卡模式。
 *
 * 和卡片页的区别：这里**一次只给一张，先看问题再看答案**。
 * 一次摊开全部内容就不叫复习了，那叫阅读。
 *
 * 三个刻意的设计：
 *
 * 1. **「先想再看」的强制停顿**。答案默认折叠，必须自己点开。
 *    这一步是整个复习流程里最值钱的 —— 直接看到答案时，大脑的
 *    "哦我会"是假的，那只是识别，不是回忆。
 * 2. **键盘 1/2/3 直接标记**，空格揭示/下一张。一轮几十张卡，
 *    每次都要把手从键盘挪到鼠标，会让人干脆不标了。
 * 3. **标记后不重排队列**（逻辑在 store 里）。标一下就重排的话，
 *    卡片会在眼皮底下跳位置，用户会以为自己标错了。
 *
 * 页面顶部还有一条「今天学多少、学什么」的设置：
 *   每天 N 张   → 传给 /review/due 的 limit
 *   方向 chips  → 传给 /review/due 的 dirs（data/directions.js 预设）
 * 两者都存**后端档案**（profiles.json，按登录用户），改完立刻重排队列 ——
 * 设置的意义就是「现在推给我的得变」，不重排等于没改。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useLearningStore, DAILY_MAX, DAILY_MIN } from '@/stores/learning'
import { useCardsStore } from '@/stores/cards'
import { levelColor, levelLabel } from '@/config/theme'
import CardBody from '@/components/CardBody.vue'
import LevelPicker from '@/components/LevelPicker.vue'

const learning = useLearningStore()
const cards = useCardsStore()

const idx = ref(0)
const revealed = ref(false)
const detail = ref(null)
const loading = ref(false)
const saving = ref(false)
/** 设置写后端时禁用按钮 —— 连点五下会发出五个 PUT，回来的顺序还没保证。 */
const savingSettings = ref(false)
/** 本轮已经标过的：{ cardId: level }。用来在结束时给个交代。 */
const done = ref({})

const queue = computed(() => learning.queue)
const cur = computed(() => queue.value[idx.value] || null)
const finished = computed(() => queue.value.length > 0 && idx.value >= queue.value.length)
const progress = computed(() =>
  queue.value.length ? Math.round((idx.value / queue.value.length) * 100) : 0
)

/** 本轮统计。结束时告诉用户「会 8 / 模糊 5 / 不会 3」——
 *  没有这个收尾，一整轮复习就是一段没有反馈的空白。 */
const summary = computed(() => {
  const rows = [3, 2, 1].map(v => ({
    level: v,
    label: levelLabel(v),
    color: levelColor(v),
    count: Object.values(done.value).filter(x => x === v).length
  }))
  return rows
})

onMounted(async () => {
  // 两件事必须按这个顺序：
  // 1. 先等档案（每日目标 + 方向）—— 反过来会先取一张按默认设置排的队列，
  //    档案一到又要重排，卡片会在眼皮底下换一批。
  // 2. 每次进本页都重取 —— 驾驶舱那次 fetchDue({limit:8}) 只是滚动榜的 8 条，
  //    顺手拿来当今日队列就会只显示 8 张。
  await learning.ensureSettings()
  await learning.fetchDue({ limit: learning.dailyTarget })
  await loadDetail()
})

/** 取当前卡的完整内容。store 里有缓存，来回翻不会重复请求。 */
async function loadDetail() {
  if (!cur.value) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    detail.value = await cards.fetchDetail(cur.value.id)
  } finally {
    loading.value = false
  }
}

watch(cur, async () => {
  revealed.value = false
  await loadDetail()
})

function reveal() {
  revealed.value = true
}

function next() {
  if (idx.value < queue.value.length) idx.value++
}

async function mark(level) {
  if (!cur.value || saving.value) return
  // ★ 先把这张卡钉住，后面一律用 cid。
  // 从前是 await 之后才读 `cur.value.id` —— 请求在途时按 ← 会改变 cur，
  // 于是这一档被记到**上一张卡**头上，并且 next() 从被回退的位置再前进，
  // 同一张卡会重复出现两次。属于「统计和实际操作不一致」的静默错误。
  const cid = cur.value.id
  saving.value = true
  try {
    await learning.mark(cid, level)
    done.value[cid] = level
    next()
  } finally {
    saving.value = false
  }
}

function restart() {
  idx.value = 0
  done.value = {}
  revealed.value = false
}

/* ---------- 今日设置：每天学几张、学什么 ---------- */

/** 点完把焦点还给页面。否则设置按钮一直持有焦点，接下来按空格是「点这个
 *  按钮」而不是「看答案」，键盘流（空格/1/2/3）会莫名其妙失灵。 */
function blur(e) {
  if (e && e.currentTarget) e.currentTarget.blur()
}

/** 改设置 = 换一批卡：写档案 → 重取队列 → 从头开始这一轮。
 *  本轮进度留着没意义（卡都不一样了），所以直接 restart。 */
async function applySettings(patch) {
  if (savingSettings.value) return
  savingSettings.value = true
  try {
    await learning.saveSettings(patch)
    restart()
    await learning.fetchDue({ limit: learning.dailyTarget })
  } finally {
    savingSettings.value = false
  }
}

async function bumpTarget(step, e) {
  blur(e)
  const v = Math.min(DAILY_MAX, Math.max(DAILY_MIN, learning.dailyTarget + step))
  if (v !== learning.dailyTarget) await applySettings({ dailyTarget: v })
}

async function toggleDir(id, e) {
  blur(e)
  const cur = learning.pickedDirs
  const next = cur.includes(id) ? cur.filter(x => x !== id) : cur.concat(id)
  await applySettings({ directions: next })
}

/** 「全部」= 清空方向（后端 dirs 为空就不筛）。再点一次没有反应。 */
async function pickAll(e) {
  blur(e)
  if (!learning.pickedDirs.length) return
  await applySettings({ directions: [] })
}

/** 空格：揭示答案，或（已揭示时）跳到下一张。 */
function onSpace(e) {
  e.preventDefault()
  if (finished.value) return
  if (revealed.value) next()
  else reveal()
}

/** 1 / 2 / 3：标记掌握度。没揭示答案、或这一轮已经结束时忽略。 */
function onMarkKey(e, key) {
  if (!revealed.value || finished.value) return
  e.preventDefault()
  mark(Number(key))
}

/** ← 回上一张。
 *  ★ 标记请求在途时不允许回退：saving 期间 cur 会变，
 *  用户会看到「标记中又跳了一张」的错乱（mark 里已经把 cid 钉住了，
 *  但界面上的跳转还是会让人以为标错了卡）。 */
function onBack() {
  if (idx.value > 0 && !saving.value) idx.value--
}

/** 键盘：空格揭示/下一张，1/2/3 标记，← 回上一张。
 *  输入框里按这些键要放过 —— 否则以后加了搜索框，打字就打不进去了。
 *  拆成三个小函数是因为整个 onKey 的分支数会顶到 ESLint 的 complexity 上限；
 *  每个分支各自成一个有名字的动作，比在一条长 if 链里读更清楚。 */
function onKey(e) {
  const tag = (e.target && e.target.tagName) || ''
  if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target?.isContentEditable) return

  if (e.key === ' ') return onSpace(e)
  if (['1', '2', '3'].includes(e.key)) return onMarkKey(e, e.key)
  if (e.key === 'ArrowLeft') return onBack()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="rv">
    <!-- ===== 顶部进度 ===== -->
    <header class="rv-head rise">
      <div class="rv-title">
        <h2>今日队列</h2>
        <span class="rv-sub">
          <template v-if="finished">本轮结束</template>
          <template v-else-if="queue.length">{{ idx + 1 }} / {{ queue.length }}</template>
          <template v-else>今天没有到期的卡</template>
        </span>
      </div>
      <div class="rv-prog">
        <span class="track"><i :style="{ width: progress + '%' }" /></span>
        <span class="pct">{{ progress }}%</span>
      </div>
    </header>

    <!-- ===== 今日设置：每天学几张、学什么（改完立刻重排队列） ===== -->
    <div class="rv-setup rise">
      <div class="setup-row">
        <span class="setup-label">每天</span>
        <div class="step">
          <button
            class="sbtn"
            type="button"
            :disabled="savingSettings || learning.dailyTarget <= DAILY_MIN"
            @click="bumpTarget(-5, $event)"
          >
            −
          </button>
          <span class="snum mono">{{ learning.dailyTarget }}</span>
          <span class="sunit">张</span>
          <button
            class="sbtn"
            type="button"
            :disabled="savingSettings || learning.dailyTarget >= DAILY_MAX"
            @click="bumpTarget(5, $event)"
          >
            ＋
          </button>
        </div>
        <span class="setup-label">方向</span>
        <div class="chips">
          <button
            class="chip"
            type="button"
            :class="{ on: !learning.pickedDirs.length }"
            :disabled="savingSettings"
            @click="pickAll($event)"
          >
            全部
          </button>
          <button
            v-for="d in learning.directions"
            :key="d.id"
            class="chip"
            type="button"
            :class="{ on: learning.pickedDirs.includes(d.id) }"
            :title="d.desc"
            :disabled="savingSettings"
            @click="toggleDir(d.id, $event)"
          >
            {{ d.name }}<i class="cnt">{{ d.count }}</i>
          </button>
        </div>
      </div>
    </div>

    <!-- ===== 空队列 ===== -->
    <div v-if="!queue.length && !learning.loading" class="blank rise">
      <p v-if="learning.pickedDirs.length">「{{ learning.dirText }}」今天没有到期的卡。</p>
      <p v-else>今天的卡都复习完了。</p>
      <div class="blank-actions">
        <button v-if="learning.pickedDirs.length" class="go ghost" @click="pickAll()">
          看全部方向
        </button>
        <button class="go" @click="$router.push('/cards')">去卡片页预习</button>
      </div>
    </div>

    <!-- ===== 一轮结束 ===== -->
    <div v-else-if="finished" class="done rise">
      <h3>这一轮标完了</h3>
      <div class="sum">
        <div v-for="s in summary" :key="s.level" class="sum-cell">
          <span class="sum-num" :style="{ color: s.color }">{{ s.count }}</span>
          <span class="sum-label">{{ s.label }}</span>
        </div>
      </div>
      <p class="done-tip">
        「模糊」和「不会」的卡会在更短时间内再出现一次 —— 这是 SM-2 的排期，
        不用自己去记哪些没掌握。
      </p>
      <div class="done-actions">
        <button class="go" @click="restart">从头再看一遍</button>
        <button class="go ghost" @click="$router.push('/dashboard')">回驾驶舱</button>
      </div>
    </div>

    <!-- ===== 抽卡主体 ===== -->
    <article v-else-if="cur" class="sheet rise">
      <div class="sheet-path">
        <span v-if="cur.domain" class="badge">{{ cur.domain }}</span>
        <span class="lv" :style="{ color: levelColor(cur.level || 0) }">
          {{ levelLabel(cur.level) }}
        </span>
      </div>

      <h1 class="sheet-q">{{ cur.title }}</h1>
      <p v-if="cur.oneLine" class="sheet-one">{{ cur.oneLine }}</p>

      <!-- 折叠区：这一步是整个复习里最值钱的停顿 -->
      <div v-if="!revealed" class="veil">
        <button class="reveal" @click="reveal">
          <span>想好了，看答案</span>
          <kbd>空格</kbd>
        </button>
        <p class="veil-tip">
          先在心里过一遍再看 —— 直接看答案时那种「我会了」是认出来的，不是想起来的。
        </p>
      </div>

      <div v-else class="answer">
        <div v-if="loading" class="loading">读取中…</div>
        <CardBody v-else-if="detail" :card="detail" @open-related="$router.push('/cards')" />
      </div>

      <footer v-if="revealed" class="sheet-foot">
        <span class="foot-label">这张卡</span>
        <LevelPicker :model-value="cur.level || 0" :loading="saving" @pick="mark" />
        <button class="skip" @click="next">先跳过 →</button>
      </footer>
    </article>
  </div>
</template>

<style scoped>
.rv {
  /* 不铺满是有意的：一屏只有一张卡，行宽拉到 1400 会读到「换行找不回上一行」，
     那比留白更难受。但原来的 880 在 1440 屏上两侧各空 280px 又太亏 ——
     1040 是这两头之间的折中：正文行宽约 60 个汉字，仍在舒适区。 */
  max-width: 1040px;
  margin: 0 auto;
}

.rv-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}
.rv-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.rv-title h2 {
  font-family: var(--font-title);
  font-size: 21px;
  font-weight: 600;
  letter-spacing: 2px;
}
.rv-sub {
  font-family: var(--font-mono);
  font-size: 13.5px;
  color: var(--dim);
}
.rv-prog {
  flex: 1;
  max-width: 300px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.track {
  flex: 1;
  height: 6px;
  border-radius: 4px;
  background: var(--line);
  overflow: hidden;
}
.track i {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--ac), var(--ac-dim));
  transition: width 0.4s cubic-bezier(0.22, 0.7, 0.28, 1);
}
.pct {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--mu);
}

/* ---- 今日设置条 ---- */
.rv-setup {
  margin-bottom: 16px;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}
.setup-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.setup-label {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-right: 14px;
  border-right: 1px dashed var(--line);
}
.sbtn {
  width: 26px;
  height: 26px;
  border: 1px solid var(--line2);
  border-radius: var(--radius-sm);
  background: var(--bg2);
  color: var(--tx);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  transition:
    border-color 0.16s,
    background 0.16s;
}
.sbtn:hover:not(:disabled) {
  border-color: var(--ac);
  background: var(--ac-glow);
}
.sbtn:disabled {
  opacity: 0.4;
  cursor: default;
}
.snum {
  font-family: var(--font-mono);
  font-size: 17px;
  font-weight: 600;
  min-width: 26px;
  text-align: center;
  color: var(--ac);
}
.sunit {
  font-size: var(--fs-xs);
  color: var(--mu);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 11px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--bg2);
  color: var(--mu);
  font-size: var(--fs-sm);
  cursor: pointer;
  transition:
    color 0.16s,
    border-color 0.16s,
    background 0.16s;
}
.chip:hover:not(:disabled) {
  color: var(--tx);
  border-color: var(--ac-dim);
}
.chip.on {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.chip:disabled {
  opacity: 0.55;
  cursor: default;
}
/* 方向后面的小数字 = 这个方向库里有多少张卡。写成 i 而不是 span：
   位置和斜体都借的是「角标」的读法，不想让它跟名字争主次 */
.chip .cnt {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-style: normal;
  color: var(--dim);
}
.chip.on .cnt {
  color: var(--ac);
  opacity: 0.75;
}

/* ---- 抽卡纸张 ---- */
.sheet {
  position: relative;
  padding: 26px 30px 24px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
}
/* 纸张顶部一条朱砂压线，像信笺的抬头 */
.sheet::before {
  content: '';
  position: absolute;
  left: 30px;
  right: 30px;
  top: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--ac), transparent 62%);
  border-radius: 0 0 2px 2px;
}

.sheet-path {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.badge {
  font-size: var(--fs-xs);
  padding: 2px 9px;
  border-radius: 20px;
  border: 1px solid var(--line);
  color: var(--mu);
}
.lv {
  font-size: var(--fs-xs);
  margin-left: auto;
}

.sheet-q {
  font-family: var(--font-title);
  font-size: 26px;
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 0.6px;
  margin-bottom: 10px;
}
.sheet-one {
  font-size: 15px;
  line-height: 1.85;
  color: var(--mu);
}

.veil {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px dashed var(--line);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 11px;
}
.reveal {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 26px;
  border: 1px solid var(--line2);
  border-radius: var(--radius-sm);
  background: var(--bg2);
  color: var(--tx);
  font-size: 15px;
  cursor: pointer;
  transition:
    border-color 0.18s,
    background 0.18s,
    transform 0.16s;
}
.reveal:hover {
  border-color: var(--ac);
  background: var(--ac-glow);
  transform: translateY(-1px);
}
.reveal kbd {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--line2);
  color: var(--dim);
}
.veil-tip {
  font-size: 13px;
  color: var(--dim);
  text-align: center;
  max-width: 520px;
  line-height: 1.7;
}

.answer {
  margin-top: 24px;
  padding-top: 22px;
  border-top: 1px dashed var(--line);
}
.loading {
  color: var(--dim);
  font-size: 14px;
}

.sheet-foot {
  position: sticky;
  bottom: -24px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin: 24px -30px -24px;
  padding: 15px 30px 18px;
  background: linear-gradient(180deg, transparent, var(--panel) 30%);
  border-top: 1px dashed var(--line);
}
.foot-label {
  font-size: 14px;
  color: var(--mu);
}
.skip {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: var(--dim);
  font-size: 13.5px;
  cursor: pointer;
}
.skip:hover {
  color: var(--mu);
}

/* ---- 空 / 结束 ---- */
.blank,
.done {
  padding: 46px 30px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  text-align: center;
}
.blank p {
  color: var(--mu);
  font-size: 15px;
  margin-bottom: 18px;
}
.blank-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}
.done h3 {
  font-family: var(--font-title);
  font-size: 23px;
  font-weight: 600;
  letter-spacing: 2px;
  margin-bottom: 22px;
}
.sum {
  display: flex;
  justify-content: center;
  gap: 46px;
  margin-bottom: 22px;
}
.sum-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.sum-num {
  font-family: var(--font-mono);
  font-size: 36px;
  font-weight: 600;
  line-height: 1.1;
}
.sum-label {
  font-size: 13.5px;
  color: var(--mu);
}
.done-tip {
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--dim);
  max-width: 460px;
  margin: 0 auto 22px;
}
.done-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.go {
  padding: 9px 20px;
  border: 1px solid var(--ac-dim);
  border-radius: var(--radius-sm);
  background: var(--ac-glow);
  color: var(--ac);
  font-size: 14.5px;
  cursor: pointer;
  transition:
    transform 0.16s,
    background 0.16s;
}
.go:hover {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--ac) 18%, transparent);
}
.go.ghost {
  border-color: var(--line2);
  background: transparent;
  color: var(--mu);
}

@media (max-width: 700px) {
  .sheet {
    padding: 20px 18px;
  }
  .sheet-q {
    font-size: 21px;
  }
  .sheet-foot {
    margin: 20px -18px -20px;
    padding: 14px 18px 16px;
  }
  .sum {
    gap: 26px;
  }
}
</style>
