<script setup>
/* ECharts 通用容器 —— 全项目画图的**唯一入口**。
 *
 * 为什么不各页面自己 init：图表有三件必做但容易漏的事，
 * 漏一件都能正常跑几天然后才炸：
 *
 *   1. **dispose**。不销毁的话实例、定时器、canvas 全留在内存里，
 *      在卡片列表这种反复进出的页面上会稳定泄漏。
 *   2. **容器尺寸变化时 resize**。用 window.resize 不够 ——
 *      el-drawer 展开、侧栏折叠、栅格断点变化都改不了窗口尺寸，
 *      只监听 resize 会得到一张永远保持旧尺寸的图。所以用 ResizeObserver。
 *   3. **切换深度legend/series 时用 notMerge**。默认是 merge，
 *      series 从 3 条减到 2 条时旧的第三条**还留在图上**，
 *      表现为「图上多出来一段说不清是什么的东西」。
 *
 * 用法：`<EChart :option="myOption" height="260px" />`
 * option 变化会自动重绘，不用自己调 setOption。
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
// 走 plugins/echarts.js 按需注册过的实例，不是 `echarts` 全量包（见那个文件的注释）
import echarts from '@/plugins/echarts'

const props = defineProps({
  /** ECharts 的 option 对象。用 computed 生成，主题变了要能自动换色。 */
  option: { type: Object, required: true },
  /** 容器高度。宽度永远跟随父容器 100%。 */
  height: { type: String, default: '260px' },
  /** 骨架态。数据没到时显示 Element 的骨架屏，而不是一张空坐标系。 */
  loading: { type: Boolean, default: false },
  /**
   * 容器宽高变化时自动 resize。默认开。
   * 只有那种「尺寸固定不变」的图才需要关掉（省一个 Observer）。
   */
  autoresize: { type: Boolean, default: true }
})

const emit = defineEmits(['click'])

const el = ref(null)
let chart = null
let ro = null
let raf = 0

/** 真正的重绘。用 requestAnimationFrame 合并同一帧内的多次调用 ——
 *  option 的多个字段同时变化时，Vue 会触发多次 watcher 回调，
 *  每次都同步 setOption 会让浏览器在一帧里画很多遍。 */
function apply() {
  if (!chart || !props.option) return
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(() => {
    // notMerge:true —— 见文件头第 3 条。series 数量变少时旧的会残留
    chart?.setOption(props.option, { notMerge: true, lazyUpdate: true })
  })
}

function resize() {
  chart?.resize()
}

/** 懒初始化 —— 容器拿到**非零**宽高之后才建实例。
 *
 * ⚠️ 不能一上来就在 onMounted 里 `echarts.init(el)`。
 * 骨架态用的是 `v-show`（不是 `v-if`）：元素存在，但 `display:none`，
 * 实测宽高都是 **0×0**。ECharts 会把这个 0×0 记成画布尺寸，
 * 力导向（graph / force）在这个尺寸下把几十个节点全收敛到原点，
 * 骨架一撤、ResizeObserver 补上 resize，**坐标系回来了但已经收敛的
 * 布局不会重算** —— 表现是「画布一片空白，只有几个标签飘在边上」。
 *
 * 为什么只有知识图谱中招：柱状/饼图这类静态布局会在 resize 后
 * 按新尺寸重新计算占比，看着就正常。所以这个坑一开始被误判成
 * 「force 的 repulsion/edgeLength 参数不对」，白调了半天。
 *
 * 返回 true 表示「这次调用真的建了实例」，调用方需要接着画第一帧。
 */
function initChart() {
  if (chart || !el.value) return false
  if (!el.value.clientWidth || !el.value.clientHeight) return false
  // renderer 固定 canvas：SVG 在节点数多时（知识图谱几百个节点）
  // 会把 DOM 数量撑到几千，交互直接卡住
  chart = echarts.init(el.value, null, { renderer: 'canvas' })
  // 把点击事件透出去。为什么不把实例直接 expose 给调用方：拿到实例以后
  // 就得自己管 dispose 时机，等于把这一层的价值作废了。
  // 只 emit 事件，实例生命周期仍然锁在这里。
  chart.on('click', params => emit('click', params))
  return true
}

onMounted(() => {
  // 首屏就可见（没有骨架态）的图，这里同步建好，省掉一次异步等待
  if (initChart()) apply()

  if (props.autoresize && typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(() => {
      // 第一次拿到非零尺寸：建实例 + 画第一帧。
      // 之后（窗口缩放 / 侧栏折叠 / 抽屉展开）才是纯 resize
      if (!chart) {
        if (initChart()) apply()
        return
      }
      chart.resize()
    })
    ro.observe(el.value)
  }
})

// deep 是必须的：option 内部的 series 数组换了内容，引用可能没变
watch(() => props.option, apply, { deep: true })

watch(
  () => props.loading,
  v => {
    // showLoading 的默认样式是套转圈的蓝字，跟两套主题都不搭，
    // 我们自己用 v-if 画骨架屏，这里不用 ECharts 的 loading
    if (v) chart?.clear()
    else apply()
  }
)

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  ro?.disconnect()
  ro = null
  chart?.dispose()
  chart = null
})

defineExpose({ resize })
</script>

<template>
  <div class="echart-wrap" :style="{ height }">
    <div v-if="loading" class="skel">
      <div class="bar" v-for="n in 4" :key="n" :style="{ height: 88 - n * 16 + '%' }" />
    </div>
    <div v-show="!loading" ref="el" class="echart-box" />
  </div>
</template>

<style scoped>
.echart-wrap {
  position: relative;
  width: 100%;
}
.echart-box {
  width: 100%;
  height: 100%;
}

/* 骨架屏：几根高低不齐的柱子，比转圈更像「图表正在来」 */
.skel {
  height: 100%;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 10px 4px;
}
.bar {
  flex: 1;
  border-radius: 6px 6px 2px 2px;
  background: linear-gradient(180deg, var(--panel2), var(--line));
  animation: pulse 1.4s ease-in-out infinite;
}
.bar:nth-child(2) {
  animation-delay: 0.12s;
}
.bar:nth-child(3) {
  animation-delay: 0.24s;
}
.bar:nth-child(4) {
  animation-delay: 0.36s;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 0.9;
  }
}
</style>
