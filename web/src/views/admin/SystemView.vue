<script setup>
/* 运行状态 —— 回答两个别人不回答的问题：
 *
 *   1. **我现在写进去了哪里？**  store / want / degraded 三件套
 *   2. **我的数据哪里有权威？**  builtin.inFile vs inDb vs stale
 *
 * 为什么这两件事必须有页面：配置里写了 STORE=mysql，但 pymysql 没装或者 MySQL
 * 没起的时候，系统会**自动降级回 JSON 继续服务**。这是刻意的可用性设计，
 * 但如果不显示出来，用户会以为自己在用数据库，其实写进了文件。
 * 「悄悄降级」比「直接报错」坏得多。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { health, storage } from '@/api/system'
import { getLlmStatus } from '@/api/ai'

const info = ref(null)
const rt = ref(null)
/* AI 可用性的**唯一依据是 /api/llm/status**，不是 /api/health.llm。
 * health.llm = bool(LLM_API_KEY)，只反映「配没配云端 key」；
 * 本机跑 Ollama 时它是 false，但精读其实可用。详见 DashboardView 同处的注释。 */
const llm = ref(null)
const loading = ref(false)
const refreshedAt = ref('')

async function refresh() {
  loading.value = true
  try {
    // 两个接口都拿。health 是「服务活着吗」，storage 是「数据落在哪」，
    // 关心的事情不一样，合并成一个反而两边都说不清
    const [s, h] = await Promise.all([storage(), health()])
    info.value = s.storage
    rt.value = h
    try {
      llm.value = await getLlmStatus()
    } catch {
      // ok:false 是正常状态（可选能力没开），不是故障
      llm.value = null
    }
    refreshedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    ElMessage.error('读取运行状态失败')
  } finally {
    loading.value = false
  }
}

onMounted(refresh)

/** 是否在降级。这是这一页最重要的一个布尔值。 */
const degraded = computed(() => Boolean(info.value?.degraded))

/** 期望后端与实际后端是否一致。不一致就是降级。 */
const mismatch = computed(() => {
  const s = info.value
  return s ? s.want !== s.store : false
})

/** 内容是否过期。**stale 为真时接口会回落读 data/*.js** ——
 *  因为文件才是权威源，MySQL 里的 cards 表只是查询副本。 */
const stale = computed(() => Boolean(info.value?.builtin?.stale))

const storeLabel = computed(() => (info.value?.store === 'mysql' ? 'MySQL' : 'JSON 文件'))

/** 体积列表。只列大于 0 的 ——
 *  空文件显示 0 B 会让人以为「没写进去」，其实是「还没有数据」。 */
const sizeRows = computed(() => {
  const b = info.value?.bytes || {}
  return Object.entries(b)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => [k, fmtBytes(v)])
})

function fmtBytes(n) {
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
}

async function copyCommand(cmd) {
  try {
    await navigator.clipboard.writeText(cmd)
    ElMessage.success('命令已复制')
  } catch {
    // 非 HTTPS 环境下 clipboard API 可能不可用，退化成提示用户手抄
    ElMessage.info('请手动复制：' + cmd)
  }
}
</script>

<template>
  <div class="stack" v-loading="loading">
    <!-- ===== 降级告警 ===== -->
    <section v-if="degraded" class="panel alert">
      <div class="alert-head">
        <svg viewBox="0 0 24 24">
          <path d="M12 8v5M12 16.5v.01" />
          <circle cx="12" cy="12" r="9" />
        </svg>
        <h3>正在降级运行</h3>
      </div>
      <p class="alert-body">
        配置要求使用 <strong>{{ info.want }}</strong
        >，实际使用的是 <strong>{{ storeLabel }}</strong
        >。系统继续照常服务，但<strong>数据没有写进数据库</strong>。
      </p>
      <p class="alert-reason">原因：{{ info.degraded }}</p>
    </section>

    <!-- ===== 内容过期告警 ===== -->
    <section v-if="stale" class="panel alert warn">
      <div class="alert-head">
        <svg viewBox="0 0 24 24">
          <path d="M12 8v5M12 16.5v.01" />
          <circle cx="12" cy="12" r="9" />
        </svg>
        <h3>库里的卡片内容与源文件不一致</h3>
      </div>
      <p class="alert-body">
        <code>data/*.js</code> 是内容的权威源，MySQL 的 cards 表只是查询副本。
        改了源文件之后要同步一次，现在接口已经<strong>回落为读文件</strong>（不会端出旧内容）。
      </p>
      <button
        class="btn btn-ghost"
        @click="copyCommand('python back_study/scripts/dbseed.py --sync')"
      >
        复制同步命令
      </button>
    </section>

    <!-- ===== 存储后端 ===== -->
    <section class="panel">
      <header class="panel-head">
        <h3>存储后端</h3>
        <div class="row-between">
          <span class="hint">刷新于 {{ refreshedAt }}</span>
          <button class="btn btn-ghost" @click="refresh">刷新</button>
        </div>
      </header>

      <dl class="kv">
        <dt>实际后端</dt>
        <dd>
          <span class="chip" :class="{ accent: !degraded }">{{ storeLabel }}</span>
        </dd>

        <dt>配置要求</dt>
        <dd>
          <span class="chip">{{ info?.want || '-' }}</span>
          <span v-if="mismatch" class="chip warn-chip">与配置不一致</span>
        </dd>

        <template v-if="info?.host">
          <dt>连接地址</dt>
          <dd class="mono">{{ info.host }}:{{ info.port }} / {{ info.db }}</dd>
        </template>

        <template v-if="info?.dir">
          <dt>数据目录</dt>
          <dd class="mono">{{ info.dir }}</dd>
        </template>

        <dt>用户数</dt>
        <dd class="mono">{{ info?.users ?? '-' }}</dd>
      </dl>
    </section>

    <!-- ===== 内容一致性 ===== -->
    <section class="panel">
      <header class="panel-head">
        <h3>内容一致性</h3>
        <span class="hint">源文件为准，库是副本</span>
      </header>
      <dl class="kv">
        <dt>库内卡片</dt>
        <dd class="mono">{{ info?.builtin?.inDb ?? '未同步' }}</dd>
        <dt>源文件卡片</dt>
        <dd class="mono">{{ info?.builtin?.inFile ?? '-' }}</dd>
        <dt>内容指纹</dt>
        <dd class="mono">
          <!-- ★ 指纹在 info 的**顶层**（mysql 后端写的是 builtinDigest），
               不在 info.builtin 里 —— 从前读 builtin.digest 永远拿到空，
               这一行恒显示「-」，看着像「没有指纹」，其实是读错了字段。 -->
          {{ info?.builtinDigest || '-' }}
          <span v-if="!stale" class="chip accent">一致</span>
          <span v-else class="chip warn-chip">不一致</span>
        </dd>
        <dt>权威源</dt>
        <dd class="mono">{{ info?.builtin?.authority || '-' }}</dd>
      </dl>
      <div class="row-between cmds">
        <button
          class="btn btn-ghost"
          @click="copyCommand('python back_study/scripts/dbseed.py --status')"
        >
          复制「查看状态」命令
        </button>
        <button
          class="btn btn-ghost"
          @click="copyCommand('python back_study/scripts/dbseed.py --sync')"
        >
          复制「同步源数据」命令
        </button>
      </div>
    </section>

    <!-- ===== 运行时 ===== -->
    <section class="panel">
      <header class="panel-head">
        <h3>运行时</h3>
      </header>
      <dl class="kv">
        <dt>后端实现</dt>
        <dd>
          <span class="chip accent">{{ rt?.framework || '-' }}</span>
        </dd>
        <dt>语言 / 框架</dt>
        <!-- /api/health 不返回 version 字段，从前这里读 rt.version 恒为空，
             只剩一个孤零零的「python 」。要么后端补字段、要么去掉 ——
             这里选去掉，版本号对排查没有实际帮助。 -->
        <dd class="mono">{{ rt?.lang || '-' }} / {{ rt?.framework || '-' }}</dd>
        <dt>卡片总数</dt>
        <dd class="mono">{{ rt?.cards ?? '-' }}</dd>
        <dt>服务端今天</dt>
        <dd class="mono">{{ rt?.today || '-' }}</dd>
        <dt>AI 精读</dt>
        <dd>
          <!-- ok:false **不是故障**，是可选能力没启用。用中性色而不是红色 -->
          <span class="chip">{{ llm?.ok ? '可用' : '未启用' }}</span>
          <span v-if="llm?.ok" class="hint-inline mono">{{ llm.provider }} · {{ llm.model }}</span>
          <span class="hint-inline">关掉它，背卡 / 复习 / 分章照常工作</span>
        </dd>
      </dl>
    </section>

    <!-- ===== 数据体积 ===== -->
    <section v-if="sizeRows.length" class="panel">
      <header class="panel-head">
        <h3>数据体积</h3>
        <span class="hint">只列非空文件</span>
      </header>
      <dl class="kv">
        <template v-for="[k, v] in sizeRows" :key="k">
          <dt class="mono">{{ k }}</dt>
          <dd class="mono">{{ v }}</dd>
        </template>
      </dl>
    </section>
  </div>
</template>

<style scoped>
.alert {
  border-color: var(--red);
  background: rgba(168, 57, 42, 0.07);
}
.alert.warn {
  border-color: var(--amber);
  background: rgba(138, 98, 24, 0.07);
}
.alert-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.alert-head svg {
  width: 19px;
  height: 19px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}
.alert h3 {
  font-size: var(--fs-md);
  font-weight: 700;
}
.alert-body {
  font-size: var(--fs-sm);
  color: var(--mu);
  line-height: 1.75;
}
.alert-reason {
  margin-top: 8px;
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
  color: var(--tx);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: rgba(58, 47, 33, 0.055);
  word-break: break-all;
}
.alert .btn {
  margin-top: 12px;
}

.warn-chip {
  color: var(--amber);
  border-color: var(--amber);
  background: rgba(138, 98, 24, 0.11);
}
.hint-inline {
  margin-left: 8px;
  font-size: var(--fs-xs);
  color: var(--dim);
}
.cmds {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
code {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--panel2);
}
</style>
