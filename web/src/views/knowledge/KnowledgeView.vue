<script setup>
/* 知识库 —— 文件夹树 + 原文阅读 + 精读注解。
 *
 * 和「文档与精读」的分工：
 * - 知识库：上传 → 自己组织（文件夹树）→ 阅读原文 →（可选）送去转卡
 * - 文档与精读：专注转卡工具
 *
 * 三栏布局：可收起的文件夹树 | 阅读区 | AI 注解（浮层）
 * PDF 用浏览器原生 iframe 预览（零依赖），md/txt 用 MarkdownRenderer。
 *
 * ★ 左树不再是 `category → domain` 两级分类（2026-10-11 重做）：
 *   那套层级固定、名字由分类器猜、改不了也删不掉。用户要的是
 *   **自己决定怎么组织**，所以分类字段降级成纯数据（仍入库，供搜索），
 *   界面只认服务端那棵 kbtree。见 core/kbtree.py 的说明。
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import PdfViewer from './PdfViewer.vue'
import BilingualView from './BilingualView.vue'
//★ 必须显式 import，不能指望「递归组件按文件名自解析」——
//  那条规则只对**组件自己引用自己**生效（KbTreeNode.vue 内部不用 import 自己）。
//  父组件要用子组件，漏了 import 会静默变成未知自定义元素：
//  构建照样成功、页面不报错，只是树上什么都不渲染（2026-10-11 踩过）。
import KbTreeNode from './KbTreeNode.vue'
import {
  listKnowledge,
  getFileUrl,
  importKnowledge,
  removeKnowledge,
  renameKnowledge,
  getKnowledgeDoc,
  reparseDoc,
  getKbTree,
  addKbFolder,
  renameKbFolder,
  collapseKbFolder,
  removeKbFolder,
  moveKbFolder,
  placeDoc,
  askDocStream,
  feedbackQa
} from '@/api/knowledge'

const route = useRoute()

/** 导入时手动选的类型。'' = 自动（后端按文件名/版面词判断）。
 *
 *  ★ 为什么必须有手动选项：自动判据只认 arxiv/paper/期刊 这类词，
 *    中文论文、自己改过名的 PDF 一律漏判，于是论文被当成资料分章，
 *    页面给的是读不懂的抽取文本而不是原件 —— 用户比规则更知道这是什么。 */
const DOC_TYPES = ['资料', '论文', '笔记']
const docType = ref('')

const docs = ref([])
const loading = ref(false)
const opened = ref(null)
const search = ref('')
const showImport = ref(false)
/** 粘贴文本默认收起：它和「上传文件」是两条路，同时摆出来会互相抢注意力。 */
const showPaste = ref(false)
const importForm = ref({ title: '', text: '' })
const importing = ref(false)
/** 「导入到此文件夹」的目标文件夹 id（'' = 不限，进未归档）。 */
const importInto = ref('')
/* ★ 默认收起（原来默认展开的是注解，那是只读信息，可以常驻）。
 *   问答是 400px 宽的浮层，常驻会把论文压掉一截 ——
 *   需要它时点一下标题栏的「AI 问答」就在。 */
const aiOpen = ref(false)

/** 论文对照模式。关着 = 只看 PDF 原件。 */
const biOpen = ref(false)

/** 顶部两栏（知识库标题栏 + 文档标题栏）是否收起。
 *
 *★ 为什么做成「记得住」而不是纯临时：收起是为了看论文，
 *  而看论文往往一坐就是半小时 —— 每次进来都要重新点两下才好看，
 *  这个功能就等于不存在。localStorage 而不是存后端：这是**个人**
 *  的显示偏好，跟账号无关，存服务器只会多一次往返。
 */
const headSlim = ref(localStorage.getItem('edu.kb.slim') === '1')
/** ★ 阅读区默认形态：**原件优先**。
 *
 * 参照飞书/Notion 的做法：上传文件以**原格式**保存，PDF 就用 PDF 阅读器打开，
 * 不做「PDF → 在线文档」的转换（官方原话是转换后「排版和字体可能稍有变化」）。
 * 原因很实在 —— 双栏论文的文本层是残缺的：左右栏交错、公式和图表丢失、
 * 页码混进正文。不管做多少启发式修补都回不到原样。
 *
 * 所以：PDF（和 docx）永远显示原件；md/txt 才走飞书式文档视图 ——
 * 它们本来就是结构化文本，抽取无损。
 *
 * 文本版不是被废弃了，而是**降级**：它仍用于全文搜索、复制、AI 精读和
 * RAG 检索，只是不再冒充「阅读版」，入口放在右侧抽屉里。
 */
/** 右侧「提取文本」抽屉：仅供搜索/复制，不是阅读替代品。 */
const showExtract = ref(false)
const reparsing = ref(false)
const extractBox = ref(null)

/* ==================================================================
 * AI 问答（右下角抽屉，就当前这份文档提问）
 *
 * ★ 为什么从「注解」改成「问答」：
 *   原来的 AI 注解是**只读**的 —— 要先在另一个页面逐章精读，
 *   这里才有东西显示。论文压根不分章，于是这个抽屉对论文永远是空的
 *   （当时正是用 `!isPaper` 把它挡掉的）。
 *   问答反过来：没有历史也立刻能用，而且**只答这一份文档**，
 *   正好对上「我正在读这篇论文，卡住了就问一句」的场景。
 * ================================================================== */
const qaInput = ref('')
const qaBusy = ref(false)
/** [{role:'q'|'a', text, sources?:number[]}] */
const qaTurns = ref([])
/** 每个答案轮次的反馈：轮次下标 -> 'up' | 'down'（已反馈后不再显示按钮）。 */
const qaVotes = ref({})
const qaBox = ref(null)
/** 换文档就清空对话：上一个文档的问答留在这里会答串。 */
watch(
  () => opened.value?.id,
  () => {
    qaTurns.value = []
    qaVotes.value = {}
    qaInput.value = ''
    qaBusy.value = false
  }
)

/** 按论文类型给几个「用户真会问」的引导，点一下就填进输入框。 */
const qaHints = computed(() => {
  const t = (opened.value?.title || '').toLowerCase()
  if (isPaper.value) {
    if (t.includes('react')) return ['这篇论文的核心贡献是什么？', 'ReAct 里的推理和行动怎么交错？', '实验是怎么证明它有效的？']
    return ['这篇论文要解决什么问题？', '方法是怎么做的？', '实验结论是什么？']
  }
  return ['这份文档主要讲了什么？', '有哪些重点章节？']
})

async function onAsk(text) {
  const q = (text ?? qaInput.value).trim()
  if (!q || qaBusy.value || !opened.value) return
  qaInput.value = ''
  qaBusy.value = true
  // 历史只带**已经答完**的轮次：正在生成的那条是半截的，
  // 塞进去会让模型把「我还没说完的话」当成既定事实继续编。
  const hist = qaTurns.value
    .filter(t => t.role === 'q' || t.text)
    .reduce((acc, t) => {
      if (t.role === 'q') acc.push({ question: t.text, answer: '' })
      else if (acc.length) acc[acc.length - 1].answer = t.text
      return acc
    }, [])
  qaTurns.value.push({ role: 'q', text: q })
  const ai = { role: 'a', text: '', sources: [] }
  qaTurns.value.push(ai)
  await nextTick()
  scrollQa()
  try {
    await askDocStream(opened.value.id, q, hist, {
      onText: t => {
        ai.text = t
        scrollQa()
      },
      onSources: ids => {
        ai.sources = ids
      },
      onDone: t => {
        if (t && !ai.text) ai.text = t
        qaBusy.value = false
        scrollQa()
      },
      onError: msg => {
        ai.text = ai.text || ('问不了：' + msg)
        qaBusy.value = false
      }
    })
  } catch (e) {
    ai.text = '问不了：' + (e?.message || e)
    qaBusy.value = false
  } finally {
    qaBusy.value = false
  }
}

/** 给一条回答打 👍/👎，驱动自进化 RAG 纠错。
 *  question 取该答案轮次的前一轮（q 轮）。 */
function vote(i, good) {
  const q = qaTurns.value[i - 1]?.text
  if (!q || qaVotes.value[i]) return
  qaVotes.value = { ...qaVotes.value, [i]: good ? 'up' : 'down' }
  feedbackQa(opened.value.id, q, good).catch(() => {})
}

/** 新内容才滚。**每次 token 都滚会把用户正在往前翻的旧答案拽回底部**，
 *  所以先记住「贴底」状态，用户主动往回看就别打扰。 */
function scrollQa() {
  const box = qaBox.value
  if (!box) return
  const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80
  if (nearBottom || qaBusy.value) box.scrollTop = box.scrollHeight
}

/* ==================================================================
 * 文件夹树（PyCharm 式）
 * ================================================================== */

/** 服务端那棵树，形状见 core/kbtree.py：
 *  [{id,name,children:[…],docs:[did…],collapsed:bool}]
 *  顶层是数组，没有虚拟根。 */
const kbTree = ref([])
/** 左面板整体收起（用户明确要的「向左隐藏」）。**
 *  收起时宽度压到 0 只留一个把手 —— 不是 display:none，
 *  否则「展开」的按钮也跟着没了，用户找不到回来的路。 */
const sideOpen = ref(true)
/** 「全部」根节点自己的折叠态。这是 UI 层的，不进库里
 *  （库里那份 collapsed 只属于真实文件夹，根节点不是文件夹）。 */
const rootOpen = ref(localStorage.getItem('edu.kb.rootOpen') !== '0')
watch(rootOpen, v => {
  // 存本地而不是库里：根节点是**当前窗口的视图状态**，
  // 不是账号级数据（账号级的是文件夹自己的 collapsed）。
  // 放库里会让「A 把全部收起」变成「B 的树也收起了」。
  localStorage.setItem('edu.kb.rootOpen', v ? '1' : '0')
})

const byId = computed(() => {
  const m = new Map()
  for (const d of docs.value) m.set(String(d.id), d)
  return m
})

/** 没进任何文件夹的文档。
 *
 *  ★ 必须显式给它们一个落脚点，不能「看不见就没了」。
 *    树存的是「文档属于哪些文件夹」这**一份**关系，反过来查不到
 *    「哪些文档一处都没放」—— 数据上是天然的孤儿。用户建完树之后
 *    一眼看不到自己刚导的那 5 份资料，会以为导入失败了。 */
const orphans = computed(() => {
  const inTree = new Set()
  const walk = nodes => {
    for (const n of nodes) {
      for (const id of n.docs || []) inTree.add(String(id))
      walk(n.children || [])
    }
  }
  walk(kbTree.value)
  return docs.value.filter(d => !inTree.has(String(d.id)))
})

/** 树 + 文档合成视图模型。递归带上真实文档对象和子树文档数。
 *
 *  过滤（搜索）在这一层做：命中的文档保留，**空文件夹隐藏** ——
 *  否则搜一个字却看到几十个空文件夹，等于搜索失效。 */
const treeView = computed(() => {
  const q = search.value.trim().toLowerCase()
  const hit = d =>
    !q ||
    (d.title || '').toLowerCase().includes(q) ||
    (d.category || '').toLowerCase().includes(q) ||
    (d.domain || '').toLowerCase().includes(q) ||
    (d.tags || []).some(t => t.toLowerCase().includes(q))

  const build = nodes => {
    const out = []
    for (const n of nodes) {
      const kids = build(n.children || [])
      const mine = (n.docs || []).map(id => byId.value.get(String(id))).filter(Boolean)
      const shown = q ? mine.filter(hit) : mine
      // 自己这一层没留下东西、孩子也全被过滤掉 → 这个文件夹不显示
      if (q && !shown.length && !kids.length) continue
      out.push({
        id: n.id,
        name: n.name,
        collapsed: !!n.collapsed,
        docs: shown,
        children: kids,
        total: (n.docs || []).length + kids.reduce((s, k) => s + k.total, 0)
      })
    }
    return out
  }
  return build(kbTree.value)
})

const orphanDocs = computed(() => {
  const q = search.value.trim().toLowerCase()
  const list = orphans.value
  if (!q) return list
  return list.filter(
    d =>
      (d.title || '').toLowerCase().includes(q) ||
      (d.category || '').toLowerCase().includes(q) ||
      (d.domain || '').toLowerCase().includes(q)
  )
})

const rootCount = computed(() => docs.value.length)

/** 统一收口：所有写操作都返回整棵 tree，直接覆盖本地。
 *  前端绝不本地改树 —— 两份状态不一致时「刷新又弹回去」最难查。 */
function applyTree(r) {
  if (r && Array.isArray(r.tree)) kbTree.value = r.tree
}

async function fetchTree() {
  try {
    applyTree(await getKbTree())
  } catch (e) {
    ElMessage.error(e?.message || '文件夹树加载失败')
  }
}

async function onNewFolder(parentId = '') {
  let name = ''
  try {
    const r = await ElMessageBox.prompt('文件夹名', '新建文件夹', {
      inputValue: '',
      inputValidator: v => (v || '').trim() ? true : '名字不能为空',
      confirmButtonText: '创建',
      cancelButtonText: '取消'
    })
    name = (r.value || '').trim()
  } catch {
    return
  }
  if (!name) return
  try {
    const r = await addKbFolder(name, parentId)
    applyTree(r)
    // 建在别人（顶层）里要顺手展开，否则建完看不见 —— 建了等于没建
    if (parentId) {
      const p = findNode(kbTree.value, parentId)
      if (p) p.collapsed = false
    } else {
      rootOpen.value = true
    }
  } catch (e) {
    ElMessage.error(e?.message || '新建失败')
  }
}

/** 在树里按 id 找节点（用于展开父级）。找不到返回 null。 */
function findNode(nodes, fid) {
  for (const n of nodes) {
    if (n.id === fid) return n
    const hit = findNode(n.children || [], fid)
    if (hit) return hit
  }
  return null
}

async function onRenameFolder(n) {
  let name = ''
  try {
    const r = await ElMessageBox.prompt('新的文件夹名', '重命名', {
      inputValue: n.name,
      inputValidator: v => (v || '').trim() ? true : '名字不能为空',
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    name = (r.value || '').trim()
  } catch {
    return
  }
  if (!name || name === n.name) return
  try {
    applyTree(await renameKbFolder(n.id, name))
    ElMessage.success('已改名')
  } catch (e) {
    ElMessage.error(e?.message || '改名失败')
  }
}

async function onToggleFolder(n) {
  const next = !n.collapsed
  n.collapsed = next // 先动界面：折叠是纯 UI 反馈，等网络会明显卡一下
  try {
    applyTree(await collapseKbFolder(n.id, next))
  } catch (e) {
    n.collapsed = !next // 回滚，别让界面停在骗人的状态
    ElMessage.error(e?.message || '保存折叠状态失败')
  }
}

async function onDelFolder(n) {
  let mode = 'doc2root'
  try {
    await ElMessageBox.confirm(
      `删除文件夹「${n.name}」？里面的 ${n.total} 份文档不会丢，会挪到「未归档」。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    const r = await removeKbFolder(n.id, mode)
    applyTree(r)
    ElMessage.success(r.moved?.length ? `已删除，${r.moved.length} 份文档挪到未归档` : '已删除')
  } catch (e) {
    ElMessage.error(e?.message || '删除失败')
  }
}

/* ---- 拖拽 ----
 * 统一用 dataTransfer 传 JSON 而不是自定义全局变量：
 * ① 一个页面只能有一个「正在拖的东西」，用变量存的话拖到一半
 *    状态被别处改掉就丢；② dataTransfer 是浏览器给的通道，
 *    天然跟着这次拖拽走，不存在跨事件串味。 */
const DRAG_FOLDER = 'text/x-kb-folder'
const DRAG_DOC = 'text/x-kb-doc'
const dragOver = ref('')

function startDragFolder(ev, n) {
  ev.dataTransfer.effectAllowed = 'move'
  ev.dataTransfer.setData(DRAG_FOLDER, n.id)
}
function startDragDoc(ev, d) {
  ev.dataTransfer.effectAllowed = 'move'
  ev.dataTransfer.setData(DRAG_DOC, String(d.id))
}

function onDragOverFolder(ev, n) {
  if (!ev.dataTransfer.types.includes(DRAG_FOLDER) && !ev.dataTransfer.types.includes(DRAG_DOC)) return
  ev.preventDefault() // 不 preventDefault 就不会触发 drop
  ev.dataTransfer.dropEffect = 'move'
  dragOver.value = n.id
}
function onDragLeave(ev, n) {
  // relatedTarget 为空 = 移出了这个节点（而不是移到了它的孩子上），
  // 移进孩子时不该清高亮，否则高亮一直闪。
  if (dragOver.value === n.id && !ev.currentTarget.contains(ev.relatedTarget)) {
    dragOver.value = ''
  }
}
function onDropFolder(ev, n) {
  ev.preventDefault()
  dragOver.value = ''
  const fid = ev.dataTransfer.getData(DRAG_FOLDER)
  const did = ev.dataTransfer.getData(DRAG_DOC)
  if (fid) {
    if (fid === n.id) return
    moveKbFolder(fid, n.id)
      .then(r => {
        applyTree(r)
        ElMessage.success('已移动')
      })
      .catch(e => ElMessage.error(e?.message || '移动失败'))
  } else if (did) {
    onPlaceDoc(did, [...folderIdsOf(did), n.id])
  }
}

/** 某文档当前已属于哪些文件夹的 id。
 *
 *  ★ 必须从**库里那份树**查，不能拿 treeView —— treeView 是过滤后的视图，
 *    搜索时它只剩命中的节点，据它算「已属于哪些文件夹」会把用户
 *    放进 A 文件夹的文档当成没放，拖进 B 就变成同时属于 A 和 B。 */
function folderIdsOf(did) {
  const out = []
  const walk = nodes => {
    for (const n of nodes) {
      if ((n.docs || []).some(x => String(x) === String(did))) out.push(n.id)
      walk(n.children || [])
    }
  }
  walk(kbTree.value)
  return out
}

async function onPlaceDoc(did, folderIds) {
  try {
    applyTree(await placeDoc(did, folderIds))
    ElMessage.success(folderIds.length ? '已归位' : '已移出文件夹')
  } catch (e) {
    ElMessage.error(e?.message || '设置失败')
  }
}

/** 把文档挪到某一个文件夹（不再多归属）。菜单项直接给这个用。 */
function onMoveDocTo(d, n) {
  onPlaceDoc(d.id, [...folderIdsOf(d.id).filter(x => x !== n.id), n.id])
}

/** 只有一份文档只属于这一个文件夹时，「移出」才等于回到未归档。 */
function canLeave(d) {
  return folderIdsOf(d.id).length <= 1
}

/** 从某个文件夹移出（其余归属保留）。 */
function onUnplaceDoc(d, fid) {
  onPlaceDoc(d.id, folderIdsOf(d.id).filter(x => x !== fid))
}

/** 拖到左树空白处 = 移出所有文件夹（回到「未归档」）。 */
function onDropRoot(ev) {
  dragOver.value = ''
  const did = ev.dataTransfer.getData(DRAG_DOC)
  if (did && folderIdsOf(did).length) onPlaceDoc(did, [])
}

/** 移动文件夹的薄封装：把后端 400 的 msg 原样带出来（防环就是靠它提示的）。 */
function onMoveKbFolder(fid, parentId) {
  moveKbFolder(fid, parentId)
    .then(applyTree)
    .catch(e => ElMessage.error(e?.message || '移动失败'))
}

async function copyText() {
  try {
    await navigator.clipboard.writeText(docText.value)
    ElMessage.success('已复制全文')
  } catch {
    ElMessage.warning('复制失败，用手动全选吧')
  }
}

/** 收起状态下「⋯」菜单里的动作（2026-10-11）。
 *  命令字符串直写在前端模板里，不做映射表 —— 三个命令三个分支，
 *  多一层间接只会让「这个命令对应哪个函数」更难查。 */
function onMore(cmd) {
  if (cmd === 'download') {
    // 动态造一个 <a download> 而不是 fetch + blob：
    // 原生下载自带进度条、可以另存到别的目录、失败时浏览器会给提示，
    // 这三样手写都做不全（blob 方案失败就是静默失败）。
    const a = document.createElement('a')
    a.href = fileUrl.value
    // 文件名带上后缀：少了它浏览器会用 URL 里的 docId 当文件名，
    // 用户拿到的就是「doc-20261011-2.pdf」这种没法认的名字。
    a.download = (opened.value?.title || 'document') + (opened.value?.rawFile || '')
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
  } else if (cmd === 'extract') {
    showExtract.value = !showExtract.value
    if (showExtract.value) { aiOpen.value = false; biOpen.value = false }
  } else if (cmd === 'bi') {
    biOpen.value = !biOpen.value
    if (biOpen.value) { showExtract.value = false; aiOpen.value = false }
  } else if (cmd === 'reparse') {
    onReparse()
  }
}

/** 就地重跑解析：旧版本导入的 PDF 存的 text 是裸文本（代码无围栏、
 *  标题无标记），重新导入会换新 id、丢章节进度，所以提供这个按钮。 */
async function onReparse() {
  if (!opened.value) return
  reparsing.value = true
  try {
    const r = await reparseDoc(opened.value.id)
    ElMessage.success('已重新解析，代码块和标题层级已就位')
    await fetchList()
    opened.value = r.doc
    const i = docs.value.findIndex(x => String(x.id) === String(r.doc.id))
    if (i >= 0) docs.value[i] = { ...docs.value[i], ...r.doc }
  } catch (e) {
    ElMessage.error(e?.message || '重新解析失败')
  } finally {
    reparsing.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchList(), fetchTree()])
  const want = route.query.doc || localStorage.getItem('edu.kb') || ''
  if (want) {
    const hit = docs.value.find(d => String(d.id) === String(want))
    if (hit) await openDoc(hit)
    else localStorage.removeItem('edu.kb')
  }
})

async function fetchList() {
  loading.value = true
  try {
    const r = await listKnowledge()
    docs.value = r.docs || []
  } finally {
    loading.value = false
  }
}

async function openDoc(d) {
  opened.value = null
  const r = await getKnowledgeDoc(d.id)
  opened.value = r.doc
  const i = docs.value.findIndex(x => String(x.id) === String(d.id))
  if (i >= 0) {
    docs.value[i] = { ...docs.value[i], ...r.doc }
  }
  localStorage.setItem('edu.kb', String(r.doc.id))
}

async function onRemove(d) {
  try {
    await ElMessageBox.confirm(
      `删除《${d.title}》？章节内容、精读结果和原始文件都会一起删掉。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await removeKnowledge(d.id)
  } catch (e) {
    ElMessage.error(e?.message || '删除失败')
    return
  }
  if (opened.value?.id === d.id) {
    opened.value = null
    localStorage.removeItem('edu.kb')
  }
  ElMessage.success('已删除')
  await Promise.all([fetchList(), fetchTree()])
}

/** 改名。
 *
 *  ★ 后端 rename_deck 是**级联**的：组名就是文档标题，改名会连带把
 *    自定义卡和草稿里的 deck 一起改（不这样会出现两组 chips）。
 *    所以别自己只改 title —— 走接口。
 * 顺带支持在左树上直接点标题旁的改名按钮，不用先打开文档。 */
async function onRename(d) {
  let name = ''
  try {
    const r = await ElMessageBox.prompt('新的名称', '重命名', {
      inputValue: d.title || '',
      inputValidator: v => (v || '').trim() ? true : '名字不能为空',
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    name = (r.value || '').trim()
  } catch {
    return
  }
  if (!name || name === d.title) return
  try {
    await renameKnowledge(d.id, name)
    ElMessage.success(`已改名为《${name}》`)
    await fetchList()
    if (opened.value?.id === d.id) {
      const r = await getKnowledgeDoc(d.id)
      opened.value = r.doc
    }
  } catch (e) {
    ElMessage.error(e?.message || '改名失败')
  }
}

const OK_EXT = ['pdf', 'docx', 'md', 'markdown', 'txt']

/** 单文件上限。与后端 docparse.MAX_UPLOAD_BYTES 同口径（40MB）。
 *  上传走 base64 膨胀 4/3，请求体上限 64MB —— 三个数必须配套，见后端注释。 */
const MAX_BYTES = 40 * 1024 * 1024

async function onFile(ev) {
  const f = ev.target.files && ev.target.files[0]
  ev.target.value = ''
  if (!f) return
  const ext = (f.name.split('.').pop() || '').toLowerCase()
  if (!OK_EXT.includes(ext)) {
    ElMessage.warning('只支持 PDF / Word(.docx) / md / txt')
    return
  }
  if (f.size > MAX_BYTES) {
    ElMessage.warning(`文件超过 ${MAX_BYTES >> 20}MB，先拆小一点`)
    return
  }
  importing.value = true
  try {
    let body
    if (ext === 'pdf' || ext === 'docx') {
      body = { filename: f.name, dataB64: await readB64(f) }
    } else {
      body = { filename: f.name, text: await f.text() }
    }
    const t = importForm.value.title.trim()
    if (t) body.title = t
    // 选了类型才传；留空=自动判断（后端默认 auto）
    body.docType = docType.value || undefined
    const r = await importKnowledge(body)
    ElMessage.success(
      `已导入《${r.doc?.title || ''}》，自动分类为「${r.doc?.category || '未分类'}」`
    )
    importForm.value = { title: '', text: '' }
    docType.value = ''
    showImport.value = false
    await fetchList()
    await openDoc(r.doc)
    await dropIntoFolder(r.doc.id)
  } catch (e) {
    ElMessage.error(e?.message || '导入失败')
  } finally {
    importing.value = false
  }
}

/** 导入后落到「导入到」指定的文件夹。空 = 留在未归档。
 *  不这么做的话，用户对着某个文件夹点「导入到此」，结果文件飘到
 *  「未归档」里，还得再拖一次 —— 正是这一步最烦人。 */
async function dropIntoFolder(did) {
  if (!importInto.value) return
  const target = importInto.value
  importInto.value = ''
  await onPlaceDoc(did, [target])
}

/** 「导入到此文件夹」：记住目标并打开导入面板。 */
function onImportInto(fid) {
  importInto.value = fid
  showImport.value = true
}

async function onImportText() {
  const s = importForm.value.text.trim()
  if (!s) {
    ElMessage.warning('先粘一段内容')
    return
  }
  importing.value = true
  try {
    const r = await importKnowledge({
      title: importForm.value.title.trim() || undefined,
      text: s,
      docType: docType.value || undefined
    })
    ElMessage.success(
      `已导入《${r.doc?.title || ''}》，自动分类为「${r.doc?.category || '未分类'}」`
    )
    importForm.value = { title: '', text: '' }
    showImport.value = false
    await fetchList()
    await openDoc(r.doc)
    await dropIntoFolder(r.doc.id)
  } catch (e) {
    ElMessage.error(e?.message || '导入失败')
  } finally {
    importing.value = false
  }
}

function readB64(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(String(fr.result).split(',')[1] || '')
    fr.onerror = () => reject(fr.error)
    fr.readAsDataURL(file)
  })
}

const chapters = computed(() => opened.value?.chapters || [])

/** 有留档原文就能按原样渲染。粘贴导入的也有 text（只是没有 rawFile），
 *  所以判据是「有没有原文」而不是「后缀是不是 md」—— 粘贴一段 md 也该走这条。 */
const isText = computed(() => Boolean(opened.value?.text))
const isPaper = computed(() => opened.value?.isPaper === true)
const fileUrl = computed(() => (opened.value?.rawFile ? getFileUrl(opened.value.id) : ''))

/** ★ A：原件能读到就走原件。
 *  早期导入的文档 rawFile 为空（那时还没这功能），但 data/store/files/ 下
 *  可能已经躺着一份 —— raw_path 的兜底顺序会挨个后缀试，所以照样打得��。
 *  PDF 尤其要走原件：pypdf 抽出来的纯文本没有版面（页码混进正文、目录页
 *  被当正文、缩进全丢），再怎么排版也回不到原样。 */
const canShowOriginal = computed(() => Boolean(fileUrl.value))
const isDocx = computed(() => (opened.value?.rawFile || '').endsWith('.docx'))

/** md/txt 的渲染源：导入时留档的原文。
 *  不用 chapters 拼 —— 拼出来会丢章节标题、切断代码块
 *  （分章把 `# comment` 当过标题）、图片占位也渲染不出来。 */
const docText = computed(() => opened.value?.text || '')

/** ★ 目录必须从**实际渲染的那份内容**里提，不能用 chapters。
 *
 * 之前用 chapters 的标题做目录、正文用 doc.text 渲染，两者是**各自独立
 * 解析**的：chapters 是按 5000 字折叠出来的，doc.text 是原文，标题数量和
 * 位置都对不上。结果就是点目录跳到的地方和点的那条根本不是一回事。
 *
 * 现在直接从渲染容器里的 h1~h4 收集 —— 看到什么标题就跳到什么位置，
 * 索引天然对齐。渲染完 nextTick 再收集，否则 DOM 还没建好。
 */
const toc = ref([])
const activeToc = ref(-1)
const docBox = ref(null)
let remeasureTimer = 0

function collectToc() {
  const box = docBox.value
  if (!box) {
    toc.value = []
    return
  }
  const items = []
  box.querySelectorAll('h1, h2, h3, h4').forEach(el => {
    // 跳过代码块里的假标题（MarkdownRenderer 会把 ``` 里的 #xxx 渲染成 h1）
    if (el.closest('.md-codeblk')) return
    const text = (el.textContent || '').trim()
    if (!text) return
    el.dataset.tocIdx = String(items.length)
    items.push({
      idx: items.length,
      title: text.length > 40 ? text.slice(0, 40) + '…' : text,
      level: Number(el.tagName.slice(1)),
      el
    })
  })
  toc.value = items
  activeToc.value = -1
  measureToc()
}

/** 把每个标题相对**滚动容器**的位置量一次缓存下来。
 *
 * ★ 为什么不能用 el.offsetTop：offsetTop 是相对 offsetParent 的，
 *   而 MarkdownRenderer 嵌在 .doc-paper 里，offsetParent 不是滚动容器
 *   .doc-scroll —— 算出来的位置全是错的，表现就是「已经读到下一章了，
 *   高亮还停在上���章」。
 *
 * 为什么要在收集后立刻量、而不是每次滚动时量：getBoundingClientRect 会
 * 触发强制重排，滚动事件里每帧调一次，长文档直接卡住。
 */
function measureToc() {
  const box = docBox.value
  if (!box) return
  const base = box.getBoundingClientRect().top - box.scrollTop
  for (const t of toc.value) {
    t.top = t.el.getBoundingClientRect().top - base
  }
}

function scrollToToc(idx) {
  const t = toc.value[idx]
  if (!t) return
  // 不用 scrollIntoView：它会把**所有**祖先容器一起滚，页面本身会跟着跳。
  // 这里只滚自己的容器，行为可预期。
  const box = docBox.value
  if (!box) return
  if (t.top == null) measureToc()
  box.scrollTo({ top: Math.max(0, t.top - 12), behavior: 'smooth' })
}

/** 滚动时高亮当前章节。取「最后一个已经越过顶部的标题」。
 *
 * ★ 阈值 12 而不是「视口高度的一半」：文档顶部本来就该高亮第一个标题，
 *   如果按视口中线算，读到第一屏开头时一个标题都没亮，观感是「目录失灵」。
 *   按「标题顶边越过容器顶部 12px」判定，行为和点目录跳转完全一致 ——
 *   点第 N 条跳过去，滚回来时高亮也正好回到第 N 条。
 */
function onScroll() {
  const box = docBox.value
  if (!box || !toc.value.length) return
  const line = box.scrollTop + 12
  let cur = -1
  for (const t of toc.value) {
    if (t.top == null) break
    if (t.top <= line) cur = t.idx
    else break
  }
  activeToc.value = cur
}

/** 图片加载完 / 窗口尺寸变了都要重量一次 —— 位置是按当前排版量的，
 *  图片一加载完整个文档高度就变了，缓存的 top 全部作废。 */
function scheduleRemeasure() {
  scheduleTocCollect()
  clearTimeout(remeasureTimer)
  remeasureTimer = setTimeout(measureToc, 200)
}

/** 顶部搜索框命中提取文本时，把抽屉打开并滚到第一处匹配。
 *  这是「提取文本」抽屉最实际的用途 —— PDF 原件里 Ctrl+F 只能搜当前渲染页，
 *  而这里能跨整篇全文定位。 */
watch(headSlim, v => {
  try {
    localStorage.setItem('edu.kb.slim', v ? '1' : '0')
  } catch {
    /* 隐私模式下 localStorage 会抛，忽略即可（功能还在，只是记不住） */
  }
  // 收起/展开改了容器高度 → PDF 得按新宽度重排（高度变了但宽度没变时
  // 宽度铺满其实不受影响，可这里仍要触发一次，让「整页」类的逻辑有机会跑）
  window.dispatchEvent(new Event('resize'))
})

watch(search, async v => {
  const q = (v || '').trim()
  if (q.length < 2 || !isText.value) return
  showExtract.value = true
  await nextTick()
  const box = extractBox.value
  if (!box) return
  const hit = findHit(box, q)
  if (hit) hit.scrollIntoView({ behavior: 'smooth', block: 'center' })
})

/** 在文本节点里找第一处匹配，返回包住它的 <mark>。 */
function findHit(box, q) {
  const lower = q.toLowerCase()
  const walker = document.createTreeWalker(box, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) {
    const i = (node.nodeValue || '').toLowerCase().indexOf(lower)
    if (i < 0) continue
    const range = document.createRange()
    range.setStart(node, i)
    range.setEnd(node, i + q.length)
    const mark = document.createElement('mark')
    try {
      range.surroundContents(mark)
    } catch {
      continue
    }
    return mark
  }
  return null
}

/** 目录收集要等 DOM **真正**建好。
 *
 * ★ 为什么 nextTick 不够：MarkdownRenderer 内部是 computed(v-html)，
 *   nextTick 只等 Vue 的更新队列，hljs 高亮是同步的所以大部分时候够用；
 *   但章节流分支是 v-for + 子组件，节点是分批插入的。收集早了一帧，
 *   toc 就是空的或不完整的 —— 表现是「点第一次没反应，��两次才对」。
 *
 * 稳妥做法：不猜时机，直接盯 DOM。 MutationObserver 在子节点插入时触发，
 * 连续触发用 debounce 收敛，最后一次一定是齐的。
 */
let tocObserver = null
let tocTimer = 0
let lastTocSig = ''

function scheduleTocCollect() {
  clearTimeout(tocTimer)
  tocTimer = setTimeout(() => {
    const box = docBox.value
    if (!box) return
    // 签名变了才重收，避免图片加载等无关变动反复重建目录
    const sig = box.querySelectorAll('h1, h2, h3, h4').length + ':' + box.scrollHeight
    if (sig === lastTocSig) return
    lastTocSig = sig
    collectToc()
  }, 120)
}

watch(
  () => [opened.value?.id, isText.value, canShowOriginal.value],
  async () => {
    lastTocSig = ''
    await nextTick()
    collectToc()
    // 挂上观察器，等后续的节点插入/图片加载
    if (!tocObserver && docBox.value) {
      tocObserver = new MutationObserver(scheduleTocCollect)
      tocObserver.observe(docBox.value, { childList: true, subtree: true })
    }
  },
  { immediate: true }
)

onMounted(() => window.addEventListener('resize', scheduleRemeasure))
onUnmounted(() => {
  window.removeEventListener('resize', scheduleRemeasure)
  clearTimeout(tocTimer)
  tocObserver?.disconnect()
  tocObserver = null
})

function aiOf(c) {
  return c.ai || {}
}
</script>

<template>
  <div class="kb" :class="{ 'slim-root': headSlim }">
    <!-- ★ 顶栏：可整条收起（2026-10-11）。
         做「可隐藏」而不是继续压padding，是因为再压下去就贴到不可用了
         （搜索框 260px 高 24px，再砍就点不中）。而这一条对论文区
         的**边际收益最大**：它和标题栏各占40~50px，一起能省出约 100px，
         相当于多显示小半页 A4。
         收起后还留着这一行（标题变成可点的展开按钮），不是整条 v-if 掉 ——
         用 v-if 的话连「找回来的入口」一起消失，用户只能刷新页面。 -->
    <header class="kb-head panel" :class="{ slim: headSlim }">
      <h3 class="kb-title">
        <button class="slim-toggle" :title="headSlim ? '展开顶部' : '收起顶部（论文区更高）'"
                @click="headSlim = !headSlim">
          <span class="slim-arrow">{{ headSlim ? '▾' : '▴' }}</span>
          知识库
        </button>
      </h3>
      <div v-show="!headSlim" class="kb-tools">
        <input v-model="search" class="kb-search" placeholder="搜索标题 / 分类 / 标签…" />
        <button class="btn btn-primary" @click="showImport = !showImport">
          <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
          导入
        </button>
      </div>
    </header>

    <div v-if="showImport" class="import-box panel">
      <!-- ★ 只留「选文件 + 选类型」两件事（2026-10-11 精简）。
        原来的标题输入、正文 textarea、「导入并分章」按钮全删了：
        标题在导入后随时能改（改名按钮就在阅读区标题栏和左树上），
        而正文 textarea 让「上传文件」这条主路径显得像第二选择 ——
        两者挤在一个面板里，用户看不出该点哪个。
        粘贴文本仍可用（onImportText），从搜索框旁的入口走。 -->
      <div class="file-row">
        <label class="file-btn">
          <input type="file" accept=".pdf,.docx,.md,.markdown,.txt" @change="onFile" />
          选择文件
        </label>
        <span class="muted">PDF / Word(.docx) / md / txt，最大 40MB</span>
        <button class="btn btn-bare" @click="showPaste = !showPaste">
          {{ showPaste ? '收起' : '粘贴文本' }}
        </button>
      </div>
      <!-- 类型：论文走原件阅读、资料/笔记分章。留空=自动判断。 -->
      <div class="file-row">
        <span class="lb">类型</span>
        <button
          v-for="tp in DOC_TYPES"
          :key="tp"
          class="type-btn"
          :class="{ on: docType === tp }"
          @click="docType = docType === tp ? '' : tp"
        >
          {{ tp }}
        </button>
        <span class="muted">{{
          docType === '论文'
            ? '按原件显示，不分章'
            : docType
              ? '分章 + 目录'
              : '不选=自动判断'
        }}</span>
      </div>
      <div v-if="showPaste" class="file-row">
        <textarea
          v-model="importForm.text"
          class="kb-input"
          rows="5"
          placeholder="粘贴 md / txt 内容。# 与「第X章」会被识别成章节"
        />
        <button class="btn btn-ghost" :disabled="importing" @click="onImportText">
          {{ importing ? '导入中…' : '导入这段文字' }}
        </button>
      </div>
    </div>

    <div class="kb-body" :class="{ 'side-closed': !sideOpen }">
      <aside v-if="sideOpen" class="kb-tree panel">
        <!-- 收起把手贴在树左缘。放在面板**内部**而不是作为 kb-body 的
             独立子元素：grid 子元素每一个都占一格，独立放会顶掉
             树自己的列（表现为树跑到页面中间）。 -->
        <button class="side-handle" title="收起左栏（向左隐藏）" @click="sideOpen = false">
          ‹
        </button>
        <div class="tree-top">
          <span class="tree-top-title">全部资料</span>
          <button class="btn btn-bare" title="新建文件夹" @click="onNewFolder('')">＋</button>
        </div>
        <div class="tree-scroll" v-loading="loading"
             @dragover.prevent="dragOver = ''" @drop.prevent="onDropRoot">
          <div v-if="!rootCount" class="empty">
            <span class="big">还没有资料</span>
            点右上角「导入」，把 PDF / 论文 / 笔记传进来
          </div>

          <!-- 「全部」虚拟根：不是文件夹，没有 id，所以只是展开/收起 -->
          <div v-if="rootCount" class="node root">
            <div class="node-row" @click="rootOpen = !rootOpen">
              <span class="arw" :class="{ open: rootOpen }">▸</span>
              <span class="ico">🗂</span>
              <span class="nm">全部</span>
              <span class="cnt">{{ rootCount }}</span>
            </div>
            <div v-if="rootOpen" class="kids">
              <KbTreeNode
                  v-for="n in treeView"
                  :key="n.id"
                  :node="n"
                  :active-id="opened?.id"
                  :drag-over="dragOver"
                  @open="openDoc"
                  @toggle="onToggleFolder"
                  @rename="onRenameFolder"
                  @del="onDelFolder"
                  @new-sub="onNewFolder"
                  @move-sub="onMoveKbFolder"
                  @place="onMoveDocTo"
                  @unplace="onUnplaceDoc"
                  :can-leave="canLeave"
                  @import-into="onImportInto"
                  @drop-node="onDropFolder"
                  @drag-folder="startDragFolder"
                  @drag-doc="startDragDoc"
                  @drag-over="onDragOverFolder"
                  @drag-leave="onDragLeave"
                  @rename-doc="onRename"
                  @remove-doc="onRemove"
                />

              <div v-if="orphanDocs.length" class="node orphan">
                <div class="node-row">
                  <span class="arw open">▸</span>
                  <span class="ico">◌</span>
                  <span class="nm">未归档</span>
                  <span class="cnt">{{ orphanDocs.length }}</span>
                </div>
                <div class="kids">
                  <div v-for="d in orphanDocs" :key="d.id" class="leaf"
                       :class="{ on: opened?.id === d.id }" draggable="true"
                       @dragstart="startDragDoc($event, d)" @click="openDoc(d)">
                    <span class="nm">{{ d.title }}</span>
                    <span class="leaf-acts">
                      <button title="改名" @click.stop="onRename(d)">改名</button>
                      <button title="删除" @click.stop="onRemove(d)">×</button>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="search" class="empty">
            <span class="big">没匹配到</span>
            换个词试试，或清空搜索框
          </div>
        </div>
        <div class="tree-foot">
          <span class="dim">拖文件到文件夹即可归类</span>
        </div>
      </aside>

      <!-- 收起态：留一个浮在正文左缘的窄把手（v-else 而不是 display:none，
           否则展开入口一起消失，用户再也回不来）。 -->
      <button v-else class="side-handle side-handle-lite" title="展开左栏"
              @click="sideOpen = true">
        ›
      </button>

      <main class="kb-reader panel">
        <p v-if="!opened" class="empty">
          <span class="big">选一份资料</span>
          左边点一下，这里会打开原文
        </p>
        <template v-else>
          <!-- ★ 文档标题栏：跟着 headSlim 一起收起。
               这一行是**紧贴 PDF 的那一行**，收起来的收益比知识库顶栏更大：
               它把标题、徽标、六个操作按钮全压成~26px。
               但保留标题（截断）+ 「改名/AI问答/删除」三个按钮 ——
               收起后要还能认出「现在看的是哪篇」，且最常用的操作够得着。
               下载原件/提取文本/重新解析这三个在收起时藏进「⋯」，
               它们都是低频的，全留着会让这一行又变宽。 -->
          <header class="reader-head" :class="{ slim: headSlim }">
            <div class="reader-title" v-show="!headSlim">
              <h3>{{ opened.title }}</h3>
              <div class="reader-meta">
                <span v-if="isPaper" class="chip accent">论文 · 原件</span>
                <span v-if="opened.category && !isPaper" class="chip accent">{{
                  opened.category
                }}</span>
                <span v-if="opened.domain" class="chip">{{ opened.domain }}</span>
                <span v-for="t in (opened.tags || []).slice(0, 4)" :key="t" class="chip">{{
                  t
                }}</span>
                <span v-if="!isPaper" class="muted"
                  >{{ chapters.length }} 章 · {{ opened.stats?.chars ?? 0 }} 字</span
                >
                <span v-else-if="opened.source" class="muted">{{ opened.source }}</span>
              </div>
            </div>
            <!-- 收起时给一行留个标题占位：不然左边空了、右边一排按钮悬着，
                 像坏掉了一样。而且要能认出在看哪篇。 -->
            <h3 v-show="headSlim" class="slim-title" :title="opened.title">{{
              opened.title
            }}</h3>
            <div class="reader-actions">
              <button class="btn btn-bare" @click="onRename(opened)">改名</button>
              <!-- 收起时把低频操作收进「⋯」。不是纯 CSS 隐藏：
                   收起状态下这行只有 ~120px 宽（标题 + AI问答 + ⋯ + 删除），
                   再平铺三个按钮会把标题挤没 —— 那样「认出在看哪篇」就失败了。
                   ★ 用 v-if 而不是 v-show：藏在菜单里的按钮不该再占布局，
                     而这行的宽度正是我们要省的东西。 -->
              <el-dropdown v-if="headSlim" trigger="click" @command="onMore">
                <button class="btn btn-bare">⋯</button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="canShowOriginal" command="download">
                      下载原件
                    </el-dropdown-item>
                    <el-dropdown-item v-if="isText" command="extract">
                      {{ showExtract ? '收起文本' : '提取文本' }}
                    </el-dropdown-item>
                    <el-dropdown-item v-if="canShowOriginal" command="bi">
                      {{ biOpen ? '收起译文' : '论文对照' }}
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="canShowOriginal && !isPaper"
                      command="reparse"
                      :disabled="reparsing"
                    >
                      {{ reparsing ? '解析中…' : '重新解析' }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <a
                v-if="canShowOriginal && !headSlim"
                class="btn btn-ghost"
                :href="fileUrl"
                target="_blank"
                rel="noopener"
                download
                >下载原件</a
              >
              <!-- 提取文本：仅供全文搜索 / 复制，不是阅读替代品。
                   论文现在也存抽取文本了（供 RAG），同样可以搜/复制。 -->
              <button
                v-if="isText && !headSlim"
                class="btn btn-ghost"
                @click="showExtract = !showExtract; if (showExtract) aiOpen = false"
              >
                {{ showExtract ? '收起文本' : '提取文本' }}
              </button>
              <!-- 论文对照：与「提取文本」互斥（同为占掉阅读区的第二栏）。
                   条件是 canShowOriginal 而不是 isText —— 对照的价值在
                   「原文旁边给译文」，只有有原件时才成立；
                   纯粘贴进来的 md 也没有分好段的原文可对。 -->
              <button
                v-if="!headSlim && canShowOriginal"
                class="btn btn-ghost"
                @click="biOpen = !biOpen; if (biOpen) { showExtract = false; aiOpen = false }"
              >
                {{ biOpen ? '收起译文' : '论文对照' }}
              </button>
              <!-- 旧版本导入的 PDF 没经过代码块/标题识别，用这个就地补跑。论文没有文本，不适用。 -->
              <button
                v-if="canShowOriginal && !isPaper && !headSlim"
                class="btn btn-bare"
                :disabled="reparsing"
                @click="onReparse"
              >
                {{ reparsing ? '解析中…' : '重新解析' }}
              </button>
              <!--★ 问答和「提取文本」共用右下角这一个浮层位。
               两个同时开就是两块 400px 面板重叠，谁也点不到。
               与其算高度互相错开（extract 高度不固定，会抖），
               不如互斥打开 —— 这两个功能的使用场景本来就是交替的。 -->
              <button class="btn btn-ghost" @click="aiOpen = !aiOpen; if (aiOpen) showExtract = false">
                {{ aiOpen ? '收起问答' : 'AI 问答' }}
              </button>
              <button class="btn btn-bare danger" @click="onRemove(opened)">删除</button>
            </div>
          </header>

          <!-- 原件区。
               ★ PDF 改用 PdfViewer 自己渲染（2026-10-11）：原生 iframe 的
                 工具栏是浏览器插件画的深灰条，跟主题对不上，而且它是独立
                 浏览上下文 —— Ctrl+F 只搜当前页、无法与译文并排、无法截图。
                 自己渲染后工具栏跟随主题、连续滚动，还为「中英对照」留了位置。
               Word 没有浏览器渲染器，给下载而不是硬转。 -->
          <!-- 原件区。biOpen（论文对照）优先于 PDF ——
               两者同占这块地方，而对照模式本身也带着原文。 -->
          <div v-if="canShowOriginal" class="reader-content">
            <BilingualView
              v-if="!isDocx && biOpen"
              :key="'bi' + opened.id"
              :doc-id="String(opened.id)"
              :has-text="isText"
            />
            <PdfViewer
              v-else-if="!isDocx"
              :key="opened.id"
              :doc-id="String(opened.id)"
            />
            <div v-else class="docx-hint empty">
              <span class="big">Word 文档</span>
              浏览器没法直接渲染 .docx，点上方「下载」用 Word / WPS 看
            </div>
          </div>

          <!-- 文档视图：飞书式 —— 左侧悬浮目录 + 居中窄列正文。
               只给 md/txt（和没留原件的旧文档）：这类文件本身是结构化文本，
               渲染成文档不会丢东西。PDF 走上面的原件，不进这条路。 -->
          <div v-else class="reader-body">
            <nav v-if="toc.length > 1" class="doc-toc">
              <div class="toc-head rule">目录</div>
              <button
                v-for="t in toc"
                :key="t.idx"
                class="toc-item"
                :class="[{ on: activeToc === t.idx }, 'lv' + Math.min(t.level, 3)]"
                :title="t.title"
                @click="scrollToToc(t.idx)"
              >
                {{ t.title }}
              </button>
            </nav>

            <div ref="docBox" class="doc-scroll" @scroll.passive="onScroll">
              <article class="doc-paper">
                <!-- 有留档原文就用 markdown 渲染（代码块有高亮、标题成层级） -->
                <MarkdownRenderer v-if="isText" :text="docText" />
                <!-- 否则退回章节流（粘贴导入的旧文档没留原文） -->
                <section v-for="(c, i) in chapters" v-else :key="i" class="ch-block">
                  <h4 class="ch-title">{{ c.title }}</h4>
                  <div class="ch-body">{{ c.body }}</div>
                  <div v-if="aiOf(c).analogy || aiOf(c).points?.length" class="ai">
                    <div v-if="aiOf(c).analogy" class="ai-row">
                      <span class="ai-k">类比</span>
                      <span class="ai-v">{{ aiOf(c).analogy }}</span>
                    </div>
                    <ul v-if="aiOf(c).points?.length" class="ai-v">
                      <li v-for="(p, pi) in aiOf(c).points" :key="pi">{{ p }}</li>
                    </ul>
                  </div>
                </section>
              </article>
            </div>
          </div>
        </template>
      </main>
    </div>

    <!-- AI 问答：浮在右下角的抽屉，不占正文宽度。
         正文列宽是照飞书定的（680px 最佳行长），再塞一栏固定的问答会把
         正文挤到 600px 以下 —— 窄了行长就短，一句话断成三行。
         但论文的原件区本来就是「居中窄页+ 左右大片留白」，
         把抽屉做成浮层叠在右侧留白上，对论文一点宽度都不占。 -->
    <aside v-if="aiOpen && opened" class="kb-ai kb-qa panel">
      <header class="panel-head">
        <h3>AI 问答</h3>
        <button class="btn btn-bare" @click="qaTurns = []; qaInput = ''">清空</button>
        <button class="btn btn-bare" @click="aiOpen = false">收起</button>
      </header>

      <div ref="qaBox" class="qa-body">
        <!-- 空态：给引导问题而不是一句「暂无内容」——
             空面板用户不知道怎么用，点一个按钮就学会了。 -->
        <div v-if="!qaTurns.length" class="qa-intro">
          <p class="dim">只依据这份文档回答，不联网、不用外部知识。答案出不来时它会直说。</p>
          <button v-for="h in qaHints" :key="h" class="qa-hint" :disabled="qaBusy" @click="onAsk(h)">
            {{ h }}
          </button>
        </div>

        <div v-for="(t, i) in qaTurns" :key="i" class="qa-turn" :class="t.role">
          <div v-if="t.role === 'q'" class="qa-q">{{ t.text }}</div>
          <template v-else>
            <div v-if="!t.text" class="qa-thinking">
              <span class="dot" /><span class="dot" /><span class="dot" />
              <span class="dim">正在读文档…</span>
            </div>
            <MarkdownRenderer v-else :text="t.text" />
            <!-- 命中片段：让用户能核对答案是从哪几段来的 -->
            <div v-if="t.sources?.length" class="qa-src">依据片段 {{ t.sources.join('、') }}</div>
            <!-- 反馈：回答完才出现，驱动自进化 RAG 纠错 -->
            <div v-if="t.text && !qaVotes[i]" class="qa-fb">
              <button class="btn btn-bare" :disabled="qaBusy" title="答得对" @click="vote(i, true)">👍 准</button>
              <button class="btn btn-bare" :disabled="qaBusy" title="答错了" @click="vote(i, false)">👎 错</button>
            </div>
            <div v-else-if="qaVotes[i]" class="qa-fb dim">
              已反馈：{{ qaVotes[i] === 'up' ? '👍 已认可' : '👎 已纠正（以后不再复用此答）' }}
            </div>
          </template>
        </div>
      </div>

      <div class="qa-foot">
        <textarea
          v-model="qaInput"
          class="qa-in"
          rows="2"
          placeholder="就这份文档问一句…（Enter 发送，Shift+Enter 换行）"
          @keydown.enter.exact.prevent="onAsk()"
        />
        <button class="btn btn-primary" :disabled="qaBusy || !qaInput.trim()" @click="onAsk()">
          {{ qaBusy ? '回答中' : '发送' }}
        </button>
      </div>
    </aside>

    <!-- 提取文本抽屉：PDF 的「文本版」放这儿，而不是顶掉原件。
         它是机器抽取的结果 —— 双栏交错、图表丢失，**不适合阅读**，
         但全文搜索、复制、AI 精读、RAG 检索都靠它。定位说清楚，
         免得用户以为是原件渲染坏了。 -->
    <aside v-if="showExtract && opened" class="kb-ai panel">
      <header class="panel-head">
        <h3>提取文本</h3>
        <button class="btn btn-bare" @click="showExtract = false">收起</button>
      </header>
      <div class="extract-note">
        机器从原件抽取的纯文本，供<b>搜索、复制、AI 精读</b>使用。 双栏论文的图表与公式会丢失 ——
        <b>阅读请看左侧原件</b>。
      </div>
      <div class="extract-body" ref="extractBox">
        <pre>{{ docText }}</pre>
      </div>
      <div class="extract-foot">
        <span class="dim">{{ docText.length }} 字</span>
        <button class="btn btn-bare" @click="copyText">复制全文</button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.kb {
  display: flex;
  flex-direction: column;
  /* gap 8px 而不是 14px：顶栏/导入框/正文三段之间各14px，
     论文区上方就有 42px 的纯留白。这个页面 90% 的时间是在读 PDF，
     这些留白没有任何信息量。收起顶部时进一步压到 4px。 */
  gap: 8px;
  height: 100%;
  min-height: 0;
}
.kb.slim-root {
  gap: 4px;
}

.kb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  transition: padding 0.18s;
  /* ★ 上方压缩（2026-10-11）：论文是「竖长」内容，纵向每一像素都是钱 ——
     顶栏和标题栏各占一格，两格加起来吃掉约 100px，
     相当于少看三分之一页 A4。所以这两个头都改成单行紧凑排版。
     用padding 减半而不是缩小字号：字号缩到 13px 以下在Windows 上
     反而因为 hinting 显得更小更糊。 */
  padding: 9px 16px;
  flex: none;
}
.kb-head h3 {
  font-size: var(--fs-md);
  font-weight: 600;
  margin: 0;
}
/* 收起态：整条压到 26px。这条和下面的 .reader-head 各省约 24px，
   合计接近小半页 A4 —— 这就是「论文区高一点」的全部来源。 */
.kb-head.slim {
  padding: 2px 12px;
}
.kb-head.slim h3 {
  font-size: var(--fs-sm);
}
.slim-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 1px 6px 1px 2px;
  font: inherit;
  color: inherit;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.slim-toggle:hover {
  color: var(--ac);
  background: var(--ac-glow);
}
.slim-arrow {
  font-size: 10px;
  color: var(--dim);
}
.kb-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}
.kb-search {
  width: 260px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line2);
  background: var(--panel2);
  color: var(--tx);
  font-size: var(--fs-sm);
  outline: none;
  transition: border-color 0.16s;
}
.kb-search:focus {
  border-color: var(--ac);
}
.kb-search::placeholder {
  color: var(--dim);
}

.import-box {
  flex: none;
  padding: 16px 20px;
}
.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.file-btn {
  position: relative;
  overflow: hidden;
  display: inline-block;
  padding: 7px 14px;
  border: 1px dashed var(--ac);
  border-radius: 6px;
  color: var(--ac);
  font-size: 13.5px;
  cursor: pointer;
}
.file-btn:hover {
  background: var(--ac-glow);
}
.file-btn input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.lb {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--mu);
}
.lb em {
  font-style: normal;
  font-weight: 400;
  margin-left: 6px;
}
.kb-input {
  padding: 9px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line2);
  background: var(--panel2);
  color: var(--tx);
  font-size: var(--fs-sm);
  font-family: inherit;
  outline: none;
  resize: vertical;
  transition: border-color 0.16s;
}
.kb-input:focus {
  border-color: var(--ac);
}

/* 左：文件夹树（可收起） | 右：阅读区（含目录 + 正文） */
.kb-body {
  display: grid;
  grid-template-columns: 244px minmax(0, 1fr);
  gap: 14px;
  flex: 1;
  min-height: 0;
}
/* 收起：保留一列 22px 给「展开」把手。整块 display:none 会让
   展开入口一起消失 —— 这个面板是导航，失去入口就等于废了。
   ★ 展开态的把手不做成 grid 子元素（见下面 .side-handle 的注释），
     收起态才让把手占列：那时树已经 v-if 掉了，不存在抢列的问题。 */
.kb-body.side-closed {
  grid-template-columns: 22px minmax(0, 1fr);
}

.kb-tree,
.kb-reader,
.kb-ai {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 0;
}
/* ★ 面板内的把手（贴在树左缘），而不是 kb-body 的独立子元素。
   放成独立子元素时它会**占掉 grid 的第一列**（244px 那一格），
   把真正的树挤到第二列去 —— 表现是「树跑到中间去了，
   左边剩一条空窄条」。教训：grid 子元素**每一个**都占一格，
   不加 position 就会被算进去。 */
.kb-tree {
  position: relative;
}
.side-handle {
  position: absolute;
  left: -1px;
  top: 0;
  bottom: 0;
  width: 16px;
  padding: 0;
  font-size: 11px;
  color: var(--dim);
  background: none;
  border: 0;
  border-right: 1px solid var(--line);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.14s;
}
.kb-tree:hover .side-handle {
  opacity: 1;
}
.side-handle:hover {
  color: var(--ac);
  opacity: 1;
}
/* 收起态的展开把手：grid 子元素（树已v-if 掉，这一格空着给它） */
.side-handle-lite {
  position: relative;
  left: auto;
  top: auto;
  bottom: auto;
  width: auto;
  height: 100%;
  font-size: 15px;
  border-right: 0;
  border-radius: var(--radius-sm);
  background: var(--panel);
  opacity: 1;
  font-family: var(--font-title);
}
.side-handle-lite:hover {
  background: var(--panel2);
}
.tree-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px 8px;
  border-bottom: 1px solid var(--line);
  flex: none;
}
.tree-top-title {
  font-size: var(--fs-xs);
  letter-spacing: 0.6px;
  color: var(--dim);
  text-transform: uppercase;
}
.tree-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 10px 14px;
}
.tree-foot {
  flex: none;
  padding: 8px 14px;
  border-top: 1px solid var(--line);
  font-size: 10.5px;
  color: var(--dim);
}

/* 「全部」虚拟根 —— 不是文件夹，只用来折叠/展开 + 计数。
   顶上一条细横线把它和下面的真实文件夹分开，否则它会看起来像同级节点。 */
.node.root > .node-row {
  margin-bottom: 2px;
}
/* 子层缩进。和 KbTreeNode.vue 里的 .kids 是同一套值 ——
   同一个视觉层级不能有两种缩进，「全部」下的第一层和文件夹下的
   第一层必须对齐。★ 注意子组件的样式是 **scoped** 的，父组件里的
   .kids 不会自动继承，得各写一份（同一个数抄两遍比两套值安全）。 */
.kids {
  padding-left: 13px;
  margin-left: 7px;
  border-left: 1px solid var(--line);
}
/* 父组件里的两行虚拟节点（「全部」「未归档」）共用同一套行样式。
   ★ 必须和 KbTreeNode.vue 里的值保持一致：树里只有这两行在父组件，
     别的行在子组件 —— 两套值会让「全部」这一行的字号/缩进和它下面
     的文件夹对不齐，看起来像「树歪了一格」。
     而子组件样式是 **scoped** 的，这边写了也不影响它，所以只能抄一份。 */
.node-row {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px 5px 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.14s;
}
.node-row:hover {
  background: var(--panel2);
}
.arw {
  flex: none;
  width: 12px;
  font-size: 9px;
  color: var(--dim);
  transition: transform 0.16s;
}
.arw.open {
  transform: rotate(90deg);
}
.ico {
  flex: none;
  font-size: 12px;
  line-height: 1;
}
.node-row .nm {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
  color: var(--tx);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-row .cnt {
  flex: none;
  font-size: 10.5px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}

.node.orphan {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--line);
}
.node.orphan > .node-row {
  color: var(--dim);
}
.node.orphan .nm {
  color: var(--mu);
}

/* 左树里的文档叶子。未归类的也用同一套 —— 之前「资料」下面是
   一串带「原件」徽标的行，「未分类」是另一套，视觉上像两种东西。 */
.tree-scroll .leaf {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.tree-scroll .leaf:hover {
  background: var(--panel2);
}
.tree-scroll .leaf.on {
  background: var(--ac-glow);
}
.tree-scroll .leaf .nm {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-scroll .leaf .leaf-acts {
  display: none;
  gap: 2px;
}
.tree-scroll .leaf:hover .leaf-acts {
  display: flex;
}
.tree-scroll .leaf .leaf-acts button {
  padding: 0 5px;
  font-size: 10px;
  line-height: 16px;
  color: var(--ac);
  background: var(--ac-glow);
  border: 1px solid var(--ac-dim);
  border-radius: 4px;
  cursor: pointer;
}
.type-btn {
  padding: 5px 12px;
  font-size: 12.5px;
  border-radius: 999px;
  border: 1px solid var(--line2);
  background: var(--panel2);
  color: var(--mu);
  cursor: pointer;
  transition: all 0.16s;
}
.type-btn:hover {
  border-color: var(--ac-dim);
  color: var(--tx);
}
.type-btn.on {
  border-color: var(--ac);
  background: var(--ac-glow);
  color: var(--ac);
  font-weight: 600;
}

.reader-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  /* 单行紧凑：标题和操作按钮同一基线。省下的一行正是论文正文要的位置。 */
  padding: 8px 14px;
  border-bottom: 1px solid var(--line);
  flex: none;
  transition: padding 0.18s;
}
/* 收起态：只留标题 + 四个按钮，压到 ~26px。
   border-bottom 保留 —— 去掉的话 PDF 会直接顶到标题文字上，
   视觉上像布局散了，而不是像「被压缩了」。 */
.reader-head.slim {
  padding: 2px 12px;
}
.slim-title {
  margin: 0;
  font-size: var(--fs-sm);
  font-weight: 600;
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reader-title {
  min-width: 0;
}
.reader-title h3 {
  font-size: var(--fs-md);
  font-weight: 600;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reader-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  overflow: hidden;
}
.reader-actions {
  display: flex;
  gap: 8px;
  flex: none;
}
.reader-head.slim .reader-actions {
  gap: 4px;
}
/* 收起态下按钮要更矮，否则行高被按钮撑回去，padding 省下的都白省了 */
.reader-head.slim .btn {
  padding: 2px 8px;
  font-size: var(--fs-xs);
  line-height: 18px;
}
.reader-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}
/* .pdf-frame 已删：PDF 改由 PdfViewer 自己渲染，不再用 iframe。 */
.docx-hint {
  flex: 1;
  align-content: center;
}

/* ===== 文档视图（飞书式）=====
 * 两条是照着飞书文档抄的，不是审美偏好：
 *
 * 1. **正文列限宽 680px 并居中**。飞书的默认页宽就是这个量级，根源是
 *    「一行 65 字符」—— 一行太长眼睛要横扫回去接行，读几段就累；
 *    太短又会被迫频繁换行打断句子。1200px 满宽的中文一行能塞 60 个字，
 *    正好是最难受的那个区间。
 * 2. **左侧目录悬浮在正文外**。它是导航不是内容，压在正文上会挡字；
 *    放正文左边又不占滚动区，跳转靠 scrollIntoView。 */
.reader-body {
  flex: 1;
  min-height: 0;
  display: flex;
}
.doc-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 36px 32px 80px;
}
.doc-paper {
  max-width: 680px;
  margin: 0 auto;
}

/* 文档视图里覆盖 MarkdownRenderer 的「聊天气泡」节奏。
   那边段距 6px 是为了不让长回答看起来漏内容；文章里 6px 太紧，
   段落糊成一片，正是「不想看」的来源之一。 */
.doc-paper :deep(p) {
  margin: 14px 0;
  line-height: 1.95;
}
.doc-paper :deep(h1),
.doc-paper :deep(h2),
.doc-paper :deep(h3),
.doc-paper :deep(h4) {
  font-family: var(--font-title);
  scroll-margin-top: 20px;
  margin: 34px 0 12px;
}
.doc-paper :deep(h1) {
  font-size: 1.72em;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}
.doc-paper :deep(h2) {
  font-size: 1.4em;
}
.doc-paper :deep(h3) {
  font-size: 1.2em;
}
.doc-paper :deep(h4) {
  font-size: 1.08em;
}
/* 首个标题不额外上边距：正文列顶部已有 36px 内边距，
   再叠 34px margin 会让标题低下去一截，看着像没对齐 */
.doc-paper :deep(> *:first-child) {
  margin-top: 0;
}
.doc-paper :deep(ul),
.doc-paper :deep(ol) {
  line-height: 1.9;
  margin: 12px 0;
}
.doc-paper :deep(blockquote) {
  border-left: 3px solid var(--line2);
  padding-left: 16px;
  color: var(--mu);
  margin: 16px 0;
}
/* 代码块：气泡里的样式在文档里太挤。行高放宽一点、
   左右留点呼吸，长行能横向滚而不是撑破正文列。 */
.doc-paper :deep(.md-codeblk) {
  margin: 20px 0;
  border-radius: var(--radius-sm);
  box-shadow: 0 3px 12px -4px rgba(30, 30, 30, 0.4);
}
.doc-paper :deep(.md-codeblk pre) {
  padding: 16px 18px;
  font-size: 13.5px;
  line-height: 1.8;
}
.doc-paper :deep(.md-code-head) {
  background: rgba(255, 255, 255, 0.06);
  padding: 7px 14px;
}
.doc-paper :deep(.md-code-lang) {
  color: #9aa8b5;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  font-size: 11px;
}

/* 目录 */
.doc-toc {
  flex: none;
  width: 208px;
  padding: 26px 12px 26px 18px;
  overflow-y: auto;
  border-right: 1px solid var(--line);
}
.doc-toc .toc-head {
  margin-bottom: 10px;
  font-size: var(--fs-xs);
}
.toc-item {
  display: block;
  width: 100%;
  padding: 5px 10px;
  border: 0;
  border-left: 2px solid transparent;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: none;
  color: var(--mu);
  font-size: var(--fs-sm);
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition:
    background 0.14s,
    color 0.14s;
}
.toc-item:hover {
  background: var(--panel2);
  color: var(--tx);
}
.toc-item.on {
  border-left-color: var(--ac);
  background: var(--ac-glow);
  color: var(--ac);
  font-weight: 600;
}
/* 层级只做轻微缩进。飞书最多 9 级标题，真给 9 档缩进的话目录右半边全是
 * 缩进线，反而找不到字 —— 层级靠字重和缩进一点点就够。 */
.toc-item.lv2 {
  padding-left: 20px;
}
.toc-item.lv3 {
  padding-left: 30px;
  font-size: var(--fs-xs);
}

/* 章节块（无留档原文时的退化视图） */
.ch-block {
  margin-bottom: 34px;
  scroll-margin-top: 20px;
}
.ch-title {
  font-family: var(--font-title);
  font-size: var(--fs-lg);
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.ch-body {
  font-size: var(--fs-md);
  line-height: 1.95;
  color: var(--tx);
  white-space: pre-wrap;
  word-break: break-word;
}
.ai {
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  border-left: 2px solid var(--ac);
  background: var(--ac-glow);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-row {
  display: flex;
  gap: 10px;
  font-size: var(--fs-sm);
}
.ai-k {
  flex: none;
  width: 38px;
  font-weight: 600;
  color: var(--ac);
}
.ai-v {
  flex: 1;
  min-width: 0;
  line-height: 1.7;
}
.ai-v ul {
  margin: 0;
  padding-left: 16px;
}
.ai-v li {
  margin-bottom: 2px;
}

/* 注解抽屉：贴右下角的浮层，不参与 kb-body 的三栏网格。
   fixed + 右下角锚定，避开顶栏和侧栏。 */
.kb-ai {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 20;
  width: 320px;
  max-height: 58vh;
  box-shadow:
    var(--shadow),
    0 0 0 1px rgba(58, 47, 33, 0.08);
  animation: rise 0.28s cubic-bezier(0.22, 0.7, 0.28, 1) both;
}
.kb-ai .panel-head {
  padding: 14px 16px;
  margin-bottom: 0;
}
.ai-panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 16px;
}

/* ===== AI 问答抽屉 =====
 * 比注解宽、比注解高：问答是来回多轮的，320px 宽的窄条里
 * 一行放十几个字，读起来比论文本身还费劲。 */
.kb-qa {
  width: 400px;
  /* ★ 用 max-height 而不是固定 height：**内容少时（刚打开、只问了一句）
   *   固定 height 会让中间留一大片空白，输入框被顶到屏幕最底下，
   *   眼睛要在一堆空气里找输入框。max-height 让它贴着内容长高，
   *   聊多了才涨到上限、开始内部滚动。 */
  max-height: min(72vh, 640px);
  display: flex;
  flex-direction: column;
}
.kb-qa .panel-head {
  padding: 10px 14px;
  flex: none;
}
.qa-body {
  /* 不给 flex:1 —— 有它就会把面板撑满高度，正好是要避免的。
     给一个 max-height，超过就自己滚。 */
  max-height: min(52vh, 460px);
  overflow-y: auto;
  padding: 12px 14px;
}
.qa-intro p {
  margin: 0 0 10px;
  font-size: var(--fs-xs);
  line-height: 1.6;
}
.qa-hint {
  display: block;
  width: 100%;
  text-align: left;
  padding: 7px 10px;
  margin-bottom: 6px;
  font-size: var(--fs-sm);
  color: var(--mu);
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.16s;
}
.qa-hint:hover:not(:disabled) {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.qa-hint:disabled {
  opacity: 0.5;
  cursor: default;
}
.qa-turn {
  margin-bottom: 12px;
}
.qa-q {
  align-self: flex-end;
  max-width: 88%;
  padding: 7px 11px;
  margin-left: auto;
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: var(--tx);
  background: var(--ac-glow);
  border: 1px solid var(--ac-dim);
  border-radius: 10px 10px 2px 10px;
}
.qa-turn.a {
  padding: 0 2px;
  font-size: var(--fs-sm);
  line-height: 1.75;
  color: var(--tx);
}
/* MarkdownRenderer 渲染出来的元素默认有 margin，收紧一下不然对话很散 */
.qa-turn.a :deep(p) {
  margin: 0 0 6px;
}
.qa-turn.a :deep(p:last-child) {
  margin-bottom: 0;
}
.qa-turn.a :deep(ul),
.qa-turn.a :deep(ol) {
  margin: 4px 0 6px;
  padding-left: 18px;
}
.qa-src {
  margin-top: 5px;
  font-size: var(--fs-xs);
  color: var(--dim);
}
.qa-fb {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
}
.qa-fb .btn {
  font-size: var(--fs-xs);
  padding: 1px 7px;
  line-height: 1.6;
}
.qa-thinking {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-xs);
  color: var(--dim);
}
/* 三个点依次跳 —— 本地模型首个 token 要好几秒，
   没有这个用户会以为卡死而关掉面板。 */
.qa-thinking .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--ac);
  animation: qaBlink 1.2s infinite;
}
.qa-thinking .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.qa-thinking .dot:nth-child(3) {
  animation-delay: 0.4s;
  margin-right: 3px;
}
@keyframes qaBlink {
  0%,
  60%,
  100% {
    opacity: 0.25;
  }
  30% {
    opacity: 1;
  }
}
.qa-foot {
  flex: none;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
}
.qa-in {
  flex: 1;
  min-height: 38px;
  max-height: 120px;
  padding: 8px 10px;
  font-size: var(--fs-sm);
  line-height: 1.5;
  color: var(--tx);
  background: var(--panel2);
  border: 1px solid var(--line2);
  border-radius: var(--radius-sm);
  outline: none;
  resize: vertical;
  font-family: inherit;
}
.qa-in:focus {
  border-color: var(--ac);
}
.ai-chapter {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.ai-chapter:last-child {
  border-bottom: 0;
  margin-bottom: 0;
  padding-bottom: 0;
}
.ai-ch-title {
  font-size: var(--fs-sm);
  font-weight: 600;
  margin-bottom: 6px;
}
.ai-line {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.7;
  margin-bottom: 4px;
}
.ai-points {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: var(--fs-sm);
  color: var(--mu);
}
.ai-points li {
  margin-bottom: 2px;
}

/* 提取文本抽屉 */
.extract-note {
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel2);
  font-size: var(--fs-xs);
  line-height: 1.7;
  color: var(--mu);
}
.extract-note b {
  color: var(--tx);
}
.extract-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 16px;
}
.extract-body pre {
  margin: 0;
  font-family: var(--font);
  font-size: var(--fs-sm);
  line-height: 1.85;
  color: var(--mu);
  white-space: pre-wrap;
  word-break: break-word;
}
.extract-body mark {
  background: rgba(200, 160, 60, 0.35);
  color: var(--tx);
  border-radius: 2px;
  padding: 0 1px;
}
.extract-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px;
  border-top: 1px solid var(--line);
  font-size: var(--fs-xs);
}

/* 窄屏逐级让路：先收问答（浮层挡字），再收目录，最后收资料树。
   目录优先级高于资料树 —— 正在读一份文档时，「跳到第 7 章」比
   「换一份文档」用得频繁得多。 */
@media (max-width: 1400px) {
  .kb-ai {
    width: 300px;
    max-height: 50vh;
  }
  /*问答要来回多轮，压得太窄反而不好用 —— 所以比注解多留一点，
     再窄才退成 280。 */
  .kb-qa {
    width: 340px;
    max-height: min(66vh, 560px);
  }
  .qa-body {
    max-height: min(46vh, 380px);
  }
}
@media (max-width: 1150px) {
  .kb-body {
    grid-template-columns: 208px minmax(0, 1fr);
  }
  .doc-toc {
    display: none;
  }
}
/* 窄屏：左树自动收起成把手（收起后仍留 22px 把手能展开回来）。
   用 :not(.side-closed) 是为了尊重用户的手动选择 —— 已经自己收起的
   面板不会被这条规则再展开，也已经被手动展开的不强制收掉。 */
@media (max-width: 860px) {
  .kb-body {
    grid-template-columns: 22px minmax(0, 1fr);
  }
  .kb-tree {
    display: none;
  }
  .doc-scroll {
    padding: 24px 18px 72px;
  }
}
</style>
