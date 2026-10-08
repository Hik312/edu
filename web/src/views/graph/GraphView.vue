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
 *
 * ## 节点大小：degree → PageRank（2026-10-03 换掉）
 *
 * 原来按 `degree`（连着几个节点）画大小。换成后端算的 **PageRank**
 * （`/api/graph/rank`），因为 degree 数的是「我连着几个知识点」，
 * PageRank 数的是「连着我的知识点有多重要」——
 *
 *   AQS 详解        degree 11（全库最高）→ PR 第 40 名
 *   一次阻塞 read() degree  9            → PR 第 1 名
 *
 * AQS 挂了很多 relate，是**造卡时手勤**；一次阻塞 read() 被一堆 JVM
 * 相关的卡指着，是**真的中心**。degree 分不出这个区别，PageRank 可以。
 * 悬停时侧栏同时给出两个数和各自排名，让人看出「它凭什么这么大」。
 *
 * ## 社区配色：Louvain 分块
 *
 * 后端 `/api/graph/insight` 跑 Louvain 社区发现。这一层解决的是
 * 「用户不知道该点哪个 chips」—— 手选分类是按**造卡时分的类**，
 * Louvain 是按**实际连边密度**分的，两者经常对不上
 * （实测：单卡 MySQL 索引 4 张自成一社区，手点 chips 是选不出来）。
 *
 * 配色用 SEQ 循环（多色相、中明度，纸底上都能读）。
 * 结构节点按它**所在社区里最多的那张卡**上色 —— 一个 topic 节点
 * 底下全是 Java 卡，就该是 Java 那支颜色，而不是它自己的黄。
 *
 * ## 模块筛选：一次只看一个模块
 *
 * 全量图（416 卡 + 结构节点）力导向会糊成毛线球，所以顶栏两级 chips：
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EChart from '@/components/EChart.vue'
import {
  catalog as fetchCatalog,
  graph as fetchGraph,
  graphInsight as fetchInsight,
  graphPath as fetchPath,
  graphRank as fetchRank,
  graphRecommend as fetchRecommend,
  neighbors as fetchNeighbors
} from '@/api/system'
import {
  CHART_BG,
  INK,
  LEVEL_COLOR,
  LEVEL_LABEL,
  SEQ,
  chartBase,
  levelColor
} from '@/config/theme'

const router = useRouter()

const base = chartBase()

const raw = ref({ nodes: [], edges: [] })
const loading = ref(true)
/** 当前选中的节点 id。选中后右侧出详情面板。 */
const picked = ref('')
/** 选中节点的邻居（单独拉接口，不全图找）。 */
const near = ref({ nodes: [], edges: [] })

/** 结构洞察：PageRank / Betweenness / Louvain 社区 / 连通性体检。
 *  比 /graph 重（要跑 60 次幂迭代），所以**和图分开加载**——
 *  图先出来能看，指标后到不影响交互。 */
const insight = ref(null)
/** id → {pagerank, pagerankRank, pagerankPct, betweenness, community} */
const rankOf = ref({})
/** 个性化 PageRank 推荐。种子 = 当前用户「不会」的卡。 */
const reco = ref(null)
/** 路径高亮：从 A 点到 B 点的最短 prereq 链（节点 id 序列）。 */
const pathNodes = ref([])
const pathEdges = ref([])
/** 路径说明 / 找不到的原因。空串 = 没在查路径。 */
const pathNote = ref('')
/** 社区筛选：null = 不筛。存社区序号。 */
const commFilter = ref(null)
/** 等级筛选：只看掌握度 ≤ 这个值。null = 不筛。 */
const levelFilter = ref(null)

/** 模块选择：两级 chips（全部 → 分类 → 科目）。和卡片页同一套交互。 */
const catList = ref([])
const catId = ref('')
const subId = ref('')

const LEVELS = [
  { v: 1, label: '不会', color: INK.weak },
  { v: 2, label: '模糊', color: INK.fuzzy },
  { v: 3, label: '会', color: INK.known },
  { v: 0, label: '未学', color: INK.unmarked }
]

/** 选了科目才有的二级 chips。没选分类就不给选科目 —— 跨分类的科目名会重。 */
const subList = computed(() => {
  if (!catId.value) return []
  const hit = catList.value.find(c => c.id === catId.value)
  return hit ? hit.subjects || [] : []
})

/**
 * 页面上当前**可见**的卡片 id。
 *
 * 为什么要单独算：排名 / 推荐 / 路径全都是全库口径算的，但图上是筛过的。
 * 直接把全库 PageRank 画到「只选了 python」的图上，那个 0.0047 可能是
 * 一张 Java 卡 —— 数字和画出来的东西对不上，用户会以为算错了。
 * 可见集合内重新归一化才对。
 */
const visibleIds = computed(() => {
  const keep = view.value.nodes.filter(n => n.type === 'card')
  return keep.map(n => n.id)
})

/** 当前视图内的 PageRank 归一化到 0~1（用于画大小）。 */
const prNorm = computed(() => {
  const ids = new Set(visibleIds.value)
  const vals = []
  for (const [id, r] of Object.entries(rankOf.value)) {
    if (ids.has(id)) vals.push(r.pagerank || 0)
  }
  if (!vals.length) return {}
  const lo = Math.min(...vals)
  const hi = Math.max(...vals)
  const span = hi - lo
  const out = {}
  for (const [id, r] of Object.entries(rankOf.value)) {
    if (!ids.has(id)) continue
    // span 为 0（全库同分）时不能除，直接给 0.5 —— 否则 NaN 会让
    // symbolSize 变 undefined，ECharts 会把节点画成默认大小甚至不画
    out[id] = span > 1e-12 ? ((r.pagerank || 0) - lo) / span : 0.5
  }
  return out
})

/** 社区 → 颜色（SEQ 循环）。结构节点跟着它下面最多的卡走，见文件头。 */
const commColor = computed(() => {
  const map = {}
  const comms = insight.value?.communities || []
  comms.forEach((c, i) => { map[i] = SEQ[i % SEQ.length] })

  // id → 社区序号。建一次，别在每次画节点时 O(社区数×成员数) 地找
  const commOf = {}
  comms.forEach((c, i) => { for (const m of c.members) commOf[m] = i })
  // painted 只有「够大」的社区才有颜色（阈值同 commLegend）。
  // 散卡社区的卡按 TYPE 本色画 —— 见 commLegend 的说明。
  const painted = {}
  comms.forEach((c, i) => { if (c.size >= 6) painted[i] = map[i] })

  // 结构节点（category/subject/topic）继承其子节点的社区众数：
  // 一个 topic 底下全是 Java 卡，它就该是 Java 那支颜色。
  const children = {}
  for (const e of raw.value.edges) {
    if (e.kind !== 'belong') continue
    ;(children[e.source] = children[e.source] || []).push(e.target)
  }
  const structural = {}
  for (const n of raw.value.nodes) {
    if (n.type === 'card') continue
    const cnt = {}
    for (const k of children[n.id] || []) {
      const ci = commOf[k]
      if (ci !== undefined) cnt[ci] = (cnt[ci] || 0) + 1
    }
    const top = Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a])[0]
    if (top !== undefined) structural[n.id] = map[top]
  }
  return { map, structural, commOf, painted }
})

/** 社区列表（带颜色和规模），给图例筛选用。
 *
 *  ★ 只给「卡数 >= 6」的社区上色。散卡社区（AI 工程里的 A2A、
 *    Red Teaming 那一小撮）也有社区号，但把它染成第 15 种颜色
 *    只会让图变成调色盘 —— 那些卡按 TYPE 的本色 + 掌握度色走更清楚。
 *    它们仍然**可以被点开**（筛选是有用的），只是不抢颜色。
 */
const commLegend = computed(() => {
  const comms = insight.value?.communities || []
  return comms.map((c, i) => ({
    idx: i,
    size: c.size,
    cardCount: (c.members || []).length,
    label: communityName(c),
    color: c.size >= 6 ? commColor.value.map[i] : null
  }))
})

/** 社区起名：优先用 subject / category（有意义的模块名）。
 *
 *  不用编号（「社区 3」）—— 用户看到编号没法判断该不该点。
 *  三级兜底：
 *   1. subject / category → 直接用（这是真正的模块名）
 *   2. 成员里有 topic → 用**最浅的那个 topic**（depth 小的靠近章节根部），
 *      比「首张卡的标题」准 —— 一个只装了 15 张卡的 RAG 社区，
 *      叫「高级 RAG 变体…」比叫「A2A 协议…」贴切。
 *   3. 都没有（纯卡社区）→ 首卡标题 + 「等 N 张」，标明它是卡簇不是科目。
 *  真的一个成员都取不到才叫「（空）」—— 那是数据出问题了，不是命名问题。
 */
function communityName(c) {
  const nodeOf = new Map(raw.value.nodes.map(n => [n.id, n]))
  const members = (c.members || []).map(m => nodeOf.get(m)).filter(Boolean)
  const root = members.find(n => n.type === 'subject')
    || members.find(n => n.type === 'category')
  if (root) return root.label
  const topics = members.filter(n => n.type === 'topic')
    .sort((a, b) => (a.depth ?? 9) - (b.depth ?? 9))
  if (topics.length) return topics[0].label
  const cards = members.filter(n => n.type === 'card')
  if (!cards.length) return '（空）'
  const first = String(cards[0].label || '').slice(0, 10)
  return cards.length > 1 ? `${first} 等 ${cards.length} 张` : first
}

async function loadGraph() {
  loading.value = true
  picked.value = ''
  near.value = { nodes: [], edges: [] }
  pathNodes.value = []
  pathEdges.value = []
  localStorage.setItem('edu.graph', catId.value + '|' + subId.value)
  try {
    // 科目优先：选了科目就只按科目过滤（后端 all_cards 里 subject 也带 category 归属）
    const p = {}
    if (subId.value) p.subject = subId.value
    else if (catId.value) p.category = catId.value
    const r = await fetchGraph(Object.keys(p).length ? p : undefined)
    raw.value = r.graph || { nodes: [], edges: [] }
    // await：rankOf 要在图渲染前到位，否则第一帧画的是 degree 大小，
    // 排名回来再跳一下 —— 用户会以为图在抖。拉不到也只是退回 degree。
    await loadRanks()
    // 洞察跟着图一起重拉（同口径，见 loadInsight 的注释）。不 await：
    // 图已经能看了，社区色和侧栏榜稍后补上。
    loadInsight()
  } finally {
    loading.value = false
  }
}

/** 排名要按「可见的卡」批量问，所以依赖 view —— 图一变就重问。
 *
 *  缓存命中在后端（5 分钟 TTL + mtime 失效），问起来不贵；
 *  但也别在 onMounted 里跟图一起并发 —— 那会儿还不知道可见集合是谁。 */
async function loadRanks() {
  const ids = visibleIds.value
  if (!ids.length) {
    rankOf.value = {}
    return
  }
  try {
    const r = await fetchRank(ids.slice(0, 50))
    rankOf.value = r.ranks || {}
  } catch {
    // 排名拿不到不是致命错：图还能画，只是节点大小退回 degree。
    // 静默降级，别弹 toast 打断正在看图的人。
    rankOf.value = {}
  }
}

/** 洞察和推荐：**跟着当前筛选走**。
 *
 *  ★ 这里原来写成「只在首次进入时拉一次、指标是全库口径」—— 错了。
 *    图是带筛选的（切了科目就只剩那个科目），社区却是全库算的，
 *    于是 communityName 拿「筛后的 nodes」去查「全库的 members」，
 *    一个 id 都对不上，图例 13/14 全变成「（空）」。
 *    而且 PageRank 本来就依赖图的连通范围：全库算出来的排名，
 *    画到只含一个科目的图上，数字和画出来的东西对不上。
 *    顺带一提：recommend 也必须跟着筛选走，不然在「AI 工程」模块里
 *    推一张 Java 卡，用户点了就跳到别的模块去了。
 */
async function loadInsight() {
  const p = {}
  if (subId.value) p.subject = subId.value
  else if (catId.value) p.category = catId.value
  try {
    const r = await fetchInsight(p)
    insight.value = r && !r.empty ? r : null
  } catch {
    insight.value = null
  }
  try {
    const r = await fetchRecommend({ ...p, limit: 8 })
    reco.value = r || null
  } catch {
    reco.value = null
  }
}

function pickCat(id) {
  catId.value = id
  subId.value = '' // 换了分类就把上一个分类的科目清掉，否则筛出空图
  resetFilters()
  loadGraph()
}

function pickSub(id) {
  // 再点一次同一个科目就取消，省得用户找不到「取消筛选」的按钮
  subId.value = subId.value === id ? '' : id
  resetFilters()
  loadGraph()
}

/** 换模块时把社区/等级筛选一起清掉。
 *
 *  为什么必须清：模块换了以后原社区序号在新图里根本不存在，
 *  commFilter 还留着的话 view 会筛出**空节点集** —— 图整个空白，
 *  而 chips 上还显示着「社区 2 已选」，用户完全不知道发生了什么。
 */
function resetFilters() {
  commFilter.value = null
  levelFilter.value = null
  pathNodes.value = []
  pathEdges.value = []
}

function toggleComm(idx) {
  commFilter.value = commFilter.value === idx ? null : idx
  pathNodes.value = []
  pathEdges.value = []
}

function toggleLevel(lv) {
  levelFilter.value = levelFilter.value === lv ? null : lv
  pathNodes.value = []
  pathEdges.value = []
}

/** 找出 A → B 的最短学习路径并高亮。
 *
 * found=false 是**正常答案**（当前 234 条 prereq 全是一跳，
 * 大多数两张卡之间根本没有依赖链），所以显示后端给的 reason，
 * 不弹错误 —— 让用户以为操作失败是最差的处理。
 */
async function showPath(a, b) {
  if (!a || !b || a === b) {
    clearPath()
    return
  }
  try {
    const r = await fetchPath(a, b)
    if (r.found && r.nodes?.length) {
      pathNodes.value = r.nodes.map(n => n.id)
      pathEdges.value = r.edges || []
      pathNote.value = `${r.nodes.length - 1} 跳前置链：${r.nodes.map(n => n.label).join(' → ')}`
    } else {
      pathNodes.value = []
      pathEdges.value = []
      pathNote.value = r.reason || '两卡之间没有依赖链'
    }
  } catch {
    pathNodes.value = []
    pathEdges.value = []
    pathNote.value = '路径查询失败'
  }
}

function clearPath() {
  pathNodes.value = []
  pathEdges.value = []
  pathNote.value = ''
}

/** 路径模式开关。开了之后点节点是选端点，不是看详情。 */
const pathMode = ref(false)

/** 路径起点：点第一个节点时记下来，第二个节点到了就自动查链。 */
const pathFrom = ref('')

/** 切路径模式前先清掉上一次的结果 —— 留着一条旧链会让人以为
 *  新选的两个点之间也有这条依赖。 */
function togglePathMode() {
  pathMode.value = !pathMode.value
  pathFrom.value = ''
  clearPath()
}

function onPathPick(id) {
  if (!pathFrom.value) {
    pathFrom.value = id
    pathNote.value = '再点一个节点，算两者的最短前置链'
    return
  }
  if (pathFrom.value === id) {
    pathFrom.value = ''
    clearPath()
    return
  }
  const a = pathFrom.value
  pathFrom.value = ''
  showPath(a, id)
}

onMounted(async () => {
  // 上次看的模块记住（localStorage，不占后端）。格式 cat|sub，空段就是没选。
  // 首次进来默认「工作」而不是「全部」：全量 150 节点力导向就是一坨毛线球，
  // 而这一页存在的意义就是分模块看。「全部」仍然是第一颗 chips，一击可切。
  const saved = localStorage.getItem('edu.graph')
  const [c0, s0] = (saved === null ? 'work|' : saved).split('|')
  catId.value = c0 || ''
  subId.value = s0 || ''
  // 洞察由 loadGraph 内部触发（必须跟图同口径），这里不再单独拉。
  await loadGraph()
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
      await loadGraph()
    }
  } catch {
    catList.value = [] // 分类树拿不到就只剩「全部」，图谱照常能看
  }
})

/**
 * 当前选择下的子图，**依次**做四层筛选：
 *   1. 按模块范围裁结构节点（去掉没信息量的 category 层）
 *   2. 按社区筛（commFilter）
 *   3. 按掌握度筛（levelFilter：只看 level ≤ N 的，0 档是「未学」要并进来）
 *   4. 把两端都还在的边留下
 *
 * 顺序不能反 —— 先留边会留下指向已裁节点的悬空边，ECharts 直接不画。
 *
 * ★ levelFilter 里 0 的处理：等级 0 = 未标记（压根没学过），
 *   它不是「不会」，但用户点「只看不会的」时显然也该看到没学过的 ——
 *   否则一个全新用户筛「不会」会看到空图，还以为图挂了。
 */
const view = computed(() => {
  const all = raw.value
  const drop = new Set()
  if (subId.value || catId.value) drop.add('category')
  let keep = all.nodes.filter(n => !drop.has(n.type))

  if (commFilter.value !== null) {
    const inComm = new Set(
      (insight.value?.communities?.[commFilter.value]?.members) || []
    )
    keep = keep.filter(n => inComm.has(n.id))
  }

  if (levelFilter.value !== null) {
    const want = Number(levelFilter.value)
    keep = keep.filter(n => {
      if (n.type !== 'card') return false // 结构节点没有掌握度，一起藏起来
      const lv = n.level || 0
      return want === 0 ? lv === 0 : lv > 0 && lv <= want
    })
  }

  const ids = new Set(keep.map(n => n.id))
  return {
    nodes: keep,
    edges: all.edges.filter(e => ids.has(e.source) && ids.has(e.target))
  }
})

/** 路径高亮的边集合（source|target 的无序对，便于 O(1) 查）。 */
const pathEdgeSet = computed(() => {
  const s = new Set()
  const ns = pathNodes.value
  for (let i = 0; i + 1 < ns.length; i++) {
    s.add([ns[i], ns[i + 1]].sort().join('|'))
  }
  return s
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
  const pset = new Set(pathNodes.value)
  const pEdge = pathEdgeSet.value

  const nodes = view.value.nodes.map(n => {
    const t = TYPE[n.type] || TYPE.card
    const isPicked = picked.value && n.id === picked.value
    const onPath = pset.has(n.id)
    const pr = n.type === 'card' ? prNorm.value[n.id] : undefined

    // 节点大小：卡片走 PageRank（见文件头），结构节点仍按类型固定尺寸。
    // ★ 就算排名没拉到（rankOf 空）也要退回 degree，不能变成 0：
    //   symbolSize 0 = 节点完全不可见，用户会以为图空了。
    const size = n.type === 'card'
      ? (pr === undefined
          ? Math.min(12 + (n.degree || 0) * 1.6, 32)
          : Math.round(13 + pr * 21))
      : t.size

    // 颜色优先级：路径高亮 > 掌握度 > 社区 > 类型本色
    // （掌握度优先于社区：用户最想知道的是「哪些还没学会」，
    //   社区是导航信息，不该压过学习状态）
    let color = t.color
    if (n.type === 'card') {
      // 社区色作底，掌握度覆盖上去。没筛社区时不给社区上色 ——
      // 否则 17 个社区的色相 + 4 个掌握度色相混在一起，图会花掉。
      const ci = commColor.value.commOf[n.id]
      if (commFilter.value === null && ci !== undefined) {
        color = commColor.value.painted[ci] || t.color
      }
      if (n.level) color = levelColor(n.level)
    } else {
      color = commColor.value.structural[n.id] || t.color
    }
    if (onPath) color = INK.accent

    return {
      id: n.id,
      name: n.label,
      // 卡片 title 很长，图上只显示前 12 个字 + 省略号，
      // 完整内容放 tooltip。全显示的话五十个标签会糊成一片
      label: {
        show: n.type !== 'topic' || (n.degree || 0) > 3,
        position: 'right',
        fontSize: 12,
        color: isPicked || onPath ? CHART_BG.text : CHART_BG.label,
        formatter: p => {
          const s = String(p.name)
          return s.length > 13 ? s.slice(0, 13) + '…' : s
        }
      },
      symbolSize: isPicked ? size * 1.5 : size,
      itemStyle: {
        color,
        // 描边用纸面本色：圆点之间靠"露出的纸"分开，比画深色描边干净。
        // 选中时改成靛蓝，跟侧栏选中态是同一个信号
        borderColor: isPicked || onPath ? INK.accent : CHART_BG.paper,
        borderWidth: isPicked || onPath ? 2.5 : 1.5
      },
      // 自定义字段透传，tooltip 里要用
      _raw: n,
      _rank: rankOf.value[n.id] || null
    }
  })

  const edges = view.value.edges.map(e => {
    const k = KIND[e.kind] || KIND.related
    const on = picked.value && (e.source === picked.value || e.target === picked.value)
    const isPath = pEdge.has([e.source, e.target].sort().join('|'))
    return {
      source: e.source,
      target: e.target,
      lineStyle: {
        color: isPath ? INK.accent : k.color,
        width: isPath ? k.width + 2.4 : on ? k.width + 1.4 : k.width,
        curveness: k.curveness,
        // 非路径边压淡：路径高亮时要看清那条链，其余退成背景
        opacity: pset.size && !isPath ? 0.12 : on || isPath ? 1 : 0.5
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
          // 把「为什么这么大」讲清楚：PageRank 和 degree 排一起，
          // 用户能看出这张卡是真中心还是 related 填得多
          const rk = d._rank
          const rankLine = rk
            ? `<br/>PageRank ${fmtNum(rk.pagerank)}（超过全图 ${rk.pagerankPct}%）` +
              ` · 连着 ${r.degree ?? 0} 个`
            : `<br/>连着 ${r.degree ?? 0} 个`
          return (
            `<strong>${escapeHtml(r.label)}</strong><br/>` +
            `<span style="color:${CHART_BG.label}">${escapeHtml((r.oneLine || '').slice(0, 46))}</span>` +
            rankLine
          )
        }
        return `<strong>${escapeHtml(r.label)}</strong><br/>${(TYPE[r.type] || TYPE.card).label}`
      }
    },
    // 刻意不用 ECharts 的 legend：graph 系列的图例筛选要求每个节点带
    // category **索引**，而我们的分类是 type 字符串。为了图例再维护一份
    // 「type → 索引」映射，等于把分组逻辑复制一遍 —— 不值得。
    // 社区图例是自己画的（要显示社区规模 + 起名，见 commLegend）。
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

/** PageRank 是小数，直接显示会是一串 0.00217323…，用科学计数反而好读。 */
function fmtNum(v) {
  const n = Number(v) || 0
  return n >= 0.01 ? n.toFixed(4) : n.toExponential(2)
}

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

/**
 * 节点太多时力导向必糊（ECharts 的四叉树近似再稳，400 个点摊在
 * 一张图上标签也压不住）。给一句人话建议 + 一步可达的操作，
 * 而不是让用户自己在 chips 里猜该点哪个。
 *
 * 阈值 160 是实测来的：160 节点以内标签能读、布局不塌；超过就开始
 * 连成一片（原来 391 节点的截图就是一团糊）。
 */
const tooMany = computed(() => ({
  n: view.value.nodes.length,
  busy: view.value.nodes.length > 160,
  // 推荐下一手：当前分类下卡最多的那个科目
  hint: (() => {
    const subs = (subList.value.length ? subList.value : [])
      .map(s => {
        const c = raw.value.nodes.filter(
          x => x.type === 'card' && (x.cat || '') === catId.value && (x.sub || '') === s.id
        ).length
        return { id: s.id, name: s.name, n: c }
      })
      .filter(x => x.n > 0)
      .sort((a, b) => b.n - a.n)
    return subs[0] || null
  })()
}))

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

/** 连通性体检。孤岛率高 = 该补 related，这是**数据现状**不是算法出错。 */
const covStat = computed(() => {
  const c = insight.value?.coverage
  if (!c) return null
  return {
    nodes: c.nodes,
    cards: c.cards,
    edges: c.edges,
    components: c.components,
    largest: c.largest,
    coverage: Math.round((c.coverage || 0) * 100),
    orphanCards: c.orphanCards,
    orphanRate: Math.round((c.orphanRate || 0) * 100)
  }
})

/** 当前选中卡的排名信息 + 它所属社区名。 */
const pickedRank = computed(() => (picked.value ? rankOf.value[picked.value] : null) || null)
const pickedCommName = computed(() => {
  if (!picked.value) return ''
  const ci = commColor.value.commOf[picked.value]
  if (ci === undefined) return ''
  const c = insight.value?.communities?.[ci]
  return c ? communityName(c) : ''
})

/** 推荐列表。allDone 时给一句「都学完了」而不是空面板。 */
const recoList = computed(() => {
  if (!reco.value || reco.value.empty) return []
  if (reco.value.allDone) return []
  return reco.value.items || []
})

/** 薄弱点摘要：告诉用户推荐是从什么出发的。 */
const recoMeta = computed(() => {
  const r = reco.value
  if (!r || r.empty) return null
  return {
    weakCount: r.weakCount ?? 0,
    seedCount: r.seedCount ?? 0,
    algo: r.algo || 'pagerank',
    note: r.note || ''
  }
})

/** 选中某节点并拉它的邻居子图。
 *
 *  ★ 章节节点（category/subject/topic）必须开 untilCards：卡挂在
 *    subject → topic → … → card 的深层，固定 1 跳点章节只会拉回一堆
 *    章节节点，一张卡都看不见（第二张截图就是这个现象）。
 *    卡节点自己就是终点，开了也没影响，所以统一按类型判断。 */
async function selectNode(id) {
  picked.value = id
  const node = raw.value.nodes.find(n => n.id === id)
  const untilCards = !!node && node.type !== 'card'
  try {
    near.value = (await fetchNeighbors(id, 1, untilCards)) || { nodes: [], edges: [] }
  } catch {
    near.value = { nodes: [], edges: [] }
  }
}

async function onPick(evt) {
  const id = evt?.data?.id
  if (!id) return
  // 路径模式下点节点是选路径端点，不弹详情 —— 否则每选一个端点
  // 侧栏就被邻居列表刷掉，用户还没选第二个端点就找不到原来的位置了
  if (pathMode.value) {
    onPathPick(id)
    return
  }
  await selectNode(id)
}

function openCard(id) {
  router.push({ name: 'cards', query: { open: id } })
}

/** 点推荐/邻居/榜单里的卡 → 在图上定位并选中它。
 *
 * ★ 定位靠 ECharts 的 dispatchAction —— 但本项目的 EChart 组件只透传
 *   click，不透出实例，所以这里用「改 picked + 清筛选」代替
 *   dispatchAction：把模块筛选放开到能看见这张卡的范围。
 *   做不到精确居中，但保证「点了之后图上看得见它」—— 这才是关键。 */
async function locateCard(id) {
  const node = raw.value.nodes.find(n => n.id === id)
  if (!node) return
  // 放开可能挡住它的筛选
  if (commFilter.value !== null) commFilter.value = null
  if (levelFilter.value !== null) levelFilter.value = null
  // 放开模块筛选：卡可能在别的科目里
  if (subId.value || catId.value) {
    catId.value = ''
    subId.value = ''
    await loadGraph()
  }
  await loadRanks()
  await selectNode(id)
}

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/** 卡 id → 标题。给「推荐理由」用：只显示「因为 A、B」不给 id。 */
function cardTitle(cid) {
  const n = raw.value.nodes.find(x => x.id === cid)
  const s = String(n?.label || cid)
  return s.length > 16 ? s.slice(0, 16) + '…' : s
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

      <!-- 路径模式：开了之后点节点是选端点，不是看详情 -->
      <div class="toolbar">
        <button
          class="mod"
          :class="{ on: pathMode }"
          :title="pathMode ? '再点两个节点算前置链' : '算两张卡之间的最短学习路径'"
          @click="togglePathMode"
        >
          {{ pathMode ? '路径模式 · 开' : '查学习路径' }}
        </button>
        <span v-if="pathMode" class="tool-note">
          {{
            pathFrom
              ? '已选起点，再点一个节点'
              : '点第一个节点作为起点'
          }}
        </span>
        <span v-else-if="pathNote" class="tool-note">{{ pathNote }}</span>
        <span class="spacer" />
        <!-- 掌握度筛选：找出「还没学会的」在图里的位置 -->
        <span class="tool-label">只看</span>
        <button
          v-for="l in LEVELS"
          :key="l.v"
          class="mod lv"
          :class="{ on: levelFilter === l.v }"
          @click="toggleLevel(l.v)"
        >
          <span class="dot-swatch" :style="{ background: l.color }" />
          {{ l.label }}
        </button>
        <button v-if="levelFilter !== null" class="btn btn-bare" @click="levelFilter = null">
          取消
        </button>
      </div>

      <!-- 社区图例（Louvain）。点一下只留这个社区。
           灰色点 = 散卡社区（<6 张），不参与配色但仍可筛 -->
      <div v-if="commLegend.length" class="comms">
        <span class="tool-label">社区</span>
        <button
          v-for="c in commLegend"
          :key="c.idx"
          class="mod comm"
          :class="{ on: commFilter === c.idx }"
          :title="c.size + ' 个节点'"
          @click="toggleComm(c.idx)"
        >
          <span
            class="dot-swatch"
            :style="c.color
              ? { background: c.color }
              : { background: 'var(--dim)', opacity: 0.5 }"
          />
          {{ c.label }}
          <span class="cnt mono">{{ c.size }}</span>
        </button>
        <button v-if="commFilter !== null" class="btn btn-bare" @click="commFilter = null">
          显示全部
        </button>
      </div>

      <!-- 节点太多时力导向必糊。与其让用户自己猜该点哪个科目，
           不如直接说清「为什么糊」并给一个具体的下一步。 -->
      <p v-if="tooMany.busy" class="crowd">
        当前 {{ tooMany.n }} 个节点，力导向会把它们压成一团 ——
        选个科目或社区看细节。
        <button
          v-if="tooMany.hint"
          class="link"
          @click="pickSub(tooMany.hint.id)"
        >
          看「{{ tooMany.hint.name }}」（{{ tooMany.hint.n }} 张卡）
        </button>
      </p>

      <div class="canvas-holder">
        <EChart :option="option" :loading="loading" height="100%" @click="onPick" />
      </div>
    </section>

    <aside class="side-col">
      <!-- 图的体检报告。孤岛率是**数据现状**不是 bug，得让人看见。 -->
      <section v-if="covStat" class="panel">
        <header class="panel-head"><h3>图结构</h3></header>
        <dl class="kv">
          <dt>卡片</dt>
          <dd class="mono">{{ covStat.cards }}</dd>
          <dt>关系边</dt>
          <dd class="mono">{{ covStat.edges }}</dd>
          <dt>连通块</dt>
          <dd class="mono">{{ covStat.components }}</dd>
          <dt>最大连通块</dt>
          <dd class="mono">{{ covStat.largest }}（{{ covStat.coverage }}%）</dd>
        </dl>
        <p v-if="covStat.orphanCards" class="tip warn">
          {{ covStat.orphanCards }} 张卡（{{ covStat.orphanRate }}%）只连着 0~1 个知识点 ——
          该给它们补 related，否则图算法算不到它们。
        </p>
      </section>

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

      <!-- 全局权威知识点（PageRank）。可点，点了在图上定位。 -->
      <section v-if="insight?.pagerank?.length" class="panel">
        <header class="panel-head"><h3>核心知识点</h3></header>
        <p class="tip top">按 PageRank 排 —— 「连着我的知识点有多重要」，比单纯数连接数准</p>
        <ul class="rank-list">
          <li v-for="(x, i) in insight.pagerank.slice(0, 8)" :key="x.id">
            <button class="rank-row" @click="locateCard(x.id)">
              <span class="rank-no mono">{{ i + 1 }}</span>
              <span class="rank-label">{{ x.label }}</span>
              <span class="chip deg" :title="'连接数 ' + x.degree">
                {{ x.degree }} 连
              </span>
            </button>
          </li>
        </ul>
      </section>

      <!-- 个性化推荐：PPR 从「不会的」往外推 -->
      <section class="panel">
        <header class="panel-head"><h3>该学什么</h3></header>
        <template v-if="reco?.allDone">
          <p class="empty small">{{ reco.reason }}</p>
        </template>
        <template v-else-if="recoList.length">
          <p v-if="recoMeta" class="tip top">
            以 {{ recoMeta.weakCount }} 张薄弱点为种子（取最紧急的
            {{ recoMeta.seedCount }} 张）向外扩散
          </p>
          <p v-if="recoMeta?.note" class="tip warn">{{ recoMeta.note }}</p>
          <ul class="reco-list">
            <li v-for="x in recoList" :key="x.id">
              <button class="reco-row" @click="locateCard(x.id)">
                <span class="rank-label">{{ x.label }}</span>
                <span class="chip lv" :style="{ background: LEVEL_COLOR[x.level] }">
                  {{ LEVEL_LABEL[x.level] }}
                </span>
              </button>
              <p v-if="x.because?.length" class="because">
                因为你不会：
                <span v-for="(b, j) in x.because" :key="b">{{ cardTitle(b) }}</span>
              </p>
            </li>
          </ul>
        </template>
        <p v-else class="empty small">图算法还没算完，或者没有可推荐的卡</p>
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

        <!-- 排名：把「这张卡有多重要」摆出来，且和连接数并排，
             让人看出 degree 高 ≠ 重要 -->
        <dl v-if="pickedNode.type === 'card'" class="kv compact">
          <dt>PageRank</dt>
          <dd class="mono">
            {{ pickedRank ? pickedRank.pagerank.toFixed(5) : '—' }}
            <span v-if="pickedRank" class="dim">
              （超过全图 {{ pickedRank.pagerankPct }}%）
            </span>
          </dd>
          <dt>连接数</dt>
          <dd class="mono">{{ pickedNode.degree ?? 0 }}</dd>
        </dl>
        <dl class="kv compact">
          <dt v-if="pickedCommName">所属社区</dt>
          <dd v-if="pickedCommName">{{ pickedCommName }}</dd>
          <dt v-if="pickedNode.topic">所属主题</dt>
          <dd v-if="pickedNode.topic">{{ pickedNode.topic }}</dd>
          <dt v-if="pathNodes.includes(pickedNode.id)">在路径上</dt>
          <dd v-if="pathNodes.includes(pickedNode.id)">
            第 {{ pathNodes.indexOf(pickedNode.id) + 1 }} / {{ pathNodes.length }} 站
          </dd>
        </dl>

        <div v-if="pickedNode.type === 'card'" class="btn-row">
          <button class="btn btn-primary" @click="openCard(pickedNode.id)">
            打开这张卡
          </button>
          <button
            class="btn"
            :class="{ 'btn-on': pathMode }"
            :title="pathMode ? '已开路径模式，再点一个节点算链' : '以这张卡为起点查路径'"
            @click="pathMode ? onPathPick(pickedNode.id) : (pathMode = true, pathFrom = pickedNode.id)"
          >
            查它的学习路径
          </button>
        </div>

        <template v-if="near.nodes?.length > 1">
          <div class="sep" style="margin: 14px 0" />
          <h5 class="sub">相邻节点 {{ near.nodes.length - 1 }} 个</h5>
          <ul class="near">
            <li v-for="n in near.nodes" :key="n.id">
              <button v-if="n.id !== pickedNode.id" class="near-row" @click="locateCard(n.id)">
                <span class="dot" :style="{ background: TYPE[n.type]?.color }" />
                <span class="n-label">{{ n.label }}</span>
                <span class="chip">{{ TYPE[n.type]?.label }}</span>
              </button>
            </li>
          </ul>
        </template>
      </section>

      <section v-else class="panel">
        <p class="empty small">
          点一个节点看它的详情和邻居。<br />
          想看「该先学哪张」→ 用上面的<b>该学什么</b>；<br />
          想看「两张卡之间怎么走」→ 开<b>查学习路径</b>。
        </p>
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

/* 宽屏：左侧画布固定，右侧栏独立滚动（滚侧栏不动画布）。原理同 GenerateView：
   根容器占满 .content，列 stretch 后右侧栏自己 overflow。窄屏单列，整页滚。 */
@media (min-width: 1181px) {
  .graph-wrap {
    height: 100%;
    align-items: stretch;
  }
  .canvas-panel {
    min-height: 0;
  }
  .side-col {
    min-height: 0;
    overflow-y: auto;
  }
}
.canvas-panel {
  min-width: 0;
  /* 画布这一列改成 flex 纵向：让 EChart 去填「标题+筛选+工具栏」以下的剩余高度。
     之前写死 height="calc(100vh - 320px)"，可这列顶上还有标题/分类/工具栏/社区图例
     一堆固定高度元素，两段相加比内容区还高 → 画布撑出面板（用户反馈「超出了」）。
     改成 flex 填充后，画布高度由面板决定，和右栏一样被内容区约束住。 */
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 画布容器：flex:1 吃掉面板剩余高度，EChart 传 height="100%" 去填它。
   ⚠️ flex 子项要能缩到内容以下必须 min-height:0，否则内容顶死不滚。 */
.canvas-holder {
  flex: 1;
  min-height: 0;
}
/* 窄屏（单列、整页滚）：面板是auto 高度，flex:1 会塌成 0 —— 给个确定高度。 */
@media (max-width: 1180px) {
  .canvas-holder {
    flex: none;
    height: calc(100vh - 320px);
  }
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

/* ---- 工具条（路径模式 + 等级筛选） ----
   和 .mods 分开画一条分隔：上面那排是「看哪一块」（导航），
   这条是「在图里找什么」（操作），混在一排会让人以为是一组 chips */
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 10px 0 8px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.tool-label {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.tool-note {
  font-size: var(--fs-xs);
  color: var(--ac);
}
.spacer {
  flex: 1;
}
.mod.lv {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: var(--fs-xs);
}

/* 社区图例。模块尺寸跟着社区大小排，看起来就是「谁大谁小」 */
.comms {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.mod.comm {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: var(--fs-xs);
}
.cnt {
  color: var(--dim);
  font-size: 11px;
}

/* ---- 榜单 / 推荐 ---- */
.rank-list,
.reco-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 8px 0 0;
}
.rank-row,
.reco-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 5px 7px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--tx);
  font-size: var(--fs-sm);
  text-align: left;
  cursor: pointer;
  transition: background 0.14s;
}
.rank-row:hover,
.reco-row:hover {
  background: var(--ac-glow);
}
.rank-no {
  flex: none;
  width: 17px;
  font-size: 11px;
  color: var(--dim);
  text-align: right;
}
.rank-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chip.deg {
  flex: none;
  font-size: 11px;
  color: var(--dim);
}
/* 推荐理由：为什么推它。非灰度小字 —— 这是让用户相信推荐的唯一凭据 */
.because {
  margin: 1px 0 6px 32px;
  font-size: var(--fs-xs);
  color: var(--dim);
  line-height: 1.6;
}
.because span {
  display: inline-block;
  margin-right: 5px;
  padding: 1px 5px;
  border: 1px solid var(--line);
  border-radius: 4px;
  color: var(--mu);
}
.btn-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.btn-row .btn {
  flex: 1;
  justify-content: center;
}
.btn-on {
  border-color: var(--ac);
  color: var(--ac);
  background: var(--ac-glow);
}
/* 邻居行也做成可点的（原来只是纯文本，点不动 —— 详情面板里
   能直接跳到相邻节点才算「以这张卡为中心看图」） */
.near-row {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 3px 5px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: inherit;
  font-size: var(--fs-sm);
  text-align: left;
  cursor: pointer;
}
.near-row:hover {
  background: var(--ac-glow);
}
.tip.top {
  margin: 2px 0 0;
}
.crowd {
  margin: 0 0 10px;
  padding: 7px 11px;
  border-left: 2px solid var(--ac-dim);
  border-radius: 0 5px 5px 0;
  background: var(--ac-glow);
  font-size: var(--fs-xs);
  color: var(--mu);
  line-height: 1.7;
}
/* 「看 XX」这种行内操作：长得像文字而不是按钮，点得动但不抢版面 */
.link {
  margin-left: 5px;
  padding: 0;
  border: none;
  background: none;
  color: var(--ac);
  font-size: inherit;
  text-decoration: underline;
  cursor: pointer;
}
.link:hover {
  color: var(--tx);
}
.tip.warn {
  color: var(--ink-fuzzy, #8a6218);
}
.dim {
  color: var(--dim);
  font-size: var(--fs-xs);
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
