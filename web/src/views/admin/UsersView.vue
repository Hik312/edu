<script setup>
/* 用户管理 —— 这一页面现在只做一件事：**看名单**。
 *
 * 登录方式目前只有一种：用户名 + 密码，换 HS256 的 JWT。
 * `user` 表里留了 openid 列（将来接微信登录时写到同一行即可，不用改表），
 * 但**小程序端已于 2026-09-26 整端移除**，所以这一列现在必然全空 ——
 * 页面上不再显示「来源」列，因为答案永远是「网页」。
 *
 * ## 为什么这一代不做增删改
 *
 * 后端目前只有 `GET /auth/users`（管理员可见），没有写接口。
 * 这不是取舍，是**刻意先不加**：在此之前需要先回答「删掉一个用户时，
 * 他的 progress / notes / attempts 怎么办」，而这个问题要等 per-user 数据
 * 隔离做完才有意义。列在这儿是为了不让它被忘掉。
 */
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listUsers } from '@/api/auth'

const auth = useAuthStore()
const users = ref([])
const loading = ref(false)
const q = ref('')

/** 普通成员进来时，后端会直接 403。页面这一层也挡一下，
 *  但**页面挡不等于后端挡** —— 真正的权限判断必须在服务端，
 *  这里只是省掉一次必然失败的请求和一个红报错。 */
const forbidden = computed(() => auth.user?.role !== 'admin')

onMounted(async () => {
  if (forbidden.value) return
  loading.value = true
  try {
    users.value = (await listUsers()).users || []
  } catch {
    users.value = []
  } finally {
    loading.value = false
  }
})

const rows = computed(() => {
  const k = q.value.trim().toLowerCase()
  if (!k) return users.value
  return users.value.filter(
    u =>
      String(u.username || '')
        .toLowerCase()
        .includes(k) ||
      String(u.displayName || '')
        .toLowerCase()
        .includes(k)
  )
})
</script>

<template>
  <div class="stack">
    <section v-if="forbidden" class="panel">
      <p class="empty">
        <span class="big">没有权限</span>
        这个页面只对管理员开放。第一个注册的账号会自动成为管理员。
      </p>
    </section>

    <template v-else>
      <section class="panel">
        <header class="panel-head">
          <h3>
            用户 <span class="count">{{ users.length }} 个</span>
          </h3>
          <el-input v-model="q" placeholder="搜用户名 / 昵称" clearable style="max-width: 240px" />
        </header>

        <div class="table-wrap" v-loading="loading">
          <table class="tb">
            <thead>
              <tr>
                <th style="width: 56px">ID</th>
                <th>用户名</th>
                <th>昵称</th>
                <th style="width: 96px">角色</th>
                <th style="width: 150px">注册时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in rows" :key="u.id">
                <td class="mono dim">{{ u.id }}</td>
                <td class="strong">{{ u.username }}</td>
                <td>{{ u.displayName || '—' }}</td>
                <td>
                  <span class="chip" :class="{ accent: u.role === 'admin' }">
                    {{ u.role === 'admin' ? '管理员' : '学习者' }}
                  </span>
                </td>
                <td class="dim">{{ u.createdAt || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!loading && !rows.length" class="empty">
            <span class="big">没有匹配的用户</span>
            换个关键词试试
          </p>
        </div>
      </section>

      <section class="panel">
        <header class="panel-head">
          <h3>关于账号</h3>
        </header>
        <dl class="kv">
          <dt>登录方式</dt>
          <dd>用户名 + 密码换 HS256 的 JWT（pbkdf2 存口令），7 天有效期</dd>
          <dt>管理员从哪来</dt>
          <dd>第一个注册的账号自动成为管理员，之后注册的默认是学习者</dd>
          <dt>已预留但未启用</dt>
          <dd>
            <code>user.openid</code> 列已在表结构里，将来接微信登录时写到同一行即可 ——
            小程序端已移除，这一列现在全空
          </dd>
          <dt>这一版没做的事</dt>
          <dd>
            用户的增删改要到 per-user 数据隔离完成后才加 —— 先回答「删用户时他的学习记录怎么办」
          </dd>
        </dl>
      </section>
    </template>
  </div>
</template>

<style scoped>
.count {
  font-size: var(--fs-xs);
  font-weight: 400;
  color: var(--dim);
}

.table-wrap {
  overflow-x: auto;
}
.tb {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}
.tb th {
  text-align: left;
  padding: 9px 12px;
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--mu);
  border-bottom: 1px solid var(--line2);
  white-space: nowrap;
}
.tb td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--line);
  vertical-align: middle;
}
.tb tbody tr:hover {
  background: var(--panel2);
}
.tb tbody tr:last-child td {
  border-bottom: 0;
}
.strong {
  font-weight: 600;
}
</style>
