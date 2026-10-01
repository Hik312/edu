<script setup>
/* 三档掌握度选择器。
 *
 * 复习页和卡片详情共用同一份 —— 各写一遍的话，「哪个颜色是哪个档」
 * 迟早会写反（1 是不会、3 是会，很容易记成一不会二三会）。
 * 颜色的唯一真相在 `api/learning.js` 的 LEVELS，这里只负责渲染。
 *
 * 只给 1 / 2 / 3 三档。**0（未标记）不是一个选项，它是「还没选」** ——
 * 把它做成按钮的话，用户会以为那是第四种掌握程度。
 */
import { computed } from 'vue'
import { LEVELS } from '@/api/learning'

// 不用接变量名：这几个 prop 只在模板里用（modelValue / loading / compact），
// script 里没有任何一处需要读它。写成 const props = 会被 lint 判为未使用。
defineProps({
  /** 当前档位，0 表示未标记 */
  modelValue: { type: Number, default: 0 },
  /** 请求中：锁住按钮，避免连点把进度写乱 */
  loading: { type: Boolean, default: false },
  compact: { type: Boolean, default: false }
})

const emit = defineEmits(['pick'])

const options = computed(() =>
  [1, 2, 3].map(v => ({ value: v, label: LEVELS[v].label, color: LEVELS[v].color }))
)

/** 快捷键提示写在这里，键盘处理交给父组件的 window 监听 ——
 *  按钮自己不监听键盘，否则一页里多个选择器会互相抢按键。 */
const HINT = { 1: '1', 2: '2', 3: '3' }
</script>

<template>
  <div class="picker" :class="{ compact }">
    <button
      v-for="o in options"
      :key="o.value"
      class="opt"
      :class="{ on: modelValue === o.value }"
      :disabled="loading"
      :style="modelValue === o.value ? { '--c': o.color } : null"
      @click="emit('pick', o.value)"
    >
      <span class="dot" />
      <span class="label">{{ o.label }}</span>
      <!-- 键盘提示只在非触屏的宽屏显示，手机上是干扰 -->
      <kbd>{{ HINT[o.value] }}</kbd>
    </button>
  </div>
</template>

<style scoped>
.picker {
  display: flex;
  gap: 8px;
}

.opt {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 15px;
  border: 1px solid var(--line2);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--mu);
  font-size: 14.5px;
  cursor: pointer;
  transition:
    transform 0.14s,
    border-color 0.18s,
    color 0.18s,
    background 0.18s;
}

.opt:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--c, var(--ac));
  color: var(--tx);
}

.opt:disabled {
  opacity: 0.55;
  cursor: progress;
}

/* 选中态：边框和文字都取那一档的颜色，底色是它的 12% 透明版本 */
.opt.on {
  border-color: var(--c);
  color: var(--c);
  background: color-mix(in srgb, var(--c) 12%, transparent);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.55;
  flex: none;
}
.opt.on .dot {
  opacity: 1;
  box-shadow: 0 0 8px currentColor;
}

kbd {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 0 4px;
  border-radius: 3px;
  border: 1px solid var(--line2);
  color: var(--dim);
  opacity: 0.8;
}

.compact .opt {
  padding: 5px 10px;
  font-size: 13.5px;
}
.compact kbd {
  display: none;
}

/* 触屏或窄屏就去掉键盘提示：那里没有物理键盘 */
@media (max-width: 860px), (hover: none) {
  kbd {
    display: none;
  }
}
</style>
