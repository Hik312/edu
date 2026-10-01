<script setup>
/* 内容解析报告 —— 出卡前的确认关卡。从 DocsView 拆出来（那边 max-lines
 * 700 到顶了）。
 *
 * 两种形态：
 *   未解析 → 一个「AI 解析内容」按钮（导入后会自动跑到这一步）
 *   已解析 → 逐章勾选 + 「按保留的 N 章出卡」按钮（终点，出卡由人点）
 *
 * 组件只管展示与交互形态：解析/勾选/出卡的动作 emit 出去，由 DocsView
 * 转给 docAgent 发请求 —— 数据的所有权不在这里（opened 是共享状态）。
 */
import { computed } from 'vue'

const props = defineProps({
  opened: { type: Object, required: true },
  parsing: Boolean,
  agent: { type: Object, required: true },
  agentLabel: { type: String, default: '' },
  busyAuto: Boolean // 「全部转卡」旧链路在跑（和出卡互斥）
})
const emit = defineEmits(['run-parse', 'toggle-keep', 'toggle-agent'])

const chapters = computed(() => props.opened?.chapters || [])
const parse = computed(() => props.opened?.parse || null)
const hasParse = computed(() => Boolean(parse.value))
const keepCount = computed(() => (parse.value?.chapters || []).filter(r => r.keep).length)
</script>

<template>
  <div class="parse-box">
    <div v-if="!hasParse" class="parse-empty">
      <span class="hint">
        先让 AI 读一遍内容：剔掉目录、封面、参考文献这类没用的章，出卡前给你过目
      </span>
      <button
        class="btn btn-primary"
        :disabled="parsing || busyAuto || agent.on"
        @click="emit('run-parse')"
      >
        {{ parsing ? '解析中…' : 'AI 解析内容' }}
      </button>
    </div>

    <template v-else>
      <div class="parse-head">
        <span class="parse-sum">
          内容解析报告 · 保留 <b>{{ keepCount }}</b> / {{ chapters.length }} 章
          <template v-if="chapters.length - keepCount">
            · 剔除 {{ chapters.length - keepCount }}</template
          >
        </span>
        <span class="hint">{{ parse.at }}</span>
        <button
          class="btn btn-ghost"
          :disabled="parsing || busyAuto || agent.on"
          title="重新精修分章并重新判定（会覆盖手动勾选）"
          @click="emit('run-parse')"
        >
          {{ parsing ? '解析中…' : '重新解析' }}
        </button>
      </div>

      <p v-if="parse.modelOk === false" class="parse-warn">
        AI 判定未运行（{{ parse.msg || '模型不可用' }}），以下为规则初筛结果，可手动勾选
      </p>

      <ul class="parse-list">
        <li
          v-for="row in parse.chapters"
          :key="row.index"
          class="parse-row"
          :class="{ off: !row.keep }"
        >
          <input
            type="checkbox"
            class="parse-ck"
            :checked="row.keep"
            :disabled="parsing || agent.on"
            @change="emit('toggle-keep', row.index, $event.target.checked)"
          />
          <span class="c-idx mono">{{ String(row.index + 1).padStart(2, '0') }}</span>
          <span class="parse-title">{{ chapters[row.index]?.title || '（无标题）' }}</span>
          <span
            class="parse-badge"
            :class="row.by || 'def'"
            :title="
              row.by === 'user'
                ? '你手动调过'
                : row.by === 'ai'
                  ? 'AI 判定'
                  : row.by === 'rule'
                    ? '规则初筛'
                    : '默认保留'
            "
            >{{ row.keep ? '保留' : '剔除' }}</span
          >
          <span v-if="row.reason" class="parse-why">{{ row.reason }}</span>
        </li>
      </ul>

      <div class="parse-foot">
        <button
          class="btn btn-primary"
          :disabled="!keepCount || agent.on || parsing || busyAuto"
          @click="emit('toggle-agent')"
        >
          {{ agent.on ? agentLabel : `按保留的 ${keepCount} 章出卡` }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.parse-box {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  margin-bottom: 16px;
}
.parse-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.hint {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.parse-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.parse-sum {
  font-size: var(--fs-sm);
}
.parse-warn {
  font-size: var(--fs-xs);
  color: var(--dim);
  margin: 4px 0;
}
.parse-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 280px;
  overflow-y: auto;
}
.parse-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 2px;
  font-size: var(--fs-sm);
  border-top: 1px dashed var(--line2);
}
.parse-row.off .parse-title {
  text-decoration: line-through;
  color: var(--dim);
}
.parse-ck {
  accent-color: var(--ac);
  cursor: pointer;
  flex: none;
}
.c-idx {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.parse-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.parse-badge {
  font-size: var(--fs-xs);
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--ac-glow);
  color: var(--ac);
  flex: none;
}
.parse-row.off .parse-badge {
  background: var(--line2);
  color: var(--dim);
}
.parse-why {
  font-size: var(--fs-xs);
  color: var(--mu);
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: none;
}
.parse-foot {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>
