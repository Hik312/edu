/* DataV 组件注册入口 —— 按需装，不全量 install。
 *
 * 为什么不全量：`import DataVVue3 from '@kjgl77/datav-vue3'` 会把
 * BorderBox1~13、Decoration1~12、各类图表全注册进来，首屏多背几百 KB。
 * 我们实际只用了滚动榜和一条装饰线，缺哪个往下面的数组里加一个就行。
 *
 * ## 三个查过源码才知道的坑
 *
 * 1. **注册名带 `Dv` 前缀**。`app.use(ScrollBoardPlugin)` 之后，模板里必须写
 *    `<DvScrollBoard>`；写 `<ScrollBoard>` **不报错，只是什么都不显示** ——
 *    静默失败是最难查的那类 bug。
 * 2. **图表类组件（Charts / ActiveRingChart / CapsuleChart / FlylineChart）依赖
 *    外部注入的 echarts 实例**，版本不对就在运行时炸，而且报错信息跟真实原因
 *    八竿子打不着。这一版图表已经全面换成直接用 ECharts（见 components/EChart.vue），
 *    DataV 只留自绘的滚动榜和装饰线。
 * 3. **颜色字段名不统一**：PercentPond 的 `colors` 是数组，ConicalColumnChart
 *    的 `columnColor` 却是单个字符串。写反了不报错，只是颜色不生效。
 */
import { Decoration3Plugin, ScrollBoardPlugin, ScrollRankingBoardPlugin } from '@kjgl77/datav-vue3'

// 装饰组件不引这个 CSS 就只剩一堆没有描边的方框
import '@kjgl77/datav-vue3/dist/style.css'

/** 注册后模板里要写 `<DvScrollBoard>` / `<DvDecoration3>` —— 带 Dv 前缀。 */
const plugins = [ScrollBoardPlugin, ScrollRankingBoardPlugin, Decoration3Plugin]

export default {
  install(app) {
    plugins.forEach(p => app.use(p))
  }
}
