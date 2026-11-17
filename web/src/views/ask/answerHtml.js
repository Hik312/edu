/* AI 回答气泡的 HTML 渲染 —— 公式（KaTeX）、粗体、**代码块**。
 *
 * 为什么需要：气泡原来是 {{ m.text }} 纯文本，模型写的 $...$ LaTeX、**粗体**
 * 和 ``` 代码块原样露出来（用户反馈：$ P(\theta_{t+1}...)$ 是一堆乱字符、
 * 示例代码挤成一坨很难读）。
 *
 * 渲染三种：
 *   代码块  ```lang ... ``` → 带语言标签的代码块（豆包风格：圆角+浅底+等宽字体+横向滚动）
 *   公式    $...$（行内）/ $$...$$（块级），katex；语法错了原样显示，不炸页面
 *   粗体    **xxx**（回答里的小标题、强调）
 * 其余保持纯文本 —— 不上全套 markdown：提示词没要求模型输出表格，
 * 真出来了 white-space: pre-wrap 也能读。
 *
 * 流式安全：未闭合的 ``` 或 $（生成到一半）不匹配、原样显示，下一段补齐了再渲染。
 *
 * 安全性：普通文本、代码内容都先 HTML 转义再拼进 v-html，模型输出当不了 HTML 执行；
 * katex 自己的输出可信（出错时它也转义原文）。
 */
import katex from 'katex'
import 'katex/dist/katex.min.css'

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function tex(html, texSrc, display) {
  try {
    return html + katex.renderToString(texSrc.trim(), { throwOnError: false, displayMode: display })
  } catch {
    // throwOnError:false 理论上不抛；真抛了也不能让整条回答崩掉
    return html + esc(texSrc)
  }
}

function plain(seg) {
  // 转义之后再换粗体 —— ** 只可能是模型写的强调，不会撞 HTML 标签
  return esc(seg).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
}

/** 渲染非代码片段：公式 + 粗体（抽成独立函数，便于代码块分段复用）。 */
function renderText(s) {
  let out = ''
  let last = 0
  // 块级在前；行内公式不允许跨行（半截 $ 在流式里很常见，放行跨行会把
  // 两段正文吞进公式）。纯数字的 $..$ 当钱跳过（"$10 一杯"不是公式）
  const re = /\$\$([\s\S]+?)\$\$|\$([^$\n]+)\$/g
  let m
  while ((m = re.exec(s))) {
    out += plain(s.slice(last, m.index))
    if (m[1] !== undefined) out = tex(out, m[1], true)
    else if (/^[\d.,\s]+$/.test(m[2])) out += esc(m[0])
    else out = tex(out, m[2], false)
    last = m.index + m[0].length
  }
  out += plain(s.slice(last))
  return out
}

/** 一个代码块 → 带语言标签的 HTML（豆包风格靠 CSS，这里只出结构）。 */
function codeBlock(lang, code) {
  const label = esc((lang || '').trim() || 'code')
  // 代码整体转义；换行由 .code-pre 的 white-space:pre 还原
  return (
    '<div class="code-block">' +
    '<div class="code-head"><span class="code-lang">' +
    label +
    '</span></div>' +
    '<pre class="code-pre"><code>' +
    esc(code.replace(/\n+$/, '')) +
    '</code></pre>' +
    '</div>'
  )
}

/**
 * 回答正文 → 可直接塞进 v-html 的 HTML。
 * @param {string} text 已经过 cleanAnswer 的纯文本
 * @returns {string}
 */
export function answerHtml(text) {
  if (!text) return ''
  const s = String(text)
  // 先按 ``` fence 把代码块切出来，剩下的片段走公式/粗体。
  // 未闭合的 ```（流式到一半，正则吃到结尾也没有结束 fence）当普通文本 ——
  // 等下一段补齐再整体重渲染，避免半截代码被当成完整块、加个框又跳变。
  const fence = /```([\w+#.-]*)[ \t]*\n?([\s\S]*?)(```|$)/g
  let out = ''
  let last = 0
  let m
  while ((m = fence.exec(s))) {
    out += renderText(s.slice(last, m.index))
    // m[3] 非空 = 闭合了；m[3]=='' 说明是「未闭合，匹配到串尾」
    out += m[3] ? codeBlock(m[1], m[2]) : plain(m[0])
    last = m.index + m[0].length
    if (!m[3]) break // 未闭合：已经吃到串尾，没有后续可匹配
  }
  out += renderText(s.slice(last))
  return out
}
