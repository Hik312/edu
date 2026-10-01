<script setup>
/* 知识图谱 —— 用 ECharts 的 graph series 铺开「一科知识长什么样」。
 *
 * ## 为什么换掉旧版的 Canvas 自绘
 *
 * 旧版（单文件页 / 小程序）是自己实现的力导向 + 粒子场，效果确实炫，
 * 但三个问题是自绘绕不过去的：
 *   1. **没有 tooltip / 缩放 / 图例筛选**，要就自己写一套，写完还想加拖拽又是一套
 *   2. **节点多了就掉帧**：canvas 每帧重画全部节点，几百个点必 card
 *   3. 两套 Spaces 要维护两份几乎一样的物理参数
 *
 * ECharts 的 force 布局用四叉树做斥力近似，几十到几百个节点都稳，
 * 而且缩放、tooltip、图例筛选全是免费的。
 *
 * ## 节点四种类型，edges 的 kind 决定连线颜色
 *
 *   category / subject / topic = 结构节点（来自 topicPath）
 *   card                       = 真正的知识点卡片
 *
 * 结构节点存在的意义是让「Agent 属于 核心概念 属于 AI工程」这条链看得见 ——
 * 只有二十个孤立的卡片点，是看不出知识结构的。
 *
 * ## 配色：纸面上的四种色相，不是深底上的四支荧光笔
 *
 * 深色底靠亮度拉开层次，纸底上亮度都接近，**只能靠色相差**。
 * 所以这四类节点取的是四个明显不同的色相（蓝 / 绿 / 黄 / 绛），
 * 而且都压过饱和度 —— 纸上高饱和的圆点看着像贴纸。
 * 卡片节点有掌握度时用 levelColor 覆盖，那是最重要的信息（哪些还没掌握）。
 *
 * ## 模块筛选：一次只看一个模块
 *
 * 全量图（67 卡 + 结构节点）力导向会糊成毛线球，所以顶栏两级 chips：
 * 分类 → 科目，选中哪个就只画哪个的子图（后端 `/api/graph?category=&subject=`）。
 * 跨模块的 related 边会被后端按 id 白名单丢掉 —— 这正是"其他模块不出现"的语义。
 *
 * 结构节点按选中范围裁剪，省掉一层没信息量的骨架：
 *   全部       → category / subject / topic / card 四层都在
 *   选了分类   → 去掉 category（只剩一个自己，没有分组意义）
 *   选了科目   → 去掉 category，保留 subject 当这组图的根
 *
 * 为什么不去后端裁：裁剪是**视图**的事（换种选法要换套规则），
 * 后端给全量子图，前端按当前选择丢节点 —— 一个参数不用加。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EChart from '@/components/EChart.vue'
import {
  catalog as fetchCatalog,
  graph as fetchGraph,
  neighbors as fetchNeighbors
} from '@/api/system'
import { CHART_BG, INK, chartBase, levelColor } from '@/config/theme'

const router = useRouter()

const base = chartBase()

const raw = ref({ nodes: [], edges: [] })
const loading = ref(true)
/** 当前选中的节点 id。选中后右侧出详情面板。 */
const picked = ref('')
/** 选中节点的邻居（单独拉接口，不全图找）。 */
const near = ref({ nodes: [], edges: [] })

/** 模块选择：两级 chips（全部 → 分类 → 科目）。和卡片页同一套交互。 */
const catList = ref([])
const catId = ref('')
const subId = ref('')

/** 选了科目才有的二级 chips。没选分类就不给选科目 —— 跨分类的科目名会重。 */
const subList = computed(() => {
  if (!catId.value) return []
  const hit = catList.value.find(c => c.id === catId.value)
  return hit ? hit.subjects || [] : []
})

async function loadGraph() {
  loading.value = true
  picked.value = ''
  near.value = { nodes: [], edges: [] }
  localStorage.setItem('edu.graph', catId.value + '|' + subId.value)
  try {
    // 科目优先：选了科目就只按科目过滤（后端 all_cards 里 subject 也带 category 归属）
    const p = {}
    if (subId.value) p.subject = subId.value
    else if (catId.value) p.category = catId.value
    const r = await fetchGraph(Object.keys(p).length ? p : undefined)
    raw.value = r.graph || { nodes: [], edges: [] }
  } finally {
    loading.value = false
  }
}

function pickCat(id) {
  catId.value = id
  subId.value = '' // 换了分类就把上一个分类的科目清掉，否则筛出空图
  loadGraph()
}

function pickSub(id) {
  // 再点一次同一个科目就取消，省得用户找不到「取消筛选」的按钮
  subId.value = subId.value === id ? '' : id
  loadGraph()
}

onMounted(async () => {
  // 上次看的模块记住（localStorage，不占后端）。格式 cat|sub，空段就是没选。
  // 首次进来默认「工作」而不是「全部」：全量 150 节点力导向就是一坨毛线球，
  // 而这一页存在的意义就是分模块看。「全部」仍然是第一颗 chips，一击可切。
  const saved = localStorage.getItem('edu.graph')
  const [c0, s0] = (saved === null ? 'work|' : saved).split('|')
  catId.value = c0 || ''
  subId.value = s0 || ''
  loadGraph()
  try {
    const c = await fetchCatalog()
    catList.value = c.catalog || []
    // 记住的选择已不在分类树里（catalog 改过）就退回「全部」，否则请求的
    // 是不存在的参数：图是空的、chips 也没高亮，看不出所以然
    const hit = catList.value.find(x => x.id === catId.value)
    const catOk = !catId.value || Boolean(hit)
    const subOk = !subId.value || (hit?.subjects || []).some(x => x.id === subId.value)
    if (!catOk || !subOk) {
      catId.value = catOk ? catId.value : ''
      subId.value = ''
      loadGraph()
    }
  } catch {
    catList.value = [] // 分类树拿不到就只剩「全部」，图谱照常能看
  }
})

/**
 * 当前选择下的子图：先按范围裁结构节点，再把两端都还在的边留下。
 * 顺序不能反 —— 先留边会留下指向已裁节点的悬空边，ECharts 直接不画。
 */
const view = computed(() => {
  const all = raw.value
  const drop = new Set()
  if (subId.value || catId.value) drop.add('category')
  const keep = all.nodes.filter(n => !drop.has(n.type))
  const ids = new Set(keep.map(n => n.id))
  return {
    nodes: keep,
    edges: all.edges.filter(e => ids.has(e.source) && ids.has(e.target))
  }
})

/** 类型 → 中文名 + 颜色 + 基准半径。 */
const TYPE = {
  category: { label: '分类', color: '#1f4b6b', size: 30 },
  subject: { label: '科目', color: '#3f8f6d', size: 26 },
  topic: { label: '主题', color: '#c08a2e', size: 20 },
  card: { label: '卡片', color: '#a8553f', size: 17 }
}

/** 关系类型 → 中文 + 线色。belong 是结构线，用纸的折痕色（它只是骨架）；
 *  prereq 是「学这个之前得先会那个」，是最有价值的边，用朱砂压住。 */
const KIND = {
  belong: { label: '归属', color: '#c8b894', width: 1, curveness: 0 },
  prereq: { label: '前置', color: '#a8392a', width: 1.8, curveness: 0.12 },
  extends: { label: '延伸', color: '#3f8f6d', width: 1.6, curveness: 0.12 },
  compare: { label: '对比', color: '#c08a2e', width: 1.6, curveness: 0.12 },
  related: { label: '相关', color: '#8a7859', width: 1.2, curveness: 0.1 }
}

const option = computed(() => {
  const nodes = view.value.nodes.map(n => {
    const t = TYPE[n.type] || TYPE.card
    const isPicked = picked.value && n.id === picked.value
    // 卡片节点的大小随度数走：度数高说明它连着很多知识点，是枢纽
    const size = n.type === 'card' ? Math.min(14 + (n.degree || 0) * 1.6, 34) : t.size
    return {
      id: n.id,
      name: n.label,
      // 卡片 title 很长，图上只显示前 12 个字 + 省略号，
      // 完整内容放 tooltip。全显示的话五十个标签会糊成一片
      label: {
        show: n.type !== 'topic' || (n.degree || 0) > 3,
        position: 'right',
        fontSize: 12,
        color: isPicked ? CHART_BG.text : CHART_BG.label,
        formatter: p => {
          const s = String(p.name)
          return s.length > 13 ? s.slice(0, 13) + '…' : s
        }
      },
      symbolSize: isPicked ? size * 1.5 : size,
      itemStyle: {
        color: n.type === 'card' && n.level ? levelColor(n.level) : t.color,
        // 描边用纸面本色：圆点之间靠"露出的纸"分开，比画深色描边干净。
        // 选中时改成靛蓝，跟侧栏选中态是同一个信号
        borderColor: isPicked ? INK.accent : CHART_BG.paper,
        borderWidth: isPicked ? 2.5 : 1.5
      },
      // 自定义字段透传，tooltip 里要用
      _raw: n
    }
  })

  const edges = view.value.edges.map(e => {
    const k = KIND[e.kind] || KIND.related
    const on = picked.value && (e.source === picked.value || e.target === picked.value)
    return {
      source: e.source,
      target: e.target,
      lineStyle: {
        color: k.color,
        width: on ? k.width + 1.4 : k.width,
        curveness: k.curveness,
        opacity: on ? 1 : 0.5
      },
      // 透传关系类型给 tooltip 用（ECharts 不会劫持下划线开头的字段）
      _kind: e.kind
    }
  })

  return {
    ...base,
    tooltip: {
      ...base.tooltip,
      trigger: 'item',
      formatter: p => {
        const d = p.data
        if (!d) return ''
        if (d.source !== undefined) {
          const k = KIND[d._kind] || KIND.related
          return `关系：${k.label}`
        }
        const r = d._raw || {}
        if (r.type === 'card') {
          return (
            `<strong>${escapeHtml(r.label)}</strong><br/>` +
            `<span style="color:${CHART_BG.label}">${escapeHtml((r.oneLine || '').slice(0, 46))}</span><br/>` +
            `连接 ${r.degree ?? 0} 个节点`
          )
        }
        return `<strong>${escapeHtml(r.label)}</strong><br/>${(TYPE[r.type] || TYPE.card).label}`
      }
    },
    // 刻意不用 ECharts 的 legend：graph 系列的图例筛选要求每个节点带
    // category **索引**，而我们的分类是 type 字符串。为了图例再维护一份
    // 「type → 索引」映射，等于把分组逻辑复制一遍 —— 不值得。
    // 右侧「规模」面板已经把类型分布讲清楚了。
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: nodes,
        edges,
        force: {
          // repulsion 随节点数放大：固定值在小图上会把点甩到天边，
          // 在大图上又全糊在中间
          repulsion: Math.max(120, 4200 / Math.max(nodes.length / 12, 1)),
          edgeLength: [40, 110],
          gravity: 0.09,
          friction: 0.12
        },
        emphasis: { focus: 'adjacency', scale: false, lineStyle: { width: 3 } },
        lineStyle: { opacity: 0.5 }
      }
    ]
  }
})

const pickedNode = computed(() => view.value.nodes.find(n => n.id === picked.value) || null)

/** 顶栏 hint 用：现在看的是哪个范围。 */
const modName = computed(() => {
  if (subId.value) {
    const s = subList.value.find(x => x.id === subId.value)
    if (s) return s.name
  }
  if (catId.value) {
    const c = catList.value.find(x => x.id === catId.value)
    if (c) return c.name
  }
  return '全部模块'
})

/** 规模统计跟着**当前子图**走 —— 选了模块却显示全库数字，会让人以为没筛选。 */
const statGroups = computed(() => {
  const c = { category: 0, subject: 0, topic: 0, card: 0 }
  view.value.nodes.forEach(n => {
    if (c[n.type] !== undefined) c[n.type]++
  })
  return Object.entries(c)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({
      key: k,
      label: TYPE[k].label,
      value: v,
      color: TYPE[k].color
    }))
})

/** 关系类型的分布。让用户知道图上有多少 prereq —— 那是真正有用的依赖关系。 */
const edgeStats = computed(() => {
  const c = {}
  view.value.edges.forEach(e => {
    c[e.kind] = (c[e.kind] || 0) + 1
  })
  return Object.entries(c)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({
      key: k,
      label: (KIND[k] || KIND.related).label,
      value: v,
      color: (KIND[k] || KIND.related).color
    }))
})

async function onPick(evt) {
  const id = evt?.data?.id
  if (!id) return
  picked.value = id
  try {
    near.value = (await fetchNeighbors(id)) || { nodes: [], edges: [] }
  } catch {
    near.value = { nodes: [], edges: [] }
  }
}

function openCard(id) {
  router.push({ name: 'cards', query: { open: id } })
}

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// EChart 组件的 click 事件由组件内部透出（见 components/EChart.vue），
// 这里只接结果，不碰 echarts 实例本身
</script>

<template>
  <div class="graph-wrap">
    <section class="panel canvas-panel">
      <header class="panel-head">
        <h3>知识网络</h3>
        <span class="hint">{{ modName }} · 滚轮缩放 · 拖拽节点 · 点击看详情</span>
      </header>

      <!-- 模块筛选：一次只画一个模块，选谁就只有谁 -->
      <div class="mods">
        <button class="mod" :class="{ on: !catId }" @click="pickCat('')">全部</button>
        <button
          v-for="c in catList"
          :key="c.id"
          class="mod"
          :class="{ on: catId === c.id }"
          @click="pickCat(c.id)"
        >
          {{ c.name }}
        </button>
      </div>
      <div v-if="subList.length" class="mods subs">
        <button
          v-for="s in subList"
          :key="s.id"
          class="mod sub"
          :class="{ on: subId === s.id }"
          @click="pickSub(s.id)"
        >
          {{ s.name }}
        </button>
      </div>

      <EChart :option="option" :loading="loading" height="calc(100vh - 230px)" @click="onPick" />
    </section>

    <aside class="side-col">
      <section class="panel">
        <header class="panel-head"><h3>规模</h3></header>
        <dl class="kv">
          <template v-for="g in statGroups" :key="g.key">
            <dt>
              <span class="dot-swatch" :style="{ background: g.color }" />
              {{ g.label }}
            </dt>
            <dd class="mono">{{ g.value }}</dd>
          </template>
        </dl>
      </section>

      <section class="panel">
        <header class="panel-head"><h3>关系类型</h3></header>
        <dl class="kv">
          <template v-for="e in edgeStats" :key="e.key">
            <dt>
              <span class="line-swatch" :style="{ background: e.color }" />
              {{ e.label }}
            </dt>
            <dd class="mono">{{ e.value }}</dd>
          </template>
        </dl>
        <p class="tip">前置（prereq）最有价值：它决定了「该先学哪个」</p>
      </section>

      <section v-if="pickedNode" class="panel detail">
        <header class="panel-head">
          <h3>{{ TYPE[pickedNode.type].label }}详情</h3>
          <button class="btn btn-bare" @click="picked = ''">关闭</button>
        </header>
        <h4 class="d-title">{{ pickedNode.label }}</h4>
        <p v-if="pickedNode.oneLine" class="d-line">{{ pickedNode.oneLine }}</p>

        <div v-if="pickedNode.keywords?.length" class="tags">
          <span v-for="k in pickedNode.keywords" :key="k" class="chip">{{ k }}</span>
        </div>

        <dl class="kv compact">
          <dt>连接数</dt>
          <dd class="mono">{{ pickedNode.degree ?? 0 }}</dd>
          <dt v-if="pickedNode.topic">所属主题</dt>
          <dd v-if="pickedNode.topic">{{ pickedNode.topic }}</dd>
        </dl>

        <button
          v-if="pickedNode.type === 'card'"
          class="btn btn-primary block-btn"
          @click="openCard(pickedNode.id)"
        >
          打开这张卡
        </button>

        <template v-if="near.nodes?.length">
          <div class="sep" style="margin: 14px 0" />
          <h5 class="sub">相邻节点 {{ near.nodes.length }} 个</h5>
          <ul class="near">
            <li v-for="n in near.nodes" :key="n.id">
              <span class="dot" :style="{ background: TYPE[n.type]?.color }" />
              <span class="n-label">{{ n.label }}</span>
              <span class="chip">{{ TYPE[n.type]?.label }}</span>
            </li>
          </ul>
        </template>
      </section>

      <section v-else class="panel">
        <p class="empty small">点一个节点看它的详情和邻居</p>
      </section>
    </aside>
  </div>
</template>

<style scoped>
.graph-wrap {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
}
.canvas-panel {
  min-width: 0;
}

/* 模块筛选 chips。和卡片页同一套形状（圆角胶囊），但底色更轻 ——
   这里是图的工具栏，不该和列表页的导航抢注意力 */
.mods {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.mods.subs {
  margin-bottom: 12px;
}
.mod {
  padding: 5px 13px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--panel);
  color: var(--mu);
  font-size: var(--fs-sm);
  cursor: pointer;
  transition:
    color 0.16s,
    border-color 0.16s,
    background 0.16s;
}
.mod:hover {
  color: var(--tx);
  border-color: var(--ac-dim);
}
.mod.on {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
/* 二级 chips 虚线边：一眼看出它是「分类下的科目」这一档，不是并列的一级 */
.mod.sub {
  border-style: dashed;
  font-size: var(--fs-xs);
  padding: 4px 11px;
}
.mod.sub.on {
  border-style: solid;
}
.side-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 两个 swatch：点表示节点类型，线段表示关系类型。
   形状上就区分开，用户不用读文字也知道在图里该找什么 */
.dot-swatch {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 7px;
  border-radius: 50%;
  vertical-align: 1px;
}
.line-swatch {
  display: inline-block;
  width: 14px;
  height: 2px;
  margin-right: 6px;
  vertical-align: 3px;
  border-radius: 2px;
}
.tip {
  margin-top: 10px;
  font-size: var(--fs-xs);
  color: var(--dim);
  line-height: 1.7;
}

.detail .d-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  line-height: 1.55;
  margin-bottom: 8px;
}
.d-line {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.75;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0;
}
.kv.compact {
  margin-top: 10px;
}
.block-btn {
  width: 100%;
  justify-content: center;
  margin-top: 12px;
}
.sub {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--mu);
  margin-bottom: 8px;
}
.near {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
  max-height: 220px;
  overflow-y: auto;
}
.near li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: var(--fs-sm);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}
.n-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty.small {
  padding: 22px 12px;
}

@media (max-width: 1180px) {
  .graph-wrap {
    grid-template-columns: 1fr;
  }
}
</style>
