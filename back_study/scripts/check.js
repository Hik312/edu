// 全量校验：卡片数据 → 网页内联脚本 → Python 编译 → 后端 API 冒烟。
//
// 目录约定（本文件在 back_study/scripts/ 下）：
//   ROOT = study/            BACK = study/back_study/   后端
//   WEB  = study/web/        前端工程根（Vite）
//   DATA = study/data/       共用卡片数据
//
// （MINI = study/minprogram/ 微信小程序 —— 2026-09-26 整端移除，相关检查已删）
//
// web/ 从「单文件 index.html」改成了 Vite 工程：
//   web/index.html      → Vite 入口（<div id="app"> + 内联 SW 清理脚本 + module script）
//   web/dist/           → 构建产物（npm run build）
// 校验内联脚本时读 index.html —— 它里面那段 Service Worker 清理脚本是要保证语法的。
// 读出 0 个 <script> 的话校验会「静默通过」而不是报错，所以下面先打出匹配数。
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const BACK = path.join(ROOT, 'back_study');
const WEB = path.join(ROOT, 'web');
const DIST = path.join(WEB, 'dist');
const DATA = path.join(ROOT, 'data');

const html = fs.readFileSync(path.join(WEB, 'index.html'), 'utf8');

const blocks = [...html.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
blocks.forEach((b, i) => {
  try { new Function(b); console.log('inline script #' + i + ' OK, lines=' + b.split('\n').length); }
  catch (e) { console.log('inline script #' + i + ' SYNTAX ERROR: ' + e.message); }
});

// 加载 data/ 下所有卡片文件（与 Python 后端 load_source_cards 的口径一致），
// 否则新增的 AI 工程等科目的卡不会进校验，related 指向也会被误判为「卡不存在」。
const DATA_DIR = DATA;
const cards = [];
fs.readdirSync(DATA_DIR).forEach(function (f) {
  if (!f.endsWith('.js') || f === 'catalog.js') return;
  try {
    const mod = require(path.join(DATA_DIR, f));
    if (Array.isArray(mod)) cards.push.apply(cards, mod);
  } catch (e) {
    console.log('LOAD FAIL ' + f + ': ' + e.message);
  }
});
console.log('cards loaded: ' + cards.length + ' (from data/*.js)');

let bad = 0;
cards.forEach(c => {
  ['id', 'domain', 'category', 'subject', 'topicPath', 'title', 'oneLine', 'analogy', 'mechanism', 'scene', 'interviewQ', 'keywords'].forEach(k => {
    if (!c[k]) { console.log('MISSING field ' + k + ' -> ' + c.id); bad++; }
  });
  if (c.scene && c.scene.length < 2) { console.log('SCENE too thin -> ' + c.id); bad++; }
  const d = c.diagram;
  if (!d) return;
  if (d.kind === 'pipeline') {
    d.frames.forEach((f, i) => {
      if (f.s < 0 || f.s >= d.stages.length) { console.log('BAD stage index ' + c.id + ' frame ' + i + ' s=' + f.s); bad++; }
    });
  } else if (d.kind === 'state-machine') {
    const ids = d.nodes.map(n => n.id);
    d.edges.forEach(e => {
      if (ids.indexOf(e.from) < 0 || ids.indexOf(e.to) < 0) { console.log('BAD edge ' + c.id + ' ' + e.from + '->' + e.to); bad++; }
    });
    d.frames.forEach((f, i) => {
      if (ids.indexOf(f.n) < 0) { console.log('BAD frame node ' + c.id + ' frame ' + i + ' n=' + f.n); bad++; }
    });
  } else if (d.kind === 'snapshot') {
    d.frames.forEach((f, i) => {
      (f.active || []).forEach(a => {
        if (a < 0 || a >= d.panels.length) { console.log('BAD panel active ' + c.id + ' frame ' + i + ' a=' + a); bad++; }
      });
    });
  } else {
    console.log('UNSUPPORTED kind: ' + d.kind + ' -> ' + c.id); bad++;
  }
  if (!d.frames || !d.frames.length) { console.log('EMPTY frames ' + c.id); bad++; }
});
// 分类必须在 CATALOG 里登记过，否则导航里根本选不到这张卡
const CATALOG = require(path.join(DATA, 'catalog.js'));
const catMap = {};
CATALOG.forEach(g => { catMap[g.id] = (g.subjects || []).map(s => s.id); });
cards.forEach(c => {
  if (!catMap[c.category]) {
    console.log('BAD category -> ' + c.id + ' = ' + c.category); bad++;
  } else if (catMap[c.category].indexOf(c.subject) < 0) {
    console.log('BAD subject -> ' + c.id + ' = ' + c.subject + '（领域 ' + c.category + ' 下没有这个科目）'); bad++;
  }
});
console.log('catalog: ' + CATALOG.map(g => g.name + '(' + g.subjects.length + '科)').join(' · '));

// 关联卡片：related 里的 id 必须真实存在，kind 只能是这三种，note 必须写清「为什么连」。
// 不写理由的链接迟早退化成关键词乱连，图谱就成了毛线球
const REL_KINDS = ['prereq', 'extends', 'compare'];
const idSet = new Set(cards.map(c => c.id));
let relCount = 0;
cards.forEach(c => {
  (c.related || []).forEach(r => {
    relCount++;
    if (!idSet.has(r.id)) {
      console.log('BAD related target -> ' + c.id + ' -> ' + r.id + '（这张卡不存在）'); bad++;
    }
    if (r.id === c.id) { console.log('SELF related -> ' + c.id); bad++; }
    if (REL_KINDS.indexOf(r.kind) < 0) {
      console.log('BAD related kind -> ' + c.id + ' -> ' + r.kind +
        '（只允许 ' + REL_KINDS.join(' / ') + '）'); bad++;
    }
    if (!r.note || !r.note.trim()) {
      console.log('EMPTY related note -> ' + c.id + ' -> ' + r.id + '（要写清为什么连）'); bad++;
    }
  });
});
const relKindCnt = {};
cards.forEach(c => (c.related || []).forEach(r => {
  relKindCnt[r.kind] = (relKindCnt[r.kind] || 0) + 1;
}));
console.log('related: ' + relCount + ' 条 ' + JSON.stringify(relKindCnt) +
  '（' + cards.filter(c => (c.related || []).length).length + '/' + cards.length + ' 张有）');
const noRel = cards.filter(c => !(c.related || []).length).map(c => c.id);
if (noRel.length) console.log('WARN 没有关联的卡片: ' + noRel.join(', '));

console.log(bad === 0 ? 'ALL CHECKS PASSED' : 'ISSUES FOUND: ' + bad);

const kinds = {};
cards.forEach(c => { if (c.diagram) kinds[c.diagram.kind] = (kinds[c.diagram.kind] || 0) + 1; });
console.log('diagram kinds: ' + JSON.stringify(kinds));

// （小程序端 minprogram/ 已于 2026-09-26 整体移除 ——
//  这里的 JS 语法 / app.json / WXML 检查一并删掉。三端只剩网页端。）

// 网页端。目录结构改过（单文件 index.html → Vite 工程），这里要跟着改：
//   web/index.html          Vite 入口（<div id="app"> + 内联脚本 + module script）
//   web/public/*            PWA 资源（源，构建时被原样复制进 dist/）
// 少一个都说明结构被谁动过，而这类问题在线上通常表现为「打开白屏」。
const webFiles = [
  'index.html',
  'public/manifest.json',
  'public/sw.js',
  'public/icons/icon-192.png',
  'public/icons/icon-512.png'
];
// 结构检查的失败计数（原来叫 mpBad，小程序端移除后改名）
let structBad = 0;
webFiles.forEach(function (f) {
  if (!fs.existsSync(path.join(WEB, f))) { console.log('WEB MISSING ' + f); structBad++; }
});
// 构建产物是可选的（跑过 npm run build 才有）。没构建不算错，只提示一声，
// 免得没装 node 的机器上跑 check 一直报红。
if (!fs.existsSync(path.join(DIST, 'index.html'))) {
  console.log('WEB note   web/dist 未构建（cd web && npm run build），跳过产物检查');
}

// 共用卡片数据：网页端读这一份，缺了就是空平台
['catalog.js', 'springboot.js', 'aizhuan.js'].forEach(function (f) {
  if (!fs.existsSync(path.join(DATA, f))) { console.log('DATA MISSING ' + f); structBad++; }
});

console.log(structBad === 0 ? 'ALL CHECKS PASSED' : 'ISSUES FOUND: ' + structBad);

// ---------- Python 后端文件 ----------
// ⚠️ 这份清单以前漏了 6 个文件（security.py / deps.py / auth.py / 整个 core/store/），
// 也就是说**鉴权那几个文件一直没进编译检查**。2026-09-26 补齐。
// 教训：清单靠手维护就会漏 —— 加新 py 文件后记得回来看一眼，
// 或者干脆改成 glob 扫 back_study/ 下所有 .py（排除 .venv 和 scripts）。
const pyFiles = [
  // 入口（零依赖版 server.py 已于 2026-09-26 移除，只剩 FastAPI 这一条线）
  'back_study/run.py',
  // 核心模块（数据层 / 导入 / 大模型 / 网络探测 / 鉴权 / 文件解析）
  'back_study/core/db.py', 'back_study/core/importer.py',
  'back_study/core/llm.py', 'back_study/core/netinfo.py',
  'back_study/core/security.py', 'back_study/core/docparse.py',
  // 存储层：base 是契约，jsonfile / mysql 是两套实现
  'back_study/core/store/__init__.py', 'back_study/core/store/base.py',
  'back_study/core/store/jsonfile.py', 'back_study/core/store/mysql.py',
  // FastAPI 包
  'back_study/app/__init__.py', 'back_study/app/config.py',
  'back_study/app/deps.py', 'back_study/app/schemas.py',
  'back_study/app/main.py',
  'back_study/app/routers/__init__.py', 'back_study/app/routers/auth.py',
  'back_study/app/routers/system.py', 'back_study/app/routers/cards.py',
  'back_study/app/routers/learning.py', 'back_study/app/routers/notes.py',
  'back_study/app/routers/imports.py', 'back_study/app/routers/docs.py',
  'back_study/app/routers/ai.py',
  // AI Agent 路由（可选依赖，函数内延迟 import agent 包）
  'back_study/app/routers/agent.py',
  // AI Agent 层（LangGraph + 本地 Ollama，可选依赖，2026-09-29 加）
  // 分层：config 参数 / model 模型 / tools 工具 / nodes 节点 / graph 编排 /
  //       runtime 执行 / demo 命令行
  // 公共层（所有 Agent 共用）
  'back_study/agent/__init__.py', 'back_study/agent/config.py',
  'back_study/agent/model.py',
  // 业务层 · 问答（已跑通）
  'back_study/agent/qa/__init__.py', 'back_study/agent/qa/tools.py',
  'back_study/agent/qa/nodes.py', 'back_study/agent/qa/graph.py',
  'back_study/agent/qa/runtime.py', 'back_study/agent/qa/demo.py',
  // 业务层 · 问答检索（混合检索：向量为主+关键词兜底，2026-09-29 加）
  'back_study/agent/qa/retrieval.py',
  // 业务层 · 路径规划（write 节点待填）
  'back_study/agent/planner/__init__.py', 'back_study/agent/planner/planner.py',
  'back_study/agent/planner/run.py',
  // 业务层 · 文档转卡（structure 结构精修 + chapter 逐章出卡，2026-10-01 加）
  'back_study/agent/cards/__init__.py', 'back_study/agent/cards/nodes.py',
  'back_study/agent/cards/graph.py', 'back_study/agent/cards/runtime.py',
  // 脚本 · 大纲批量造卡（按 catalog 让本地 Ollama 生成卡片，2026-09-29 加）
  'back_study/scripts/gen_cards.py',
  // 脚本 · 文档批量摄取（data/docs 下 md/pdf 走 parse_document→enrich→to_card→草稿，2026-09-29 加）
  'back_study/scripts/gen_docs.py',
  // 算法层（间隔重复 / 知识追踪，2026-09-29 加，零依赖叶子包）
  // 分层：base 契约 / sm2 + fsrs 实现 / __init__ 注册表 / demo 对拍台
  'back_study/algo/__init__.py', 'back_study/algo/base.py',
  'back_study/algo/sm2.py', 'back_study/algo/fsrs.py',
  'back_study/algo/bkt.py', 'back_study/algo/demo.py',
  // 缓存层（Redis 优先 / 内存降级，2026-09-29 加）
  'back_study/core/cache.py',
  // 算法库（事件流 / 掌握度 / 参数，2026-09-29 加）与业务库 store/ 分开
  // 分层：base 契约 / jsonfile 默认+降级 / pg 已启用 / __init__ 工厂
  'back_study/core/algostore/__init__.py', 'back_study/core/algostore/base.py',
  'back_study/core/algostore/jsonfile.py', 'back_study/core/algostore/pg.py'
];
let pyBad = 0;
pyFiles.forEach(function (f) {
  const p = path.join(ROOT, f);
  if (!fs.existsSync(p)) { console.log('PY MISSING ' + f); pyBad++; return; }
});
console.log(pyBad === 0 ? 'python files present: ' + pyFiles.length : 'PY ISSUES: ' + pyBad);

// ---------- 后端 API 冒烟：起临时 Python 服务 → 打接口 → 关掉 ----------
const { spawn, spawnSync } = require('child_process');

function pickPython() {
  const cands = [
    process.env.PY,
    // 项目自己的 .venv 最优先：版本和依赖都随仓库走，换机器结论不会漂
    path.join(BACK, '.venv', 'Scripts', 'python.exe'),
    'python', 'python3',
    'C:/Users/wangh/.workbuddy/binaries/python/versions/3.13.12/python.exe'
  ].filter(Boolean);
  for (const c of cands) {
    try {
      const r = spawnSync(c, ['--version'], { stdio: 'ignore' });
      if (!r.error && r.status === 0) return c;
    } catch (e) {}
  }
  return null;
}

// Python 编译检查
const PYCHECK = (function () {
  const py = pickPython();
  if (!py) return null;
  let bad = 0;
  pyFiles.forEach(function (f) {                 // 真正编译一遍，比肉眼看靠谱
    const r = spawnSync(py, ['-m', 'py_compile', path.join(ROOT, f)], { stdio: 'ignore' });
    console.log((r.status === 0 ? 'PY OK    ' : 'PY FAIL  ') + f);
    if (r.status !== 0) bad++;
  });

  // ---- 未用 import / 未定义名（pyflakes）----
  //
  // py_compile 只看语法，查不出「import 了但没用」这类死代码 —— 也不会查出
  // 反过来那种更危险的：**删掉一个看似没用的 import 之后才暴露的 NameError**。
  //
  // ⚠️ 这一步**故意只提示、不计入失败**。原因是 pyflakes 会把
  // 「本模块没用到、但转手导出给别人用的 import」报成 "imported but unused"：
  // 2026-09-26 就是照它删了 app/config.py 的 DATA_DIR，py_compile 全绿、
  // 这一步之外的检查全过，一直到真起服务才 ImportError（main.py 从 config 取不到）。
  // 所以：**看到这里的提示先 grep 一遍跨模块引用，确认没人用再删。**
  // 做成硬门禁的话，等于逼着下一个人把再导出删掉。
  const pf = spawnSync(py, ['-m', 'pyflakes',
                            'back_study/core', 'back_study/app',
                            'back_study/scripts', 'back_study/run.py'],
                       { cwd: ROOT, encoding: 'utf8' });
  // ★ 两种失败必须分开报，别混成一句「没装 pyflakes」。
  // `pf.error` 是**起不了进程**（EPERM / ENOENT / 超时），跟「没装包」完全是
  // 两回事。从前它们并成一个分支，于是沙箱里跑（子进程创建被拒）时会打印
  // 「跳过（没装 pyflakes：pip install pyflakes）」—— 而 pyflakes 其实是装着的
  // （实测 .venv 里 4.0.0）。人被这句话指向「去装包」，永远查不到真正的原因。
  // 另外 stdio 被管道接走时 pf.stderr 是 null，`|| ''` 又把失败信息吞掉，
  // 连是哪一步失败的都看不出来。
  const pfErr = pf.error ? String(pf.error.message || pf.error) : '';
  const pfNoMod = /No module named pyflakes/.test(pf.stderr || '');
  if (pf.error) {
    console.log('PY LINT  起不了子进程，跳过（' + pfErr + '）');
    console.log('         这不是「没装 pyflakes」，是进程创建被环境拒绝了');
  } else if (pfNoMod) {
    console.log('PY LINT  跳过（这个解释器里没有 pyflakes：'
                + py + ' -m pip install pyflakes）');
  } else {
    const hits = (pf.stdout || '').trim().split('\n').filter(Boolean);
    if (!hits.length) console.log('PY LINT  clean');
    else {
      console.log('PY LINT  ' + hits.length + ' 条提示（不判失败，先 grep 引用点再动手）：');
      hits.forEach(function (h) { console.log('   ' + h); });
    }
  }
  return { py: py, bad: bad };
})();

// 找一个装齐了后端依赖的 Python。
// 零依赖版 server.py 移除之后，**没有 fastapi + uvicorn + PyJWT 就跑不起来冒烟** ——
// 所以探测条件里必须带上 jwt：只查 fastapi 的话，缺 PyJWT 时会起服务失败，
// 报错是 500 而不是「少装了包」，排查方向会跑偏。
function pickFastPython() {
  const cands = [
    process.env.PYFAST,
    path.join(BACK, '.venv', 'Scripts', 'python.exe'),
    'C:/Users/wangh/.workbuddy/binaries/python/envs/default/Scripts/python.exe',
    process.env.PY,
    'python', 'python3'
  ].filter(Boolean);
  for (const c of cands) {
    try {
      const r = spawnSync(c, ['-c', 'import fastapi, uvicorn, jwt'], { stdio: 'ignore' });
      if (!r.error && r.status === 0) return c;
    } catch (e) {}
  }
  return null;
}

// 同一套用例跑一遍，返回失败条数。
// 只有 FastAPI 一个实现 —— 零依赖版 server.py 已于 2026-09-26 移除。
async function smoke(py) {
  console.log('');
  console.log('---- API 冒烟 ----');
  let bad2 = 0;
  const port = 8600 + Math.floor(Math.random() * 200);
  const entry = path.join(BACK, 'run.py');
  const srv = spawn(py, [entry, String(port)], {
    cwd: BACK, stdio: ['ignore', 'pipe', 'pipe']
  });
  let out = '';
  srv.stdout.on('data', d => { out += d; });
  srv.stderr.on('data', d => { out += d; });
  const B = 'http://127.0.0.1:' + port;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  //: 登录后填上，之后所有请求默认带它。声明必须在 call 之前 ——
  //: `let` 有暂时性死区，放在 call 之后会在调用时直接 ReferenceError。
  let authToken = '';
  // ★ 默认带上 token。个人数据端点（notes / progress / docs / cards / drafts /
  // llm / outline / graph / plan …）现在全部要求登录了，不带就是一片 401。
  // 顺序上没问题：下面认证那一组会**先**把 authToken 填上，之后才跑其它用例。
  // 要显式测「没带 token 会怎样」的用例传 `auth: false`。
  const call = async (u, opt) => {
    const o = Object.assign({}, opt);
    const withAuth = o.auth;
    delete o.auth;
    if (authToken && withAuth !== false) {
      o.headers = Object.assign({ Authorization: 'Bearer ' + authToken },
                                o.headers || {});
    }
    const r = await fetch(B + u, o);
    // headers 一起返回：图片端点要看 content-type（FileResponse），其余用不到
    return { code: r.status, body: await r.json().catch(() => null), headers: r.headers };
  };
  let up = false;
  // ★ 等待窗口必须够长。原先是 40 × 150ms ≈ 6 秒，而本机冷启动实测要
  // **18 秒**（Python 导入 + MySQL/PG 连接 + 建表探测 + 67 张卡入内存）。
  // 结果是服务明明起来了，却打印「API FAIL 服务没起来」── 后面紧跟的
  // 启动横幅和 8639 端口都证明它活着。假失败比没有检查更糟：
  // 人会去查一个不存在的问题。改成 120 × 500ms = 60 秒。
  const READY_TRIES = 120;
  const READY_GAP = 500;
  for (let i = 0; i < READY_TRIES; i++) {
    try { const r = await call('/api/health'); if (r.body && r.body.ok) { up = true; break; } } catch (e) {}
    await wait(READY_GAP);
  }
  if (!up) {
    console.log('API FAIL 服务在 ' + (READY_TRIES * READY_GAP / 1000)
                + ' 秒内没起来\n' + out);
    srv.kill(); process.exitCode = 1;
    return 1;                    // 必须返回数字：返回 undefined 会让累加变成 NaN，
  }                              // 而 NaN 是 falsy —— 失败的运行会被当成通过
  const t = async (name, fn) => {
    try { const r = await fn(); console.log((r ? 'API OK   ' : 'API FAIL ') + name); if (!r) bad2++; }
    catch (e) { console.log('API ERR  ' + name + ': ' + e.message); bad2++; }
  };
  const TEST_ID = 'zz-check-probe';
  let docsTestId = null;

  await t('health 且实现标识正确', async () => {
    const b = (await call('/api/health')).body;
    // 零依赖版移除后只有 fastapi 这一个实现，这里写死而不是传参进来比
    return b.ok === true && b.lang === 'python' && b.framework === 'fastapi';
  });
  await t('health 带 store 字段（json / mysql）', async () => {
    const b = (await call('/api/health')).body;
    return b.store === 'json' || b.store === 'mysql';
  });

  // ---------- 认证 ----------
  // 这一组校验的是**状态码语义**，必须逐字一致：
  //   401 = 没登录 / token 失效 → 前端清 token 跳登录页
  //   400 = 凭据不对 / 参数不合法 → 就地弹提示
  // 要是哪一版把「密码错」实现成 401，表现就是「在登录页上输错密码，
  // 页面刷新一下提示登录已过期」，人会觉得页面坏了。
  //
  // 账号固定用 zz_check_probe（**下划线，不能写连字符** —— 用户名规则是
  // 3-20 位字母/数字/下划线，带连字符会被 400 拦下，看起来像后端坏了）。
  // 幂等：已存在就改走登录，空库和有数据的库上都能跑，名字一眼看得出是测试。
  const AUTH_USER = 'zz_check_probe';
  const AUTH_PASS = 'zz_check_123456';
  const authHeaders = (tk) => ({ Authorization: 'Bearer ' + tk });
  const post = (u, obj) => call(u, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(obj || {})
  });
  // 注意：`let authToken` 已经在上面（call 的定义之前）声明过了，
  // 这里**不能**再声明一次 —— 重复 let 是 SyntaxError；
  // 而把它只放这里又会踩 call 里的暂时性死区（ReferenceError）。
  // 所以声明上移，这里直接赋值。

  await t('注册：用户名不合法 → 400', async () => {
    const r = await post('/api/auth/register', { username: 'a', password: AUTH_PASS });
    return r.code === 400 && r.body && r.body.ok === false;
  });
  await t('注册：密码太短 → 400', async () => {
    // 用户名要合法，否则会被用户名规则先拦下，测不到密码这条
    const r = await post('/api/auth/register', { username: 'zz_probe_pw', password: '123' });
    return r.code === 400 && r.body && r.body.ok === false;
  });
  await t('注册/登录后 user.id 是真实数字（不是 null）', async () => {
    // 这条断言来自一个真踩过的坑：JSON 后端的 user_put 忘了分配 id，
    // 签出来的 token 里 sub 是字符串 "None"，表现是「注册看着成功、
    // 一刷新就掉登录」，日志里一点错都没有。
    let r = await post('/api/auth/register', { username: AUTH_USER, password: AUTH_PASS });
    if (r.code === 400) {
      r = await post('/api/auth/login', { username: AUTH_USER, password: AUTH_PASS });
    }
    if (!r.body || !r.body.token || !r.body.user) return false;
    authToken = r.body.token;
    return r.body.user.id !== null && r.body.user.id !== undefined && r.body.user.id !== '';
  });
  await t('认证接口不回传 passwordHash', async () => {
    const r = await call('/api/auth/me', { headers: authHeaders(authToken) });
    const raw = JSON.stringify(r.body);
    return raw.indexOf('passwordHash') === -1 && raw.indexOf('pbkdf2') === -1;
  });
  await t('auth/me 无 token → 401', async () => {
    // auth:false = 这一次**故意不带** Authorization（call 默认会补上）
    return (await call('/api/auth/me', { auth: false })).code === 401;
  });
  await t('auth/me 伪造签名的 token → 401', async () => {
    const fake = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
               + '.eyJzdWIiOiIxIiwiZXhwIjo5OTk5OTk5OTk5fQ'
               + '.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
    return (await call('/api/auth/me', { headers: authHeaders(fake) })).code === 401;
  });
  await t('auth/me 带有效 token → 拿到同一个用户', async () => {
    const r = await call('/api/auth/me', { headers: authHeaders(authToken) });
    return r.code === 200 && r.body.user.username === AUTH_USER;
  });
  await t('密码错 → 400（不是 401，否则前端会当成掉线）', async () => {
    const r = await post('/api/auth/login', { username: AUTH_USER, password: 'zz-wrong-pass' });
    return r.code === 400;
  });
  await t('用户不存在与密码错话术完全相同（防用户名枚举）', async () => {
    const a = await post('/api/auth/login', { username: AUTH_USER, password: 'zz-wrong-pass' });
    const b = await post('/api/auth/login', { username: 'zz-no-such-user', password: 'zz-wrong-pass' });
    return a.code === b.code && a.body.msg === b.body.msg;
  });
  await t('用户列表：按角色返回 200 / 403', async () => {
    const me = (await call('/api/auth/me', { headers: authHeaders(authToken) })).body.user;
    const r = await call('/api/auth/users', { headers: authHeaders(authToken) });
    if (me.role === 'admin') return r.code === 200 && Array.isArray(r.body.users);
    return r.code === 403;
  });

  await t('storage 端点与 health 口径一致', async () => {
    const h = (await call('/api/health')).body;
    const s = (await call('/api/storage')).body.storage;
    if (!s) return false;
    if (s.store !== h.store) return false;
    // 内置卡条数必须和接口真正在用的那批卡对得上，否则说明
    // 「库里有一份、接口读的是另一份」，那是最难查的一类不一致
    if (s.builtin.inFile !== cards.length) return false;
    if (h.store === 'mysql') {
      // 用了 mysql 就必须真的用了：要么指纹一致，要么明确报 stale
      return s.builtin.stale === false || typeof s.builtin.stale === 'boolean';
    }
    return s.builtin.inDb === null;
  });
  await t('没有静默降级到其他存储', async () => {
    // 配置说要用 mysql 就必须是 mysql —— 除非 degraded 里写清了为什么
    // 回退。悄悄回退是最坏的情况：用户以为在用数据库，其实写进 JSON 了。
    const s = (await call('/api/storage')).body.storage;
    if (s.want !== 'mysql') return true;          // 本来就想用文件，没事
    return s.store === 'mysql' || !!s.degraded;
  });

  // ---------- 前端产物（没构建过就跳过，不算失败）----------
  // SPA 回落是很容易被改坏又不容易发现的一处：本地开发用 Vite dev server，
  // /cards 由 dev server 自己兜底，一切正常；一上线换成后端挂 dist，
  // 刷新 /cards 就 404 白屏 —— 而且开发时永远复现不了。
  if (fs.existsSync(path.join(DIST, 'index.html'))) {
    await t('前端产物：/ 返回 Vue 入口', async () => {
      const r = await fetch(B + '/');
      const ct = r.headers.get('content-type') || '';
      const h = await r.text();
      return r.status === 200 && ct.includes('text/html') && h.includes('id="app"');
    });
    await t('前端产物：深层路由回落 index.html（history 模式）', async () => {
      const r = await fetch(B + '/cards');
      const h = await r.text();
      return r.status === 200 && h.includes('id="app"');
    });
    await t('前端产物：缺失的 .js 保持 404（不回落成 HTML）', async () => {
      // 回落成 HTML 的话浏览器会把它当 JS 解析，报的错跟真正原因没关系
      return (await fetch(B + '/assets/zz-definitely-missing.js')).status === 404;
    });
    await t('前端产物：/api 下的未知路径是 JSON 404，不是 HTML', async () => {
      const r = await fetch(B + '/api/zz-no-such-endpoint');
      const ct = r.headers.get('content-type') || '';
      return r.status === 404 && ct.includes('json');
    });
  } else {
    console.log('API SKIP 前端产物未构建，跳过 SPA 回落检查（cd web && npm run build）');
  }
  await t('复习队列排序：不会 → 模糊 → 未标记 → 会', async () => {
    // 排序规则是两套实现必须一致的地方（MySQL 走 SQL 的 ORDER BY，
    // 文件后端走 Python 的 sort），所以这里断言的是**规则本身**。
    // 两套实现互相对照在下面的「存储后端一致性」里单独跑。
    const q = (await call('/api/review/due?all=1&limit=500')).body.queue;
    if (!q.length) return false;
    const rank = { 1: 0, 2: 1, 0: 2, 3: 3 };
    for (let i = 1; i < q.length; i++) {
      if (rank[q[i - 1].level] > rank[q[i].level]) {
        console.log('       队列乱序: ' + q[i - 1].id + '(lv' + q[i - 1].level
          + ') 排在 ' + q[i].id + '(lv' + q[i].level + ') 前面');
        return false;
      }
    }
    return true;
  });
  await t('cards 数量与数据文件一致', async () => {
    const r = await call('/api/cards');
    return r.body.total === cards.length;
  });
  await t('cards 搜索命中', async () => {
    const r = await call('/api/cards?q=' + encodeURIComponent('事务'));
    return r.body.total > 0;
  });
  await t('stats 字段完整', async () => {
    const s = (await call('/api/stats')).body.stats;
    return s && typeof s.total === 'number' && typeof s.dueToday === 'number';
  });
  // ★ 标记进度**必须带 token**：复习事件要记到具体的人头上，端点加了登录要求。
  //   这里不带 token 的话会拿到 401，而 401 和「业务拒绝」长得不一样 ——
  //   校验脚本看不出差别，会把「没登录」当成「接口坏了」。
  const PH = Object.assign({ 'Content-Type': 'application/json' }, authHeaders(authToken));
  await call('/api/progress/' + TEST_ID, { method: 'DELETE', headers: PH });   // 先清干净，别让上次残留影响间隔计算
  await t('标记 level=2 返回下次复习日期', async () => {
    const r = await call('/api/progress/' + TEST_ID, {
      method: 'PUT', headers: PH, body: JSON.stringify({ level: 2 })
    });
    return r.code === 200 && !!r.body.progress.nextAt;
  });
  await t('连续标记「会」间隔递增', async () => {
    const a = await call('/api/progress/' + TEST_ID, { method: 'PUT', headers: PH, body: JSON.stringify({ level: 3 }) });
    const b = await call('/api/progress/' + TEST_ID, { method: 'PUT', headers: PH, body: JSON.stringify({ level: 3 }) });
    const c = await call('/api/progress/' + TEST_ID, { method: 'PUT', headers: PH, body: JSON.stringify({ level: 3 }) });
    return c.body.progress.interval > a.body.progress.interval && c.body.progress.reps === 3;
  });
  await t('非法 level 被拒', async () => {
    const r = await call('/api/progress/' + TEST_ID, { method: 'PUT', headers: PH, body: JSON.stringify({ level: 9 }) });
    return r.code === 400;
  });
  await t('未登录标记进度 → 401（事件不能记到无名氏头上）', async () => {
    // auth:false = 故意不带 Authorization（call 现在默认会补上 token）
    const r = await call('/api/progress/' + TEST_ID, {
      auth: false,
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ level: 3 })
    });
    return r.code === 401;
  });
  await t('复习事件流按人隔离且严格有序', async () => {
    const r = await call('/api/review/events?limit=50', { headers: PH });
    const ev = (r.body && r.body.events) || [];
    if (r.code !== 200 || ev.length < 3) return false;
    // 时序必须单调：同一天连标多次时，顺序乱了 BKT 回放就是错的
    for (let i = 1; i < ev.length; i++) {
      const pa = String(ev[i - 1].at), pb = String(ev[i].at);
      if (pb < pa) return false;
      if (pb === pa && Number(ev[i].id) <= Number(ev[i - 1].id)) return false;
    }
    return ev.every((e) => e.user_id !== undefined && e.correct !== undefined);
  });
  await t('复习队列返回', async () => (await call('/api/review/due?limit=5')).body.queue.length > 0);
  await t('分类树可读取', async () => {
    const r = await call('/api/catalog');
    return r.body.catalog && r.body.catalog.length >= 2;
  });
  await t('学习方向目录可读取', async () => {
    const r = await call('/api/directions');
    const ds = r.body.directions || [];
    // count 允许是 0（先建方向、后补卡），但字段不能缺 —— chips 上要显示它
    return ds.length >= 12 && ds.every(d => d.id && d.name && typeof d.count === 'number');
  });
  await t('队列按方向过滤', async () => {
    const all = await call('/api/review/due?limit=500');
    const one = await call('/api/review/due?limit=500&dirs=agent');
    const unk = await call('/api/review/due?limit=500&dirs=zz-no-such-dir');
    const ids = new Set(all.body.queue.map(x => x.id));
    const oneIds = one.body.queue.map(x => x.id);
    // 两个方向性断言：方向卡必须是全队列的子集（没混进别的东西），
    // 以及**未知方向不能把队列筛成空** —— 否则档案里 id 写错就再也学不到卡，
    // 而页面只会显示「今天没有到期的卡」，看不出是自己配错了。
    return oneIds.length > 0 && oneIds.every(id => ids.has(id)) &&
      unk.body.queue.length === all.body.queue.length;
  });
  await t('按科目过滤卡片', async () => {
    // a：合法且已铺满的 combo，必须返回卡片
    const a = await call('/api/cards?category=work&subject=java&brief=1');
    // b：跨科目的非法 combo（java 不归 kaoyan 管），过滤后必须为空。
    // 注意：gen_cards.py 已把 8 个科目全部铺满，不能再靠「某科目没卡」来测空，
    // 改用跨科目非法组合验证过滤器确实在收窄，而非返回全量。
    const b = await call('/api/cards?category=kaoyan&subject=java&brief=1');
    return a.body.total > 0 && b.body.total === 0;
  });
  await t('笔记新建 / 修改 / 删除', async () => {
    const c = await call('/api/notes', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '校验用笔记', body: '正文', category: 'work', subject: 'java' }) });
    const id = c.body.note.id;
    const u = await call('/api/notes/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '校验用笔记2', body: '正文2', category: 'work', subject: 'java' }) });
    const g = await call('/api/notes?category=work');
    await call('/api/notes/' + id, { method: 'DELETE' });
    return u.body.note.title === '校验用笔记2' && g.body.total >= 1;
  });
  await t('空笔记被拒', async () => {
    const r = await call('/api/notes', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '', body: '' }) });
    return r.code === 400;
  });
  await t('草稿可编辑后入库', async () => {
    const imp = await call('/api/import', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: '# 校验标题\n一句话说明\n1. 第一步\n2. 第二步', category: 'work', subject: 'java', domain: '工作' }) });
    const d = imp.body.drafts[0];
    const put = await call('/api/drafts/' + d.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene: ['场景一：具体系统里的用法', '场景二：踩过的坑'], keywords: ['校验'] }) });
    const pub = await call('/api/drafts/publish', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: d.id }) });
    if (pub.body.ok) {                       // 入库成功就顺手删掉，别留脏数据
      await call('/api/cards/' + d.id, { method: 'DELETE' });
    } else {
      await call('/api/drafts/' + d.id, { method: 'DELETE' });
    }
    return put.code === 200 && pub.body.ok === true;
  });
  await t('导入切分出草稿', async () => {
    const r = await call('/api/import', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: '# 测试标题\n一句话说明。\n1. 第一步\n2. 第二步\n3. 第三步', domain: '测试' })
    });
    return r.body.count >= 1 && !!r.body.drafts[0].id;
  });
  await t('未补全的草稿不允许入库', async () => {
    const d = await call('/api/drafts');
    const id = d.body.drafts[d.body.drafts.length - 1].id;
    const r = await call('/api/drafts/publish', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: id }) });
    await call('/api/drafts/' + id, { method: 'DELETE' });   // 清理测试草稿
    return r.code === 400;                                    // scene 不足 2 条 → 应被拒
  });

  await t('文档导入并按标题自动分章', async () => {
    const md = '# MySQL 八股\n\n## 第一章 索引\n### 1. B+树\n矮胖，IO 少。\n### 2. 回表\n二级索引存主键。\n\n## 第二章 事务\n### 1. ACID\nundo/redo。\n';
    const r = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: md, filename: 't.md', category: 'work', subject: 'java', title: '校验文档' }) });
    if (!r.body || !r.body.ok) return false;
    docsTestId = r.body.doc.id;
    const ch = r.body.doc.chapters;
    return r.body.doc.stats.headings >= 5 && ch.length >= 5 && ch[1].title.indexOf('第一章') >= 0;
  });
  await t('文档 列表 / 详情 / 删除', async () => {
    const l = await call('/api/docs');
    const d = await call('/api/docs/' + docsTestId);
    const del = await call('/api/docs/' + docsTestId, { method: 'DELETE' });
    const after = await call('/api/docs');
    return l.body.total >= 1 && d.body.doc.chapters.length >= 5
      && del.body.ok === true && after.body.total === l.body.total - 1;
  });
  await t('base64 上传按文本解码并分章', async () => {
    const b64 = Buffer.from('# 标题\n\n## 小节一\n正文内容要够长一点。\n## 小节二\n再写一段文字。', 'utf8').toString('base64');
    const r = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: 'a.txt', dataB64: b64, title: 'b64文档' }) });
    if (!r.body || !r.body.ok) return false;
    await call('/api/docs/' + r.body.doc.id, { method: 'DELETE' });
    return r.body.doc.stats.chapters >= 3;
  });
  await t('docx 上传：zip 拆包 → Word 标题转 markdown 分章', async () => {
    // 现场用 python 拼一个最小 docx（zip + word/document.xml），不在 JS 里手写 zip 结构
    const pyCode = `
import io, zipfile, base64, sys
xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
       '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>绪论</w:t></w:r></w:p>'
       '<w:p><w:r><w:t>这一段是正文，写得足够长以便通过导入时的字数校验。</w:t></w:r></w:p>'
       '<w:p><w:pPr><w:outlineLvl w:val="1"/></w:pPr><w:r><w:t>背景知识</w:t></w:r></w:p>'
       '<w:p><w:r><w:t>背景的正文也写得足够长，确保能正常切成章节。</w:t></w:r></w:p>'
       '</w:body></w:document>')
b = io.BytesIO()
with zipfile.ZipFile(b, 'w') as z:
    z.writestr('word/document.xml', xml)
sys.stdout.write(base64.b64encode(b.getvalue()).decode())
`;
    const r0 = spawnSync(py, ['-c', pyCode], { encoding: 'utf8' });
    if (r0.status !== 0 || !r0.stdout) return false;
    const r = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: 'zz-probe.docx', dataB64: r0.stdout.trim() }) });
    if (!r.body || !r.body.ok) return false;
    const ch = r.body.doc.chapters || [];
    const ok = r.body.doc.stats.headings >= 2 && ch.length >= 2
      && ch[0].title.indexOf('绪论') >= 0 && ch[1].title.indexOf('背景') >= 0;
    await call('/api/docs/' + r.body.doc.id, { method: 'DELETE' });
    return ok;
  });
  await t('章节转卡带卡片组（deck / deckId）', async () => {
    // body.ai 显式覆盖：这条测的是「转卡时挂组」这条数据通路，不跑真模型
    const md = '# 组标题\n\n## 一章\n' + '这章的正文要足够长，长到可以被转卡流程接受。'.repeat(3);
    const imp = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: md, title: '卡片组校验文档' }) });
    if (!imp.body || !imp.body.ok) return false;
    const did = imp.body.doc.id;
    const r = await call('/api/llm/to-card', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ docId: did, index: 1,
        ai: { oneLine: '一句话结论', analogy: '像生活里的例子', mechanism: ['① 第一步', '② 第二步'] } }) });
    await call('/api/docs/' + did, { method: 'DELETE' });
    const draft = r.body && r.body.draft;
    if (draft) await call('/api/drafts/' + draft.id, { method: 'DELETE' });   // 清理测试草稿
    return r.code === 200 && draft && draft.deck === '卡片组校验文档' && draft.deckId === did;
  });

  // ---------- 卡片 Agent + 图片链路：只测不碰模型的确定路径 ----------
  // 真模型（结构精修 / 逐章出卡）在 deck_e2e 脚本里跑，不塞进校验 ——
  // 几十秒/章 + 结果不固定，进 check 只会又慢又飘。
  await t('cards Agent 端点：缺参 400 / 文档不存在 404 / 下标越界 400', async () => {
    const a = await post('/api/agent/cards/structure', {});
    const b = await post('/api/agent/cards/structure', { docId: 'zz-none' });
    const md = '# t\n\n## 一章\n' + '这章正文足够长，用来测越界下标在进线程池之前就被拦下来。'.repeat(3);
    const imp = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: md, title: 'agent校验文档' }) });
    if (!imp.body || !imp.body.ok) return false;
    const c = await post('/api/agent/cards/chapter', { docId: imp.body.doc.id, index: 99 });
    await call('/api/docs/' + imp.body.doc.id, { method: 'DELETE' });
    return a.code === 400 && b.code === 404 && c.code === 400;
  });
  await t('parse 端点：缺参 400 / 不存在 404 / 未解析就勾选 400', async () => {
    // 不测存在文档的 POST parse —— 那会真调模型（几十秒 + 结果不固定），
    // 真模型在 e2e 脚本里跑。这里只走 db 查不到 / 没解析过两条快速路径。
    const a = await post('/api/agent/cards/parse', {});
    const b = await post('/api/agent/cards/parse', { docId: 'zz-none' });
    const c = await call('/api/agent/cards/parse', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ docId: 'zz-none', keeps: {} })
    });
    const md = '# t\n\n## 一章\n' + '这章正文足够长，确保导入后有章节可以做勾选保存测试。'.repeat(3);
    const imp = await call('/api/import/doc', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: md, title: 'parse校验文档' })
    });
    if (!imp.body || !imp.body.ok) return false;
    const d = await call('/api/agent/cards/parse', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ docId: imp.body.doc.id, keeps: { '0': true } })
    });
    await call('/api/docs/' + imp.body.doc.id, { method: 'DELETE' });
    return a.code === 400 && b.code === 404 && c.code === 404 && d.code === 400;
  });
  await t('docx 带图：占位符进正文 / 图片可读 / 删文档连图删', async () => {
    // 现场拼一个带 word/media 的最小 docx：标题 + 段落里引用一张 1x1 PNG。
    // a:blip 直接挂在 w:p 下（docparse 按命名空间找 r:embed，不校验 Word 语义）
    const pyCode = `
import io, zipfile, base64, sys
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
       ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
       ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>'
       '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>图示章节</w:t></w:r></w:p>'
       '<w:p><w:r><w:t>这段正文足够长，长到能通过导入时的字数校验，配图就接在后面。</w:t></w:r>'
       '<a:blip r:embed="rId2"/></w:p>'
       '</w:body></w:document>')
rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId2"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"'
        ' Target="media/image1.png"/></Relationships>')
b = io.BytesIO()
with zipfile.ZipFile(b, 'w') as z:
    z.writestr('word/document.xml', xml)
    z.writestr('word/_rels/document.xml.rels', rels)
    z.writestr('word/media/image1.png', PNG)
sys.stdout.write(base64.b64encode(b.getvalue()).decode())
`;
    const r0 = spawnSync(py, ['-c', pyCode], { encoding: 'utf8' });
    if (r0.status !== 0 || !r0.stdout) return false;
    const r = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: 'zz-img.docx', dataB64: r0.stdout.trim() }) });
    if (!r.body || !r.body.ok) return false;
    const did = r.body.doc.id;
    const body0 = ((r.body.doc.chapters || [])[0] || {}).body || '';
    const hasToken = body0.indexOf('![](media:image1.png)') >= 0;
    const img = await call('/api/media/' + did + '/image1.png');
    const noAuth = await call('/api/media/' + did + '/image1.png', { auth: false });
    await call('/api/docs/' + did, { method: 'DELETE' });          // 删文档应连图一起删
    const gone = await call('/api/media/' + did + '/image1.png');
    // 路径穿越：owner 带反斜杠（%5c），SAFE_NAME 挡在 media_path 里
    const traversal = await call('/api/media/zz%5c../a.png');
    const ctype = img.headers ? (img.headers.get('content-type') || '') : '';
    return hasToken && img.code === 200 && ctype.indexOf('image/png') >= 0
      && noAuth.code === 401 && gone.code === 404 && traversal.code === 404;
  });

  // 本地大模型：只测「确定路径」——状态接口、错误分支、以及精读后落盘。
  // 不在这里跑真模型：6 秒/章 + 结果不固定，塞进 CI 只会让校验又慢又飘。
  await t('llm 状态接口返回 provider', async () => {
    const r = await call('/api/llm/status');
    return r.body && (r.body.provider === 'ollama' || r.body.provider === 'cloud');
  });
  await t('llm 精读空章节 / 短正文 拒绝', async () => {
    const r = await call('/api/llm/enrich', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: '太短' }) });
    return r.code === 400 || r.code === 502;
  });
  await t('llm 存卡片：未精读的章要拒绝', async () => {
    const md = '# t\n\n## 一章\n' + '这一章写点够长的正文，用来验证接口而不是模型。'.repeat(3);
    const imp = await call('/api/import/doc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: md, title: 'llm校验文档' }) });
    if (!imp.body || !imp.body.ok) return false;
    const did = imp.body.doc.id;
    const r = await call('/api/llm/to-card', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ docId: did, index: 1 }) });
    await call('/api/docs/' + did, { method: 'DELETE' });
    return r.code === 400;
  });

  await call('/api/progress/' + TEST_ID, { method: 'DELETE', headers: PH });   // 清理测试进度
  console.log(bad2 === 0 ? 'API SMOKE PASSED' : 'API ISSUES: ' + bad2);
  srv.kill();
  srv.kill('SIGKILL');   // uvicorn 有时不吃 SIGTERM
  return bad2;
}

// ---- 存储后端一致性：同一个到期队列，两套存储实现必须给出同一个顺序 ----
// 这是接数据库以后最容易悄悄坏掉的地方：MySQL 走 SQL 的 ORDER BY，
// 文件后端走 Python 的 sort，两份规则的「未标记排哪」一错位，
// 复习队列就会莫名其妙地把新卡甩到最后 —— 而且只有用一种后端时才发现不了。
// 所以这里把同一个服务起两遍（一遍 STORE=json、一遍 STORE=mysql），
// 拿两条队列逐位比。
async function crossStore(py) {
  console.log('');
  console.log('---- 存储后端一致性（json vs mysql）----');
  const port = 8800 + Math.floor(Math.random() * 100);

  /** 幂等登录：先试着登录，账号不存在再注册。返回 token 或 null。
   *  账号名带 zz_ 前缀，一眼看得出是测试造的。 */
  const loginOrRegister = async (base, user, pass) => {
    const post = async (p, body) => {
      const r = await fetch(base + p, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      return r.json().catch(() => null);
    };
    let j = await post('/api/auth/login', { username: user, password: pass });
    if (!j || !j.token) {
      j = await post('/api/auth/register', { username: user, password: pass });
    }
    return (j && j.token) || null;
  };

  const run = async (storeName, p) => {
    const srv = spawn(py, [path.join(BACK, 'run.py'), String(p)], {
      cwd: BACK, stdio: ['ignore', 'pipe', 'pipe'],
      env: Object.assign({}, process.env, { STORE: storeName })
    });
    let out = '';
    srv.stdout.on('data', d => { out += d; });
    srv.stderr.on('data', d => { out += d; });
    const B = 'http://127.0.0.1:' + p;
    const wait = ms => new Promise(r => setTimeout(r, ms));
    let up = false;
    // 同上：等待窗口要给够（冷启动实测 18 秒）
    for (let i = 0; i < 120; i++) {
      try { const r = await fetch(B + '/api/health'); if (r.ok) { up = true; break; } } catch (e) {}
      await wait(500);
    }
    if (!up) {
      srv.kill(); srv.kill('SIGKILL');
      console.log('  服务没起来（STORE=' + storeName + '）:\n' + out);
      return null;
    }
    const health = await (await fetch(B + '/api/health')).json();
    // ★ 先登录拿 token。`/api/storage`、`/api/progress`、`/api/review/due`
    // 现在都要求登录了（它们含个人进度 / 库名主机这类信息），不带 token
    // 一律 401，下面的 `due.ok !== true` 会直接判失败。
    // 每个实例各登录一次：json 与 mysql 是**两套账号表**，一个实例发的
    // token 在另一个实例上解不出来。
    const auth = await loginOrRegister(B, 'zz_cross_store', 'zz_cross_123456');
    if (!auth) {
      srv.kill(); srv.kill('SIGKILL');
      console.log('  拿不到 token（STORE=' + storeName + '）:\n' + out);
      return null;
    }
    const AH = { Authorization: 'Bearer ' + auth };
    // ⚠️ limit 上限是 500（learning.py: `Query(50, ge=1, le=500)`）。
    // 这里原来写 1000：FastAPI 版直接 400，而老的零依赖版不校验上限、照常返回，
    // 于是这份对照**一直是拿空队列比空队列**，还打印一句 SKIP 假装没事。
    // 零依赖版 2026-09-26 移除后这个洞才暴露出来 —— 所以「两套实现互为对照」
    // 这套机制有个反面：宽松的那套会帮严格的那套把错误吞掉。
    const due = await (await fetch(B + '/api/review/due?all=1&limit=500',
                                   { headers: AH })).json();
    const st = await (await fetch(B + '/api/storage', { headers: AH })).json();
    const pg = await (await fetch(B + '/api/progress', { headers: AH })).json();
    srv.kill(); srv.kill('SIGKILL');
    if (due.ok !== true) {
      console.log('  /api/review/due 失败（STORE=' + storeName + '）: '
                  + JSON.stringify(due).slice(0, 200));
      return null;
    }
    // 每张卡的 level —— 队列顺序是由它决定的，所以比对之前必须先确认
    // 两边的**输入**是一样的（见下面「数据要先对齐」那段）。
    const lvs = {};
    for (const k of Object.keys(pg.progress || {})) {
      lvs[k] = (pg.progress[k] || {}).level || 0;
    }
    return { actual: health.store, ids: (due.queue || []).map(x => x.id),
             storage: st.storage || {}, lvs: lvs };
  };

  const j = await run('json', port);
  const m = await run('mysql', port + 1);
  if (!j || !m) return 1;

  console.log('  STORE=json  → 用了 ' + j.actual + '，队列 ' + j.ids.length + ' 张');
  console.log('  STORE=mysql → 用了 ' + m.actual + '，队列 ' + m.ids.length + ' 张');

  let bad = 0;
  if (j.actual !== 'json') {
    console.log('API FAIL STORE=json 没生效（实际 ' + j.actual + '）');
    bad++;
  }
  if (m.actual !== 'mysql') {
    console.log('API SKIP MySQL 用不上，跳过对照：' + (m.storage.degraded || '没配'));
    return bad;
  }
  // 数据是 20 张卡，任一边队列为空都说明接口没返回数据。
  // 这时下面的比对会「两边都是空 → 逐位相等」地通过 —— 假绿，必须当失败。
  if (!j.ids.length || !m.ids.length) {
    console.log('API FAIL 队列为空（json ' + j.ids.length
                + ' / mysql ' + m.ids.length + '），对照没有意义');
    return 1;
  }

  // ---- 数据要先对齐 ----
  // 队列顺序 = f(每张卡的 level, nextAt)。所以「顺序一致」这个结论只有在
  // **两边输入相同**时才成立。之前这项一直是绿的，是因为 MySQL 起不来、
  // 两个实例都降级成 json、读的是同一个文件 —— 自己跟自己比，必然一致。
  // 等 MySQL 真起来了才暴露：两个库的 progress 各存各的，本来就不是一份数据。
  // 这时逐位比对一定失败，但那是**数据不同步**，不是排序逻辑写错了。
  // 所以先查输入一不一样；不一样就明确 SKIP 并给出对齐办法，别报 FAIL 吓人。
  const keys = new Set([...Object.keys(j.lvs), ...Object.keys(m.lvs)]);
  const diffK = [...keys].filter(k => (j.lvs[k] || 0) !== (m.lvs[k] || 0));
  if (diffK.length) {
    console.log('API SKIP 两边进度数据不同步（' + diffK.length
                + ' 张卡的 level 不一样），顺序比对没有意义');
    console.log('       例：' + diffK.slice(0, 5).map(
      k => k + '(json=' + (j.lvs[k] || 0) + ' mysql=' + (m.lvs[k] || 0) + ')'
    ).join('  '));
    console.log('       对齐办法：node/python back_study/scripts/dbseed.py --sync'
                + ' 把卡片同步后，再跑 dbseed.py --import-json 搬进度；');
    console.log('       或者两边都用同一个后端开发（STORE 固定一个值）。');
    return bad;                       // 数据问题，不算代码失败
  }

  // 只比两边都有的 id：允许某个后端多出几张（比如 JSON 里留着手工测试的卡），
  // 但**共有的那批卡顺序必须完全一样**
  const both = new Set(j.ids.filter(x => m.ids.indexOf(x) >= 0));
  const oj = j.ids.filter(x => both.has(x));
  const om = m.ids.filter(x => both.has(x));
  const same = oj.length === om.length && oj.every((x, i) => x === om[i]);
  if (!same) {
    console.log('API FAIL 共有 ' + oj.length + ' 张卡的队列顺序不一致');
    for (let i = 0; i < Math.max(oj.length, om.length); i++) {
      if (oj[i] !== om[i]) {
        console.log('       第 ' + i + ' 位: json=' + oj[i] + '  mysql=' + om[i]);
      }
    }
    bad++;
  } else if (oj.length === 0) {
    console.log('API SKIP 两个后端没有共有的卡，没法比顺序（先跑 dbseed.py --sync）');
  } else {
    let extra = '';
    if (j.ids.length !== m.ids.length) {
      extra = '；但总量不同 json=' + j.ids.length + ' mysql=' + m.ids.length
            + '，跑 dbseed.py --sync --import-json 对齐';
    }
    console.log('API OK   共有 ' + oj.length + ' 张卡的队列顺序完全一致' + extra);
  }
  return bad;
}

(async function () {
  if (!PYCHECK) {
    console.log('API SKIP 没找到可用的 Python（可设环境变量 PY 指定路径）');
    return;
  }
  // 零依赖版移除之后，冒烟**必须**跑在装齐 fastapi + uvicorn + PyJWT 的 Python 上。
  // 找不到就不能假装通过：以前缺 fastapi 还能拿 stdlib 版兜底，现在没有兜底了，
  // 静默跳过等于「改坏了接口，校验还报全绿」。
  const pyFast = pickFastPython();
  if (!pyFast) {
    console.log('');
    console.log('API FAIL 没找到装齐依赖的 Python（需要 fastapi / uvicorn / PyJWT）');
    console.log('  装上再跑 → pip install -r back_study/requirements.txt');
    console.log('  或设环境变量 PYFAST 指定解释器路径');
    process.exitCode = 1;
    return;
  }
  console.log('API 用 Python: ' + pyFast);
  let total = PYCHECK.bad || 0;
  // 每一项的返回值必须是有限数字；万一将来有人写漏了 return，
  // 这里按「失败 1 项」算，而不是让 total 变成 NaN 悄悄通过
  const add = n => { total += (typeof n === 'number' && isFinite(n)) ? n : 1; };

  add(await smoke(pyFast));
  add(await crossStore(pyFast));

  console.log('');
  console.log(total === 0
    ? 'ALL API SMOKE PASSED（存储后端结果一致）'
    : 'API TOTAL ISSUES: ' + total);
  if (total) process.exitCode = 1;
})();
