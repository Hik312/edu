/* 可视化配色 —— ECharts 图表、DataV 组件、掌握度标签共用。
 *
 * 集中在这里的意义：**ECharts 默认是一整套蓝绿黄粉，DataV 默认是青蓝 #00c2ff，
 * 两个都跟牛皮纸底不搭**。两个库都支持传色，但散在页面里写死的话，
 * 换一次配色要改十几个地方，改漏一个就出现「这一块是蓝的、那一块是绿的」。
 *
 * ## 这一版为什么只有一套色
 *
 * 上一版有 `DARK`（暗底高亮）和 `LIGHT`（浅底压深）两份，按页面的主题挑一份。
 * 现在全站统一牛皮纸，**两份合并成一份 `INK`**，所有函数也不再接受 theme 参数。
 *
 * 参数去掉是有意的：留着 `levelColor(1, 'dark')` 这种签名，就等于留着一个
 * 「也许某天还要有深色」的钩子，而每次有人传错参数都不会报错，只会画出
 * 一个在纸上几乎看不见的浅色。没有参数就没有这个错误。
 *
 * ## 取值标准
 *
 * 纸底 #f8f3e6 比纯白暗一档，所以颜色要**比在纯白上再压深一点**才能过对比度。
 * 语义色按 4.5:1 卡（文字会用到），序列色按 3:1 卡（只做色块填充）。
 */

/** 语义色。论文/文档类界面里这几档要能在纸底上直接读。 */
export const INK = {
  known: '#2f7057', // 会：松绿压深
  fuzzy: '#8a6218', // 模糊：赭黄
  weak: '#a8392a', // 不会：朱砂
  unmarked: '#7d6b4c', // 未标记：纸褐（刻意淡，它表示"还没看"）
  accent: '#1f4b6b' // 靛蓝墨水，跟 --ac 一致
}

/** ECharts 的轴线 / 图例 / tooltip 用色，跟 tokens.css 手工对齐。
 *  为什么不用 getComputedStyle 读 CSS 变量：图表 option 是 computed 生成的对象，
 *  读 DOM 会让它依赖渲染时机，主题一变就要手动失效一次。直接对齐常量更稳。 */
const LINE = '#ddd1b6'
const LABEL = '#63543c'
const PAPER = '#f8f3e6'
const PAPER2 = '#f1ead8'
const INK_TEXT = '#3a2f21'

/**
 * 图表多色序列。柱子、饼图扇区按顺序取，超过长度自动循环。
 *
 * 取的是**多色相 + 中明度**：十个色相拉开，才不会在一张饼里出现
 * 「两块差不多的绿」。饱和度都压过一遍 —— 纸底上高饱和色会跳出画面，
 * 看着像贴上去的标签而不是图的一部分。
 *
 * ⚠️ 这一版把**洋红和紫棠换掉了**（原来是 #b0607f / #6a5aa8）。
 * 原因是 `colorOf` 是**哈希取色**，落到哪个色相不受控 —— 只要那两个还留在
 * 表里，两三个类目的图就有 1/5 的概率抽到一支跟靛蓝主色打架的艳色，
 * 驾驶舱上就出现了「土黄条 + 玫红条」这种一眼就不像一家的组合。
 * 哈希的落点改不了，能改的是**把每个候选都调成纸面能接受的颜色**：
 * 现在无论抽到哪一个，都是中低饱和、跟主色同一明度带的。
 */
export const SEQ = [
  '#2f6fa5', // 靛青 —— 跟 --ac 同族，类目少时大概率是它，正好压住画面
  '#3f8f6d', // 松绿
  '#c08a2e', // 赭黄
  '#a8553f', // 绛
  '#3f8f8a', // 青碧
  '#7a8b3a', // 橄榄
  '#5c7fa8', // 灰蓝
  '#8a6f9e', // 黛紫（原紫棠 #6a5aa8 压灰压暗，不再像荧光）
  '#b0794f', // 陶土（替换洋红 #b0607f，同为暖色但退到纸面里）
  '#9a7a4a' // 土褐
]

/** 掌握度四档 → 语义色。level 取值全项目统一：0 未标记 / 1 不会 / 2 模糊 / 3 会。 */
export const LEVEL_COLOR = {
  0: INK.unmarked,
  1: INK.weak,
  2: INK.fuzzy,
  3: INK.known
}

/** 取某个掌握度的颜色。
 * @param {number} level 0-3
 * @returns {string} 色值
 */
export function levelColor(level) {
  return LEVEL_COLOR[level] ?? LEVEL_COLOR[0]
}

/** 取一个数据项的稳定颜色。
 *
 * 用名字做哈希而不是随机取：**刷新一下颜色全变会让图看着像假数据**。
 * 同一个 key 在任何一次渲染里都必须拿到同一个颜色 —— 图例行、tooltip、
 * 图上的扇区三处必须一致，否则用户会以为是两个不同的东西。
 * @param {string} key 数据项名字
 * @param {string[]} [palette] 色板，默认 SEQ
 * @returns {string} 色值
 */
export function colorOf(key, palette = SEQ) {
  let hash = 0
  const s = String(key ?? '')
  for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0
  return palette[hash % palette.length]
}

/**
 * ECharts 的基础配置。只放**跟纸面有关的那部分**（文字色、轴线色、提示框），
 * 数据类配置留给各图表自己。
 *
 * 为什么要这么切：一个图 = 基础配置 + 数据配置。
 * 把两块揉在一个对象里，以后想给某张图换个 tooltip 格式就得整份重写；
 * 分开以后页面里只需要 merge 数据那部分。
 * @returns {Object} ECharts option 片段
 */
export function chartBase() {
  return {
    textStyle: { fontFamily: 'Microsoft YaHei, PingFang SC, system-ui, sans-serif', fontSize: 13 },
    tooltip: {
      // 纸上不用半透明黑：深色浮层压在纸底上会像"挖了个洞"。
      // 用纸面本色 + 描边，读起来像一张便签
      backgroundColor: PAPER,
      borderColor: LINE,
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: INK_TEXT, fontSize: 13 },
      extraCssText: 'border-radius:8px;box-shadow:0 8px 22px -12px rgba(58,47,33,.45);'
    },
    legend: {
      // ⚠️ 这里的 `show: false` 是**必须的**，不是可有可无的保险。
      //
      // ECharts 判定"要不要画图例"看的是 **legend 这个键存不存在**，
      // 而不是里面的 show 值是真是假 —— 只要对象在，就按 show:true 渲染。
      // 所以这段本来只想提供样式的配置，会让**每一个**用 chartBase() 的图
      // 都平白长出一个图例。驾驶舱环形图上那个贴在圆环边上的
      // 「■ 未标记 100%」就是这么来的，而且它跟扇区 label 的信息完全重复。
      //
      // 需要图例的图自己写：`legend: { ...base.legend, show: true, ... }`
      show: false,
      textStyle: { color: LABEL, fontSize: 13 },
      itemWidth: 12,
      itemHeight: 12,
      icon: 'roundRect'
    }
  }
}

/** 直角坐标系的通用样式（类目轴 / 数值轴）。
 * @returns {Object} 含 grid / xAxis / yAxis 的 option 片段
 */
export function axisBase() {
  return {
    grid: { left: 8, right: 16, top: 18, bottom: 6, containLabel: true },
    xAxis: {
      axisLine: { lineStyle: { color: LINE } },
      axisTick: { show: false },
      axisLabel: { color: LABEL, fontSize: 12.5, margin: 12 },
      splitLine: { show: false }
    },
    yAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: LABEL, fontSize: 12.5, margin: 10 },
      splitLine: { lineStyle: { color: LINE, type: 'dashed' } }
    }
  }
}

/** 图表里要用到的底色常量。页面画图时引用它，别再写字面值。 */
export const CHART_BG = { paper: PAPER, paper2: PAPER2, line: LINE, label: LABEL, text: INK_TEXT }
