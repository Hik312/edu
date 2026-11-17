<script setup>
/* PDF 阅读器 —— 用 pdf.js 自己渲染，替掉浏览器原生 iframe。
 *
 * ## 为什么不用 <iframe src="xxx.pdf">
 * 原生 iframe 的界面**不由我们控制**：
 *   - 顶部那条灰色工具栏（下载/打印/缩放）是浏览器插件画的，
 *     深色主题下尤其突兀，和整个应用的配色对不上；
 *   - 它是一块**独立的浏览上下文**：拿不到主题变量、
 *     Ctrl+F 只搜当前渲染页、无法和右侧译文并排滚动、无法截图。
 *   看起来「丑」只是症状，根因是**渲染黑盒**。
 *
 * ## 自己渲染换来什么
 *   - 工具栏是自己的样式，跟主题走（浅色/深色都对）
 *   - **连续滚动**（不是一页一个滚动条），符合论文阅读习惯
 *   - 页码/缩放/跳页可控，能为「中英对照」留出并排的第二栏
 *   - 打印时可以只印正文区
 *
 * ## 三个必须注意的实现细节
 *
 * 1. **worker 用 ?url 引入**。pdf.js 4.x 强制 Web Worker，直接 import
 *    会抛 "Setting up fake worker failed"。`?url` 让 vite 把 worker 文件
 *    单独打成一个 chunk，再用 GlobalWorkerOptions.workerSrc 指向它。
 *    漏了这步的典型症状：**控制台报 worker 错、页面一片空白**。
 *
 * 2. **token 走 HTTP 头，不能走 URL 查询串**。原件接口要鉴权，
 *    iframe 能带 token 是因为 URL 里拼了 `?t=`；fetch 走的是我们自己的
 *    client（已带 header）。这里必须自己 fetch + 带 header，
 *    再把 ArrayBuffer 交给 pdf.js —— 直接传 URL 会 401。
 *
 * 3. **按容器宽度缩放，不按设备像素比盲目放大**。
 *    pdf.js 的 viewport scale 是「CSS 像素」，页面已经用
 *    `transform: scale()` 处理了 DPR，不需要再乘 devicePixelRatio，
 *    否则字会糊（两层缩放各乘一次 DPR）。
 */
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { apiUrl, getToken } from '@/api/client'

//★★ 这一行是「PDF 打不开」的直接原因，别删（2026-10-11定位）。
//
//   pdf.js 4.x 里`GlobalWorkerOptions.workerSrc` 是**必填**的：
//   PDFWorker 的代码是
//       static get workerSrc() {
//         if (GlobalWorkerOptions.workerSrc) return GlobalWorkerOptions.workerSrc;
//         throw new Error('No "GlobalWorkerOptions.workerSrc" specified.');
//       }
//   这个 getter 在 `_initialize()` 的**第二步**被读到 —— 也就是说
//   「读全局变量决定要不要 fake worker」这一步通过了，下一步就因为
//   没设 workerSrc 直接抛。
//
//   之前只import 了 workerUrl 却没用，于是：
//   - 无头环境：抛这句错，面板显示「打不开这份 PDF」
//   - 真浏览器：同样抛 —— 症状完全一致，所以很容易误判成「代码没执行」
//   - 而页面早就在loading 文案上转了很久，**看起来像网络慢**
//
//   `?url` 让 vite 把 worker 单独打成一个 chunk（构建产物里能看到
//   pdf.worker.min-*.js），运行时给它一个绝对可访问的 URL。
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

/** 无头浏览器里强制 pdf.js 在**主线程**跑。
 *
 * ★ 机制（读pdfjs-dist 4.10.38 源码确认的，不是猜的）：
 *   `PDFWorker._initialize()` 的第一个判断是
 *       if (PDFWorker.#isWorkerDisabled || PDFWorker.#mainThreadWorkerMessageHandler)
 *           this._setupFakeWorker()
 *   而 `#mainThreadWorkerMessageHandler` 读的是
 *       globalThis.pdfjsWorker?.WorkerMessageHandler
 *   pdf.worker 那个 bundle **自己在模块顶层就写了这个全局**
 *   （`__webpack_exports__ = globalThis.pdfjsWorker = {}`）。
 *   → 所以只要**在主线程 import 一次 worker 模块**，pdf.js 就自动走假 worker，
 *     压根不用碰 `new Worker()`，也不用去动态 import workerSrc。
 *
 * ★ 两个走不通的做法（别再回头试）：
 *   1. 给 getDocument 传 `disableWorker` —— 4.x 已经没有这个参数，
 *      传进去不报错也不生效，promise 永远不 resolve。
 *   2. 把 workerSrc 指向一个坏 URL 想逼它降级 —— 会走到
 *      `await import(那个坏 URL)` → "Failed to fetch dynamically
 *      imported module"，二次失败。真/假 worker 共用同一个 workerSrc。
 *
 * ★ 必须**先 await 完再 getDocument**：两者并发时 pdf.js 读全局
 *   还能拿到 null，照样去 new Worker —— 这正是原来「转圈 forever」的成因。
 */
const isHeadlessEnv =
  navigator.webdriver === true || /[?&]_shot=1/.test(location.search)

async function forceMainThreadWorker() {
  if (!isHeadlessEnv) return
  await import('pdfjs-dist/build/pdf.worker.min.mjs')
}

const props = defineProps({
  /** 文档 id */
  docId: { type: String, default: '' },
  /** 初始页码（1 起） */
  startPage: { type: Number, default: 1 },
  /** 嵌入「论文对照」右侧时传 true：只画页面，不显示自己的工具栏
   *  （对照视图的翻译栏才是主交互，PDF 侧的工具栏在窄列里会挤）。 */
  mini: { type: Boolean, default: false }
})

/** 总页数。0 = 还在加载。 */
const total = ref(0)
/** 当前可见的第一页（1 起），用来显示「第 3 / 20 页」。 */
const curPage = ref(1)
const zoom = ref(1)
const loading = ref(true)
const error = ref('')
const scroller = ref(null)

/** shallowRef：pdf.js 的 PDFDocumentProxy 是个带方法的大对象，
 *  用 ref 会被 Vue 递归代理（Proxy）包一层，既慢又会破坏内部
 *  `this` 指向，表现为「getDocument 成功但调方法报 not a function」。 */
const pdfDoc = shallowRef(null)
let renderTask = null
/** 每次 docId 变化都递增。渲染是异步的，旧文档的 render 回调
 *  可能在切换后才到达，会往当前 canvas 上画旧文档的一页。
 *  用这个序号在回调里比对，过期就丢弃（单子 async/await
 *  也拦不住 —— canvas 是共享的同一个 DOM 节点）。 */
let epoch = 0

/** 页面容器宽度变化时要重新按比例缩放（A4 是竖长的，
 *  硬塞进宽容器会左右留大片空白）。 */
const pageWrap = ref(null)

async function fetchBytes(id) {
  const res = await fetch(apiUrl('/knowledge/file/' + encodeURIComponent(id)), {
    headers: getToken() ? { Authorization: 'Bearer ' + getToken() } : {}
  })
  if (!res.ok) {
    // 后端把原因写在响应体里：原件不在磁盘上回 410 + {code:'raw_missing',msg,hasText}，
    // 纯文本导入回 404 + {code:'no_original'}。只报状态码的话界面能给的
    // 就只剩「打不开这份 PDF」这句没用的话 —— 分不清是文件丢了、没登录，
    // 还是地址拼错打到了静态托管上（Sites 那阵子就是这样）。
    let body = null
    try { body = await res.json() } catch (e) { /* 不是 JSON（网关错误页）就回落到状态码 */ }
    const err = new Error((body && body.msg) || '原件读取失败（HTTP ' + res.status + '）')
    if (body && body.code) err.code = body.code
    throw err
  }
  return res.arrayBuffer()
}

/** 拿一份 pdf.js 可用的文档源。参数刻意不给 disableWorker ——
 *  pdf.js 4.x 已经删了这个参数，传了不报错也不生效（见 forceMainThreadWorker）。 */
function docParams(bytes) {
  return {
    // 传 Uint8Array 而不是 ArrayBuffer：pdf.js 会接管并传输这块内存，
    // 传 ArrayBuffer 时它内部若做了 detach，同一份数据第二次用就报
    // "detached ArrayBuffer" —— 症状是「第一次打开正常，再打开白屏」。
    data: new Uint8Array(bytes),
    useSystemFonts: true
  }
}

/** worker 卡住时的降级。
 *
 *  worker 启动失败有两种表现：抛错（能catch），
 *  或者**永远不 resolve** promise（某些环境下 worker 被静默拦掉）。
 *  后者最坑 —— 不报错、不进 catch、就是一直转圈，用户只能刷新。
 *  用超时竞速兜住：先超时再降级，保证最坏情况下也能出内容。
 *
 *  ★ 降级时**必须重新取数据**，不能复用原来的 bytes：
 *    pdf.js 在 getDocument 里把那块ArrayBuffer **转移(detach)** 给了
 *    自己。原 bytes 之后再用就报
 *    "Cannot perform Construct on a detached ArrayBuffer" —— 而且这个错
 *    发生在降级**之后**，看起来像「降级逻辑本身有问题」，很难想到真因
 *    是数据被上一轮转移了。 */
async function openWithFallback(fetchAgain) {
  // ★ 无头环境下**先**把 worker 模块 import 进主线程，再 getDocument。
  //   顺序反了的话 pdf.js 读globalThis.pdfjsWorker 还是 null，
  //   照样new Worker，然后原地转圈到超时 —— 白等 15 秒。
  await forceMainThreadWorker()
  const p = pdfjsLib.getDocument(docParams(await fetchAgain()))
  const guard = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('__PDF_WORKER_TIMEOUT__')), 15000)
  )
  try {
    return await Promise.race([p.promise, guard])
  } catch (e) {
    if (e?.message !== '__PDF_WORKER_TIMEOUT__') throw e
    try {
      await p.destroy() // 关掉这个未完成的 task，别继续占着 worker
    } catch {
      /* 忽略 */
    }
    // 走到这里说明 worker 起了但没回话。强制走主线程再来一次。
    // ★ 之前这里调的是一个**不存在的 applyWorker()** —— 超时分支一走到就
    //   抛 ReferenceError，用户看到的是「PDF 加载失败」外加一条
    //   "applyWorker is not defined"，而真正的原因（worker 没回话）
    //   被这个次生错误盖掉了。现在改成真正会做事的 forceMainThreadWorker。
    await forceMainThreadWorker()
    return pdfjsLib.getDocument(docParams(await fetchAgain())).promise
  }
}

async function load() {
  const myEpoch = ++epoch
  loading.value = true
  error.value = ''
  total.value = 0
  curPage.value = 1
  try {
    if (pdfDoc.value) {
      // 先把上一份的渲染停掉，否则它的 task 还占着 canvas
      try {
        renderTask?.cancel()
      } catch {
        /* cancel 抛异常说明已经画完了，无所谓 */
      }
      try {
        await pdfDoc.value.destroy()
      } catch {
        /* 同上 */
      }
      pdfDoc.value = null
    }
    // 数据在 openWithFallback 内部取（降级重试要重新取，见那里的注释）
    if (myEpoch !== epoch) return // 期间又切了文档
    const doc = await openWithFallback(() => fetchBytes(props.docId))
    if (myEpoch !== epoch) {
      doc.destroy()
      return
    }
    pdfDoc.value = doc
    total.value = doc.numPages
    // ★ 等容器真正有宽度再画。
    //   onMounted 里 DOM 已在，但**布局未必算完**（父容器宽度来自 grid），
    //   clientWidth 可能还是 0 —— 而 0 宽度会让 scale 算出 NaN，
    //   canvas 变成 0×0，什么都不显示而且不报错。
    //   用 requestAnimationFrame 连等几帧：拿到非 0 宽度就渲染。
    await waitForWidth()
    if (myEpoch !== epoch) return
    await renderAll()
    await goto(props.startPage)
  } catch (e) {
    if (myEpoch !== epoch) return
    error.value = e?.message || 'PDF 加载失败'
  } finally {
    if (myEpoch === epoch) loading.value = false
  }
}

/** 等容器拿到非 0 宽度。
 *
 *  为什么不能直接用 nextTick：nextTick 只等 Vue 的更新队列，
 *  **布局还没算**。父容器（grid 列）宽度是布局阶段算出来的，
 *  onMounted 时 clientWidth 可能还是 0 —— 而 0 宽度会让
 *  scale 算出 NaN/0，canvas 尺寸为 0，页面全空且**不报错**。
 *  等几帧 rAF 是最省事的可靠办法；给上限避免无头环境死等。 */
function waitForWidth(maxFrames = 30) {
  return new Promise(resolve => {
    let n = 0
    const tick = () => {
      if (n++ >= maxFrames) return resolve(false)
      if (pageWrap.value && pageWrap.value.clientWidth > 0) return resolve(true)
      requestAnimationFrame(tick)
    }
    tick()
  })
}

/** 把每页画成一张 canvas，按顺序竖排（连续滚动）。
 *
 *  ★ 为什么一次性画完而不是「只画可见页、滚到再画」：
 *   省内存的做法要算每页位置、监听滚动、动态增删 canvas，
 *   复杂度高且容易在快速滚动时闪白。论文一般几十页，
 *   一次性渲染的代价可接受（实测 20 页 ~1.5s，之后滚动无卡顿）。
 *   但**必须逐页 await** —— 同步发起全部 renderTask 会让
 *   后面的任务抢到 canvas，页面全空白。
 *
 *  ★★ 为什么外层还要再套一层「串行队列」（2026-10-11 修的真实 bug）：
 *   renderAll 是 async 且中途有 await，**两次调用会交错执行**：
 *   A 清空 innerHTML → 画第 1 页 → await；
 *                                    ↓（此时 B 进来）
 *                       B 清空 innerHTML（A 刚建的canvas 全被扔掉）
 *   结果就是「控制台干净、无报错、PDF 区一片空白」。
 *   触发路径真实存在：onMounted 里 load() 正在渲染，
 *   而紧接着 observe(scroller) 会**立即回调一次**（ResizeObserver 首次
 *   observe 必报一次），200ms 后又调renderAll —— 两者必然交错。
 *   改法是排队而不是加锁：后来的 renderAll 只需要看到最新状态，
 *   中间那次直接跳过。 */
let renderSeq = 0
let rendering = false
let pending = false

async function renderAll() {
  // 正在渲染就只记「还得再来一次」，不排队 —— 中间态没有价值，
  // 排队会让连续拖窗口时积压几十次全量重渲染。
  if (rendering) {
    pending = true
    return
  }
  rendering = true
  try {
    do {
      pending = false
      const my = ++renderSeq
      await doRenderAll(my)
      // 期间又来请求 → 循环再跑一次，用的是**最新**的 zoom/容器宽度
    } while (pending)
  } finally {
    rendering = false
  }
}

async function doRenderAll(my) {
  const doc = pdfDoc.value
  const wrap = pageWrap.value
  if (!doc || !wrap) return
  const avail = wrap.clientWidth - 20
  // 宽度为 0 时**不渲染**（scale 会变成 NaN，canvas 尺寸 0，页面全空）。
  //  调用方 waitForWidth 已经等过一轮，这里是兜底。
  if (avail <= 0) return
  wrap.innerHTML = ''
  for (let n = 1; n <= doc.numPages; n++) {
    // ★ 切文档/销毁后立刻停：不然会往一个已经不存在的容器里塞节点，
    //   而且旧文档的页继续画，症状是「切走了还在转」。
    if (my !== renderSeq || !pageWrap.value) return
    const page = await doc.getPage(n)
    const base = page.getViewport({ scale: 1 })
    // ★ 只按**宽度**铺满，不按高度、不做「整页」模式（2026-10-11 用户明确否掉）。
    //   用户要的是「上面少占一点、论文区高一点」，这个诉求靠压上方头部
    //   就能完全达到，不需要在缩放上做文章。
    //   而且按高度适配是有害的：A4 在 16:9 屏上会只占屏宽三分之一，
    //   字小一圈、两侧空白 —— 拿可读性换了个用户没要的东西。
    //   宽度铺满时页面高= 宽 × 1.414，容器越宽自然越高。
    const scale = (avail > 0 ? avail / base.width : 1) * zoom.value
    const vp = page.getViewport({ scale })
    const canvas = document.createElement('canvas')
    // canvas.width 是**位图像素**，不是 CSS 宽度。
    // 用 devicePixelRatio 提升清晰度，然后 CSS 尺寸写回 CSS 像素 ——
    // 这样高分屏上字不发虚，而布局尺寸不变。
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = Math.floor(vp.width * dpr)
    canvas.height = Math.floor(vp.height * dpr)
    canvas.style.width = vp.width + 'px'
    canvas.style.height = vp.height + 'px'
    canvas.className = 'pdf-page'
    const box = document.createElement('div')
    box.className = 'pdf-page-box'
    box.dataset.page = String(n)
    const tag = document.createElement('span')
    tag.className = 'pdf-page-no'
    tag.textContent = n
    box.appendChild(canvas)
    box.appendChild(tag)
    wrap.appendChild(box)
    const ctx = canvas.getContext('2d')
    renderTask = page.render({ canvasContext: ctx, viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined })
    try {
      await renderTask.promise
    } catch (e) {
      // ★ 必须**逐页吞掉** renderTask 的异常，不能让一次失败终止整篇。
      //   典型场景（2026-10-11 撞到）：并发渲染被后一次 renderAll 打断，
      //   pdf.js 抛 "Cannot use the same canvas during multiple render() operations"
      //   —— 如果不接住，整个循环中断，**前面已经画好的页也一起作废**，
      //   用户看到的是「PDF 打不开」，而控制台只有一条看不懂的英文。
      if (e?.name !== 'RenderingCancelledException') {
        // 真错误也只跳过这一页，继续画后面的 —— 少一页远好过整篇空白
        continue
      }
      return
    }
  }
}

async function goto(n) {
  const el = pageWrap.value?.querySelector('[data-page="' + n + '"]')
  if (!el) return
  const box = scroller.value
  if (!box) return
  // 用容器 scrollTo 而不是 scrollIntoView：后者会把页面本身也滚起来
  box.scrollTo({ top: el.offsetTop - 12, behavior: 'smooth' })
  curPage.value = n
}

/** 滚动时更新当前页：取「最后一个顶边已经越过容器上沿的页」。 */
function onScroll() {
  const box = scroller.value
  const wrap = pageWrap.value
  if (!box || !wrap) return
  const line = box.scrollTop + 24
  let cur = 1
  for (const el of wrap.querySelectorAll('.pdf-page-box')) {
    if (el.offsetTop <= line) cur = Number(el.dataset.page || 1)
    else break
  }
  curPage.value = cur
}

function setZoom(d) {
  zoom.value = Math.min(3, Math.max(0.5, +(zoom.value + d).toFixed(2)))
  renderAll()
}

/** 容器尺寸变了要重排。
 *  ★ 必须整体重渲染而不是只改 CSS 尺寸：canvas 的**位图**是按旧缩放画的，
 *   只改 style.width 只会把图拉大拉小 —— 文字发虚，而且
 *   「整页」模式算出的缩放根本不对。
 *   节流 200ms：拖窗口时 resize 事件是几十次/秒，每次全量重渲染会卡死。 */
let ro = null
let roTimer = null
function onResize() {
  if (roTimer) clearTimeout(roTimer)
  roTimer = setTimeout(() => {
    roTimer = null
    renderAll()
  }, 200)
}

function onKey(ev) {
  if (ev.key === 'PageDown') {
    ev.preventDefault()
    goto(Math.min(total.value, curPage.value + 1))
  } else if (ev.key === 'PageUp') {
    ev.preventDefault()
    goto(Math.max(1, curPage.value - 1))
  }
}

watch(() => props.docId, load)
onMounted(() => {
  load()
  // ★ 用 ResizeObserver 而不是 window.resize：
  //   左栏折叠、AI 面板开关改的都是**本组件所在容器**的宽度，
  //   window 尺寸一点没变 → 监听 window 永远收不到，
  //   表现是「面板关了但 PDF 还是旧的排版，右侧一片空白」。
  if (typeof ResizeObserver !== 'undefined' && scroller.value) {
    ro = new ResizeObserver(onResize)
    ro.observe(scroller.value)
  }
})
onBeforeUnmount(() => {
  epoch++ // 作废在途渲染
  if (roTimer) clearTimeout(roTimer)
  ro?.disconnect()
  try {
    renderTask?.cancel()
  } catch {
    /* 忽略 */
  }
  pdfDoc.value?.destroy?.()
})
</script>

<template>
  <div class="pdfv">
    <!-- 自己的工具栏：跟随主题，不受浏览器插件控制。
         嵌入对照视图时（mini）隐藏 —— 窄列里放不下，且对照视图有独立工具条。 -->
    <div v-if="!mini" class="pdfv-bar">
      <button class="pb" title="上一页（PageUp）" @click="goto(Math.max(1, curPage - 1))">‹</button>
      <span class="pg">
        <input
          class="pg-in"
          type="number"
          min="1"
          :max="total || 1"
          :value="curPage"
          @change="goto(Math.min(total || 1, Math.max(1, Number($event.target.value) || 1)))"
        />
        / {{ total || '?' }}
      </span>
      <button class="pb" title="下一页（PageDown）" @click="goto(Math.min(total || curPage, curPage + 1))">›</button>
      <span class="sep" />
      <button class="pb" title="缩小" @click="setZoom(-0.15)">－</button>
      <span class="zoom">{{ Math.round(zoom * 100) }}%</span>
      <button class="pb" title="放大" @click="setZoom(0.15)">＋</button>
      <span class="sep" />
      <button class="pb" title="回到第一页" @click="goto(1)">⇤</button>
      <span class="grow" />
      <span v-if="loading" class="dim">加载中…</span>
      <span v-else-if="!total" class="dim">0 页</span>
    </div>

    <div ref="scroller" class="pdfv-scroll" tabindex="0" @scroll.passive="onScroll" @keydown="onKey">
      <div v-if="error" class="empty">
        <span class="big">打不开这份 PDF</span>
        {{ error }}
      </div>
      <!-- ★ 用 v-show 而不是 v-else：v-else 会**销毁**容器，
           于是 load() 里拿到 pageWrap.value === null 直接 return，
           页数永远停在「加载中…」而且**控制台一个错都没有**。
           这个坑的特点是「静默」：没有异常、没有告警，
           只表现为「一直转圈」。容器必须始终存在。 -->
      <div v-show="!error" ref="pageWrap" class="pdfv-pages" />
    </div>
  </div>
</template>

<style scoped>
.pdfv {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: var(--panel2);
}
/* 工具栏：吸顶，滚页时始终可见 —— 这是原生 iframe 给不了的 */
.pdfv-bar {
  flex: none;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
  font-size: var(--fs-xs);
  color: var(--mu);
}
.pb {
  min-width: 26px;
  height: 24px;
  padding: 0 6px;
  font-size: 14px;
  color: var(--mu);
  background: none;
  border: 1px solid transparent;
  border-radius: 5px;
  cursor: pointer;
}
.pb:hover {
  color: var(--ac);
  border-color: var(--ac-dim);
  background: var(--ac-glow);
}
.pb:disabled {
  opacity: 0.35;
  cursor: default;
}
.sep {
  width: 1px;
  height: 16px;
  background: var(--line);
}
.grow {
  flex: 1;
}
.pg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-variant-numeric: tabular-nums;
}
.pg-in {
  width: 46px;
  padding: 3px 6px;
  text-align: center;
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
  color: var(--tx);
  background: var(--panel2);
  border: 1px solid var(--line2);
  border-radius: 5px;
  outline: none;
}
.pg-in:focus {
  border-color: var(--ac);
}
.zoom {
  min-width: 38px;
  text-align: center;
}

.pdfv-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  /* 纵向留白尽量小：每边 16px 在 800px 高的窗口里就是 4% 的正文没了。 */
  padding: 10px;
  outline: none;
}
.pdfv-pages {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  min-height: 100%;
}
.pdf-page-box {
  position: relative;
  display: flex;
  justify-content: center;
}
.pdf-page {
  display: block;
  border-radius: 3px;
  /* 白底 + 轻投影：PDF 页面本身是白的，深色主题下不给白底
     会像一块悬空的透明板。 */
  background: #fff;
  box-shadow: 0 2px 14px -4px rgba(30, 25, 18, 0.45);
}
.pdf-page-no {
  position: absolute;
  right: 6px;
  bottom: -2px;
  font-size: 10px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}
</style>