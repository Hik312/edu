<script setup>
/* 卡片列表项 —— 卷宗里的一页。
 *
 * 设计上的四个决定：
 *
 * 1. **左侧一条靛蓝细线**，像纸的装订边。整块卡片没有别的装饰，
 *    靠这一道竖线把"这是一张卡"的印象立住。
 * 2. **标题用宋体**（--font-title）。衬线体在小字号下笔画会糊，
 *    所以宋体只用在标题这一档，正文仍然是雅黑。
 * 3. **掌握度用右侧一个小色点**，不用彩色标签块。列表里几十张卡，
 *    每张都挂一个彩块会把页面变成信号灯。
 * 4. **底部挂真实 id 当档号**，不编流水号 —— 编号必须能跟数据对上，
 *    只是为了好看而编的号，一旦有人拿去搜索就露馅。
 */
import { computed } from 'vue'
import { levelColor, levelLabel } from '@/config/theme'

const props = defineProps({
  card: { type: Object, required: true }
})

defineEmits(['open'])

// 文案与颜色都来自 theme，别在这里再立一套（从前是从 api/learning 的
// LEVELS 拿，那份颜色是上一版深色的荧光色，跟路径页/图谱对不上）
const levelText = computed(() => levelLabel(props.card.level ?? 0))
const levelTint = computed(() => levelColor(props.card.level ?? 0))
const tags = computed(() => (props.card.tags || []).slice(0, 3))
</script>

<template>
  <article
    class="ci"
    tabindex="0"
    @click="$emit('open', card)"
    @keydown.enter="$emit('open', card)"
  >
    <span class="edge" />
    <header class="ci-head">
      <h3 class="ci-title">{{ card.title }}</h3>
      <span class="ci-level" :style="{ color: levelTint }" :title="levelText">
        <i class="dot" />
        {{ levelText }}
      </span>
    </header>

    <p class="ci-one">{{ card.oneLine }}</p>

    <footer class="ci-foot">
      <span class="ci-dno dno">{{ card.id }}</span>
      <span v-if="card.domain" class="ci-domain">{{ card.domain }}</span>
      <!-- 卡片组（来自哪份文档的文件夹）：超长截断，鼠标悬停看全名 -->
      <span v-if="card.deck" class="ci-deck" :title="`来自《${card.deck}》`">
        《{{ card.deck }}》
      </span>
      <span v-for="t in tags" :key="t" class="ci-tag">#{{ t }}</span>
      <span class="ci-arrow">
        <svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
      </span>
    </footer>
  </article>
</template>

<style scoped>
.ci {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 15px 17px 13px 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
  cursor: pointer;
  transition:
    transform 0.18s cubic-bezier(0.22, 0.7, 0.28, 1),
    box-shadow 0.18s,
    border-color 0.18s;
}

/* 装订边：一条朱砂竖线。做成渐隐的，像笔划收尾 */
.edge {
  position: absolute;
  left: 0;
  top: 13px;
  bottom: 13px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: linear-gradient(180deg, var(--ac), transparent);
  opacity: 0.5;
  transition: opacity 0.2s;
}

.ci:hover {
  transform: translateY(-2px);
  border-color: var(--line2);
  box-shadow: 0 14px 30px -18px rgba(80, 60, 30, 0.7);
}
.ci:hover .edge {
  opacity: 1;
}
.ci:focus-visible {
  outline: none;
  box-shadow: var(--ring);
}

.ci-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.ci-title {
  flex: 1;
  font-family: var(--font-title);
  font-size: var(--fs-lg);
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 0.3px;
  color: var(--tx);
}

.ci-level {
  flex: none;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-xs);
}
.ci-level .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.ci-one {
  font-size: 14px;
  line-height: 1.75;
  color: var(--mu);
  /* 两行截断：列表要的是等高的格子，长短不一会让网格参差不齐 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ci-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 4px;
  border-top: 1px dashed var(--line);
  font-size: var(--fs-xs);
}
.ci-dno {
  color: var(--dim);
  opacity: 0.9;
}
.ci-domain {
  color: var(--dim);
}
.ci-deck {
  color: var(--ac);
  opacity: 0.75;
  max-width: 46%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ci-tag {
  color: var(--ac);
  opacity: 0.85;
}
.ci-arrow {
  margin-left: auto;
  color: var(--dim);
  opacity: 0;
  transition:
    opacity 0.18s,
    transform 0.18s;
}
.ci:hover .ci-arrow {
  opacity: 1;
  transform: translateX(2px);
}
.ci-arrow svg {
  width: 14px;
  height: 14px;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
