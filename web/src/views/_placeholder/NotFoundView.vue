<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="wrap">
    <div class="code">404</div>
    <p class="msg">这个地址没有对应页面。</p>
    <el-button size="small" @click="router.replace('/dashboard')">回到概览</el-button>
  </div>
</template>

<style scoped>
.wrap {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.code {
  font-size: 42px;
  font-weight: 500;
  color: var(--line);
  letter-spacing: 4px;
}
.msg {
  font-size: 14px;
  color: var(--mu);
}
</style>
