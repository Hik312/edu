<script setup>
/* 笔记 —— 两种形态共用一张表，靠 cardId 区分：
 *
 *   独立笔记  cardId 为空，就是普通笔记本
 *   卡片理解  cardId 有值，是挂在某张卡下面的心得
 *
 * 界面上不把这两种拆成两个菜单：**用户不关心数据怎么存，只关心自己写了什么**。
 * 区别只体现在列表里那一行「挂在 xx 卡下」的角标。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listNotes, removeNote, saveNote } from '@/api/notes'

const notes = ref([])
const loading = ref(false)
const saving = ref(false)

// 搜索词从 localStorage 起：setup 期赋初值，下面的 watch(q) 不会误触发一次搜索
const q = ref(localStorage.getItem('edu.noteQ') || '')
/** 当前正在编辑的笔记。id 为空串表示「新建且还没存过」。 */
const form = ref({ id: '', title: '', body: '', tags: '', cardId: '' })
const dirty = ref(false)

/** 未保存的正文刷新不该没 —— 写了一半的字丢了是最招人烦的一类事故。
 *  只在 dirty 时存；保存 / 丢弃 / 新建都会把 dirty 置回 false → 自动清掉。 */
function persist() {
  try {
    if (q.value) localStorage.setItem('edu.noteQ', q.value)
    else localStorage.removeItem('edu.noteQ')
    if (dirty.value) localStorage.setItem('edu.noteDraft', JSON.stringify(form.value))
    else localStorage.removeItem('edu.noteDraft')
  } catch {
    /* 配额满了就不存 */
  }
}
watch([q, form, dirty], persist, { deep: true })

/** 搜索防抖。每敲一个字就打一次接口，本地跑没事，
 *  换成云上 MySQL 会把连接池占满。 */
let timer = 0
watch(q, () => {
  clearTimeout(timer)
  timer = setTimeout(fetchList, 280)
})

async function fetchList() {
  loading.value = true
  try {
    const params = {}
    if (q.value.trim()) params.q = q.value.trim()
    notes.value = (await listNotes(params)).notes || []
  } finally {
    loading.value = false
  }
}

/** 打开一篇。改动未保存时先问一句 ——
 *   silently 丢掉用户刚写的字是最招人烦的一类 bug。 */
async function openNote(n) {
  if (dirty.value && !(await confirmDiscard())) return
  form.value = {
    id: n.id || '',
    title: n.title || '',
    body: n.body || '',
    tags: (n.tags || []).join(', '),
    cardId: n.cardId || ''
  }
  dirty.value = false
}

/** 新建。改动未保存时也要先问 —— 新建按钮一样能毁掉没保存的内容。 */
async function newNote() {
  if (dirty.value && !(await confirmDiscard())) return
  form.value = { id: '', title: '', body: '', tags: '', cardId: '' }
  dirty.value = false
}

async function onSave() {
  if (!form.value.title.trim() && !form.value.body.trim()) {
    ElMessage.warning('标题和正文至少写一个')
    return
  }
  saving.value = true
  try {
    const body = {
      title: form.value.title.trim() || '未命名笔记',
      body: form.value.body,
      cardId: form.value.cardId || '',
      tags: form.value.tags
        .split(/[,，\s]+/)
        .map(s => s.trim())
        .filter(Boolean)
    }
    // 有 id 就带上，后端靠它区分「更新」还是「新建」
    if (form.value.id) body.id = form.value.id

    const r = await saveNote(body)
    form.value.id = r.note?.id || form.value.id
    dirty.value = false
    ElMessage.success('已保存')
    await fetchList()
  } finally {
    saving.value = false
  }
}

async function onRemove() {
  if (!form.value.id) {
    resetForm()
    return
  }
  try {
    await ElMessageBox.confirm('删除这篇笔记？删除后不能恢复。', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  await removeNote(form.value.id)
  ElMessage.success('已删除')
  resetForm()
  await fetchList()
}

function resetForm() {
  form.value = { id: '', title: '', body: '', tags: '', cardId: '' }
  dirty.value = false
}

/** 丢弃确认。统一用这一份 —— 新建和切换都走它。
 *  两个入口用两种确认框（一个 ElMessageBox 一个 window.confirm）
 *  会让同一个操作在不同位置长得不一样，用户会以为规则不同。 */
async function confirmDiscard() {
  try {
    await ElMessageBox.confirm('当前笔记还没保存，要丢弃吗？', '未保存的改动', {
      type: 'warning',
      confirmButtonText: '丢弃',
      cancelButtonText: '继续编辑'
    })
    return true
  } catch {
    return false
  }
}

function onInput() {
  dirty.value = true
}

/** 列表里的摘要：取正文头 60 字，换行压成空格。
 *  直接显示全文会让列表变成一堆长文段，扫不出重点。 */
function digest(n) {
  return (n.body || '').replace(/\s+/g, ' ').slice(0, 60) || '（空）'
}

/** 时间只显示到「月-日 时:分」。年份在笔记列表里毫无意义，
 *  但占了六个字符，还让每条都一样长，看不出早晚。 */
function fmt(t) {
  if (!t) return ''
  const s = String(t).replace('T', ' ').slice(5, 16)
  return s
}

const isNew = computed(() => !form.value.id)

onMounted(() => {
  try {
    const d = JSON.parse(localStorage.getItem('edu.noteDraft') || 'null')
    if (d && typeof d === 'object' && (d.title || d.body)) {
      form.value = { id: '', title: '', body: '', tags: '', cardId: '', ...d }
      dirty.value = true // 恢复出来的是没保存的稿子，「未保存」角标要亮着
    }
  } catch {
    /* 坏数据不恢复 */
  }
  fetchList()
})
</script>

<template>
  <div class="notes">
    <!-- ===== 列表 ===== -->
    <section class="panel list">
      <header class="panel-head">
        <h3>全部笔记</h3>
        <span class="hint">{{ notes.length }} 篇</span>
      </header>

      <el-input v-model="q" placeholder="搜标题 / 正文 / 标签" clearable size="large" />

      <div class="row-between" style="margin: 12px 0">
        <span class="chip accent">独立笔记</span>
        <button class="btn btn-primary" @click="newNote">
          <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
          新建
        </button>
      </div>

      <div v-loading="loading" class="items">
        <button
          v-for="n in notes"
          :key="n.id"
          class="row"
          :class="{ on: n.id === form.id }"
          @click="openNote(n)"
        >
          <div class="row-top">
            <span class="r-title">{{ n.title || '未命名' }}</span>
            <span class="r-time">{{ fmt(n.updatedAt || n.createdAt) }}</span>
          </div>
          <p class="r-digest">{{ digest(n) }}</p>
          <div class="row-tags">
            <span v-if="n.cardId" class="chip accent">挂在卡片</span>
            <span v-for="t in n.tags || []" :key="t" class="chip">{{ t }}</span>
          </div>
        </button>
        <p v-if="!loading && !notes.length" class="empty">
          <span class="big">还没有笔记</span>点右上角「新建」开始写
        </p>
      </div>
    </section>

    <!-- ===== 编辑器 ===== -->
    <section class="panel editor">
      <header class="panel-head">
        <h3>{{ isNew ? '新建笔记' : '编辑笔记' }}</h3>
        <span v-if="dirty" class="chip accent">未保存</span>
      </header>

      <label class="field">
        <span class="lb">标题</span>
        <el-input
          v-model="form.title"
          size="large"
          placeholder="这一篇在说什么"
          maxlength="60"
          show-word-limit
          @input="onInput"
        />
      </label>

      <label class="field">
        <span class="lb">正文</span>
        <el-input
          v-model="form.body"
          type="textarea"
          :rows="13"
          resize="none"
          placeholder="想清楚的地方、卡住的地方、跟别的东西连起来的地方"
          @input="onInput"
        />
      </label>

      <div class="two">
        <label class="field">
          <span class="lb">标签<em class="muted">逗号分隔</em></span>
          <el-input v-model="form.tags" placeholder="例如：并发, MySQL" @input="onInput" />
        </label>
        <label class="field">
          <span class="lb">关联卡片 ID<em class="muted">可选</em></span>
          <el-input v-model="form.cardId" placeholder="留空就是独立笔记" @input="onInput" />
        </label>
      </div>

      <footer class="row-between actions">
        <button v-if="!isNew" class="btn btn-danger" @click="onRemove">删除</button>
        <span v-else />
        <button class="btn btn-primary" :disabled="saving" @click="onSave">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.notes {
  display: grid;
  grid-template-columns: minmax(300px, 380px) 1fr;
  gap: 16px;
  align-items: start;
}
.list,
.editor {
  display: flex;
  flex-direction: column;
}

/* 列表区有滚动：笔记多了以后把整个页面撑长，
   右侧编辑器会跟着滚到屏幕外面去 */
.items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: calc(100vh - 320px);
  overflow-y: auto;
  margin: 0 -4px;
  padding: 0 4px;
}

.row {
  width: 100%;
  text-align: left;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: var(--panel2);
  cursor: pointer;
  transition:
    border-color 0.16s,
    background 0.16s;
}
.row:hover {
  border-color: var(--line2);
}
/* 选中态要有两个以上的视觉差异：这里同时换了边框和底色。
   只换一种的话，在内容密集的列表里很容易看不出选了谁 */
.row.on {
  border-color: var(--ac);
  background: var(--ac-glow);
}
.row-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.r-title {
  font-size: var(--fs-md);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.r-time {
  flex: none;
  font-size: var(--fs-xs);
  color: var(--dim);
}
.r-digest {
  margin: 4px 0 7px;
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.row-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
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
.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.actions {
  margin-top: 4px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

@media (max-width: 1080px) {
  .notes {
    grid-template-columns: 1fr;
  }
  .items {
    max-height: none;
  }
  .two {
    grid-template-columns: 1fr;
  }
}
</style>
