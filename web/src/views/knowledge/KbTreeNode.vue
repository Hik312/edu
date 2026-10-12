<script setup>
/* 知识库文件夹树的**递归**节点组件。
 *
 * ★ 为什么必须单独抽成组件而不是在 KnowledgeView 里 v-for 套 v-for：
 *   树是任意层级的（资料 → RAG → 0/1/2 → 子目录……），层数用户自己定。
 *   固定层数的嵌套 v-for 写不出来，只能递归 —— 一个组件在自己的
 *   template 里引用自己。Vue 的 `<script setup>` 里组件可以按文件名
 *   直接引用（这里就是 KbTreeNode），不需要显式 import。
 *
 * 它是**纯展示 + 抛事件**：不调 API、不改状态。所有的写操作都交给父级，
 * 由父级用响应里回传的整棵树统一覆盖 —— 树只有一份真值。
 *
 * 折叠时不是 v-if 卸载，而是保留 DOM 但隐藏：卸载会丢掉滚动位置，
 * 展开时整棵子树重新插入，滚动容器会跳一下。
 */
import { computed, ref } from 'vue'

const props = defineProps({
  /** 视图模型节点（不是库里那份）：{id,name,docs:[文档对象],children:[…],total,collapsed} */
  node: { type: Object, required: true },
  /** 当前打开的文档 id，用来高亮。 */
  activeId: { type: [String, Number], default: null },
  /** 正在被悬停的拖放目标文件夹 id。 */
  dragOver: { type: String, default: '' },
  /** (doc) => boolean：这份文档是不是只属于当前这个文件夹。
   *
   *  ★ 传函数而不是在组件里算：子组件看得到的是**过滤后的视图**
   *    （treeView 可能是搜索态、也可能只有部分），要判断「还有没有
   *    别的归属」必须查库里那份完整树。视图算出来的答案会骗人。 */
  canLeave: { type: Function, default: () => () => false }
})

const emit = defineEmits([
  'open', // (doc) 打开文档
  'toggle', // (node) 折叠/展开
  'rename', // (node) 重命名文件夹
  'del', // (node) 删文件夹
  'new-sub', // (parentId) 新建子文件夹
  'move-sub', // (fid, parentId) 移动文件夹
  'place', // (doc, folder) 把文档放进这个文件夹
  'unplace', // (doc, folderId) 从这个文件夹移出
  'drop-node', // (ev, node) 有东西被拖到这个文件夹上
  'drag-folder', // (ev, node) 开始拖文件夹
  'drag-doc', // (ev, doc) 开始拖文档
  'drag-over', // (ev, node)
  'drag-leave', // (ev, node)
  'rename-doc', // (doc)
  'remove-doc', // (doc)
  'import-into' // (folderId) 导入到这个文件夹
])

/** 菜单默认关着。树上悬停就弹一堆按钮太吵（PyCharm 也是靠右键）。 */
const menu = ref(false)
const menuPos = ref({ x: 0, y: 0 })

/** 在鼠标位置弹菜单。
 *
 *  ★ 记下坐标而不是「出现在按钮正下方」：树可能很长，
 *    顶部节点的按钮贴着屏幕顶，菜单往下展开直接跑出视口，
 *    用户得滚页面才能看到菜单 —— 而此时菜单已经关了。 */
function openMenu(ev) {
  menuPos.value = { x: ev.clientX, y: ev.clientY }
  menu.value = !menu.value
}

/** 点空白处关菜单。菜单是 fixed 定位的浮层，点击别处必须能收掉。 */
function closeMenu() {
  menu.value = false
}

/** 「移出这个文件夹」能不能点，交给父级判断（见 canLeave prop）。 */
function canLeave(d) {
  return props.canLeave(d)
}

/** 文档尾部的小徽标：有原件就标一下 —— 论文靠它走 PDF 原件阅读。
 *  和旧的 `isPaper` / `rawFile` 两个分支合并成一个：
 *  界面上区分两种没有任何意义，用户只需要知道「有原件」。 */
function badge(d) {
  if (d.isPaper) return '论文'
  if (d.rawFile) return '原件'
  return ''
}
</script>

<template>
  <div class="node" :style="{ '--d': 0 }">
    <!-- 文件夹行 -->
    <div
      class="node-row"
      :class="{ over: dragOver === node.id }"
      draggable="true"
      @click="emit('toggle', node)"
      @dragstart="emit('drag-folder', $event, node)"
      @dragover="emit('drag-over', $event, node)"
      @dragleave="emit('drag-leave', $event, node)"
      @drop="emit('drop-node', $event, node)"
      @contextmenu.prevent="openMenu($event)"
    >
      <span class="arw" :class="{ open: !node.collapsed }">▸</span>
      <span class="ico">📁</span>
      <span class="nm" :title="node.name">{{ node.name }}</span>
      <span class="cnt">{{ node.total }}</span>
      <span class="acts" @click.stop>
        <button title="新建子文件夹" @click="emit('new-sub', node.id)">＋</button>
        <button title="更多" @click="openMenu($event)">⋯</button>
      </span>
    </div>

    <!-- 右键/⋯ 菜单。删单独做危险色，且放在最后。 -->
    <div
      v-if="menu"
      class="menu panel"
      :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }"
      @click="closeMenu"
    >
      <button @click="emit('rename', node)">重命名</button>
      <button @click="emit('new-sub', node.id)">新建子文件夹</button>
      <button @click="emit('import-into', node.id)">导入到此文件夹…</button>
      <div class="menu-sep" />
      <button @click="emit('move-sub', node.id, '')">移到顶层</button>
      <button class="danger" @click="emit('del', node)">删除文件夹</button>
    </div>

    <!-- 折叠时保留 DOM（见文件头注释） -->
    <div v-show="!node.collapsed" class="kids">
      <!-- 子文件夹：递归自己 -->
      <KbTreeNode
        v-for="c in node.children"
        :key="c.id"
        :node="c"
        :active-id="activeId"
        :drag-over="dragOver"
        :can-leave="canLeave"
        @open="emit('open', $event)"
        @toggle="emit('toggle', $event)"
        @rename="emit('rename', $event)"
        @del="emit('del', $event)"
        @new-sub="(id) => emit('new-sub', id)"
        @move-sub="(id, p) => emit('move-sub', id, p)"
        @place="(d, f) => emit('place', d, f)"
        @unplace="(d, f) => emit('unplace', d, f)"
        @drop-node="(e, n) => emit('drop-node', e, n)"
        @drag-folder="(e, n) => emit('drag-folder', e, n)"
        @drag-doc="(e, d) => emit('drag-doc', e, d)"
        @drag-over="(e, n) => emit('drag-over', e, n)"
        @drag-leave="(e, n) => emit('drag-leave', e, n)"
        @rename-doc="d => emit('rename-doc', d)"
        @remove-doc="d => emit('remove-doc', d)"
        @import-into="id => emit('import-into', id)"
      />

      <!-- 本文件夹里的文档（叶子） -->
      <div
        v-for="d in node.docs"
        :key="d.id"
        class="leaf"
        :class="{ on: activeId === d.id }"
        draggable="true"
        :title="d.title"
        @click="emit('open', d)"
        @dragstart="emit('drag-doc', $event, d)"
      >
        <span class="nm">{{ d.title }}</span>
        <span v-if="badge(d)" class="bdg">{{ badge(d) }}</span>
        <span class="acts" @click.stop>
          <button v-if="canLeave(d)" title="移出这个文件夹" @click="emit('unplace', d, node.id)">
            移出
          </button>
          <button title="改名" @click="emit('rename-doc', d)">改名</button>
          <button title="删除" @click="emit('remove-doc', d)">×</button>
        </span>
      </div>

      <div v-if="!node.children.length && !node.docs.length" class="leaf-hint">
        空文件夹 · 拖进来，或点 ＋
      </div>
    </div>
  </div>
</template>

<style scoped>
.node {
  position: relative; /* 菜单 absolute 定位的锚 */
}

/* 行：文件夹和文档共用一套排版，只是图标不同。
   统一成一行是必要的 —— 混用两套 padding 会让树看起来「歪」，
   因为同一列的左边缘对不齐。 */
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
/* 拖放悬停：整行高亮而不是描边。用户要一眼看出「会放这儿」，
   描边太弱，而且和 hover 态会打架。 */
.node-row.over {
  background: var(--ac-glow);
  box-shadow: inset 0 0 0 1px var(--ac);
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
.nm {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
  color: var(--tx);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cnt {
  flex: none;
  font-size: 10.5px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}

/* 操作按钮：hover 才显形。树上全是标签，实体按钮太吵。 */
.acts {
  display: none;
  flex: none;
  gap: 2px;
}
.node-row:hover .acts,
.leaf:hover .acts {
  display: flex;
}
.node-row:hover .cnt {
  display: none; /* 让位给按钮，数量信息没那么重要 */
}
.acts button {
  padding: 0 4px;
  font-size: 10px;
  line-height: 16px;
  color: var(--mu);
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
}
.acts button:hover {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.acts button:last-child:hover {
  color: var(--danger, #c0392b);
  border-color: currentColor;
}

.kids {
  padding-left: 13px;
  margin-left: 7px;
  border-left: 1px solid var(--line);
}

.leaf {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.14s;
}
.leaf:hover {
  background: var(--panel2);
}
.leaf.on {
  background: var(--ac-glow);
}
.leaf.on .nm {
  color: var(--ac);
  font-weight: 600;
}
.leaf .nm {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.bdg {
  flex: none;
  font-size: 9.5px;
  line-height: 15px;
  padding: 0 4px;
  color: var(--ac);
  border: 1px solid var(--ac-dim);
  border-radius: 4px;
}

.leaf-hint {
  padding: 4px 6px;
  font-size: var(--fs-xs);
  color: var(--dim);
  font-style: italic;
}

/* 右键菜单：fixed 定位跟着鼠标走。比「点⋯ 后出现在按钮下方」好，
   因为树可能很长，菜单出现在屏幕外就找不到了。 */
.menu {
  position: fixed;
  z-index: 60;
  display: flex;
  flex-direction: column;
  min-width: 156px;
  padding: 4px;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow);
  transform: translate(2px, 2px);
}
.menu button {
  padding: 6px 10px;
  font-size: var(--fs-sm);
  color: var(--tx);
  text-align: left;
  background: none;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}
.menu button:hover {
  background: var(--panel2);
}
.menu button.danger {
  color: var(--danger, #c0392b);
}
.menu-sep {
  height: 1px;
  margin: 4px 2px;
  background: var(--line);
}
</style>