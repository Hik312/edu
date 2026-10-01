/* ECharts 按需注册入口 —— **不要**写 `import * as echarts from 'echarts'`。
 *
 * 全量引入会把二十多种图表、几十个组件全打进包里，首屏多背 1MB+。
 * 而我们实际用得着的就下面这几种，缺哪个往数组里加一个即可。
 *
 * ## 已注册的能力（按需，够用就停）
 *
 *   BarChart / LineChart / PieChart    柱、折、饼 —— 分布与趋势
 *   RadarChart                         掌握度雷达
 *   GaugeChart                         完成度仪表
 *   ScatterChart / EffectScatterChart  相关性、带动效的重点点
 *   GraphChart                         知识图谱的关系网（graph 页面用）
 *   TreeChart / TreemapChart           层级结构
 *   SankeyChart                        流量/路径
 *
 * 组件层：Tooltip / Legend / Grid / Title / DataZoom / MarkLine / MarkPoint /
 *       MarkArea / Toolbox / Polar / Radar / VisualMap / Graphic / Calendar / Brush
 *
 * ⚠️ 少了某个 Component 的典型表现**不是报错，是配置静默失效**：
 * 比如没注册 TooltipComponent，tooltip 配了完全不显示。
 * 所以缺组件时先来这里查，不要去怀疑 option 写错了。
 */
import * as echarts from 'echarts/core'

import {
  BarChart,
  EffectScatterChart,
  GaugeChart,
  GraphChart,
  LineChart,
  PieChart,
  RadarChart,
  SankeyChart,
  ScatterChart,
  TreeChart,
  TreemapChart
} from 'echarts/charts'

import {
  BrushComponent,
  CalendarComponent,
  DataZoomComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  PolarComponent,
  RadarComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
  VisualMapComponent
} from 'echarts/components'

import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  GaugeChart,
  ScatterChart,
  EffectScatterChart,
  GraphChart,
  TreeChart,
  TreemapChart,
  SankeyChart,

  TooltipComponent,
  LegendComponent,
  GridComponent,
  TitleComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  MarkAreaComponent,
  ToolboxComponent,
  PolarComponent,
  RadarComponent,
  VisualMapComponent,
  GraphicComponent,
  CalendarComponent,
  BrushComponent,

  CanvasRenderer
])

export default echarts
