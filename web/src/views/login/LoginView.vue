<script setup>
/* 登录 / 注册 —— 卷宗的封面。
 *
 * 这是整个产品给人的**第一眼**，所以它比任何业务页都更该把「这是一份
 * 卷宗」说清楚：纸底、宋体书名、朱砂印、手写线式的输入框。
 * 左栏是书名页（品牌 + 三条能力），右栏是那页你要签的字（表单）。
 *
 * 同一个表单两种模式，注册成功后直接登录 —— 少一步操作。
 * 注册完还要再登一次，是真的会掉一批人。
 *
 * 输入框是自绘的，没用 el-input。原因是纸底下要让输入框长得像
 * 「纸上的一条横线」，覆盖 Element Plus 的内阴影 + 边框 + hover 态
 * 要写二十几行 CSS，还不如自己写十行。校验逻辑照旧。
 */
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const submitting = ref(false)
const form = reactive({ username: '', password: '', password2: '', displayName: '' })

const isRegister = computed(() => mode.value === 'register')

/** 左侧三条卖点。写具体的能力，不写「智能」「高效」这种谁都能说的词。 */
const POINTS = [
  { k: '原理', t: '每张卡拆到机制层', d: '类比 → 为什么 → 分步原理，不是知识点罗列' },
  { k: '调度', t: 'SM-2 排期 + 掌握度', d: '模糊和不会的卡自己会提前回来找你' },
  { k: '图谱', t: '前置关系连成网', d: '看不懂这张，顺着线往回走就行' }
]

function switchMode(m) {
  mode.value = m
  form.password = ''
  form.password2 = ''
}

async function submit() {
  const username = form.username.trim()
  if (!username) return ElMessage.warning('请填用户名')
  if (!form.password) return ElMessage.warning('请填密码')

  if (isRegister.value) {
    if (!/^[A-Za-z0-9_]{3,20}$/.test(username)) {
      return ElMessage.warning('用户名只能是 3-20 位字母、数字或下划线')
    }
    if (form.password.length < 6) return ElMessage.warning('密码至少 6 位')
    if (form.password !== form.password2) return ElMessage.warning('两次输入的密码不一致')
  }

  submitting.value = true
  try {
    if (isRegister.value) {
      await auth.register({
        username,
        password: form.password,
        displayName: form.displayName.trim()
      })
      ElMessage.success('注册成功')
    }
    await auth.login(username, form.password)

    // 只接受站内相对路径，避免 ?redirect=https://... 被拿去做跳转钓鱼
    const back = route.query.redirect
    const target =
      typeof back === 'string' && back.startsWith('/') && !back.startsWith('//')
        ? back
        : '/dashboard'
    router.replace(target)
  } catch (e) {
    // 这里**必须**自己弹：api/client.js 的拦截器只 reject、不弹提示
    // （它只在 401 时弹「登录已过期」）。登录失败是 400，错误对象 e.message
    // 已带后端 msg（如「用户名或密码不对」）。从前这里写空 catch + 一句
    // 「由拦截器统一弹」的注释 —— 实际拦截器根本不弹，登录失败就静默了。
    ElMessage.error((e && e.message) || '登录失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <!-- 全站一套牛皮纸配色，变量都在 :root 上，这里不用声明任何主题属性。
       .lg 只管铺满纸底，.lg-inner 是那两栏。两栏铺满整屏、各自把内容居中 ——
       **不要给 .lg-inner 加 max-width**，那会让宽屏上两侧空出大片纸（详见样式区注释）。 -->
  <div class="lg">
    <div class="lg-inner">
      <!-- ===== 左：品牌 ===== -->
      <section class="brand">
        <div class="brand-inner">
          <div class="mark">
            <svg viewBox="0 0 32 32" aria-hidden="true">
              <path d="M6 25 13.5 15l5 4.2L26 7" />
              <circle cx="26" cy="7" r="3.1" />
            </svg>
          </div>

          <h1 class="name">
            智径
            <span>EduPath</span>
          </h1>
          <span class="stamp brand-stamp">自适应学习</span>
          <p class="slogan">多 Agent 自适应学习平台<br />把「我该学什么」交给它，你只管看懂</p>

          <ul class="points">
            <li v-for="p in POINTS" :key="p.k">
              <span class="pk">{{ p.k }}</span>
              <span class="pt">{{ p.t }}</span>
              <span class="pd">{{ p.d }}</span>
            </li>
          </ul>
        </div>
      </section>

      <!-- ===== 右：表单纸 ===== -->
      <section class="pane">
        <div class="sheet rise">
          <div class="tabs">
            <button :class="{ on: !isRegister }" @click="switchMode('login')">登录</button>
            <button :class="{ on: isRegister }" @click="switchMode('register')">注册</button>
            <span
              class="tab-ink"
              :style="{ transform: isRegister ? 'translateX(100%)' : 'none' }"
            />
          </div>

          <form @submit.prevent="submit">
            <label class="field">
              <span class="fl">用户名</span>
              <input
                v-model="form.username"
                autocomplete="username"
                placeholder="3-20 位字母、数字或下划线"
                @keyup.enter="submit"
              />
            </label>

            <label v-if="isRegister" class="field">
              <span class="fl">昵称</span>
              <input
                v-model="form.displayName"
                placeholder="可不填，会显示在侧栏"
                @keyup.enter="submit"
              />
            </label>

            <label class="field">
              <span class="fl">密码</span>
              <input
                v-model="form.password"
                type="password"
                autocomplete="current-password"
                placeholder="至少 6 位"
                @keyup.enter="submit"
              />
            </label>

            <label v-if="isRegister" class="field">
              <span class="fl">确认密码</span>
              <input
                v-model="form.password2"
                type="password"
                autocomplete="new-password"
                placeholder="再输一次"
                @keyup.enter="submit"
              />
            </label>

            <button type="submit" class="go" :disabled="submitting">
              {{ submitting ? '处理中…' : isRegister ? '注册并登录' : '进入' }}
            </button>
          </form>

          <div class="foot">
            <span class="hint">数据存在你自己的账号里，注册不要邮箱手机号</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* 这一页不在 AppLayout 里（登录页没有侧栏），所以纸底和纸纹要自己铺一次。
   颜色全部取 tokens.css 的变量，不写字面值。 */
.lg {
  min-height: 100%;
  display: flex;
  align-items: stretch;
  justify-content: center;
  background: var(--bg);
  /* 封面比内页多叠一层暖光：这一页留白多，光靠纸纹会显得很平 */
  background-image:
    radial-gradient(900px 520px at 22% 8%, rgba(126, 96, 44, 0.09), transparent 62%), var(--tex);
}

/* 两栏铺满整屏，**不给整组加宽度上限**。
 *
 * 这里踩过两次，方向正好相反，记清楚：
 *
 * ① 最早两栏铺满（1.05fr / 0.95fr），但品牌块是 padding 定死左边距 → 内容全贴在
 *    屏幕最左，右边空一大块。反馈："左边太靠左"。
 * ② 给整组加 `max-width: 1320px` 居中。左栏确实不贴边了，但 1920 的屏上整组只占
 *    1320、两侧各空 300px，实际内容只占全屏 57%。反馈："不占满全屏"。
 * ③ 现在：两栏照旧铺满（去掉上限），**靠 `.brand` / `.pane` 各自的 flex 居中**
 *    让内容落在自己那一栏的中间 —— 这才是①真正该用的解法。
 *    1920 下实测：品牌块 278→778、表单纸 1302→1674，内容占全屏 73%，
 *    左边距 278 / 右边距 246，两侧基本对称，且没有空带。
 *
 * 「让内容居中」和「让容器变窄」是两件事，当初混在一起做了。
 *
 * 1.1fr / 0.9fr：右栏略窄一点。表单纸只有 372px，给它太宽只会把纸推到屏幕右边。
 */
.lg-inner {
  width: 100%;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
}

/* ===== 左：品牌 =====
 *
 * 品牌块在自己的栏里居中（内部文字仍然左对齐）。上一版是 padding 定死左边距，
 * 结果内容全贴在左边、右边空一大块 —— 现在居中由 .lg-inner 的对称余白兜底。 */
.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 48px;
  position: relative;
}
.brand-inner {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  max-width: 500px;
}
/* 一条竖向墨线，像纸的装订边。position 定在左右栏交界处 */
.brand::after {
  content: '';
  position: absolute;
  right: 0;
  top: 12%;
  bottom: 12%;
  width: 1px;
  background: linear-gradient(180deg, transparent, var(--line2), transparent);
}

.mark {
  width: 54px;
  height: 54px;
}
.mark svg {
  width: 100%;
  height: 100%;
  fill: none;
  stroke: var(--ac);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.name {
  font-family: var(--font-title);
  font-size: 48px;
  font-weight: 600;
  letter-spacing: 8px;
  line-height: 1.1;
}
.name span {
  display: block;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 6px;
  color: var(--dim);
  margin-top: 10px;
  text-transform: uppercase;
}

/* 印章用全局的 .stamp，这里只解决它在 flex 列里的对齐全宽问题 */
.brand-stamp {
  align-self: flex-start;
  margin-top: -6px;
}

.slogan {
  font-size: 15px;
  line-height: 2;
  color: var(--mu);
  padding-left: 14px;
  border-left: 2px solid var(--ac);
}

.points {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 10px;
}
.points li {
  display: grid;
  grid-template-columns: 48px 1fr;
  grid-template-rows: auto auto;
  column-gap: 14px;
  row-gap: 2px;
}
.pk {
  grid-row: span 2;
  font-family: var(--font-title);
  font-size: 15px;
  color: var(--ac);
  letter-spacing: 1px;
  padding-top: 2px;
  text-align: right;
}
.pt {
  font-size: 15.5px;
  font-weight: 600;
  color: var(--tx);
}
.pd {
  font-size: 14.5px;
  line-height: 1.7;
  color: var(--dim);
}

/* ===== 右：表单 ===== */
.pane {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
}

.sheet {
  width: 100%;
  max-width: 372px;
  padding: 28px 30px 22px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: 0 18px 40px -26px rgba(80, 60, 30, 0.7);
  position: relative;
}
/* 顶部一条朱砂压线 */
.sheet::before {
  content: '';
  position: absolute;
  left: 30px;
  right: 30px;
  top: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--ac), transparent 70%);
  border-radius: 0 0 2px 2px;
}

.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  position: relative;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--line);
}
.tabs button {
  padding: 9px 0;
  border: 0;
  background: transparent;
  color: var(--dim);
  font-family: var(--font-title);
  font-size: 15px;
  letter-spacing: 3px;
  cursor: pointer;
  transition: color 0.18s;
}
.tabs button.on {
  color: var(--tx);
  font-weight: 600;
}
/* 滑块用绝对定位的一条短线，跟按钮文字下沿对齐 */
.tab-ink {
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 50%;
  height: 2px;
  background: var(--ac);
  transition: transform 0.28s cubic-bezier(0.22, 0.7, 0.28, 1);
}

.field {
  display: block;
  margin-bottom: 17px;
}
.fl {
  display: block;
  font-size: var(--fs-xs);
  letter-spacing: 1.4px;
  color: var(--dim);
  margin-bottom: 5px;
}
.field input {
  width: 100%;
  padding: 9px 2px;
  border: 0;
  border-bottom: 1px solid var(--line2);
  background: transparent;
  color: var(--tx);
  font-family: inherit;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}
.field input::placeholder {
  color: var(--dim);
  opacity: 0.75;
}
/* 聚焦时下划线变朱砂并加粗 —— 像在纸上落笔 */
.field input:focus {
  border-bottom-color: var(--ac);
  box-shadow: 0 1px 0 0 var(--ac);
}

.go {
  width: 100%;
  margin-top: 8px;
  padding: 11px 0;
  border: 1px solid var(--ac);
  border-radius: var(--radius-sm);
  background: var(--ac);
  color: #fdfaf3;
  font-family: var(--font-title);
  font-size: 15px;
  letter-spacing: 4px;
  cursor: pointer;
  transition:
    background 0.18s,
    transform 0.16s,
    box-shadow 0.18s;
}
.go:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px -14px var(--ac);
}
.go:disabled {
  opacity: 0.6;
  cursor: progress;
}

.foot {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 18px;
  padding-top: 13px;
  border-top: 1px dashed var(--line);
  font-size: var(--fs-xs);
}
.hint {
  color: var(--dim);
}

/* ===== 窄屏：品牌区收成一条头 ===== */
@media (max-width: 900px) {
  .lg {
    /* 窄屏不用再居中内容组，直接铺满 */
    display: block;
  }
  .lg-inner {
    max-width: none;
    grid-template-columns: 1fr;
  }
  .brand {
    padding: 44px 32px 8px;
  }
  /* 收成头之后不能再限宽，否则整条头只占中间 500px */
  .brand-inner {
    max-width: none;
    gap: 16px;
  }
  .brand::after {
    display: none;
  }
  .mark {
    width: 40px;
    height: 40px;
  }
  .name {
    font-size: 36px;
    letter-spacing: 6px;
  }
  .name span {
    font-size: var(--fs-xs);
    margin-top: 7px;
  }
  .points,
  .slogan {
    display: none;
  }
  .pane {
    padding: 22px 24px 44px;
  }
}
</style>
