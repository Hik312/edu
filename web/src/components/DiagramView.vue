<script setup>
/* 图示播放器 —— 把卡片里的 diagram 渲染成可一步步看的动画。
 *
 * 四种模板（数据结构不同，但都是「若干元素 + 若干帧高亮」）：
 *   pipeline       横向轨道，帧里的 s 指出当前走到第几段
 *   state-machine  节点连线，帧里的 n 指出当前站在哪个节点
 *   snapshot       几块面板并列，帧里的 active 是当前要点亮的面板下标
 *   arch           组件方框 + 带箭头的调用链，帧里的 n 点亮当前组件
 *                  （n 可以是单个 id 或 id 数组）—— 整体架构/请求链路用它
 *
 * 为什么做成播放器而不是静态图：这些过程本身就是"一步步走"的
 * （数据怎么流、状态怎么转），静态图看不出顺序。旧版就是这么做的，
 * 这一版保持同一个交互，用户不用重学。
 *
 * 播放定时器必须在卸载时清掉 —— 否则切走页面后它还在后台跑，
 * 切回来会发现"自己动了"，而且多个定时器叠在一起画面会抽搐。
 */
import { computed, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  spec: { type: Object, required: true }
})

const FRAME_MS = 1900

// marker 的 id 不能撞：一页可能同时渲染多张图（详情页 + 相关卡预览）
const uid = 'd' + Math.random().toString(36).slice(2, 8)

const i = ref(0)
const playing = ref(false)
let timer = null

const kind = computed(() => props.spec.kind || '')
const frames = computed(() => props.spec.frames || [])
const stages = computed(() => props.spec.stages || [])
const nodes = computed(() => props.spec.nodes || [])
const edges = computed(() => props.spec.edges || [])
const panels = computed(() => props.spec.panels || [])
const archNodes = computed(() => props.spec.nodes || [])
const archLinks = computed(() => props.spec.links || [])

const frame = computed(() => frames.value[i.value] || {})
const note = computed(() => frame.value.note || '')

/** 各模板当前高亮的下标。三种模板取不同字段，这里统一成三个 computed，
 *  模板里就不用写一堆三元判断。 */
const activeStage = computed(() => (kind.value === 'pipeline' ? (frame.value.s ?? -1) : -1))
const activeNode = computed(() => (kind.value === 'state-machine' ? (frame.value.n ?? '') : ''))
const activePanels = computed(() => (kind.value === 'snapshot' ? frame.value.active || [] : []))

/** arch 当前点亮的组件 id 集合（帧里的 n 允许单个字符串或数组）。 */
const activeArchIds = computed(() => {
  if (kind.value !== 'arch') return []
  const n = frame.value.n
  if (Array.isArray(n)) return n
  return n ? [n] : []
})
const archHotLinks = computed(() => {
  const ids = activeArchIds.value
  return archLinks.value.filter(l => ids.includes(l.from) || ids.includes(l.to))
})
function archNode(id) {
  return archNodes.value.find(n => n.id === id) || { x: 50, y: 50, label: '' }
}

/** 线的端点算到方框**边缘**而不是中心：端点若停在中心，箭头会被盖住的
 *  方框挡掉，看起来就像线插进盒子没了方向。盒形按 (w% × 24%) 估
 *  （方框高约 38px / 舞台高约 172px），从盒心沿连线方向求射线与矩形
 *  的第一个交点 —— 水平线停左右边、竖直线停上下边、斜线停角上都对。 */
function archAnchor(n, other) {
  const dx = other.x - n.x
  const dy = other.y - n.y
  if (!dx && !dy) return { x: n.x, y: n.y }
  const hx = (n.w || 20) / 2 + 1.5
  const hy = 27
  const t = Math.min(hx / Math.max(Math.abs(dx), 1e-6), hy / Math.max(Math.abs(dy), 1e-6), 0.5)
  return { x: Number((n.x - dx * t).toFixed(2)), y: Number((n.y - dy * t).toFixed(2)) }
}
/** 把 links 预计算成带两端锚点的线段，模板里直接用。 */
const archSegs = computed(() =>
  archLinks.value.map(l => {
    const a = archNode(l.from)
    const b = archNode(l.to)
    return { ...l, p1: archAnchor(a, b), p2: archAnchor(b, a) }
  })
)

/** 当前帧高亮的节点，用来加粗它连出去的边。 */
const activeEdges = computed(() => {
  if (kind.value !== 'state-machine') return []
  return edges.value
    .map((e, idx) => ({ ...e, idx }))
    .filter(e => e.from === activeNode.value || e.to === activeNode.value)
})

function stop() {
  playing.value = false
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function play() {
  if (playing.value) return stop()
  // 已经停在最后一帧时，再点播放就从头来 —— 否则点了没反应，像坏了
  if (i.value >= frames.value.length - 1) i.value = 0
  playing.value = true
  timer = setInterval(() => {
    if (i.value >= frames.value.length - 1) return stop()
    i.value++
  }, FRAME_MS)
}

function step(d) {
  stop()
  i.value = Math.max(0, Math.min(frames.value.length - 1, i.value + d))
}

function seek(n) {
  stop()
  i.value = n
}

// 换了一张卡（spec 变了）就从头开始，并清掉上一张的定时器
watch(
  () => props.spec,
  () => {
    stop()
    i.value = 0
  }
)

onUnmounted(stop)
</script>

<template>
  <div class="dv-figure">
    <div class="stage">
      <!-- pipeline：一条轨道 + 一个游标 -->
      <div v-if="kind === 'pipeline'" class="pipe">
        <div class="rail" />
        <div
          class="token"
          :style="{
            left: stages.length ? ((activeStage + 0.5) * 100) / stages.length + '%' : '0%'
          }"
        />
        <div
          v-for="(s, si) in stages"
          :key="si"
          class="stage-node"
          :class="{ on: si === activeStage, done: si < activeStage }"
        >
          <span class="num">{{ si + 1 }}</span>
          <span class="txt">{{ s }}</span>
        </div>
      </div>

      <!-- state-machine：节点按位置摆放 + 连线 -->
      <div v-else-if="kind === 'state-machine'" class="machine">
        <svg class="wires" viewBox="0 0 100 100" preserveAspectRatio="none">
          <line
            v-for="e in edges"
            :key="e.from + e.to"
            :x1="(nodes.find(n => n.id === e.from) || {}).x || 0"
            :y1="(nodes.find(n => n.id === e.from) || {}).y || 0"
            :x2="(nodes.find(n => n.id === e.to) || {}).x || 0"
            :y2="(nodes.find(n => n.id === e.to) || {}).y || 0"
            :class="{ hot: activeEdges.some(ae => ae.idx === edges.indexOf(e)) }"
          />
        </svg>
        <div
          v-for="n in nodes"
          :key="n.id"
          class="m-node"
          :class="{ on: n.id === activeNode }"
          :style="{ left: (n.x || 50) + '%', top: (n.y || 50) + '%' }"
        >
          {{ n.label || n.id }}
        </div>
      </div>

      <!-- snapshot：几块面板并列，逐块点亮 -->
      <div v-else-if="kind === 'snapshot'" class="snap">
        <div
          v-for="(p, pi) in panels"
          :key="pi"
          class="s-panel"
          :class="{ on: activePanels.includes(pi) }"
        >
          <div class="s-title">{{ p.title }}</div>
          <ul class="s-lines">
            <li v-for="(l, li) in p.lines || []" :key="li">{{ l }}</li>
          </ul>
        </div>
      </div>

      <!-- arch：组件方框 + 箭头调用链，逐帧点亮（整体架构/请求链路） -->
      <div v-else-if="kind === 'arch'" class="arch">
        <svg class="awires">
          <defs>
            <marker
              :id="'ah-' + uid"
              viewBox="0 0 10 10"
              refX="8.5"
              refY="5"
              markerWidth="6.5"
              markerHeight="6.5"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 Z" class="ah" />
            </marker>
            <marker
              :id="'ahh-' + uid"
              viewBox="0 0 10 10"
              refX="8.5"
              refY="5"
              markerWidth="6.5"
              markerHeight="6.5"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 Z" class="ah-hot" />
            </marker>
          </defs>
          <g v-for="(l, li) in archSegs" :key="li">
            <line
              :x1="l.p1.x + '%'"
              :y1="l.p1.y + '%'"
              :x2="l.p2.x + '%'"
              :y2="l.p2.y + '%'"
              :class="{ hot: archHotLinks.includes(l) }"
              :marker-end="
                archHotLinks.includes(l) ? 'url(#ahh-' + uid + ')' : 'url(#ah-' + uid + ')'
              "
            />
            <text
              v-if="l.label"
              :x="(l.p1.x + l.p2.x) / 2 + '%'"
              :y="(l.p1.y + l.p2.y) / 2 + '%'"
              :class="{ hot: archHotLinks.includes(l) }"
            >
              {{ l.label }}
            </text>
          </g>
        </svg>
        <div
          v-for="n in archNodes"
          :key="n.id"
          class="a-box"
          :class="{ on: activeArchIds.includes(n.id) }"
          :style="{
            left: (n.x ?? 50) + '%',
            top: (n.y ?? 50) + '%',
            width: (n.w || 20) + '%'
          }"
        >
          {{ n.label || n.id }}
        </div>
      </div>

      <div v-else class="unsupported">未支持的图示模板：{{ kind || '（空）' }}</div>
    </div>

    <p v-if="note" class="note">{{ note }}</p>

    <div class="ctl">
      <button class="btn" :disabled="!frames.length" @click="step(-1)">上一步</button>
      <button class="btn main" :disabled="!frames.length" @click="play">
        {{ playing ? '暂停' : '播放' }}
      </button>
      <button class="btn" :disabled="!frames.length" @click="step(1)">下一步</button>
      <span class="counter">{{ frames.length ? i + 1 : 0 }} / {{ frames.length }}</span>
      <span class="dots">
        <i
          v-for="(f, fi) in frames"
          :key="fi"
          class="pd"
          :class="{ on: fi === i }"
          :title="f.note || ''"
          @click="seek(fi)"
        />
      </span>
    </div>
  </div>
</template>

<style scoped>
.dv-figure {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--bg2);
  overflow: hidden;
}

.stage {
  position: relative;
  min-height: 132px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 18px;
}

/* ---- pipeline ---- */
.pipe {
  position: relative;
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: stretch;
}
.rail {
  position: absolute;
  left: 4%;
  right: 4%;
  top: 50%;
  height: 2px;
  background: var(--line);
  border-radius: 2px;
}
.token {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  margin: -6px 0 0 -6px;
  border-radius: 50%;
  background: var(--ac);
  box-shadow: 0 0 12px var(--ac);
  transition: left 0.42s cubic-bezier(0.22, 0.7, 0.28, 1);
}
.stage-node {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 30px 6px;
  border-radius: var(--radius-sm);
  color: var(--dim);
  transition:
    color 0.24s,
    background 0.24s;
}
.stage-node .num {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid var(--line2);
  background: var(--panel);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  transition:
    border-color 0.24s,
    color 0.24s,
    background 0.24s;
}
.stage-node .txt {
  font-size: 13.5px;
  text-align: center;
  line-height: 1.5;
}
.stage-node.done {
  color: var(--mu);
}
.stage-node.done .num {
  border-color: var(--ac-dim);
  color: var(--ac);
}
.stage-node.on {
  color: var(--tx);
  background: var(--ac-glow);
}
.stage-node.on .num {
  border-color: var(--ac);
  background: var(--ac);
  color: var(--bg);
}

/* ---- state-machine ---- */
.machine {
  position: relative;
  width: 100%;
  height: 190px;
}
.wires {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.wires line {
  stroke: var(--line2);
  stroke-width: 0.4;
  transition: stroke 0.24s;
}
/* 高亮边要用 stroke-width 而不是 CSS 的 scale ——
   preserveAspectRatio=none 已经把坐标拉伸了，缩放会跟着变形 */
.wires line.hot {
  stroke: var(--ac);
  stroke-width: 0.9;
}
.m-node {
  position: absolute;
  transform: translate(-50%, -50%);
  padding: 7px 13px;
  border: 1px solid var(--line2);
  border-radius: 20px;
  background: var(--panel);
  color: var(--mu);
  font-size: 13.5px;
  white-space: nowrap;
  transition:
    border-color 0.24s,
    color 0.24s,
    box-shadow 0.24s,
    background 0.24s;
}
.m-node.on {
  border-color: var(--ac);
  background: var(--ac-glow);
  color: var(--tx);
  box-shadow: 0 0 16px -4px var(--ac);
}

/* ---- snapshot ---- */
.snap {
  display: flex;
  gap: 12px;
  width: 100%;
  align-items: stretch;
}
.s-panel {
  flex: 1;
  min-width: 0;
  padding: 12px 13px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  opacity: 0.5;
  transition:
    opacity 0.26s,
    border-color 0.26s,
    transform 0.26s;
}
.s-panel.on {
  opacity: 1;
  border-color: var(--ac);
  transform: translateY(-2px);
}
.s-title {
  font-family: var(--font-title);
  font-size: 14.5px;
  font-weight: 600;
  margin-bottom: 7px;
  color: var(--tx);
}
.s-lines {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.s-lines li {
  font-size: 13px;
  line-height: 1.6;
  color: var(--mu);
  padding-left: 11px;
  position: relative;
}
.s-lines li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--dim);
}

/* ---- arch ---- */
.arch {
  position: relative;
  width: 100%;
  height: 200px;
}
.awires {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.awires line {
  stroke: var(--line2);
  stroke-width: 1.4;
  transition: stroke 0.24s;
}
.awires line.hot {
  stroke: var(--ac);
  stroke-width: 2;
}
.awires .ah {
  fill: var(--line2);
  transition: fill 0.24s;
}
.awires .ah-hot {
  fill: var(--ac);
}
.awires text {
  font-size: 11px;
  fill: var(--dim);
  text-anchor: middle;
  dominant-baseline: middle;
  paint-order: stroke;
  stroke: var(--bg2);
  stroke-width: 3px;
  stroke-linejoin: round;
  transition: fill 0.24s;
}
.awires text.hot {
  fill: var(--ac);
}
.a-box {
  position: absolute;
  transform: translate(-50%, -50%);
  min-width: 74px;
  max-width: 40%;
  padding: 8px 11px;
  border: 1px solid var(--line2);
  border-radius: 8px;
  background: var(--panel);
  color: var(--mu);
  font-size: 13px;
  text-align: center;
  line-height: 1.45;
  box-shadow: 0 1px 3px rgb(0 0 0 / 12%);
  transition:
    border-color 0.24s,
    color 0.24s,
    box-shadow 0.24s,
    background 0.24s;
}
.a-box.on {
  border-color: var(--ac);
  background: var(--ac-glow);
  color: var(--tx);
  box-shadow: 0 0 16px -4px var(--ac);
}

.unsupported {
  color: var(--dim);
  font-size: 14px;
}

.note {
  padding: 9px 16px;
  border-top: 1px dashed var(--line);
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--mu);
  min-height: 38px;
}

/* ---- 控制条 ---- */
.ctl {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  background: var(--panel);
  border-top: 1px solid var(--line);
}
.btn {
  padding: 4px 11px;
  border: 1px solid var(--line2);
  border-radius: 6px;
  background: transparent;
  color: var(--mu);
  font-size: 13px;
  cursor: pointer;
  transition:
    color 0.16s,
    border-color 0.16s,
    background 0.16s;
}
.btn:hover:not(:disabled) {
  color: var(--tx);
  border-color: var(--ac-dim);
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn.main {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.counter {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--dim);
}
.dots {
  display: flex;
  gap: 4px;
  margin-left: auto;
  flex-wrap: wrap;
}
.pd {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--line2);
  cursor: pointer;
  transition:
    background 0.18s,
    transform 0.18s;
}
.pd:hover {
  transform: scale(1.3);
}
.pd.on {
  background: var(--ac);
  box-shadow: 0 0 8px var(--ac);
}
</style>
