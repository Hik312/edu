<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/common'
import katex from 'katex'
import 'highlight.js/styles/atom-one-dark.css'
import 'katex/dist/katex.min.css'

const props = defineProps({
  text: { type: String, default: '' },
  copyable: { type: Boolean, default: true }
})

const emit = defineEmits(['copy'])

/** HTML escape */
function esc(s) {
  return String(s)
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(/'/g, '&apos;')
}

/** Split by ``` fences: [{code:false,text}, {code:true,lang,body}] */
function splitFences(s) {
  const out = []
  let last = 0
  const re = /```([^\n`]*)\n([\s\S]*?)(?:```|$)/g
  let m
  while ((m = re.exec(s))) {
    if (m.index > last) out.push({ code: false, text: s.slice(last, m.index) })
    out.push({ code: true, lang: (m[1] || '').trim(), body: m[2] })
    last = m.index + m[0].length
  }
  if (last < s.length) out.push({ code: false, text: s.slice(last) })
  return out
}

/** KaTeX render (inline/block), fallback to escaped text */
function katexHtml(texSrc, display) {
  try {
    return katex.renderToString(texSrc.trim(), { throwOnError: false, displayMode: display })
  } catch {
    return esc(texSrc)
  }
}

/** Text segment: extract math placeholders, marked.parse, restore KaTeX */
function renderTextSegment(src) {
  if (!src) return ''
  const placeholders = []
  const MATH_MARKER = '\u0000M'
  const withPlaceholders = src.replace(/\$\$([\s\S]+?)\$\$|\$([^$\n]+)\$/g, (m, disp, inline) => {
    if (inline !== undefined && /^[\d.,\s]+$/.test(inline)) return m
    const html = katexHtml(disp !== undefined ? disp : inline, disp !== undefined)
    placeholders.push(html)
    return MATH_MARKER + (placeholders.length - 1) + MATH_MARKER
  })
  const mdHtml = marked.parse(withPlaceholders, { async: false })
  return mdHtml.replace(
    new RegExp(MATH_MARKER + '(\\d+)' + MATH_MARKER, 'g'),
    (_, i) => placeholders[Number(i)]
  )
}

/** Code block: hljs highlight + copy button */
function renderCodeBlock({ lang, body }) {
  let codeHtml = esc(body)
  let cls = 'hljs'
  if (lang && hljs.getLanguage(lang)) {
    try {
      codeHtml = hljs.highlight(body, { language: lang }).value
      cls += ` language-${esc(lang)}`
    } catch {
      // ignore highlight errors
    }
  }
  const head = lang
    ? `<div class="md-code-head"><span class="md-code-lang">${esc(lang)}</span>${props.copyable ? `<button class="md-copy" data-copy title="复制代码">复制</button>` : ''}</div>`
    : ''
  return `<div class="md-codeblk">${head}<pre><code class="${cls}">${codeHtml}</code></pre></div>`
}

/** Combine: split by fences, render each, join */
const html = computed(() => {
  if (!props.text) return ''
  const segs = splitFences(props.text)
  return segs.map(s => (s.code ? renderCodeBlock(s) : renderTextSegment(s.text))).join('')
})

/** Copy button delegation */
function onClick(e) {
  const btn = e.target.closest('.md-copy')
  if (!btn) return
  const pre = btn.closest('.md-codeblk')?.querySelector('pre code')
  if (!pre) return
  const code = pre.textContent
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = '已复制'
    setTimeout(() => (btn.textContent = '复制'), 1500)
  })
  emit('copy', code)
}
</script>

<template>
  <div class="md-container" @click="onClick" v-html="html" />
</template>

<style scoped>
/* ★ **不要在这里写死color**。
 * 这个组件被用在两种底色上：浅色纸面气泡（助手）和深靛蓝气泡（用户提问）。
 * 之前这里 `color: var(--tx)`（墨褐）把**用户气泡里的文字也刷成深褐色**，
 * 于是深底深字、整块看不清 —— 而父级气泡设的浅色 color 根本压不过它
 * （scoped 选择器自带优先级）。改成 `inherit`：默认跟宿主底色走，
 * 需要固定颜色的地方（比如单独用这个组件做卡片预览）在使用处自己设。 */
.md-container {
  line-height: 1.8;
  font-size: 14.5px;
  color: inherit;
}

/* 代码块 */
.md-codeblk {
  margin: 14px 0;
  border-radius: var(--radius);
  overflow: hidden;
  background: #1e1e1e;
  border: 1px solid var(--line);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
.md-code-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid var(--line);
  font-size: 12.5px;
}
.md-code-lang {
  color: var(--dim);
  font-family: var(--font-mono);
  font-size: 12px;
  text-transform: lowercase;
}
.md-copy {
  padding: 2px 10px;
  font-size: 12px;
  border: 1px solid var(--line2);
  border-radius: 4px;
  background: transparent;
  color: var(--mu);
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s,
    border-color 0.15s;
}
.md-copy:hover {
  background: var(--ac);
  color: #fff;
  border-color: var(--ac);
}
.md-copy:focus-visible {
  outline: 2px solid var(--ac);
  outline-offset: 2px;
}
.md-codeblk pre {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  font-size: 13.5px;
  line-height: 1.7;
  font-family: var(--font-mono);
  background: transparent;
}
.md-codeblk code {
  font-family: inherit;
  font-size: inherit;
  background: transparent;
}
.hljs {
  color: #e2e8f0;
}
.hljs-comment {
  color: #6a7a8a;
}
.hljs-keyword {
  color: #c678dd;
}
.hljs-string {
  color: #98c379;
}
.hljs-number {
  color: #d19a66;
}
.hljs-function {
  color: #61afef;
}
.hljs-title {
  color: #e5c07b;
}
.hljs-params {
  color: #abb2bf;
}
.hljs-built_in {
  color: #e5c07b;
}
.hljs-type {
  color: #e5c07b;
}

/* Inline code */
:deep(code) {
  font-family: var(--font-mono);
  font-size: 0.92em;
  padding: 0.15em 0.35em;
  background: var(--bg2);
  border-radius: 3px;
  color: var(--ac);
}

/* KaTeX fixes */
:deep(.katex) {
  font-size: 1em !important;
}
:deep(.katex-display) {
  overflow-x: auto;
  overflow-y: hidden;
}

/* Basic typography */
/* 以下所有正文元素都**不写死颜色**，一律 inherit。
 * 理由同上：同一个组件要能放在浅色纸面和深靛蓝两种气泡里，
 * 任何一处写死 var(--tx) 都会在深底上变成"深底深字"。
 * 强调色（链接/引用边框）保留 —— 它们在两种底色上都读得出来。 */
:deep(h1, h2, h3, h4) {
  font-family: var(--font-title);
  font-weight: 600;
  color: inherit;
  margin: 16px 0 8px;
}
:deep(h1) {
  font-size: 1.5em;
}
:deep(h2) {
  font-size: 1.32em;
}
:deep(h3) {
  font-size: 1.18em;
}
:deep(h4) {
  font-size: 1.06em;
}
/* 段落间距收到 6px。宿主（聊天气泡）还开着 white-space: pre-wrap，
 * 模型输出里的换行本身已经产生行距，再叠 10px 的 p-margin
 * 就会把每段撑成"隔一个空行"，长回答里像漏了内容。 */
:deep(p) {
  margin: 6px 0;
}
:deep(ul, ol) {
  /* 列表原来只有 20px 左缩进，视觉上贴着段首缩进那一列，看起来"太靠左"。
     26px 能让项目符号明显缩进一级，和 2em 的段首缩进形成层次。 */
  padding-left: 26px;
  margin: 8px 0;
}
:deep(li) {
  margin: 5px 0;
}
/* 列表项和段落之间也要有节奏，否则一串 <li> 会糊成一块 */
:deep(li)::marker {
  color: var(--ac);
  opacity: 0.65;
  font-size: 0.92em;
}
/* 嵌套列表缩进得比外层再多一点，否则内外两层项目符号会齐平，看不出层级 */
:deep(li > ul),
:deep(li > ol) {
  margin: 4px 0;
}
:deep(strong) {
  font-weight: 600;
  color: inherit;
}
:deep(em) {
  font-style: italic;
}
:deep(blockquote) {
  border-left: 3px solid var(--ac);
  padding-left: 14px;
  margin: 10px 0;
  color: inherit;
  opacity: 0.82;
  font-style: italic;
}
:deep(hr) {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 16px 0;
}
:deep(a) {
  color: var(--ac);
  text-decoration: none;
  /* 深底上靛蓝链接读不出来 —— 加一道浅色描边区分（浅底下几乎不可见） */
  text-shadow: 0 0 0 currentColor;
}
:deep(a:hover) {
  text-decoration: underline;
}
</style>
