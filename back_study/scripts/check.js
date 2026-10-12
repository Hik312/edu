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
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..", "..");
const BACK = path.join(ROOT, "back_study");
const WEB = path.join(ROOT, "web");
const DIST = path.join(WEB, "dist");
const DATA = path.join(ROOT, "data");

const html = fs.readFileSync(path.join(WEB, "index.html"), "utf8");

const blocks = [
  ...html.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g),
].map((m) => m[1]);
blocks.forEach((b, i) => {
  try {
    new Function(b);
    console.log("inline script #" + i + " OK, lines=" + b.split("\n").length);
  } catch (e) {
    console.log("inline script #" + i + " SYNTAX ERROR: " + e.message);
  }
});

// 加载 data/ 下所有卡片文件（与 Python 后端 load_source_cards 的口径一致），
// 否则新增的 AI 工程等科目的卡不会进校验，related 指向也会被误判为「卡不存在」。
const DATA_DIR = DATA;
const cards = [];
// 非卡片数据文件：catalog/roles/directions 只做 require 探测，不能当卡片。
const NON_CARD_FILES = ["catalog.js", "roles.js", "directions.js"];
// 加载阶段的「导出格式错」单独计数，不能借用下面卡片字段校验的 bad
// （let 有暂时性死区，在声明之前访问会抛 ReferenceError —— 踩过一次）。
let exportBad = 0;
fs.readdirSync(DATA_DIR).forEach(function (f) {
  if (!f.endsWith(".js")) return;
  // ★ catalog/roles/directions 必须**在 require 之前**就跳过。
  //   catalog.js 导出的数组是分类领域 id（['kaoyan','work']），
  //   不是卡片 —— 混进 cards 后每张都「字段全缺 + 没有 related」，
  //   一下子造出几十个假问题，还会让 API 用例拿脏 cards 去断言。
  if (NON_CARD_FILES.indexOf(f) >= 0) return;
  let mod;
  try {
    mod = require(path.join(DATA_DIR, f));
  } catch (e) {
    console.log("LOAD FAIL " + f + ": " + e.message);
    return;
  }
  if (Array.isArray(mod)) {
    cards.push.apply(cards, mod);
    return;
  }
  // ★ 声明了 `var CARDS_X = [...]` 却没导出数组的文件，**必须报错而不是静默跳过**。
  //   后端 load_source_cards 是直接读文件里的 JSON 字面量（不 require），
  //   所以这种文件在 Python 侧完全正常、前端和校验却看不到它的卡——
  //   症状是「后端说有 527 张、check.js 只加载了 525 张」，
  //   而卡片字段校验、related 悬空检查**全都跳过了这批卡**，看起来全绿实则没测。
  //   卡片文件必须以 `module.exports = CARDS_X;` 结尾（见各 gen_*.js）。
  if (
    /\bvar\s+CARDS_[A-Za-z0-9_]+\s*=/.test(
      fs.readFileSync(path.join(DATA_DIR, f), "utf8"),
    )
  ) {
    console.log(
      "EXPORT FAIL " +
        f +
        ": 声明了 CARDS_* 但 module.exports 不是数组 —— 该文件的卡不会进入校验",
    );
    exportBad += 1;
  }
});
console.log("cards loaded: " + cards.length + " (from data/*.js)");
if (exportBad > 0) {
  console.log(
    "有 " +
      exportBad +
      " 个卡片文件导出格式不对（EXPORT FAIL），这批卡没进校验 —— 先修这个",
  );
}

let bad = 0;
cards.forEach((c) => {
  [
    "id",
    "domain",
    "category",
    "subject",
    "topicPath",
    "title",
    "oneLine",
    "analogy",
    "mechanism",
    "scene",
    "interviewQ",
    "keywords",
  ].forEach((k) => {
    if (!c[k]) {
      console.log("MISSING field " + k + " -> " + c.id);
      bad++;
    }
  });
  if (c.scene && c.scene.length < 2) {
    console.log("SCENE too thin -> " + c.id);
    bad++;
  }
  const d = c.diagram;
  if (!d) return;
  if (d.kind === "pipeline") {
    d.frames.forEach((f, i) => {
      if (f.s < 0 || f.s >= d.stages.length) {
        console.log("BAD stage index " + c.id + " frame " + i + " s=" + f.s);
        bad++;
      }
    });
  } else if (d.kind === "state-machine") {
    const ids = d.nodes.map((n) => n.id);
    d.edges.forEach((e) => {
      if (ids.indexOf(e.from) < 0 || ids.indexOf(e.to) < 0) {
        console.log("BAD edge " + c.id + " " + e.from + "->" + e.to);
        bad++;
      }
    });
    d.frames.forEach((f, i) => {
      if (ids.indexOf(f.n) < 0) {
        console.log("BAD frame node " + c.id + " frame " + i + " n=" + f.n);
        bad++;
      }
    });
  } else if (d.kind === "snapshot") {
    d.frames.forEach((f, i) => {
      (f.active || []).forEach((a) => {
        if (a < 0 || a >= d.panels.length) {
          console.log("BAD panel active " + c.id + " frame " + i + " a=" + a);
          bad++;
        }
      });
    });
  } else if (d.kind === "arch") {
    // 组件架构图：节点方框 + 连线 + 分层点亮（与 add_diagrams.validate_diagram 同口径）
    const ids = d.nodes.map((n) => n.id);
    d.links.forEach((l) => {
      if (ids.indexOf(l.from) < 0 || ids.indexOf(l.to) < 0 || l.from === l.to) {
        console.log("BAD arch link " + c.id + " " + l.from + "->" + l.to);
        bad++;
      }
    });
    const lit = new Set();
    d.frames.forEach((f, i) => {
      (Array.isArray(f.n) ? f.n : [f.n]).forEach((x) => {
        if (ids.indexOf(x) < 0) {
          console.log("BAD arch frame node " + c.id + " frame " + i + " n=" + x);
          bad++;
        } else {
          lit.add(x);
        }
      });
    });
    if (lit.size < 2) {
      console.log("ARCH frames 点亮不足 2 个组件 -> " + c.id);
      bad++;
    }
  } else {
    console.log("UNSUPPORTED kind: " + d.kind + " -> " + c.id);
    bad++;
  }
  if (!d.frames || !d.frames.length) {
    console.log("EMPTY frames " + c.id);
    bad++;
  }
});
// 分类必须在 CATALOG 里登记过，否则导航里根本选不到这张卡
const CATALOG = require(path.join(DATA, "catalog.js"));
const catMap = {};
CATALOG.forEach((g) => {
  catMap[g.id] = (g.subjects || []).map((s) => s.id);
});
cards.forEach((c) => {
  if (!catMap[c.category]) {
    console.log("BAD category -> " + c.id + " = " + c.category);
    bad++;
  } else if (catMap[c.category].indexOf(c.subject) < 0) {
    console.log(
      "BAD subject -> " +
        c.id +
        " = " +
        c.subject +
        "（领域 " +
        c.category +
        " 下没有这个科目）",
    );
    bad++;
  }
});
console.log(
  "catalog: " +
    CATALOG.map((g) => g.name + "(" + g.subjects.length + "科)").join(" · "),
);

// 关联卡片：related 里的 id 必须真实存在，kind 只能是这三种，note 必须写清「为什么连」。
// 不写理由的链接迟早退化成关键词乱连，图谱就成了毛线球
const REL_KINDS = ["prereq", "extends", "compare"];
const idSet = new Set(cards.map((c) => c.id));
let relCount = 0;
cards.forEach((c) => {
  (c.related || []).forEach((r) => {
    relCount++;
    if (!idSet.has(r.id)) {
      console.log(
        "BAD related target -> " + c.id + " -> " + r.id + "（这张卡不存在）",
      );
      bad++;
    }
    if (r.id === c.id) {
      console.log("SELF related -> " + c.id);
      bad++;
    }
    if (REL_KINDS.indexOf(r.kind) < 0) {
      console.log(
        "BAD related kind -> " +
          c.id +
          " -> " +
          r.kind +
          "（只允许 " +
          REL_KINDS.join(" / ") +
          "）",
      );
      bad++;
    }
    if (!r.note || !r.note.trim()) {
      console.log(
        "EMPTY related note -> " + c.id + " -> " + r.id + "（要写清为什么连）",
      );
      bad++;
    }
  });
});
const relKindCnt = {};
cards.forEach((c) =>
  (c.related || []).forEach((r) => {
    relKindCnt[r.kind] = (relKindCnt[r.kind] || 0) + 1;
  }),
);
console.log(
  "related: " +
    relCount +
    " 条 " +
    JSON.stringify(relKindCnt) +
    "（" +
    cards.filter((c) => (c.related || []).length).length +
    "/" +
    cards.length +
    " 张有）",
);
const noRel = cards.filter((c) => !(c.related || []).length).map((c) => c.id);
if (noRel.length) {
  // ★ 语义孤岛升为 FAIL（原来只是 WARN，实际一直没人管，攒到 12 张）。
  //   理由：belong 边来自 topicPath，任何卡都有，所以「图上能看到这张卡」
  //   并不代表能点出它的相关内容。related 为空 = Pagerank 只剩度数的贡献，
  //   personalized_pagerank 对它永远推不出来 —— 是功能缺失，不是美观问题。
  bad += noRel.length;
  console.log(
    "FAIL 没有关联的卡片（语义孤岛，图谱里点不出相关内容）: " +
      noRel.join(", "),
  );
}
// 导出格式错的文件也要让整体结论变红：那些卡根本没进校验，
// 「看起来全绿」反而是最危险的（字段/related 悬空检查全都跳过了它们）。
bad += exportBad;

console.log(bad === 0 ? "ALL CHECKS PASSED" : "ISSUES FOUND: " + bad);

const kinds = {};
cards.forEach((c) => {
  if (c.diagram) kinds[c.diagram.kind] = (kinds[c.diagram.kind] || 0) + 1;
});
console.log("diagram kinds: " + JSON.stringify(kinds));

// （小程序端 minprogram/ 已于 2026-09-26 整体移除 ——
//  这里的 JS 语法 / app.json / WXML 检查一并删掉。三端只剩网页端。）

// 网页端。目录结构改过（单文件 index.html → Vite 工程），这里要跟着改：
//   web/index.html          Vite 入口（<div id="app"> + 内联脚本 + module script）
//   web/public/*            PWA 资源（源，构建时被原样复制进 dist/）
// 少一个都说明结构被谁动过，而这类问题在线上通常表现为「打开白屏」。
const webFiles = [
  "index.html",
  "public/manifest.json",
  "public/sw.js",
  "public/icons/icon-192.png",
  "public/icons/icon-512.png",
];
// 结构检查的失败计数（原来叫 mpBad，小程序端移除后改名）
let structBad = 0;
webFiles.forEach(function (f) {
  if (!fs.existsSync(path.join(WEB, f))) {
    console.log("WEB MISSING " + f);
    structBad++;
  }
});
// 构建产物是可选的（跑过 npm run build 才有）。没构建不算错，只提示一声，
// 免得没装 node 的机器上跑 check 一直报红。
if (!fs.existsSync(path.join(DIST, "index.html"))) {
  console.log(
    "WEB note   web/dist 未构建（cd web && npm run build），跳过产物检查",
  );
}

// 共用卡片数据：网页端读这一份，缺了就是空平台
["catalog.js", "springboot.js", "aizhuan.js"].forEach(function (f) {
  if (!fs.existsSync(path.join(DATA, f))) {
    console.log("DATA MISSING " + f);
    structBad++;
  }
});

console.log(
  structBad === 0 ? "ALL CHECKS PASSED" : "ISSUES FOUND: " + structBad,
);

// ---------- Python 后端文件 ----------
// ⚠️ 这份清单以前漏了 6 个文件（security.py / deps.py / auth.py / 整个 core/store/），
// 也就是说**鉴权那几个文件一直没进编译检查**。2026-09-26 补齐。
// 教训：清单靠手维护就会漏 —— 加新 py 文件后记得回来看一眼，
// 或者干脆改成 glob 扫 back_study/ 下所有 .py（排除 .venv 和 scripts）。
// routers/ 2026-10-02 按端分包（web/ + mini/）后不再手列 —— 教训就在上面：
// 手维护清单在文件一搬家就整片过期。改 glob 扫 routers/ 全部 .py。
const globRouters = () => {
  const out = [];
  (function walk(d) {
    for (const f of fs.readdirSync(d)) {
      const p = path.join(d, f);
      if (fs.statSync(p).isDirectory()) walk(p);
      else if (f.endsWith(".py"))
        out.push(path.relative(ROOT, p).split(path.sep).join("/"));
    }
  })(path.join(ROOT, "back_study", "app", "routers"));
  return out.sort();
};
const pyFiles = [
  // 入口（零依赖版 server.py 已于 2026-09-26 移除，只剩 FastAPI 这一条线）
  "back_study/run.py",
  // 核心模块（数据层 / 导入 / 大模型 / 网络探测 / 鉴权 / 文件解析）
  "back_study/core/db.py",
  "back_study/core/importer.py",
  "back_study/core/llm.py",
  "back_study/core/netinfo.py",
  "back_study/core/security.py",
  "back_study/core/docparse.py",
  // 个人中心的报表聚合层（纯函数：错题本/复盘/遗忘曲线/学习时长，2026-10-09 加）
  "back_study/core/report.py",
  // 问答检索链（2026-10-09 重排改造后加进清单）。
  // ★ 这三个文件之前不在清单里，等于**没被编译检查过**——
  //   改坏它们要等到运行时才发现。globRouters() 只收 routers/ 下的路由文件。
  "back_study/agent/qa/retrieval.py",
  "back_study/agent/qa/rerank.py",
  "back_study/agent/qa/retr_cache.py",
  // 存储层：base 是契约，jsonfile / mysql 是两套实现
  "back_study/core/store/__init__.py",
  "back_study/core/store/base.py",
  "back_study/core/store/jsonfile.py",
  "back_study/core/store/mysql.py",
  // FastAPI 包
  "back_study/app/__init__.py",
  "back_study/app/config.py",
  "back_study/app/deps.py",
  "back_study/app/schemas.py",
  "back_study/app/main.py",
  ...globRouters(),
  // AI Agent 层（LangGraph + 本地 Ollama，可选依赖，2026-09-29 加）
  // 分层：config 参数 / model 模型 / tools 工具 / nodes 节点 / graph 编排 /
  //       runtime 执行 / demo 命令行
  // 公共层（所有 Agent 共用）
  "back_study/agent/__init__.py",
  "back_study/agent/config.py",
  "back_study/agent/model.py",
  // 业务层 · 问答（已跑通）
  "back_study/agent/qa/__init__.py",
  "back_study/agent/qa/tools.py",
  "back_study/agent/qa/nodes.py",
  "back_study/agent/qa/graph.py",
  "back_study/agent/qa/runtime.py",
  "back_study/agent/qa/demo.py",
  // 业务层 · 问答检索（混合检索：向量为主+关键词兜底，2026-09-29 加）
  "back_study/agent/qa/retrieval.py",
  // 业务层 · 路径规划（write 节点待填）
  "back_study/agent/planner/__init__.py",
  "back_study/agent/planner/planner.py",
  "back_study/agent/planner/run.py",
  // 业务层 · 文档转卡（structure 结构精修 + chapter 逐章出卡，2026-10-01 加）
  "back_study/agent/cards/__init__.py",
  "back_study/agent/cards/nodes.py",
  "back_study/agent/cards/graph.py",
  "back_study/agent/cards/runtime.py",
  // 出卡去重（本地 embedding 语义比对，模型缺失时放行，2026-10-01 加）
  "back_study/agent/cards/dedup.py",
  // 业务层 · 卡片校验自纠（react 答完核对引用卡，2026-10-08 加）
  "back_study/agent/verify/__init__.py",
  "back_study/agent/verify/runtime.py",
  // 业务缓存 · 失效靠内容指纹不靠 TTL（2026-10-08 加）
  // ⚠️ 这三个是「缓存层」不是「业务层」，但放业务目录里了，
  //    漏了它们就等于三个缓存从没被编译检查过。
  "back_study/agent/verify/cache.py",
  "back_study/agent/qa/retr_cache.py",
  "back_study/agent/qa/ans_cache.py",
  // MCP · 客户端桥接 + 4 个 stdio server（2026-10-08 加）
  "back_study/agent/mcp.py",
  "back_study/agent/servers/web_search_mcp.py",
  "back_study/agent/servers/code_exec_mcp.py",
  "back_study/agent/servers/github_resource_mcp.py",
  "back_study/agent/servers/cards_mcp.py",
  // 脚本 · 大纲批量造卡（按 catalog 让本地 Ollama 生成卡片，2026-09-29 加）
  "back_study/scripts/gen_cards.py",
  // 脚本 · 文档批量摄取（data/docs 下 md/pdf 走 parse_document→enrich→to_card→草稿，2026-09-29 加）
  "back_study/scripts/gen_docs.py",
  // 脚本 · 小程序 tabBar 图标离线生成（PIL 画 8 个 PNG，2026-10-02 加）
  "back_study/scripts/gen_miniapp_icons.py",
  // 算法层（间隔重复 / 知识追踪，2026-09-29 加，零依赖叶子包）
  // 分层：base 契约 / sm2 + fsrs 实现 / __init__ 注册表 / demo 对拍台
  "back_study/algo/__init__.py",
  "back_study/algo/base.py",
  "back_study/algo/sm2.py",
  "back_study/algo/fsrs.py",
  "back_study/algo/hlr.py",
  "back_study/algo/bkt.py",
  "back_study/algo/eval.py",
  "back_study/algo/demo.py",
  // 缓存层（Redis 优先 / 内存降级，2026-09-29 加）
  "back_study/core/cache.py",
  // 算法库（事件流 / 掌握度 / 参数，2026-09-29 加）与业务库 store/ 分开
  // 分层：base 契约 / jsonfile 默认+降级 / pg 已启用 / __init__ 工厂
  "back_study/core/algostore/__init__.py",
  "back_study/core/algostore/base.py",
  "back_study/core/algostore/jsonfile.py",
  "back_study/core/algostore/pg.py",
];
let pyBad = 0;
pyFiles.forEach(function (f) {
  const p = path.join(ROOT, f);
  if (!fs.existsSync(p)) {
    console.log("PY MISSING " + f);
    pyBad++;
    return;
  }
});
console.log(
  pyBad === 0
    ? "python files present: " + pyFiles.length
    : "PY ISSUES: " + pyBad,
);

// ---------- 后端 API 冒烟：起临时 Python 服务 → 打接口 → 关掉 ----------
const { spawn, spawnSync } = require("child_process");

/** 样例 PDF 的 base64（读一次缓存）。
 *
 *  ★ 为什么 fixture 现生成而不是提交二进制：`scripts/make_sample_pdf.py`
 *    手写 PDF 语法产出 1.7KB，内容完全可见、可改、diff 友好。
 *    文件不存在就现场调 Python 生成一次 —— 省得「谁把 fixture 删了」
 *    变成一条查不到原因的红。
 *
 *  这份 PDF 刻意不含论文版面词（Abstract/References…），所以
 *  `_looks_like_paper` 对它返回 False：**自动判据一定判不出论文**。
 *  只有这样，「手动选『论文』仍然生效」才是一条真断言而不是恒真断言。
 */
let _samplePdf = null;
function samplePdfB64() {
  if (_samplePdf !== null) return _samplePdf;
  const f = path.join(__dirname, "fixtures", "sample.pdf");
  try {
    if (!fs.existsSync(f)) {
      const py = pickPython();
      if (!py) return (_samplePdf = false);
      const r = spawnSync(py, [path.join(__dirname, "make_sample_pdf.py")], {
        encoding: "utf8",
      });
      if (r.status !== 0 || !fs.existsSync(f)) return (_samplePdf = false);
    }
    _samplePdf = fs.readFileSync(f).toString("base64");
  } catch (e) {
    _samplePdf = false;
  }
  return _samplePdf;
}

function pickPython() {
  const cands = [
    process.env.PY,
    // 项目自己的 .venv 最优先：版本和依赖都随仓库走，换机器结论不会漂
    path.join(BACK, ".venv", "Scripts", "python.exe"),
    "python",
    "python3",
    "C:/Users/wangh/.workbuddy/binaries/python/versions/3.13.12/python.exe",
  ].filter(Boolean);
  for (const c of cands) {
    try {
      const r = spawnSync(c, ["--version"], { stdio: "ignore" });
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
  pyFiles.forEach(function (f) {
    // 真正编译一遍，比肉眼看靠谱
    const r = spawnSync(py, ["-m", "py_compile", path.join(ROOT, f)], {
      stdio: "ignore",
    });
    console.log((r.status === 0 ? "PY OK    " : "PY FAIL  ") + f);
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
  const pf = spawnSync(
    py,
    [
      "-m",
      "pyflakes",
      "back_study/core",
      "back_study/app",
      "back_study/scripts",
      "back_study/run.py",
    ],
    { cwd: ROOT, encoding: "utf8" },
  );
  // ★ 两种失败必须分开报，别混成一句「没装 pyflakes」。
  // `pf.error` 是**起不了进程**（EPERM / ENOENT / 超时），跟「没装包」完全是
  // 两回事。从前它们并成一个分支，于是沙箱里跑（子进程创建被拒）时会打印
  // 「跳过（没装 pyflakes：pip install pyflakes）」—— 而 pyflakes 其实是装着的
  // （实测 .venv 里 4.0.0）。人被这句话指向「去装包」，永远查不到真正的原因。
  // 另外 stdio 被管道接走时 pf.stderr 是 null，`|| ''` 又把失败信息吞掉，
  // 连是哪一步失败的都看不出来。
  const pfErr = pf.error ? String(pf.error.message || pf.error) : "";
  const pfNoMod = /No module named pyflakes/.test(pf.stderr || "");
  if (pf.error) {
    console.log("PY LINT  起不了子进程，跳过（" + pfErr + "）");
    console.log("         这不是「没装 pyflakes」，是进程创建被环境拒绝了");
  } else if (pfNoMod) {
    console.log(
      "PY LINT  跳过（这个解释器里没有 pyflakes：" +
        py +
        " -m pip install pyflakes）",
    );
  } else {
    const hits = (pf.stdout || "").trim().split("\n").filter(Boolean);
    if (!hits.length) console.log("PY LINT  clean");
    else {
      console.log(
        "PY LINT  " +
          hits.length +
          " 条提示（不判失败，先 grep 引用点再动手）：",
      );
      hits.forEach(function (h) {
        console.log("   " + h);
      });
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
    path.join(BACK, ".venv", "Scripts", "python.exe"),
    "C:/Users/wangh/.workbuddy/binaries/python/envs/default/Scripts/python.exe",
    process.env.PY,
    "python",
    "python3",
  ].filter(Boolean);
  for (const c of cands) {
    try {
      const r = spawnSync(c, ["-c", "import fastapi, uvicorn, jwt"], {
        stdio: "ignore",
      });
      if (!r.error && r.status === 0) return c;
    } catch (e) {}
  }
  return null;
}

// 同一套用例跑一遍，返回失败条数。
// 只有 FastAPI 一个实现 —— 零依赖版 server.py 已于 2026-09-26 移除。
async function smoke(py) {
  console.log("");
  console.log("---- API 冒烟 ----");
  let bad2 = 0;
  const port = 8600 + Math.floor(Math.random() * 200);
  const entry = path.join(BACK, "run.py");
  const srv = spawn(py, [entry, String(port)], {
    cwd: BACK,
    stdio: ["ignore", "pipe", "pipe"],
  });
  let out = "";
  srv.stdout.on("data", (d) => {
    out += d;
  });
  srv.stderr.on("data", (d) => {
    out += d;
  });
  const B = "http://127.0.0.1:" + port;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  //: 登录后填上，之后所有请求默认带它。声明必须在 call 之前 ——
  //: `let` 有暂时性死区，放在 call 之后会在调用时直接 ReferenceError。
  let authToken = "";
  // ★ 默认带上 token。个人数据端点（notes / progress / docs / cards / drafts /
  // llm / outline / graph / plan …）现在全部要求登录了，不带就是一片 401。
  // 顺序上没问题：下面认证那一组会**先**把 authToken 填上，之后才跑其它用例。
  // 要显式测「没带 token 会怎样」的用例传 `auth: false`。
  const call = async (u, opt) => {
    const o = Object.assign({}, opt);
    const withAuth = o.auth;
    delete o.auth;
    if (authToken && withAuth !== false) {
      o.headers = Object.assign(
        { Authorization: "Bearer " + authToken },
        o.headers || {},
      );
    }
    const r = await fetch(B + u, o);
    // headers 一起返回：图片端点要看 content-type（FileResponse），其余用不到
    return {
      code: r.status,
      body: await r.json().catch(() => null),
      headers: r.headers,
    };
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
    try {
      const r = await call("/api/health");
      if (r.body && r.body.ok) {
        up = true;
        break;
      }
    } catch (e) {}
    await wait(READY_GAP);
  }
  if (!up) {
    console.log(
      "API FAIL 服务在 " +
        (READY_TRIES * READY_GAP) / 1000 +
        " 秒内没起来\n" +
        out,
    );
    srv.kill();
    process.exitCode = 1;
    return 1; // 必须返回数字：返回 undefined 会让累加变成 NaN，
  } // 而 NaN 是 falsy —— 失败的运行会被当成通过
  const t = async (name, fn) => {
    try {
      const r = await fn();
      console.log((r ? "API OK   " : "API FAIL ") + name);
      if (!r) bad2++;
    } catch (e) {
      console.log("API ERR  " + name + ": " + e.message);
      bad2++;
    }
  };
  const TEST_ID = "zz-check-probe";
  // 用例失败时把**原因**打出来。只负责打印，计数仍由 t() 负责。
  // ★ 少了这个定义，失败用例会以 ReferenceError: err is not defined 的
  //   形式报出来 —— 断言为什么没过被彻底吃掉，人只能去猜。
  const err = (m) => console.log("       ↳ " + m);
  let docsTestId = null;

  await t("health 且实现标识正确", async () => {
    const b = (await call("/api/health")).body;
    // 零依赖版移除后只有 fastapi 这一个实现，这里写死而不是传参进来比
    return b.ok === true && b.lang === "python" && b.framework === "fastapi";
  });
  await t("health 带 store 字段（json / mysql）", async () => {
    const b = (await call("/api/health")).body;
    return b.store === "json" || b.store === "mysql";
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
  const AUTH_USER = "zz_check_probe";
  const AUTH_PASS = "zz_check_123456";
  const authHeaders = (tk) => ({ Authorization: "Bearer " + tk });
  const post = (u, obj) =>
    call(u, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(obj || {}),
    });
  // 注意：`let authToken` 已经在上面（call 的定义之前）声明过了，
  // 这里**不能**再声明一次 —— 重复 let 是 SyntaxError；
  // 而把它只放这里又会踩 call 里的暂时性死区（ReferenceError）。
  // 所以声明上移，这里直接赋值。

  await t("注册：用户名不合法 → 400", async () => {
    const r = await post("/api/auth/register", {
      username: "a",
      password: AUTH_PASS,
    });
    return r.code === 400 && r.body && r.body.ok === false;
  });
  await t("注册：密码太短 → 400", async () => {
    // 用户名要合法，否则会被用户名规则先拦下，测不到密码这条
    const r = await post("/api/auth/register", {
      username: "zz_probe_pw",
      password: "123",
    });
    return r.code === 400 && r.body && r.body.ok === false;
  });
  await t("注册/登录后 user.id 是真实数字（不是 null）", async () => {
    // 这条断言来自一个真踩过的坑：JSON 后端的 user_put 忘了分配 id，
    // 签出来的 token 里 sub 是字符串 "None"，表现是「注册看着成功、
    // 一刷新就掉登录」，日志里一点错都没有。
    let r = await post("/api/auth/register", {
      username: AUTH_USER,
      password: AUTH_PASS,
    });
    if (r.code === 400) {
      r = await post("/api/auth/login", {
        username: AUTH_USER,
        password: AUTH_PASS,
      });
    }
    if (!r.body || !r.body.token || !r.body.user) return false;
    authToken = r.body.token;
    return (
      r.body.user.id !== null &&
      r.body.user.id !== undefined &&
      r.body.user.id !== ""
    );
  });
  await t("认证接口不回传 passwordHash", async () => {
    const r = await call("/api/auth/me", { headers: authHeaders(authToken) });
    const raw = JSON.stringify(r.body);
    return raw.indexOf("passwordHash") === -1 && raw.indexOf("pbkdf2") === -1;
  });
  await t("auth/me 无 token → 401", async () => {
    // auth:false = 这一次**故意不带** Authorization（call 默认会补上）
    return (await call("/api/auth/me", { auth: false })).code === 401;
  });
  await t("auth/me 伪造签名的 token → 401", async () => {
    const fake =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" +
      ".eyJzdWIiOiIxIiwiZXhwIjo5OTk5OTk5OTk5fQ" +
      ".AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    return (
      (await call("/api/auth/me", { headers: authHeaders(fake) })).code === 401
    );
  });
  await t("auth/me 带有效 token → 拿到同一个用户", async () => {
    const r = await call("/api/auth/me", { headers: authHeaders(authToken) });
    return r.code === 200 && r.body.user.username === AUTH_USER;
  });
  await t("密码错 → 400（不是 401，否则前端会当成掉线）", async () => {
    const r = await post("/api/auth/login", {
      username: AUTH_USER,
      password: "zz-wrong-pass",
    });
    return r.code === 400;
  });
  await t("用户不存在与密码错话术完全相同（防用户名枚举）", async () => {
    const a = await post("/api/auth/login", {
      username: AUTH_USER,
      password: "zz-wrong-pass",
    });
    const b = await post("/api/auth/login", {
      username: "zz-no-such-user",
      password: "zz-wrong-pass",
    });
    return a.code === b.code && a.body.msg === b.body.msg;
  });
  await t("用户列表：按角色返回 200 / 403", async () => {
    const me = (await call("/api/auth/me", { headers: authHeaders(authToken) }))
      .body.user;
    const r = await call("/api/auth/users", {
      headers: authHeaders(authToken),
    });
    if (me.role === "admin")
      return r.code === 200 && Array.isArray(r.body.users);
    return r.code === 403;
  });

  await t("storage 端点与 health 口径一致", async () => {
    const h = (await call("/api/health")).body;
    const s = (await call("/api/storage")).body.storage;
    if (!s) return false;
    if (s.store !== h.store) return false;
    // 内置卡条数必须和接口真正在用的那批卡对得上，否则说明
    // 「库里有一份、接口读的是另一份」，那是最难查的一类不一致
    if (s.builtin.inFile !== cards.length) return false;
    if (h.store === "mysql") {
      // 用了 mysql 就必须真的用了：要么指纹一致，要么明确报 stale
      return s.builtin.stale === false || typeof s.builtin.stale === "boolean";
    }
    return s.builtin.inDb === null;
  });
  await t("没有静默降级到其他存储", async () => {
    // 配置说要用 mysql 就必须是 mysql —— 除非 degraded 里写清了为什么
    // 回退。悄悄回退是最坏的情况：用户以为在用数据库，其实写进 JSON 了。
    const s = (await call("/api/storage")).body.storage;
    if (s.want !== "mysql") return true; // 本来就想用文件，没事
    return s.store === "mysql" || !!s.degraded;
  });

  // ---------- 前端产物（没构建过就跳过，不算失败）----------
  // SPA 回落是很容易被改坏又不容易发现的一处：本地开发用 Vite dev server，
  // /cards 由 dev server 自己兜底，一切正常；一上线换成后端挂 dist，
  // 刷新 /cards 就 404 白屏 —— 而且开发时永远复现不了。
  if (fs.existsSync(path.join(DIST, "index.html"))) {
    await t("前端产物：/ 返回 Vue 入口", async () => {
      const r = await fetch(B + "/");
      const ct = r.headers.get("content-type") || "";
      const h = await r.text();
      return (
        r.status === 200 && ct.includes("text/html") && h.includes('id="app"')
      );
    });
    await t("前端产物：深层路由回落 index.html（history 模式）", async () => {
      const r = await fetch(B + "/cards");
      const h = await r.text();
      return r.status === 200 && h.includes('id="app"');
    });
    await t("前端产物：缺失的 .js 保持 404（不回落成 HTML）", async () => {
      // 回落成 HTML 的话浏览器会把它当 JS 解析，报的错跟真正原因没关系
      return (
        (await fetch(B + "/assets/zz-definitely-missing.js")).status === 404
      );
    });
    await t("前端产物：/api 下的未知路径是 JSON 404，不是 HTML", async () => {
      const r = await fetch(B + "/api/zz-no-such-endpoint");
      const ct = r.headers.get("content-type") || "";
      return r.status === 404 && ct.includes("json");
    });
  } else {
    console.log(
      "API SKIP 前端产物未构建，跳过 SPA 回落检查（cd web && npm run build）",
    );
  }
  await t("复习队列排序：不会 → 模糊 → 未标记 → 会", async () => {
    // 排序规则是两套实现必须一致的地方（MySQL 走 SQL 的 ORDER BY，
    // 文件后端走 Python 的 sort），所以这里断言的是**规则本身**。
    // 两套实现互相对照在下面的「存储后端一致性」里单独跑。
    const q = (await call("/api/review/due?all=1&limit=500")).body.queue;
    if (!q.length) return false;
    const rank = { 1: 0, 2: 1, 0: 2, 3: 3 };
    for (let i = 1; i < q.length; i++) {
      if (rank[q[i - 1].level] > rank[q[i].level]) {
        console.log(
          "       队列乱序: " +
            q[i - 1].id +
            "(lv" +
            q[i - 1].level +
            ") 排在 " +
            q[i].id +
            "(lv" +
            q[i].level +
            ") 前面",
        );
        return false;
      }
    }
    return true;
  });
  await t("cards 数量与数据文件一致", async () => {
    // 数据文件只对应**内置卡**。/api/cards 的 total 里还有用户自己入库的
    // 自定义卡（正常用法就会有），拿 total 比文件数的话，用户发一张卡这条
    // 就永远红。mysql：storage.builtin.inDb = 库里内置卡数，和文件数比；
    // json：builtin 不在库里（inDb=null，文件即库），退回比 total。
    const st = (await call("/api/storage")).body.storage;
    const r = await call("/api/cards");
    const builtin =
      st && st.builtin && typeof st.builtin.inDb === "number"
        ? st.builtin.inDb
        : r.body.total;
    return builtin === cards.length;
  });
  await t("cards 搜索命中", async () => {
    const r = await call("/api/cards?q=" + encodeURIComponent("事务"));
    return r.body.total > 0;
  });
  // ★ /graph/rank 曾经只回**前 50 个**（后端 [:50]，前端也 slice(0,50)）。
  //   后果不是少个字段：图上 87% 的卡侧栏 PageRank 一律显示「—」、
  //   节点大小退回 degree，同一张图两种尺寸口径。
  //   用全部卡片 id 打一次、断言一个不少 —— 把「只回一批」的回归锁死。
  await t("graph/rank 按分片发能一次回全请求的卡（不再截前 50）", async () => {
    const ids = cards.map((c) => c.id);
    // ★ 必须**按分片发**，不是把全部 id 拼一个请求。
    //   接口有 MAX_RANK_IDS=500 的保护上限（system.py），因为全量 id 拼起来
    //   会顶到 GET 查询串 8KB 上限（前端按 150 一片正是为此）。
    //   曾经这里一次发全量，卡数少于 500 时刚好通过，卡数一过 500 就 FAIL ——
    //   **断言写死了库规模，而不是接口契约**，加卡必崩。
    //   现在按真实分片逻辑发，并断言「所有片的并集 == 全量」，既锁住
    //   「不回只回前50」的回归，又不受卡数增长影响。
    const CHUNK = 150;
    const ranks = {};
    for (let i = 0; i < ids.length; i += CHUNK) {
      const slice = ids.slice(i, i + CHUNK);
      const r = await call(
        "/api/graph/rank?ids=" + encodeURIComponent(slice.join(",")),
      );
      if (r.code !== 200) {
        err("code=" + r.code + " @ 片 " + i);
        return false;
      }
      Object.assign(ranks, (r.body && r.body.ranks) || {});
    }
    const got = Object.keys(ranks).length;
    if (got !== ids.length) {
      err(`请求 ${ids.length} 个 id（分片发），只回 ${got} 个排名`);
      return false;
    }
    const first = ranks[ids[0]];
    return (
      typeof first.pagerank === "number" &&
      typeof first.pagerankPct === "number"
    );
  });
  // ★ 路径查询以前只按**一个方向**搜（BFS 顺 prereq 边），而造卡数据里
  //   target 才是前置 —— 用户按直觉「先点基础、再点进阶」100% 落空，
  //   报「没有依赖链」，看着像功能坏了；而且返回顺序是「进阶 → 前置」，
  //   和「学习路径」的读法相反。
  //   这条锁死两件事：两个方向都必须查到，且两边返回的是**同一条学习顺序**
  //   （前置卡在前、起点那张进阶卡在最后）。
  await t("graph/path 双向可查，返回的是学习顺序", async () => {
    const g = await call("/api/graph");
    const es = ((g.body && g.body.graph && g.body.graph.edges) || []).filter(
      (e) => e.kind === "prereq",
    );
    if (!es.length) {
      err("图里一条 prereq 边都没有");
      return false;
    }
    const e = es[0];
    const q = async (src, dst) => {
      const r = await call(
        "/api/graph/path?src=" +
          encodeURIComponent(src) +
          "&dst=" +
          encodeURIComponent(dst),
      );
      return (r.body || {}).nodes?.map((n) => n.id) || null;
    };
    const fwd = await q(e.source, e.target); // 顺边方向
    const bwd = await q(e.target, e.source); // 反方向 = 用户直觉的点法
    if (!fwd || !bwd) {
      err(`任一方向落空：fwd=${fwd} bwd=${bwd}`);
      return false;
    }
    if (fwd.join("|") !== bwd.join("|")) {
      err(`两个方向返回的顺序不一致：${fwd.join(">")} vs ${bwd.join(">")}`);
      return false;
    }
    // 学习顺序 = 前置在前；这条边是「target 是 source 的前置」，所以最后
    // 两站必然是 [target, source]。
    if (fwd[fwd.length - 1] !== e.source || fwd[fwd.length - 2] !== e.target) {
      err(`不是学习顺序：${fwd.join(">")}（应以 ${e.target}>${e.source} 收尾）`);
      return false;
    }
    return true;
  });
  await t("stats 字段完整", async () => {
    const s = (await call("/api/stats")).body.stats;
    return s && typeof s.total === "number" && typeof s.dueToday === "number";
  });
  // ===== 个人中心（/api/profile）=====
  // 这组原来是空白，于是「前端传 cardId / 后端收 card_id」这种
  // **静默失效**的 bug 漏了过去：请求照返200，只是用户点某张卡看明细
  // 时拿到的是全库聚合曲线，没有任何报错。
  await t("profile/overview 字段完整", async () => {
    const d = (await call("/api/profile/overview")).body.data || {};
    return (
      typeof d.totalReviews === "number" &&
      typeof d.weakCards === "number" &&
      typeof d.practicedCards === "number" &&
      typeof d.avgMastery === "number" &&
      // sessionsAvailable 必须有：用来区分「我没学」和「功能降级了」
      typeof d.sessionsAvailable === "boolean"
    );
  });
  await t("profile/mistakes 与 overview 口径一致（不能各算一遍）", async () => {
    const o = (await call("/api/profile/overview")).body.data || {};
    const m = (await call("/api/profile/mistakes?period=all")).body.data || {};
    // 概览数事件流、错题本也数事件流 —— 两边必须对得上，
    // 否则用户在同一页看到「薄弱卡 0」和「薄弱卡 2」会以为有一个是错的
    return (
      o.weakCards === (m.weakCards || []).length &&
      o.fuzzyCards === (m.fuzzyCards || []).length
    );
  });
  await t("profile/forgetting-curve 认 cardId（camelCase，别退回 card_id）", async () => {
    const cid = cards[0].id;
    // ★ 用前端 api/profile.js 里真实用的参数名 cardId。
    //   FastAPI 默认把 Python 参数名 card_id 当查询参数名，前端传 cardId
    //   就进不来 → 走全库聚合分支 → 单卡明细功能形同失效，且不报错。
    //   所以这里断言返回体里的 cardId 要等于请求的那张，不能只断言 points 非空
    //   （points 非空的话整体分支也满足，只有 cardId 字段能把两种分支区分开）。
    const r = await call(
      "/api/profile/forgetting-curve?cardId=" + encodeURIComponent(cid) + "&days=30",
    );
    const d = r.body.data || {};
    if (r.code !== 200) return false;
    if (d.cardId !== cid) return false;
    // 反向：不传 cardId 时必须回聚合（cardId 为 null/空）
    const agg = (await call("/api/profile/forgetting-curve?days=30")).body.data || {};
    return agg.cardId == null || agg.cardId === "";
  });
  await t("profile/非法 period 回落 week 且如实回传", async () => {
    // _norm_period 故意不抛 400（下拉框值错了返空数据更好排查），
    // 但必须在响应里回传归一化后的值，否则调用方看不出实际用的哪个周期。
    const d = (await call("/api/profile/mistakes?period=zz-bad")).body.data || {};
    return d.period === "week";
  });
  await t("profile/个人数据端点未登录一律 401", async () => {
    const paths = [
      "/api/profile/overview",
      "/api/profile/mistakes",
      "/api/profile/forgetting-curve",
      "/api/profile/study-time",
    ];
    for (const p of paths) {
      const r = await call(p, { auth: false });
      if (r.code !== 401) return false;
    }
    return true;
  });
  // ★ dueToday 拆成「真到期」和「新卡」两个数（2026-10-03）。
  //   原来 dueToday 把「从没背过」的卡也算到期，400 张库里 398 张没标过 →
  //   界面报 400、复习页只给 20 张，同一套系统两个矛盾口径。
  //   契约：dueToday 仍 = dueLearned + fresh（老调用方不改也能跑），
  //   且 dueTodayPlan = min(dueToday, 20) 才是「今天实际要学几张」。
  await t("stats 到期口径拆分：dueToday = dueLearned + fresh", async () => {
    const s = (await call("/api/stats")).body.stats;
    if (!s) return false;
    if (typeof s.dueLearned !== "number" || typeof s.fresh !== "number") {
      err("缺 dueLearned / fresh 字段 —— stats 口径没拆开");
      return false;
    }
    if (s.dueToday !== s.dueLearned + s.fresh) {
      err(
        `dueToday(${s.dueToday}) != dueLearned(${s.dueLearned}) + fresh(${s.fresh})`,
      );
      return false;
    }
    return true;
  });
  await t("mini home 的 dueTodayPlan：有自选清单按清单，否则 min(到期, 20)", async () => {
    const h = await call("/api/mini/home");
    const s = h.body && h.body.stats;
    if (!s || typeof s.dueTodayPlan !== "number") {
      err("缺 dueTodayPlan");
      return false;
    }
    // 端点有两个分支（mini/learn.py home）：挑了今日自选清单就以清单为准 ——
    // 清单本身就是用户对「今天做多少」的显式表态；没挑才回落 min(到期, 20)。
    // 只断言后一半会把「上一轮留下清单」误判成接口坏（check 自己就会留）。
    const pick = Array.isArray(h.body.pick) ? h.body.pick.length : 0;
    const want = pick ? pick : Math.min(s.dueToday, 20);
    if (s.dueTodayPlan !== want) {
      err(
        `dueTodayPlan=${s.dueTodayPlan}，应为 ${want}（${
          pick ? `自选清单 ${pick} 张` : "min(到期, 20)"
        }）`,
      );
      return false;
    }
    return true;
  });
  // ★ 标记进度**必须带 token**：复习事件要记到具体的人头上，端点加了登录要求。
  //   这里不带 token 的话会拿到 401，而 401 和「业务拒绝」长得不一样 ——
  //   校验脚本看不出差别，会把「没登录」当成「接口坏了」。
  const PH = Object.assign(
    { "Content-Type": "application/json" },
    authHeaders(authToken),
  );
  await call("/api/progress/" + TEST_ID, { method: "DELETE", headers: PH }); // 先清干净，别让上次残留影响间隔计算
  await t("标记 level=2 返回下次复习日期", async () => {
    const r = await call("/api/progress/" + TEST_ID, {
      method: "PUT",
      headers: PH,
      body: JSON.stringify({ level: 2 }),
    });
    return r.code === 200 && !!r.body.progress.nextAt;
  });
  await t("连续标记「会」间隔递增", async () => {
    const a = await call("/api/progress/" + TEST_ID, {
      method: "PUT",
      headers: PH,
      body: JSON.stringify({ level: 3 }),
    });
    const b = await call("/api/progress/" + TEST_ID, {
      method: "PUT",
      headers: PH,
      body: JSON.stringify({ level: 3 }),
    });
    const c = await call("/api/progress/" + TEST_ID, {
      method: "PUT",
      headers: PH,
      body: JSON.stringify({ level: 3 }),
    });
    // 刻意**不**断言「同一张卡连点三次『会』、间隔必须严格变大」——
    // 那是 SM-2 的实现细节（纯规则 iv *= ef），不是跨算法的契约。
    // FSRS 是记忆模型：同一天重复答对时 R≈1、记忆稳定性几乎不涨，间隔
    // **就应该原地不动**（这正是 FSRS 强过 SM-2 的地方，不是 bug）。
    // 本项目 ALGO 可切（sm2/fsrs/bkt），冒烟要断言所有算法都成立的契约：
    // reps 记到 3、间隔是正整数、且不倒退。
    const ia = a.body.progress.interval;
    const ic = c.body.progress.interval;
    return (
      c.body.progress.reps === 3 &&
      ic >= 1 &&
      ic >= ia
    );
  });
  await t("非法 level 被拒", async () => {
    const r = await call("/api/progress/" + TEST_ID, {
      method: "PUT",
      headers: PH,
      body: JSON.stringify({ level: 9 }),
    });
    return r.code === 400;
  });
  await t("未登录标记进度 → 401（事件不能记到无名氏头上）", async () => {
    // auth:false = 故意不带 Authorization（call 现在默认会补上 token）
    const r = await call("/api/progress/" + TEST_ID, {
      auth: false,
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: 3 }),
    });
    return r.code === 401;
  });
  await t("复习事件流按人隔离且严格有序", async () => {
    const r = await call("/api/review/events?limit=50", { headers: PH });
    const ev = (r.body && r.body.events) || [];
    if (r.code !== 200 || ev.length < 3) return false;
    // 时序必须单调：同一天连标多次时，顺序乱了 BKT 回放就是错的
    for (let i = 1; i < ev.length; i++) {
      const pa = String(ev[i - 1].at),
        pb = String(ev[i].at);
      if (pb < pa) return false;
      if (pb === pa && Number(ev[i].id) <= Number(ev[i - 1].id)) return false;
    }
    return ev.every((e) => e.user_id !== undefined && e.correct !== undefined);
  });
  await t(
    "复习队列返回",
    async () => (await call("/api/review/due?limit=5")).body.queue.length > 0,
  );
  await t("复习队列默认排序不因 BKT 共存而改变", async () => {
    // 默认 by=level：不带 p 字段，且仍是「不会→模糊→未标记→会」的老顺序。
    // 这条是共存改动的护栏 —— 默认路径必须和以前逐字一致。
    const r = await call("/api/review/due?limit=10");
    const q = r.body.queue || [];
    if (!q.length) return false;
    if (q.some((x) => "p" in x)) return false; // 默认不该出现半截的 p
    const rank = { 1: 0, 2: 1, 0: 2, 3: 3 };
    for (let i = 1; i < q.length; i++) {
      if (rank[q[i - 1].level] > rank[q[i].level]) return false;
    }
    return true;
  });
  await t("复习队列 by=bkt：带 p 且按掌握度低的优先", async () => {
    // all=1 把未到期的也带上，才能看到「刚标的卡」参与排序。
    // 三级排序键 (p, level档, 逾期)：p 相同要能退回老规则，不能把
    // 原本确定的顺序弄乱。
    const r = await call("/api/review/due?limit=10&by=bkt&all=1");
    const q = r.body.queue || [];
    if (!q.length) return false;
    if (q.some((x) => typeof x.p !== "number" || x.p < 0 || x.p > 1)) return false;
    for (let i = 1; i < q.length; i++) {
      if (q[i - 1].p > q[i].p) return false; // p 必须非降序
    }
    return true;
  });
  await t("BKT 掌握度接口：汇总 + 每卡 p∈[0,1] + 四参数", async () => {
    const r = await call("/api/mastery");
    if (r.code !== 200) return false;
    const s = r.body.summary || {};
    const cards = r.body.cards || [];
    if (typeof s.total !== "number" || typeof s.avgP !== "number") return false;
    if (!cards.length) return false;
    if (cards.some((c) => !(c.p >= 0 && c.p <= 1))) return false;
    const p = r.body.params || {};
    return ["p_init", "p_transit", "p_slip", "p_guess"].every((k) => k in p);
  });
  await t("BKT 拟合接口：数据不够时如实报 fitted=false + 原因", async () => {
    // 关键：不够数据时**不能**硬凑一个「看起来拟合过了」的参数。
    const r = await call("/api/review/fit-bkt", { method: "POST" });
    if (r.code !== 200) return false;
    const info = r.body.info || {};
    if (typeof info.fitted !== "boolean") return false;
    if (info.fitted === false && !info.reason) return false; // 必须说明为什么
    return true;
  });
  await t("存储复探端点：立刻重探并如实返回 restored", async () => {
    // 不要求 restored=true —— MySQL 真挂时它本来就该是 false。
    // 这里断言的是「调用能跑通 + 状态仍然可见」，不是「一定能连上」。
    const r = await call("/api/storage/reprobe", { method: "POST" });
    if (r.code !== 200) return false;
    if (typeof r.body.restored !== "boolean") return false;
    const st = r.body.storage || {};
    return typeof st.store === "string" && "degraded" in st;
  });
  await t("算法端点：当前算法 + 可切换项 + 每个都声明了 efNote", async () => {
    // 换 ALGO 之后界面上完全看不出来，这个端点就是补这个信息缺口。
    const r = await call("/api/algo");
    if (r.code !== 200) return false;
    const c = r.body.current || {};
    if (!c.name || !c.label || !c.efNote) return false;
    const opts = r.body.options || [];
    // 四个算法（sm2/fsrs/hlr/bkt），且当前用的必须在列表里
    return opts.length >= 4 && opts.some((o) => o.name === c.name);
  });
  await t("分类树可读取", async () => {
    const r = await call("/api/catalog");
    return r.body.catalog && r.body.catalog.length >= 2;
  });
  await t("学习方向目录可读取", async () => {
    const r = await call("/api/directions");
    const ds = r.body.directions || [];
    // count 允许是 0（先建方向、后补卡），但字段不能缺 —— chips 上要显示它
    return (
      ds.length >= 12 &&
      ds.every((d) => d.id && d.name && typeof d.count === "number")
    );
  });
  await t("队列按方向过滤", async () => {
    const politics = await call("/api/review/due?limit=500&dirs=politics");
    const english = await call("/api/review/due?limit=500&dirs=english");
    const unk = await call("/api/review/due?limit=500&dirs=zz-no-such-dir");
    const plain = await call("/api/review/due?limit=500");
    const pIds = new Set(politics.body.queue.map((x) => x.id));
    const eIds = new Set(english.body.queue.map((x) => x.id));

    // ★★ 为什么用politics/english 这两个**小方向**做断言，而不是 agent：
    //   库里 500+ 张卡，而接口 limit 上限就是 500 → 大方向（如 agent）的
    //   队列会被截断，而 due_list 里「未标记卡」与「到期卡」排序权重不同，
    //   **同一个 limit 下两个请求的第 500 名不是同一张卡**。
    //   实测：rag-memory-context-state 在 agent 请求里进了前 500，
    //   在全量请求里却被截掉 → 任何「拿另一个请求当全集比子集」的断言都必失败。
    //   小方向（politics 6 张 / english 5 张）不受截断影响，且互斥，
    //   才能真正证明「方向过滤生效」。
    //
    //   验的是三条真性质：① 两个方向都非空 ② 两方向**互斥**（过滤真的筛了）
    //   ③ 未知方向不筛空（id 写错时不能再也学不到卡）。
    const disjoint = [...pIds].every((id) => !eIds.has(id));
    return (
      pIds.size > 0 &&
      eIds.size > 0 &&
      disjoint &&
      politics.body.queue.length <= plain.body.queue.length &&
      unk.body.queue.length === plain.body.queue.length
    );
  });
  await t("今日自选清单：PUT 覆盖 / due?pick=1 只回清单 / 清空", async () => {
    // 拿两张真实卡当清单内容（不存在的 id 该被 db 层过滤掉，顺带测掉）
    const all = await call("/api/review/due?all=1&limit=500");
    const two = all.body.queue.slice(0, 2).map((x) => x.id);
    if (two.length < 2) return false;
    const put = await call("/api/review/pick", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: two.concat("zz-no-such-card") }),
    });
    if (put.code !== 200 || put.body.total !== 2) return false;
    const get = await call("/api/review/pick");
    if (get.body.total !== 2 || !get.body.ids.every((i) => two.includes(i)))
      return false;
    const q = await call("/api/review/due?pick=1&limit=500");
    const qIds = q.body.queue.map((x) => x.id);
    if (q.body.total !== 2 || !qIds.every((i) => two.includes(i))) return false;
    // 清空 → 空清单必须回空队列，不能退化成普通到期队列（否则「挑完了」
    // 会突然蹦出 311 张，前端区分不出「没挑」和「刷完了」）
    const clr = await call("/api/review/pick", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [] }),
    });
    const q2 = await call("/api/review/due?pick=1&limit=500");
    return clr.body.total === 0 && q2.body.total === 0;
  });
  await t("按科目过滤卡片", async () => {
    // a：合法且已铺满的 combo，必须返回卡片
    const a = await call("/api/cards?category=work&subject=java&brief=1");
    // b：跨科目的非法 combo（java 不归 kaoyan 管），过滤后必须为空。
    // 注意：gen_cards.py 已把 8 个科目全部铺满，不能再靠「某科目没卡」来测空，
    // 改用跨科目非法组合验证过滤器确实在收窄，而非返回全量。
    const b = await call("/api/cards?category=kaoyan&subject=java&brief=1");
    return a.body.total > 0 && b.body.total === 0;
  });
  await t("笔记新建 / 修改 / 删除", async () => {
    const c = await call("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "校验用笔记",
        body: "正文",
        category: "work",
        subject: "java",
      }),
    });
    const id = c.body.note.id;
    const u = await call("/api/notes/" + id, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "校验用笔记2",
        body: "正文2",
        category: "work",
        subject: "java",
      }),
    });
    const g = await call("/api/notes?category=work");
    await call("/api/notes/" + id, { method: "DELETE" });
    return u.body.note.title === "校验用笔记2" && g.body.total >= 1;
  });
  await t("空笔记被拒", async () => {
    const r = await call("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "", body: "" }),
    });
    return r.code === 400;
  });
  await t("草稿可编辑后入库", async () => {
    const imp = await call("/api/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: "# 校验标题\n一句话说明\n1. 第一步\n2. 第二步",
        category: "work",
        subject: "java",
        domain: "工作",
      }),
    });
    const d = imp.body.drafts[0];
    const put = await call("/api/drafts/" + d.id, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scene: ["场景一：具体系统里的用法", "场景二：踩过的坑"],
        keywords: ["校验"],
      }),
    });
    const pub = await call("/api/drafts/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: d.id }),
    });
    if (pub.body.ok) {
      // 入库成功就顺手删掉，别留脏数据
      await call("/api/cards/" + d.id, { method: "DELETE" });
    } else {
      await call("/api/drafts/" + d.id, { method: "DELETE" });
    }
    return put.code === 200 && pub.body.ok === true;
  });
  await t("导入切分出草稿", async () => {
    const r = await call("/api/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: "# 测试标题\n一句话说明。\n1. 第一步\n2. 第二步\n3. 第三步",
        domain: "测试",
      }),
    });
    return r.body.count >= 1 && !!r.body.drafts[0].id;
  });
  await t("未补全的草稿不允许入库", async () => {
    const d = await call("/api/drafts");
    const id = d.body.drafts[d.body.drafts.length - 1].id;
    const r = await call("/api/drafts/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: id }),
    });
    await call("/api/drafts/" + id, { method: "DELETE" }); // 清理测试草稿
    return r.code === 400; // scene 不足 2 条 → 应被拒
  });

  await t("文档导入并按标题自动分章", async () => {
    const md =
      "# MySQL 八股\n\n## 第一章 索引\n### 1. B+树\n矮胖，IO 少。\n### 2. 回表\n二级索引存主键。\n\n## 第二章 事务\n### 1. ACID\nundo/redo。\n";
    const r = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: md,
        filename: "t.md",
        category: "work",
        subject: "java",
        title: "校验文档",
      }),
    });
    if (!r.body || !r.body.ok) return false;
    docsTestId = r.body.doc.id;
    const ch = r.body.doc.chapters;
    // 分章按层级折叠（2026-10）：只在 ## 层切，### 子节整块并进父章，
    // 空壳章（#标题 直接正文为空）丢掉 —— 期望恰好 2 章且内容完整。
    return (
      r.body.doc.stats.headings >= 5 &&
      ch.length === 2 &&
      ch[0].title.indexOf("第一章") >= 0 &&
      ch[0].body.indexOf("B+树") >= 0 &&
      ch[0].body.indexOf("回表") >= 0 &&
      ch[1].body.indexOf("ACID") >= 0
    );
  });
  await t("文档 列表 / 详情 / 删除", async () => {
    const l = await call("/api/docs");
    const d = await call("/api/docs/" + docsTestId);
    const del = await call("/api/docs/" + docsTestId, { method: "DELETE" });
    const after = await call("/api/docs");
    return (
      l.body.total >= 1 &&
      d.body.doc.chapters.length >= 2 &&
      del.body.ok === true &&
      after.body.total === l.body.total - 1
    );
  });
  await t("导入选类型 + 论文走原件 + 改名", async () => {
    // ★ 2026-10-11 加。这组用例盯的是三个曾经**静默失败**的点：
    //
    //  1. docType 手动选：文件名不含任何论文特征词（arxiv/paper/期刊…），
    //     自动判据必然漏判。选了「论文」必须照样 isPaper —— 否则用户
    //     永远看不到原版，而接口一路 200，不报错。
    //  2. 论文也必须有 text：以前刻意留空，等于把论文排除在检索/RAG 之外。
    //     注意 chapters 必须为 0（不分章），两者别搞混。
    //  3. documents.raw_file 得真的存下来：**列不存在时写入是静默丢弃**，
    //     前端 canShowOriginal 恒 false，症状是「原件在磁盘上却 404」。
    //     这条断言的就是「入库后拿得到 rawFile」，能挡住整类回归。
    const pdfB64 = await samplePdfB64();
    if (!pdfB64) {
      // 没有样例 PDF 就退化成纯文本（只测 docType 与 category 落库）
      const r0 = await call("/api/import/doc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: "# 标题\n\n## 一节\n正文内容要足够长一些便于分章。",
          filename: "手动选类型.md",
          docType: "笔记",
          title: "手动选类型的笔记",
        }),
      });
      if (!r0.body || !r0.body.ok) return false;
      await call("/api/docs/" + r0.body.doc.id, { method: "DELETE" });
      return r0.body.doc.category === "笔记";
    }

    const mk = (docType, filename, title) =>
      call("/api/import/doc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataB64: pdfB64,
          filename,
          docType,
          title,
        }),
      });

    const paper = await mk("论文", "我的读书笔记.pdf", "我起的论文名");
    const mat = await mk("资料", "讲义.pdf", "我起的讲义名");
    const p = paper.body && paper.body.doc;
    const m = mat.body && mat.body.doc;
    if (!p || !m) return false;

    const r1 = await call("/api/docs/" + p.id, { method: "DELETE" });
    const r2 = await call("/api/docs/" + m.id, { method: "DELETE" });

    return (
      // 自定义标题：用户起名优先于任何自动推断
      p.title === "我起的论文名" &&
      m.title === "我起的讲义名" &&
      // 手动选的论文：文件名毫无特征，仍按论文处理
      p.isPaper === true &&
      p.category === "论文" &&
      // 原件路径入库 —— 列不存在时这一项为 false，是整组用例的关键断言
      !!p.rawFile &&
      // 论文不分章，但**必须留文本**供检索/RAG
      (p.chapters || []).length === 0 &&
      (p.text || "").length > 100 &&
      // 同一份文件选「资料」就该分章，且不是论文
      m.isPaper === false &&
      (m.chapters || []).length >= 1 &&
      r1.body.ok === true &&
      r2.body.ok === true
    );
  });

  await t("知识库原件可读（raw_file ->文件流）", async () => {
    // ★ 另一半的坑：raw_path(did, ext) 的 ext **必须容忍前导点**。
    //   调用方一律传 os.path.splitext(...)[1] == ".pdf"，而原正则要求首字符
    //   是字母数字 → 直接 return None → 原件明明在磁盘上却永远 404。
    //   这个 bug 和「raw_file 列不存在」互相掩护：补了列还是 404 才发现。
    //   这里只验纯文本导入（它也会存原件），够覆盖 ext 那条路径。
    const pdfB64 = await samplePdfB64();
    if (!pdfB64) return false; // fixture 造不出来就跳过，不算失败
    // ⚠️ 必须用**文件**导入：粘贴进来的文本压根没有原始文件
    //   （raw_bytes 为空 → 不写 rawFile）。拿粘贴文本断言 rawFile 必然 false，
    //   而那不是 bug 是「本来就没有」—— 这种假失败会让人去查不存在的问题。
    const r = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataB64: pdfB64, filename: "原件测试.pdf" }),
    });
    if (!r.body || !r.body.ok) {
      err("导入失败：" + JSON.stringify(r.body).slice(0, 160));
      return false;
    }
    const did = r.body.doc.id;
    if (!r.body.doc.rawFile) {
      err("rawFile 没入库（documents.raw_file 列可能不存在）");
      await call("/api/docs/" + did, { method: "DELETE" });
      return false;
    }
    const f = await call("/api/knowledge/file/" + did);
    const ct = f.headers && f.headers.get("content-type");
    await call("/api/docs/" + did, { method: "DELETE" });
    if (f.code !== 200) {
      // 这是 raw_path() 不容忍前导点那个 bug 的典型症状：
      // 文件明明在磁盘上，接口却 404，且**不打任何日志**
      err("原件流返回 " + f.code + "，raw_file=" + r.body.doc.rawFile);
      return false;
    }
    if (!ct) {
      err("原件流没有 content-type");
      return false;
    }
    return true;
  });

  await t("base64 上传按文本解码并分章", async () => {
    const b64 = Buffer.from(
      "# 标题\n\n## 小节一\n正文内容要够长一点。\n## 小节二\n再写一段文字。",
      "utf8",
    ).toString("base64");
    const r = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: "a.txt",
        dataB64: b64,
        title: "b64文档",
      }),
    });
    if (!r.body || !r.body.ok) return false;
    await call("/api/docs/" + r.body.doc.id, { method: "DELETE" });
    return r.body.doc.stats.chapters === 2; // #标题是空壳章被丢，剩下两个 ##
  });
  await t("docx 上传：zip 拆包 → Word 标题转 markdown 分章", async () => {
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
    const r0 = spawnSync(py, ["-c", pyCode], { encoding: "utf8" });
    if (r0.status !== 0 || !r0.stdout) return false;
    const r = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: "zz-probe.docx",
        dataB64: r0.stdout.trim(),
      }),
    });
    if (!r.body || !r.body.ok) return false;
    const ch = r.body.doc.chapters || [];
    const ok =
      r.body.doc.stats.headings >= 2 &&
      ch.length >= 2 &&
      ch[0].title.indexOf("绪论") >= 0 &&
      ch[1].title.indexOf("背景") >= 0;
    await call("/api/docs/" + r.body.doc.id, { method: "DELETE" });
    return ok;
  });
  await t("章节转卡带卡片组（deck / deckId）", async () => {
    // body.ai 显式覆盖：这条测的是「转卡时挂组」这条数据通路，不跑真模型
    const md =
      "# 组标题\n\n## 一章\n" +
      "这章的正文要足够长，长到可以被转卡流程接受。".repeat(3);
    const imp = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: md, title: "卡片组校验文档" }),
    });
    if (!imp.body || !imp.body.ok) return false;
    const did = imp.body.doc.id;
    const r = await call("/api/llm/to-card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        docId: did,
        index: 0, // 折叠分章后 #组标题 是空壳被丢，##一章 是第 0 章
        ai: {
          oneLine: "一句话结论",
          analogy: "像生活里的例子",
          mechanism: ["① 第一步", "② 第二步"],
        },
      }),
    });
    await call("/api/docs/" + did, { method: "DELETE" });
    const draft = r.body && r.body.draft;
    if (draft) await call("/api/drafts/" + draft.id, { method: "DELETE" }); // 清理测试草稿
    return (
      r.code === 200 &&
      draft &&
      draft.deck === "卡片组校验文档" &&
      draft.deckId === did
    );
  });
  await t("重命名卡片组：文档标题级联改草稿 deck", async () => {
    // 组名真相源是文档标题，deck 是抄在草稿上的冗余 —— 只改文档不改草稿
    // 就会分裂成两个组，所以这条测的是三处级联里的「文档 + 草稿」两处。
    const md =
      "# 组标题\n\n## 一章\n" +
      "这章的正文要足够长，长到可以被转卡流程接受。".repeat(3);
    const imp = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: md, title: "旧组名zz" }),
    });
    if (!imp.body || !imp.body.ok) return false;
    const did = imp.body.doc.id;
    const rc = await call("/api/llm/to-card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        docId: did,
        index: 0,
        ai: {
          oneLine: "一句话结论",
          analogy: "像生活里的例子",
          mechanism: ["① 第一步"],
        },
      }),
    });
    const draftId = rc.body && rc.body.draft && rc.body.draft.id;
    const rr = await call("/api/docs/" + did, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "新组名zz" }),
    });
    const after = await call("/api/drafts");
    const d =
      draftId && (after.body.drafts || []).find((x) => x.id === draftId);
    const miss = await call("/api/docs/zz-no-such-doc", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "x" }),
    });
    await call("/api/docs/" + did, { method: "DELETE" });
    if (draftId) await call("/api/drafts/" + draftId, { method: "DELETE" });
    return (
      rr.code === 200 &&
      rr.body.ok &&
      rr.body.drafts === 1 &&
      d &&
      d.deck === "新组名zz" &&
      d.topicPath[1] === "新组名zz" &&
      miss.code === 404
    );
  });

  // ---------- 卡片 Agent + 图片链路：只测不碰模型的确定路径 ----------
  // 真模型（结构精修 / 逐章出卡）在 deck_e2e 脚本里跑，不塞进校验 ——
  // 几十秒/章 + 结果不固定，进 check 只会又慢又飘。
  await t(
    "cards Agent 端点：缺参 400 / 文档不存在 404 / 下标越界 400",
    async () => {
      const a = await post("/api/agent/cards/structure", {});
      const b = await post("/api/agent/cards/structure", { docId: "zz-none" });
      const md =
        "# t\n\n## 一章\n" +
        "这章正文足够长，用来测越界下标在进线程池之前就被拦下来。".repeat(3);
      const imp = await call("/api/import/doc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: md, title: "agent校验文档" }),
      });
      if (!imp.body || !imp.body.ok) return false;
      const c = await post("/api/agent/cards/chapter", {
        docId: imp.body.doc.id,
        index: 99,
      });
      await call("/api/docs/" + imp.body.doc.id, { method: "DELETE" });
      return a.code === 400 && b.code === 404 && c.code === 400;
    },
  );
  await t("parse 端点：缺参 400 / 不存在 404 / 未解析就勾选 400", async () => {
    // 不测存在文档的 POST parse —— 那会真调模型（几十秒 + 结果不固定），
    // 真模型在 e2e 脚本里跑。这里只走 db 查不到 / 没解析过两条快速路径。
    const a = await post("/api/agent/cards/parse", {});
    const b = await post("/api/agent/cards/parse", { docId: "zz-none" });
    const c = await call("/api/agent/cards/parse", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ docId: "zz-none", keeps: {} }),
    });
    const md =
      "# t\n\n## 一章\n" +
      "这章正文足够长，确保导入后有章节可以做勾选保存测试。".repeat(3);
    const imp = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: md, title: "parse校验文档" }),
    });
    if (!imp.body || !imp.body.ok) return false;
    const d = await call("/api/agent/cards/parse", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ docId: imp.body.doc.id, keeps: { 0: true } }),
    });
    await call("/api/docs/" + imp.body.doc.id, { method: "DELETE" });
    return a.code === 400 && b.code === 404 && c.code === 404 && d.code === 400;
  });
  await t("docx 带图：占位符进正文 / 图片可读 / 删文档连图删", async () => {
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
    const r0 = spawnSync(py, ["-c", pyCode], { encoding: "utf8" });
    if (r0.status !== 0 || !r0.stdout) return false;
    const r = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: "zz-img.docx",
        dataB64: r0.stdout.trim(),
      }),
    });
    if (!r.body || !r.body.ok) return false;
    const did = r.body.doc.id;
    const body0 = ((r.body.doc.chapters || [])[0] || {}).body || "";
    const hasToken = body0.indexOf("![](media:image1.png)") >= 0;
    const img = await call("/api/media/" + did + "/image1.png");
    const noAuth = await call("/api/media/" + did + "/image1.png", {
      auth: false,
    });
    await call("/api/docs/" + did, { method: "DELETE" }); // 删文档应连图一起删
    const gone = await call("/api/media/" + did + "/image1.png");
    // 路径穿越：owner 带反斜杠（%5c），SAFE_NAME 挡在 media_path 里
    const traversal = await call("/api/media/zz%5c../a.png");
    const ctype = img.headers ? img.headers.get("content-type") || "" : "";
    return (
      hasToken &&
      img.code === 200 &&
      ctype.indexOf("image/png") >= 0 &&
      noAuth.code === 401 &&
      gone.code === 404 &&
      traversal.code === 404
    );
  });

  // 本地大模型：只测「确定路径」——状态接口、错误分支、以及精读后落盘。
  // 不在这里跑真模型：6 秒/章 + 结果不固定，塞进 CI 只会让校验又慢又飘。
  await t("llm 状态接口返回 provider", async () => {
    const r = await call("/api/llm/status");
    return (
      r.body && (r.body.provider === "ollama" || r.body.provider === "cloud")
    );
  });
  await t("llm 精读空章节 / 短正文 拒绝", async () => {
    const r = await call("/api/llm/enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "太短" }),
    });
    return r.code === 400 || r.code === 502;
  });
  await t("llm 存卡片：未精读的章要拒绝", async () => {
    const md =
      "# t\n\n## 一章\n" +
      "这一章写点够长的正文，用来验证接口而不是模型。".repeat(3);
    const imp = await call("/api/import/doc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: md, title: "llm校验文档" }),
    });
    if (!imp.body || !imp.body.ok) return false;
    const did = imp.body.doc.id;
    const r = await call("/api/llm/to-card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ docId: did, index: 0 }), // 折叠分章后这文档只有 1 章
    });
    await call("/api/docs/" + did, { method: "DELETE" });
    return r.code === 400; // 章存在但没精读 → 400（测的是这个分支，不是越界）
  });
  await t("llm 补齐：缺参 400 / 草稿不存在 404", async () => {
    // 真模型调用不进 check（慢且结果不固定），只测确定分支
    const a = await post("/api/llm/fill", {});
    const b = await post("/api/llm/fill", { draftId: "zz-none" });
    return a.code === 400 && b.code === 404;
  });

  // ---- 小程序端 /api/mini/*（2026-10-02 分包后的新契约）----
  // 路径前缀就是调用方标识：mini 一律 /api/mini/*，出问题先看是不是把
  // web 的全量返回塞给了手机（分页/聚合是这组存在的理由）。
  await t("mini 登录复用同账号 / 无 token 401", async () => {
    const anon = await call("/api/mini/auth/me", { auth: false });
    const r = await post("/api/mini/auth/login", {
      username: AUTH_USER,
      password: AUTH_PASS,
    });
    return (
      anon.code === 401 &&
      r.code === 200 &&
      r.body &&
      r.body.ok &&
      !!r.body.token
    );
  });
  await t("mini home 一次拿齐 stats/catalog/directions", async () => {
    const r = await call("/api/mini/home");
    return (
      r.code === 200 &&
      r.body &&
      r.body.ok &&
      r.body.stats &&
      r.body.stats.total > 0 &&
      Array.isArray(r.body.catalog) &&
      r.body.catalog.length > 0 &&
      Array.isArray(r.body.directions)
    );
  });
  await t("mini 卡包分页：brief 字段 + hasMore + 超限 422", async () => {
    const r = await call("/api/mini/cards?page=1&pageSize=5&q=java");
    const r2 = await call("/api/mini/cards?page=1&pageSize=500");
    if (r.code !== 200 || !r.body || !r.body.ok) return false;
    if (r.body.cards.length > 5) return false;
    if (typeof r.body.hasMore !== "boolean" || !(r.body.total >= 0)) return false;
    // brief 就该是 brief：大字段不许上列表（上过一次手机列表被撑爆的当）
    const first = r.body.cards[0];
    if (first && first.mechanism !== undefined) return false;
    if (first) {
      const d = await call("/api/mini/cards/" + encodeURIComponent(first.id));
      if (d.code !== 200 || !d.body || !d.body.card) return false;
      if (!Array.isArray(d.body.card.relatedBrief)) return false;
    }
    // 参数校验失败是 400 不是 422 —— main.py 有全局处理器把 FastAPI 默认的
    // 422 统一成 400（前端契约早就是 if (status === 400)）
    return r2.code === 400;
  });
  await t("mini 复习队列 / 标记 3 级 / 非法 level 400", async () => {
    const q = await call("/api/mini/review/queue?limit=3");
    if (q.code !== 200 || !q.body || !q.body.ok || !Array.isArray(q.body.queue))
      return false;
    // 标记要挑真实存在的卡（mini 端 404 校验存在性；web 的 /api/progress
    // 接受任意 cid，两边口径不同是故意的）。测完删掉，别把脏进度留给
    // 后面的「存储一致性」比对。
    const list = await call("/api/mini/cards?page=1&pageSize=1");
    if (list.code !== 200 || !list.body || !list.body.cards.length) return false;
    const cid = list.body.cards[0].id;
    const ok = await post("/api/mini/review/" + cid, { level: 3 });
    const bad = await post("/api/mini/review/" + cid, { level: 9 });
    await call("/api/progress/" + cid, { method: "DELETE", headers: PH });
    return ok.code === 200 && ok.body && ok.body.ok && bad.code === 400;
  });
  await t("mini 卡包模块筛 dirs + idsOnly 逐张浏览清单", async () => {
    // dirs：方向卡必须是无筛全量的子集。全量用 idsOnly 拿（分页 pageSize 上限
    // 50 装不下 398 张，拿分页结果当全量会把「子集」断言误判成失败）。
    const all = await call("/api/mini/cards?idsOnly=1");
    const one = await call("/api/mini/cards?page=1&pageSize=50&dirs=agent");
    const ids = new Set(all.body.ids);
    if (!(one.body.total > 0)) return false;
    if (!one.body.cards.every((x) => ids.has(x.id))) return false;
    // idsOnly：一次回全量 id（detail 页翻页用），不带 title 明细
    const io = await call("/api/mini/cards?dirs=agent&idsOnly=1");
    return (
      io.code === 200 &&
      io.body.ok &&
      Array.isArray(io.body.ids) &&
      io.body.ids.length === io.body.total &&
      io.body.total < all.body.total &&
      io.body.cards === undefined
    );
  });
  await t("mini 今日自选清单 + queue?pick=1", async () => {
    const list = await call("/api/mini/cards?idsOnly=1");
    const two = list.body.ids.slice(0, 2);
    if (two.length < 2) return false;
    const put = await call("/api/mini/review/pick", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: two }),
    });
    if (put.code !== 200 || put.body.total !== 2) return false;
    const q = await call("/api/mini/review/queue?pick=1&limit=20");
    if (q.code !== 200 || q.body.total !== 2) return false;
    // home 的 pick 字段是首页 CTA 的口径，得和清单一致
    const h = await call("/api/mini/home");
    if (!h.body || !Array.isArray(h.body.pick) || h.body.pick.length !== 2)
      return false;
    const clr = await call("/api/mini/review/pick", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [] }),
    });
    const q2 = await call("/api/mini/review/queue?pick=1&limit=20");
    return clr.body.total === 0 && q2.body.total === 0;
  });

  await call("/api/progress/" + TEST_ID, { method: "DELETE", headers: PH }); // 清理测试进度
  console.log(bad2 === 0 ? "API SMOKE PASSED" : "API ISSUES: " + bad2);
  srv.kill();
  srv.kill("SIGKILL"); // uvicorn 有时不吃 SIGTERM
  return bad2;
}

// ---- 存储后端一致性：同一个到期队列，两套存储实现必须给出同一个顺序 ----
// 这是接数据库以后最容易悄悄坏掉的地方：MySQL 走 SQL 的 ORDER BY，
// 文件后端走 Python 的 sort，两份规则的「未标记排哪」一错位，
// 复习队列就会莫名其妙地把新卡甩到最后 —— 而且只有用一种后端时才发现不了。
// 所以这里把同一个服务起两遍（一遍 STORE=json、一遍 STORE=mysql），
// 拿两条队列逐位比。
async function crossStore(py) {
  console.log("");
  console.log("---- 存储后端一致性（json vs mysql）----");
  const port = 8800 + Math.floor(Math.random() * 100);

  /** 幂等登录：先试着登录，账号不存在再注册。返回 token 或 null。
   *  账号名带 zz_ 前缀，一眼看得出是测试造的。 */
  const loginOrRegister = async (base, user, pass) => {
    const post = async (p, body) => {
      const r = await fetch(base + p, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return r.json().catch(() => null);
    };
    let j = await post("/api/auth/login", { username: user, password: pass });
    if (!j || !j.token) {
      j = await post("/api/auth/register", { username: user, password: pass });
    }
    return (j && j.token) || null;
  };

  const run = async (storeName, p) => {
    const srv = spawn(py, [path.join(BACK, "run.py"), String(p)], {
      cwd: BACK,
      stdio: ["ignore", "pipe", "pipe"],
      env: Object.assign({}, process.env, { STORE: storeName }),
    });
    let out = "";
    srv.stdout.on("data", (d) => {
      out += d;
    });
    srv.stderr.on("data", (d) => {
      out += d;
    });
    const B = "http://127.0.0.1:" + p;
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    let up = false;
    // 同上：等待窗口要给够（冷启动实测 18 秒）
    for (let i = 0; i < 120; i++) {
      try {
        const r = await fetch(B + "/api/health");
        if (r.ok) {
          up = true;
          break;
        }
      } catch (e) {}
      await wait(500);
    }
    if (!up) {
      srv.kill();
      srv.kill("SIGKILL");
      console.log("  服务没起来（STORE=" + storeName + "）:\n" + out);
      return null;
    }
    const health = await (await fetch(B + "/api/health")).json();
    // ★ 先登录拿 token。`/api/storage`、`/api/progress`、`/api/review/due`
    // 现在都要求登录了（它们含个人进度 / 库名主机这类信息），不带 token
    // 一律 401，下面的 `due.ok !== true` 会直接判失败。
    // 每个实例各登录一次：json 与 mysql 是**两套账号表**，一个实例发的
    // token 在另一个实例上解不出来。
    const auth = await loginOrRegister(B, "zz_cross_store", "zz_cross_123456");
    if (!auth) {
      srv.kill();
      srv.kill("SIGKILL");
      console.log("  拿不到 token（STORE=" + storeName + "）:\n" + out);
      return null;
    }
    const AH = { Authorization: "Bearer " + auth };
    // ⚠️ limit 上限是 500（learning.py: `Query(50, ge=1, le=500)`）。
    // 这里原来写 1000：FastAPI 版直接 400，而老的零依赖版不校验上限、照常返回，
    // 于是这份对照**一直是拿空队列比空队列**，还打印一句 SKIP 假装没事。
    // 零依赖版 2026-09-26 移除后这个洞才暴露出来 —— 所以「两套实现互为对照」
    // 这套机制有个反面：宽松的那套会帮严格的那套把错误吞掉。
    const due = await (
      await fetch(B + "/api/review/due?all=1&limit=500", { headers: AH })
    ).json();
    const st = await (await fetch(B + "/api/storage", { headers: AH })).json();
    const pg = await (await fetch(B + "/api/progress", { headers: AH })).json();
    srv.kill();
    srv.kill("SIGKILL");
    if (due.ok !== true) {
      console.log(
        "  /api/review/due 失败（STORE=" +
          storeName +
          "）: " +
          JSON.stringify(due).slice(0, 200),
      );
      return null;
    }
    // 每张卡的 level —— 队列顺序是由它决定的，所以比对之前必须先确认
    // 两边的**输入**是一样的（见下面「数据要先对齐」那段）。
    const lvs = {};
    for (const k of Object.keys(pg.progress || {})) {
      lvs[k] = (pg.progress[k] || {}).level || 0;
    }
    return {
      actual: health.store,
      ids: (due.queue || []).map((x) => x.id),
      storage: st.storage || {},
      lvs: lvs,
    };
  };

  const j = await run("json", port);
  const m = await run("mysql", port + 1);
  if (!j || !m) return 1;

  console.log(
    "  STORE=json  → 用了 " + j.actual + "，队列 " + j.ids.length + " 张",
  );
  console.log(
    "  STORE=mysql → 用了 " + m.actual + "，队列 " + m.ids.length + " 张",
  );

  let bad = 0;
  if (j.actual !== "json") {
    console.log("API FAIL STORE=json 没生效（实际 " + j.actual + "）");
    bad++;
  }
  if (m.actual !== "mysql") {
    console.log(
      "API SKIP MySQL 用不上，跳过对照：" + (m.storage.degraded || "没配"),
    );
    return bad;
  }
  // 数据是 20 张卡，任一边队列为空都说明接口没返回数据。
  // 这时下面的比对会「两边都是空 → 逐位相等」地通过 —— 假绿，必须当失败。
  if (!j.ids.length || !m.ids.length) {
    console.log(
      "API FAIL 队列为空（json " +
        j.ids.length +
        " / mysql " +
        m.ids.length +
        "），对照没有意义",
    );
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
  const diffK = [...keys].filter((k) => (j.lvs[k] || 0) !== (m.lvs[k] || 0));
  if (diffK.length) {
    console.log(
      "API SKIP 两边进度数据不同步（" +
        diffK.length +
        " 张卡的 level 不一样），顺序比对没有意义",
    );
    console.log(
      "       例：" +
        diffK
          .slice(0, 5)
          .map(
            (k) =>
              k +
              "(json=" +
              (j.lvs[k] || 0) +
              " mysql=" +
              (m.lvs[k] || 0) +
              ")",
          )
          .join("  "),
    );
    console.log(
      "       对齐办法：node/python back_study/scripts/dbseed.py --sync" +
        " 把卡片同步后，再跑 dbseed.py --import-json 搬进度；",
    );
    console.log("       或者两边都用同一个后端开发（STORE 固定一个值）。");
    return bad; // 数据问题，不算代码失败
  }

  // 只比两边都有的 id：允许某个后端多出几张（比如 JSON 里留着手工测试的卡），
  // 但**共有的那批卡顺序必须完全一样**
  const both = new Set(j.ids.filter((x) => m.ids.indexOf(x) >= 0));
  const oj = j.ids.filter((x) => both.has(x));
  const om = m.ids.filter((x) => both.has(x));
  const same = oj.length === om.length && oj.every((x, i) => x === om[i]);
  if (!same) {
    console.log("API FAIL 共有 " + oj.length + " 张卡的队列顺序不一致");
    for (let i = 0; i < Math.max(oj.length, om.length); i++) {
      if (oj[i] !== om[i]) {
        console.log(
          "       第 " + i + " 位: json=" + oj[i] + "  mysql=" + om[i],
        );
      }
    }
    bad++;
  } else if (oj.length === 0) {
    console.log(
      "API SKIP 两个后端没有共有的卡，没法比顺序（先跑 dbseed.py --sync）",
    );
  } else {
    let extra = "";
    if (j.ids.length !== m.ids.length) {
      extra =
        "；但总量不同 json=" +
        j.ids.length +
        " mysql=" +
        m.ids.length +
        "，跑 dbseed.py --sync --import-json 对齐";
    }
    console.log(
      "API OK   共有 " + oj.length + " 张卡的队列顺序完全一致" + extra,
    );
  }
  return bad;
}

(async function () {
  if (!PYCHECK) {
    console.log("API SKIP 没找到可用的 Python（可设环境变量 PY 指定路径）");
    return;
  }
  // 零依赖版移除之后，冒烟**必须**跑在装齐 fastapi + uvicorn + PyJWT 的 Python 上。
  // 找不到就不能假装通过：以前缺 fastapi 还能拿 stdlib 版兜底，现在没有兜底了，
  // 静默跳过等于「改坏了接口，校验还报全绿」。
  const pyFast = pickFastPython();
  if (!pyFast) {
    console.log("");
    console.log(
      "API FAIL 没找到装齐依赖的 Python（需要 fastapi / uvicorn / PyJWT）",
    );
    console.log("  装上再跑 → pip install -r back_study/requirements.txt");
    console.log("  或设环境变量 PYFAST 指定解释器路径");
    process.exitCode = 1;
    return;
  }
  console.log("API 用 Python: " + pyFast);
  let total = PYCHECK.bad || 0;
  // 每一项的返回值必须是有限数字；万一将来有人写漏了 return，
  // 这里按「失败 1 项」算，而不是让 total 变成 NaN 悄悄通过
  const add = (n) => {
    total += typeof n === "number" && isFinite(n) ? n : 1;
  };

  add(await smoke(pyFast));
  add(await crossStore(pyFast));

  console.log("");
  console.log(
    total === 0
      ? "ALL API SMOKE PASSED（存储后端结果一致）"
      : "API TOTAL ISSUES: " + total,
  );
  if (total) process.exitCode = 1;
})();
