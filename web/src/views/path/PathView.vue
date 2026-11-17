<script setup>
/* 今日路径 —— 上半屏是「岗位知识地图」（拆在 PathMap.vue），下半屏是今日队列。

 下：今日队列保持原样 —— 后端 /api/review/due 已经排好序，本页只分段 + 给理由；
 但一天 311 张到期刷不完，所以加了「今日自选清单」：用户自己点名今天刷哪些。

 两块为什么放在一页：地图回答「我该学什么」，队列回答「今天先学哪个」。
 拆成两页的话，选完岗位还得自己跳过去找队列。
*/
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useLearningStore } from '@/stores/learning'
import { levelColor } from '@/config/theme'
import PathMap from '@/views/path/PathMap.vue'

const router = useRouter()
const learning = useLearningStore()

onMounted(() => {
  // all=1：今天没到期也要能看到内容，否则新用户进来是空的，
  // 会以为这一页坏了。真正的「到期才复习」约束在复习页体现。
  // ★ 必须同时给 limit：后端 /api/review/due 的 limit 默认只有 50，
  // 不给就是「静默截断」—— 库里有 67 张时路径页只显示 50 张，
  // 「已完成 x / 50」也跟着错，而且没有任何提示。500 是后端上限。
  learning.fetchDue({ all: '1', limit: 500 })
  learning.fetchStats()
  // 今日自选清单和队列一起拉：hero 要按「挑了 / 没挑」两种口径显示，
  // 晚一拍回来会让按钮先亮后灭。
  learning.fetchPick()
})

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

// ---------------------------------------------------------------------------
// 今日自选清单：一天 311 张刷不完，「今天刷哪些」由用户自己挑。
// 挑了 → hero/进度按清单口径；没挑 → 按每日目标取队列前 N 张的口径。
// 分段列表始终是全池（它是挑卡的面），清单状态只体现在行内开关上。
// ---------------------------------------------------------------------------
const pickSet = computed(() => new Set(learning.picked))
const pickOn = computed(() => learning.pickActive)

/** 今天的计划量 = 清单口径（挑了）或每日目标前 N 张（没挑）。 */
/** 今天真正要学的卡：永远排除 level 3（已掌握）。
 *
 * ★ 为什么必须排：level 3 的语义是「已经会了、今天不用管」——
 *   本页的 doneCount 也是按这个口径说的，两处不排除就自相矛盾。
 *   实测（2026-10-03）哪些入口真会带它进来：
 *   - `all=1`：**不会**。后端按 FIELD(level,1,2,0,3) 排，level 3 在最后，
 *     新卡数量远大于目标张数时根本轮不到它。
 *   - **今日自选清单：一定会**。清单是用户点名挑的，`pick=1` 照单全收，
 *     挑到已掌握的卡就会原样推出去（实测8 张全 level 3）。
 *   - 用户手动把每日目标调得很大时，`all=1` 也会碰到（末尾进入视野）。
 *   所以过滤不是多余的保险，是清单模式下的必需品。
 *   注意 mustLearn 要在**截断之前**过滤：先 slice 再滤会拿到不足 dailyTarget 张。 */
const mustLearn = c => c.level !== 3

const planItems = computed(() =>
  pickOn.value
    ? learning.queue.filter(c => pickSet.value.has(c.id))
    : learning.queue.filter(mustLearn).slice(0, learning.dailyTarget)
)

const total = computed(() => planItems.value.length)

/** 今天完成了多少（计划里已经标过、且不是"不会"的）。 */
const finished = computed(() => planItems.value.filter(c => [2, 3].includes(c.level)).length)

const percent = computed(() => (total.value ? Math.round((finished.value / total.value) * 100) : 0))

/** 行内开关：加入/移出今日清单。失败要把报错亮出来 —— 静默失败会让人
 *  以为挑上了，转头复习页照旧推 311 张。 */
async function togglePick(cid) {
  try {
    await learning.togglePick(cid)
  } catch (e) {
    ElMessage.error('清单保存失败：' + (e.message || e))
  }
}

/** 按每日目标自动挑：取当前队列（后端 due 排序）里**未掌握**的前 N 张。
 *  必须复用 planItems 的同一条口径（mustLearn）—— 这里挑的就是稍后
 *  autoPick 之后复习页会推的清单，两处算得不一样 = 用户按了「按目标挑」
 *  却得到一堆已掌握的卡。 */
async function autoPick() {
  try {
    const items = planItems.value
    const ids = items.map(c => c.id)
    await learning.savePick(ids)
    ElMessage.success(
      ids.length ? '已按每日目标挑 ' + ids.length + ' 张' : '没有需要挑的卡（都已掌握）'
    )
  } catch (e) {
    ElMessage.error('清单保存失败：' + (e.message || e))
  }
}

async function clearPick() {
  try {
    await learning.savePick([])
  } catch (e) {
    ElMessage.error('清单保存失败：' + (e.message || e))
  }
}
</script>

<template>
  <div class="path stack" v-loading="learning.loading">
    <!-- ===== 岗位知识地图（拆在 PathMap.vue） ===== -->
    <PathMap />

    <!-- ===== 概览 ===== -->
    <section class="panel hero">
      <div class="hero-txt">
        <div class="eyebrow">今日路径</div>
        <div class="hero-num">
          <span class="num mono">{{ percent }}%</span>
          <span class="unit">已完成 {{ finished }} / {{ total }} 张</span>
          <span v-if="pickOn" class="pick-tag">自选清单</span>
        </div>
        <p class="hero-sub">
          <template v-if="pickOn">
            今天按你挑的 {{ total }} 张走 —— 复习页只推这份清单，刷完就收工。
          </template>
          <template v-else>
            到期卡有 {{ learning.queue.length }} 张，一天刷不完。挑你要的几张进清单，
            或按每日目标（{{ learning.dailyTarget }} 张）自动取前 {{ learning.dailyTarget }} 张。
          </template>
          <template v-if="doneCount">另有 {{ doneCount }} 张已掌握，今天不用管。</template>
        </p>
      </div>
      <div class="hero-bar">
        <i :style="{ width: percent + '%' }" />
      </div>
      <div class="hero-act">
        <button
          v-if="!pickOn"
          class="btn"
          title="按每日目标从到期队列里取前 N 张"
          @click="autoPick"
        >
          按目标挑 {{ learning.dailyTarget }} 张
        </button>
        <button v-else class="btn" @click="clearPick">清空清单</button>
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
            <button
              class="pick-btn"
              :class="{ on: pickSet.has(c.id) }"
              :title="pickSet.has(c.id) ? '移出今日清单' : '加入今日清单'"
              @click="togglePick(c.id)"
            >
              <svg v-if="pickSet.has(c.id)" viewBox="0 0 24 24">
                <path d="M5 12.5l4.5 4.5L19 7.5" />
              </svg>
              <svg v-else viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
              {{ pickSet.has(c.id) ? '已选' : '加入' }}
            </button>
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
  display: flex;
  gap: 8px;
  align-items: center;
}
.pick-tag {
  font-size: var(--fs-xs);
  border-radius: 999px;
  padding: 3px 10px;
  background: var(--ac-glow);
  color: var(--ac);
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
/* 今日清单开关：行尾一个带字的小按钮，比纯图标一眼能读懂是干嘛的 */
.pick-btn {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--dim);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: var(--fs-xs);
  cursor: pointer;
  transition:
    border-color 0.16s,
    color 0.16s,
    background 0.16s;
}
.pick-btn svg {
  width: 12px;
  height: 12px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.pick-btn:hover {
  border-color: var(--ac);
  color: var(--ac);
}
.pick-btn.on {
  background: var(--ac-glow);
  border-color: var(--ac);
  color: var(--ac);
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
