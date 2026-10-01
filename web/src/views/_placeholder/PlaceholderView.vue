<script setup>
/* 还没搬过来的页面统一用这个占位。
 *
 * 为什么不做成「空白页」或直接 404：侧栏能点、点进来能看见「这页要做什么」，
 * 才知道进度到哪了。空白页看起来像坏了。
 */
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="ph">
    <div class="tag">待搬迁</div>
    <h2>{{ route.meta.title }}</h2>
    <p v-if="route.meta.note" class="note">{{ route.meta.note }}</p>
    <p class="hint">
      这页还没迁完。搬完后把 <span class="mono">router/index.js</span> 里那条路由的
      <span class="mono">ready</span> 改成 <span class="mono">true</span>，侧栏的标记会自己消失。
    </p>
  </div>
</template>

<style scoped>
.ph {
  max-width: 620px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 28px 26px;
}
.tag {
  display: inline-block;
  font-size: var(--fs-xs);
  color: var(--amber);
  border: 1px solid var(--line2);
  border-radius: 4px;
  padding: 3px 8px;
  margin-bottom: 14px;
}
h2 {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 10px;
}
.note {
  font-size: 14px;
  color: var(--mu);
  margin-bottom: 12px;
}
.hint {
  font-size: 13.5px;
  color: var(--dim);
  line-height: 1.8;
}

.mono {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--mu);
}
</style>
