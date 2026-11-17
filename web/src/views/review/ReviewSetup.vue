<script setup>
/* 今日设置条（每天 N 张 + 方向 chips）+ 自选清单提示条。
 *
 * 从 ReviewView 拆出来：这两条只是「取哪批卡」的开关面板，和抽卡、
 * 揭示、标记那套主流程没关系，留在一起只会把复习页越堆越长。
 * 设置改完要不要重排队列是**页面**的事（清单模式下不重排），
 * 所以这里只发事件，动作由 ReviewView 接手。
 */
import { DAILY_MAX, DAILY_MIN } from '@/stores/learning'

defineProps({
  /** 每天几张（档案里的 dailyTarget）。 */
  dailyTarget: { type: Number, required: true },
  /** 选中的方向 id。 */
  pickedDirs: { type: Array, required: true },
  /** 方向目录（含 count）。 */
  directions: { type: Array, required: true },
  /** 今日清单是否生效。 */
  pickActive: { type: Boolean, default: false },
  /** 清单张数。 */
  pickCount: { type: Number, default: 0 },
  /** 写档案中 —— 禁用按钮，连点五下会发出五个 PUT。 */
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['bump', 'toggle-dir', 'pick-all', 'use-auto', 'go-pick'])

/** 点完把焦点还给页面。否则设置按钮一直持有焦点，接下来按空格是「点这个
 *  按钮」而不是「看答案」，键盘流（空格/1/2/3）会莫名其妙失灵。 */
function blur(e) {
  if (e && e.currentTarget) e.currentTarget.blur()
}

function bump(step, e) {
  blur(e)
  emit('bump', step)
}

function toggleDir(id, e) {
  blur(e)
  emit('toggle-dir', id)
}

function pickAll(e) {
  blur(e)
  emit('pick-all')
}

function useAuto(e) {
  blur(e)
  emit('use-auto')
}
</script>

<template>
  <div>
    <!-- ===== 今日自选清单提示（挑过才显示） ===== -->
    <div v-if="pickActive" class="rv-pick rise">
      <span class="pick-txt">
        今日清单 <b class="mono">{{ pickCount }}</b> 张 —— 只推这些，
        <span class="dim">方向/每日目标对清单不生效</span>
      </span>
      <span class="pick-acts">
        <button class="sbtn" type="button" :disabled="busy" @click="useAuto($event)">
          改用自动队列
        </button>
        <button class="sbtn" type="button" @click="emit('go-pick')">去挑卡</button>
      </span>
    </div>

    <!-- ===== 今日设置：每天学几张、学什么（改完立刻重排队列） ===== -->
    <div class="rv-setup rise">
      <div class="setup-row">
        <span class="setup-label">每天</span>
        <div class="step">
          <button
            class="sbtn"
            type="button"
            :disabled="busy || dailyTarget <= DAILY_MIN"
            @click="bump(-5, $event)"
          >
            −
          </button>
          <span class="snum mono">{{ dailyTarget }}</span>
          <span class="sunit">张</span>
          <button
            class="sbtn"
            type="button"
            :disabled="busy || dailyTarget >= DAILY_MAX"
            @click="bump(5, $event)"
          >
            ＋
          </button>
        </div>
        <span class="setup-label">方向</span>
        <div class="chips">
          <button
            class="chip"
            type="button"
            :class="{ on: !pickedDirs.length }"
            :disabled="busy"
            @click="pickAll($event)"
          >
            全部
          </button>
          <button
            v-for="d in directions"
            :key="d.id"
            class="chip"
            type="button"
            :class="{ on: pickedDirs.includes(d.id) }"
            :title="d.desc"
            :disabled="busy"
            @click="toggleDir(d.id, $event)"
          >
            {{ d.name }}<i class="cnt">{{ d.count }}</i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ---- 今日自选清单提示条 ---- */
.rv-pick {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  padding: 10px 16px;
  border: 1px solid var(--ac);
  border-radius: var(--radius);
  background: var(--ac-glow);
  font-size: var(--fs-sm);
  color: var(--tx);
}
.rv-pick b {
  color: var(--ac);
}
.rv-pick .dim {
  color: var(--dim);
}
.pick-acts {
  display: flex;
  gap: 8px;
}

/* ---- 今日设置条 ---- */
.rv-setup {
  margin-bottom: 16px;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}
.setup-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.setup-label {
  font-size: var(--fs-sm);
  color: var(--mu);
}
.step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-right: 14px;
  border-right: 1px dashed var(--line);
}
.sbtn {
  width: 26px;
  height: 26px;
  border: 1px solid var(--line2);
  border-radius: var(--radius-sm);
  background: var(--bg2);
  color: var(--tx);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  transition:
    border-color 0.16s,
    background 0.16s;
}
.sbtn:hover:not(:disabled) {
  border-color: var(--ac);
  background: var(--ac-glow);
}
.sbtn:disabled {
  opacity: 0.4;
  cursor: default;
}
.pick-acts .sbtn {
  width: auto;
  height: auto;
  padding: 4px 10px;
  font-size: var(--fs-xs);
}
.snum {
  font-family: var(--font-mono);
  font-size: 17px;
  font-weight: 600;
  min-width: 26px;
  text-align: center;
  color: var(--ac);
}
.sunit {
  font-size: var(--fs-xs);
  color: var(--mu);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 11px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--bg2);
  color: var(--mu);
  font-size: var(--fs-sm);
  cursor: pointer;
  transition:
    color 0.16s,
    border-color 0.16s,
    background 0.16s;
}
.chip:hover:not(:disabled) {
  color: var(--tx);
  border-color: var(--ac-dim);
}
.chip.on {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.chip:disabled {
  opacity: 0.55;
  cursor: default;
}
/* 方向后面的小数字 = 这个方向库里有多少张卡。写成 i 而不是 span：
   位置和斜体都借的是「角标」的读法，不想让它跟名字争主次 */
.chip .cnt {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-style: normal;
  color: var(--dim);
}
.chip.on .cnt {
  color: var(--ac);
  opacity: 0.75;
}
</style>
