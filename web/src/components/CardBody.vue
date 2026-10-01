<script setup>
/* 卡片正文 —— 复习页和详情抽屉共用。
 *
 * 两个地方用的是同一份内容，**顺序必须是同一个**：复习时记下的顺序
 * 和回看时的顺序不一致，等于每次都要重新找位置。
 *
 * 顺序按「从好懂到难懂」排，不是按字段在 JSON 里的顺序：
 *   一句话 → 类比（生活话）→ 为什么重要 → 原理（分步）→ 过程演示
 *   → 面试怎么答 → 真实场景 → 关键词 → 关联卡
 *
 * 每个小节都可能缺（不是每张卡都写全了），所以逐个 v-if，
 * 而不是拼一个大字符串 —— 缺字段时不会留下空标题。
 */
import { computed } from 'vue'
import DiagramView from './DiagramView.vue'
import { relationOf } from '@/api/cards'

const props = defineProps({
  card: { type: Object, required: true }
})

const emit = defineEmits(['open-related'])

const mechanism = computed(() => props.card.mechanism || [])
const interviewQ = computed(() => props.card.interviewQ || [])
const scene = computed(() => props.card.scene || [])
const keywords = computed(() => props.card.keywords || [])
const related = computed(() => props.card.related || [])
</script>

<template>
  <div class="body">
    <p v-if="card.oneLine" class="one">{{ card.oneLine }}</p>

    <!-- 类比放在最前：它是全篇最好懂的一段，先建立直觉再看原理 -->
    <section v-if="card.analogy" class="analogy">
      <span class="mark">打比方</span>
      <p>{{ card.analogy }}</p>
    </section>

    <section v-if="card.why" class="sec">
      <h4>为什么重要</h4>
      <p>{{ card.why }}</p>
    </section>

    <section v-if="mechanism.length" class="sec">
      <h4>原理拆解</h4>
      <ol class="steps">
        <li v-for="(m, i) in mechanism" :key="i">
          <span class="idx">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="step-txt">{{ m }}</span>
        </li>
      </ol>
    </section>

    <section v-if="card.diagram" class="sec">
      <h4>过程演示</h4>
      <DiagramView :spec="card.diagram" />
    </section>

    <section v-if="interviewQ.length" class="sec">
      <h4>面试怎么答</h4>
      <ul class="qlist">
        <li v-for="(q, i) in interviewQ" :key="i">{{ q }}</li>
      </ul>
    </section>

    <section v-if="scene.length" class="sec">
      <h4>真实场景</h4>
      <ul class="scenes">
        <li v-for="(s, i) in scene" :key="i">{{ s }}</li>
      </ul>
    </section>

    <section v-if="keywords.length" class="sec">
      <h4>关键词</h4>
      <div class="chips">
        <span v-for="k in keywords" :key="k" class="chip">{{ k }}</span>
      </div>
    </section>

    <section v-if="related.length" class="sec">
      <h4>关联卡</h4>
      <div class="rel">
        <button
          v-for="r in related"
          :key="r.id"
          class="rel-item"
          @click="emit('open-related', r.id)"
        >
          <span class="rel-kind" :class="r.kind">{{ relationOf(r.kind).label }}</span>
          <span class="rel-mid">
            <span class="rel-id mono">{{ r.id }}</span>
            <span v-if="r.note" class="rel-note">{{ r.note }}</span>
          </span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.one {
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--tx);
}

/* 类比块：朱砂竖线 + 极淡底。像从别处摘来的一张便签 */
.analogy {
  display: flex;
  gap: 12px;
  padding: 12px 15px;
  border-left: 3px solid var(--ac);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--ac-glow);
}
.mark {
  flex: none;
  font-family: var(--font-title);
  font-size: 13.5px;
  color: var(--ac);
  letter-spacing: 1px;
  padding-top: 2px;
}
.analogy p {
  font-size: 14.5px;
  line-height: 1.85;
  color: var(--tx);
}

.sec h4 {
  font-family: var(--font-title);
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--tx);
  margin-bottom: 9px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line);
}
.sec p {
  font-size: 14.5px;
  line-height: 1.9;
  color: var(--mu);
}

.steps {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.steps li {
  display: flex;
  gap: 12px;
}
/* 编号用楷体数字，像手写的序号 */
.idx {
  flex: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--ac);
  padding-top: 3px;
  letter-spacing: 0.5px;
}
.step-txt {
  font-size: 14.5px;
  line-height: 1.85;
  color: var(--tx);
}

.qlist,
.scenes {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.qlist li,
.scenes li {
  font-size: 14.5px;
  line-height: 1.85;
  color: var(--mu);
  padding-left: 15px;
  position: relative;
}
.qlist li::before {
  content: 'Q';
  position: absolute;
  left: 0;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--ac);
  top: 4px;
}
.scenes li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 10px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  border: 1px solid var(--line2);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.chip {
  font-size: 13px;
  padding: 3px 10px;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--mu);
}

.rel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rel-item {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.16s,
    transform 0.16s;
}
.rel-item:hover {
  border-color: var(--ac-dim);
  transform: translateX(3px);
}
.rel-kind {
  flex: none;
  font-size: var(--fs-xs);
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid currentColor;
  line-height: 1.6;
}
/* 三种关系的颜色：前置=琥珀（拦住你的）、延伸=绿（往下走的）、对比=蓝（并列的） */
.rel-kind.prereq {
  color: var(--amber);
}
.rel-kind.extends {
  color: var(--ac);
}
.rel-kind.compare {
  color: var(--blue);
}
.rel-mid {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.rel-id {
  font-size: var(--fs-xs);
  color: var(--dim);
}
.rel-note {
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--mu);
}

.mono {
  font-family: var(--font-mono);
}
</style>
