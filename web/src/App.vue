<script setup>
// 全局配置：中文 locale（Element Plus 默认是英文，分页/表格会显示 "Total"）
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>

<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>
