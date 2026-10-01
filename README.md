# 原理卡片 · 学习平台

背原理用的卡片系统：每张卡回答三个问题 —— **它是什么 / 它怎么跑 / 面试官会怎么问**。
中间那个「怎么跑」是重点，机制写成有序步骤，不是定义。

仓库按**前端 / 后端**分开放，一层就能看清谁是谁：

```
study/
├── back_study/   后端（FastAPI，含数据层、存储层与开发脚本）
├── web/          网页端（Vite + Vue 3）
└── data/         共用卡片数据（唯一真相源）
```

存数据的地方是**可切换的**：默认单文件 JSON，配上 MySQL 就换成数据库
（见下面「存储层」一节）。换存储不动任何业务代码。

想先看全貌而不是用法，直接翻 **[docs/技术架构.md](docs/技术架构.md)** ——
分层图、三条主数据流、存储层契约、「已经做完的 / 还没做的」清单、与智径 EduPath
合并的路线图、以及「动哪里会牵到什么」都在那一份里。

**刚接手（或隔了很久回来）先读 [docs/学习路线.md](docs/学习路线.md)** ——
按什么顺序读懂这个项目、现在有哪些算法、还差什么、以及为此要学哪些算法与中间件。

---

## 跑起来

后端是 Python（FastAPI），**只有一个实现**。

> 以前还有个零依赖版 `back_study/server.py`（纯标准库，一个包都不用装），
> **2026-09-26 已移除**。原因是鉴权改用 PyJWT 之后它名不副实 —— 装了 PyJWT
> 就不是零依赖了，而继续留着它意味着每个新接口要写两遍、冒烟要跑两遍。

```bash
pip install -r back_study/requirements.txt   # fastapi / uvicorn / PyJWT（必需）+ pymysql（可选）
python back_study/run.py                     # 本机 http://127.0.0.1:8080
python back_study/run.py 8080 --lan          # 手机同 WiFi 访问（绑 0.0.0.0，注意网络安全）
python back_study/run.py 8099                # 指定端口
python back_study/run.py 8080 --reload       # 改代码自动重启（开发用）
```

**用不用 MySQL 都不用改代码**，改 `back_study/config.local.json` 里的一个字段就行：

```bash
python back_study/scripts/dbseed.py --status     # 看现在连的是哪个存储、库里有什么
python back_study/scripts/dbseed.py --sync       # 建库建表 + 把 data/*.js 灌进去
```

`back_study/.venv/` 是项目自带的虚拟环境（fastapi + uvicorn 已装好），
`back_study/.venv/Scripts/python.exe back_study/run.py` 可以直接跑，不受系统 Python 影响。
脚本会自动优先用它；删了也没关系，按 `requirements.txt` 重建即可。

手机上用：Android Chrome 菜单「添加到主屏幕」，iOS Safari 分享「添加到主屏幕」，
之后就是全屏、离线可用的图标。

改完任何代码或数据，跑一遍校验：

```bash
node back_study/scripts/check.js
```

它会检查：网页内联脚本语法、卡片必填字段、动画帧引用越界、24 个 Python 文件能否编译，
最后起一个临时服务**跑 39 项 API 冒烟**（端口随机，跑完自动关），
再把同一份到期队列用 json / mysql 两种存储各算一遍、逐位比顺序。

某个接口偷偷从 400 变成 422、或者字段改了名，这里会当场报出来。
解释器用 `PYFAST` 指定。**找不到装齐 fastapi / uvicorn / PyJWT 的 Python 会直接判失败**，
不再静默跳过 —— 以前缺 fastapi 还有零依赖版能兜底，现在没有兜底了，跳过就等于假绿。

---

## 后端：单实现（FastAPI）

只有 `back_study/run.py` 一个入口，路由按域拆在 `back_study/app/routers/`（一个域一个文件）。

| | FastAPI（`back_study/run.py`） |
|---|---|
| 启动 | `python back_study/run.py 8080` |
| 依赖 | `pip install -r back_study/requirements.txt`（fastapi / uvicorn / **PyJWT** 必需） |
| 交互文档 | 有，`/docs` 点着就能调 |
| 参数校验 | Pydantic 模型，类型不对直接 400 并说是哪个字段 |
| 静态目录 | `/data/store/` 直接 403（笔记正文、复习进度都在这儿） |

写实现时值得知道的三点：

- **端点写同步 `def` 而不是 `async def`**。db 层是同步文件 IO，在 `async def` 里直接跑会卡住
  事件循环（整个服务一起等，一个精读请求能堵死所有人）；FastAPI 见到 `def` 会自动丢进线程池。
- **`/api/llm/status` 返回 `ok:false` 时 HTTP 仍是 200**。AI 不可用是正常状态不是故障，
  前端据此渲染提示而不是弹错误。
- **请求体超 16MB 返 `413`**，查询参数写错返 `400` 并指出参数名（Pydantic 兜的）。

### 「两个后端」这段历史的教训

零依赖版存在过两年多，它换来的是**每个接口写两遍 + 冒烟跑两遍**，代价是真金白银。
而它作为"对照"的价值其实有反向的一面 —— 2026-09-26 移除它时才暴露：

> `check.js` 的存储一致性对照一直用 `?limit=1000`，而 FastAPI 版的上限是 **500**
> （`learning.py` 的 `Query(50, ge=1, le=500)`），请求直接 400。
> 零依赖版不校验这个上限、照常返回，于是那份对照**一直是拿空队列比空队列**，还打印一句 SKIP 假装没事。

**宽松的那套实现会帮严格的那套把错误吞掉。** 两套实现互为对照有个前提：
不一致要能被看见，而不是被其中一套的宽容吸收掉。

---

## 存储层：JSON 文件 / MySQL，可切换

「存哪儿」和「怎么算」是分开的：`core/db.py` 只管复习算法和数据组装，
真正落盘交给 `core/store/` 里的**可插拔后端**。所以换存储不用动业务代码，
换存储不用改任何端点。

```
core/store/
├── base.py       契约（读 / 单行写 / 整表替换，谁实现谁就得守这些签名）
├── jsonfile.py   data/store/*.json —— 默认，零依赖
├── mysql.py      MySQL 8.0 + pymysql，含建表 DDL 与内容同步
└── schema.sql    表结构（给人读的版本，可以直接手工执行）
```

### 怎么切

配置优先级：**环境变量 > `back_study/config.local.json` > 默认值**。

```jsonc
// back_study/config.local.json（已在 .gitignore 里，密码不进版本库）
{
  "STORE": "mysql",                    // 改成 "json" 就回退，不用改任何代码
  "MySQL": { "host": "127.0.0.1", "port": 3306,
             "user": "root", "password": "***", "database": "study_cards" }
}
```

```bash
# 临时切一次，不动配置文件
STORE=json python back_study/run.py 8080
```

没装 pymysql、MySQL 没起来、库还没建 —— 三种情况都会**自动回退到 JSON 并且照常服务**，
但启动横幅里会打一行带 `!!` 的告警，`/api/storage` 的 `degraded` 字段里写着原因。
**降级必须看得见**：悄悄回退最坏的结果是「你以为在用数据库，其实写进了文件」，
等哪天发现数据对不上才懵。

### 有 MySQL 之后哪些地方真的变好了

不是「换了个地方存 JSON」——只有一处查询值得上数据库，但那一处是这个系统最热的一条：

**今日到期队列**。文件后端要把全部卡读进内存、逐张比对进度、再 Python 排序；
到了库里是一条 `LEFT JOIN + ORDER BY`，`next_at` 上有索引，卡从 20 张涨到 2 万张是同一个写法。
排序规则（不会 → 模糊 → 未标记 → 会，同档逾期久的优先）在两套实现里各有一份，
所以 `check.js` 里专门有一段**把同一个服务起两遍（一遍 `STORE=json`、一遍 `STORE=mysql`），
拿两条队列逐位比**——这种不一致只有用另一种后端时才发现得了。

### 内容还是文件说了算

`data/*.js` 是**内容**（git 管理的源码），MySQL 里那份 `cards` 表是**查询用的副本**。
所以：改了 `data/*.js` 记得 `dbseed.py --sync`；如果指纹对不上，
`/api/storage` 会报 `builtin.stale: true`，而且接口会**回落到文件**，
不会端上一个「源码里已经改掉、库里还是旧的」版本 —— 那比没有数据库更难查。

```
python back_study/scripts/dbseed.py --sync          # 建表 + 内容同步（幂等）
python back_study/scripts/dbseed.py --sync --force  # 无视指纹强制重灌
python back_study/scripts/dbseed.py --import-json   # 把 data/store/*.json 的旧数据单向搬进库
python back_study/scripts/dbseed.py --drop --yes    # 删库（真的会删）
```

### 表结构

| 表 | 存什么 | 设计取舍 |
|---|---|---|
| `cards` | 内置卡 + 自定义卡，`origin` 区分 | 只把要按列查的字段（category / subject / domain / title）提成独立列，`mechanism`/`diagram`/`related` 这些**永远整张一起读写**的留在 `payload JSON` 里。拆成子表只会让每次读卡多 5 次 JOIN |
| `progress` | 复习进度（SM-2） | 反过来**全部拆成标量列**并给 `next_at` 建索引 —— 到期队列就该是一条 SQL |
| `notes` | 笔记 / 卡片下的「我的理解」 | 有 `card_id` 的就是后者 |
| `documents` | 整份导入的资料 | `chapters` 一个 JSON 列。一份八股文几十章，拆表后「打开文档」要先 JOIN 再拼回来，白折腾 |
| `drafts` | 待入库的草稿 | 缓冲区，不是卡 |
| `meta` | 键值杂项 | 放内置卡的内容指纹 |

`cards` 上还有一条 **ngram 分词的中文全文索引**（`ft_cards`）。
MySQL 内置 ngram 插件，不用装额外组件。目前搜索仍然走 Python 的字段匹配 ——
理由很直接：两个后端的搜索结果必须一字不差，而在 20 张卡的规模上，
SQL 全文检索换来的那点性能远不够抵「两套搜索语义不一致」的风险。
索引建着不碍事，卡量上来（几千张）之后再切换实现，届时以全文检索为准。

---


顶部导航切换（手机上是底部标签栏）：

| 模块 | 干什么 |
|---|---|
| **卡片库** | 主界面。左侧按「领域 → 科目」筛选，右侧看卡：类比 → 为什么 → 原理拆解 → 真实业务场景 → 过程演示 → 面试追问。底部有可选的「我的理解」。卡片墙 / 列表两种视图 |
| **复习** | 今日到期队列。未标记 = 待学，点了标记后按间隔重复排期 |
| **知识框架** | MOC 树：领域 → 科目 → 主题 → 卡片逐层展开，每个主题带掌握度色条 |
| **知识图谱** | Canvas 粒子场，**分层下钻**：默认只给「领域 → 科目」的模块总览，点科目进主题层、点主题进卡片层，逐层展开。节点外圈有小粒子在公转、边上有光点流动、背景有漂移的尘埃 |
| **笔记** | 想到什么先记下来。可挂到某张卡上、打标签、归到某个科目。**一键转成卡片草稿** |
| **导入** | ① 粘贴资料切成草稿卡；② 上传整份 md/txt/pdf/docx，按标题自动分章，每份文档自成一个「卡片组」；③ 逐章「AI 精读」出类比/重点/原理拆解，也可一键全量精读+转卡 |

笔记离线也能记（存 localStorage）；**导入、文档、AI 精读都必须跑后端**。

### 手机上的样子

底部标签栏（图标 + 文字），不是顶部的。效果见 `_shot/` 里的截图。

几个关键实现，改动前先读，不然容易踩回去：

- **底部标签栏用 flex 布局的固定项，不用 `position:fixed`。** fixed 是相对视口底部定位的，
  微信内置浏览器的工具栏正好盖在上面 —— 之前就是这么整条看不见的。
- **整屏高度用 `--vh`（JS 写 `window.innerHeight`），不用 `100vh`。** 移动浏览器的 100vh 是
  "最大视口高度"，含被地址栏/工具栏遮住的部分，拿它当整屏高会把底栏顶到可视区外面。
- **列表项是圆角卡片**（`#cards` 有内边距、`.item` 是卡片），不是贴边的横线。
- **分类栏是两行横向滚动**，不是竖着堆三条。
- **笔记是"列表 → 编辑"两屏**（`body.note-focus` 控制），不做左右分栏；编辑页顶部有返回键。
- **要滚动的面板必须显式给高度**（`flex:1` + `min-height:0`），不给高度布局会塌。
  图谱面板因此是「工具条 / 画布（flex:1）/ 图例」三段式。

### URL 直达

| 链接 | 到哪 |
|---|---|
| `?tab=graph` | 直接进某个模块（tab 取 cards / outline / graph / notes / import） |
| `?card=sb-autoconfig` | 直接打开某张卡 |
| `?card=sb-autoconfig&mine=1` | 打开某张卡并展开「我的理解」输入框 |
| `?tab=notes&card=sb-autoconfig` | 直接开一张预关联该卡的新笔记 |
| `?doc=doc-20260922-1` | 直接打开某份文档 |
| `?doc=doc-20260922-1&ch=2` | 打开文档并展开第 3 章 |
| `?tab=graph&gscope=sub:ai` | 图谱直接落到某个科目（`top` / `sub:科目id` / `topic:科目id\|主题路径` / `all` / `local`） |
| `?tab=graph&gscope=local&card=sb-autoconfig` | 图谱直接看某张卡的邻居 |
| `?debug=1` | 图谱调试：把帧数 / FPS / 模块质心 / 抽样节点坐标写进**统计条和标签标题**（无头环境下判断动画有没有在跑、节点摆在哪，就靠它）|

PWA 快捷方式和分享链接都用得上。

### 「我的理解」在哪

卡片详情页最底部，在「面试官会怎么问」之后。**就地编辑**，不用跳页面：
点「+ 写我的理解」直接出现输入框，保存后原地显示，可再编辑 / 删除。
整块是可选的 —— 不写完全不影响复习。

这条链路的用意：**原理看懂 ≠ 能说出来**。逼自己用自己的话写一遍，卡住的那一步就是没真懂的。

## 分类树

`data/catalog.js`，两层：领域（考研 / 工作）× 科目。改这个文件即可，导航、筛选、统计会自动跟着变。

```
考研 → 政治 / 英语 / 数学 / 专业课
工作 → Java后端 / Python / AI工程 / 计算机基础 / 前端
```

每张卡带 `category` + `subject` 两个 id。`back_study/scripts/check.js` 会校验这两个值在分类树里登记过
（拼错一个 id 这张卡在导航里就选不到）。

## 目录

```
study/
├── README.md / DEPLOY.md   项目说明与部署
├── .gitignore              排除 config.local.json（有密码）与截图产物
├── docs/                   文档
│   ├── 技术架构.md           全貌：分层 / 数据流 / 存储契约 / 缺口 / 踩坑
│   └── 学习路线.md           从零读懂项目的顺序 + 要学的算法与中间件
├── web/                    网页端（Vue 3 + Vite 工程）
│   ├── src/                  源码：api / stores / views / components / styles
│   │   ├── styles/tokens.css   全站设计令牌唯一出处（配色 / 字号只改这里）
│   │   └── config/theme.js     图表配色唯一出处
│   ├── public/                icons/（PWA 图标）、_seed.html（登录种子页）、sw.js（历史 SW 清理）
│   └── vite.config.js         写死 127.0.0.1 + strictPort（见架构文档踩坑）
├── data/                   共用卡片数据（唯一真相源）
│   ├── catalog.js            分类树（考研/工作 × 科目）
│   ├── roles.js              目标岗位（选一个岗位 → /api/plan 算出缺哪些考点）
│   ├── directions.js         学习方向（选方向 → 复习队列只推这个方向的卡）
│   ├── springboot.js         卡片数据（严格 JSON 字面量，JS/Python 都能读）
│   ├── aizhuan.js            AI 工程卡片
│   └── store/                运行时数据（进度/自定义卡/草稿/笔记/文档/AI 档案）
│                             用 MySQL 时这一层就闲置了，但留着 —— 它就是降级目标
└── back_study/             后端
    ├── run.py                FastAPI 入口（python back_study/run.py 8080）
    ├── requirements.txt      依赖（fastapi/uvicorn/PyJWT 必需，pypdf/pymysql 可选）
    ├── config.local.json     本机配置：用哪个存储、MySQL 连哪儿（不进版本库）
    ├── .venv/                项目自带虚拟环境，依赖随仓库走（删了可按 requirements 重建）
    ├── app/                  FastAPI 后端
    │   ├── main.py             装配：中间件 / 异常翻译 / 静态挂载 / 启动横幅
    │   ├── config.py           路径、体积上限、错误话术、OpenAPI 元信息
    │   ├── schemas.py          请求体模型（字段名与 data/*.js 的契约逐字对齐）
    │   └── routers/            接口按域拆：结构 / 卡片 / 学习 / 笔记 / 导入 / 文档 / AI
    ├── core/                核心（除 pymysql 外只用标准库）
    │   ├── db.py               数据层：卡片读取 + 进度持久化 + 间隔调度
    │   ├── store/              存储后端（可插拔）
    │   │   ├── base.py           契约：读 / 单行写 / 整表替换
    │   │   ├── jsonfile.py       JSON 文件实现（默认，也是降级目标）
    │   │   ├── mysql.py          MySQL 实现（pymysql，含 DDL 与内容同步）
    │   │   └── schema.sql        表结构（给人读的版本）
    │   ├── importer.py         导入：文本 → 草稿卡 / 整份文档分章
    │   ├── llm.py              大模型通道（Ollama / 云端，零依赖 urllib）
    │   └── netinfo.py          局域网地址探测（含虚拟网卡规避）
    ├── scripts/             开发脚本
    │   ├── check.js            一键校验（39 项 API 冒烟 + 存储后端一致性对照）
    │   ├── dbseed.py           建库建表 / 内容同步 / JSON 存量数据迁移 ⭐
    │   ├── test_security.py    鉴权单测（pbkdf2 + PyJWT，含伪造 token 用例）
    │   ├── make_icon.py        生成 PWA 图标
    │   ├── fixtures/           手工测试样本（别放 _shot/，那目录整删）
    │   └── _oneoff/            已跑完的一次性数据迁移，留档别当工具用
    └── _shot/                截图产物，删了不影响运行
```

---

## 卡片 schema

新增卡必须带这些字段，否则 `check.js` 会报错：

| 字段 | 说明 |
|---|---|
| `id` | 英文短横线，全局唯一 |
| `category` | 领域 id，如 `work`（必须在 catalog.js 里登记过） |
| `subject` | 科目 id，如 `java` |
| `domain` | 旧字段，仅作兼容保留，新卡用上面两个 |
| `topicPath` | 层级路径，如 `["SpringBoot","核心原理","自动装配"]` |
| `title` | 标题（问句更好，逼自己答出来） |
| `oneLine` | 一句话结论 |
| `analogy` | 生活类比 |
| `mechanism` | **有序步骤**，描述它怎么跑 |
| `scene` | 真实业务场景，**至少 2 条**，禁止「广泛应用」这类空话 |
| `interviewQ` | 面试官会怎么追问 |
| `keywords` | 搜索用关键词 |
| `diagram` | 可选，动画（`pipeline` / `state-machine` / `snapshot`） |

---

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康探测（前端据此决定走 API 还是本地存储），带 `store` 字段 |
| GET | `/api/storage` | 存储后端状态：用的哪个、库里几行、内容副本有没有过期、有没有降级 |
| GET | `/api/catalog` | 分类树 |
| GET | `/api/cards?q=&category=&subject=&deckId=&brief=1` | 卡片列表，支持关键词搜索、分类与卡片组过滤 |
| GET | `/api/cards/:id` | 单张卡 |
| POST | `/api/cards` | 新增自定义卡 |
| PUT / DELETE | `/api/cards/:id` | 改 / 删自定义卡（内置卡不在这里改） |
| GET | `/api/progress` | 全部复习进度 |
| PUT | `/api/progress/:id` | 标记 `{level}`，1=不会 2=模糊 3=会，返回下次复习日期 |
| GET | `/api/review/due?limit=&dirs=` | 今日复习队列（未标记的算待学）；`dirs` 按学习方向过滤，**先过滤再截断 limit** |
| GET | `/api/stats` | 统计 |
| POST | `/api/import` | 文本导入 → 草稿卡 |
| GET / DELETE | `/api/drafts` | 草稿列表 / 清空 |
| PUT | `/api/drafts/:id` | 编辑草稿（补原理步骤和场景） |
| DELETE | `/api/drafts/:id` | 丢弃草稿 |
| POST | `/api/drafts/publish` | 草稿入库（字段不全会被拒） |
| GET | `/api/notes?category=&subject=&q=&cardId=` | 笔记列表 |
| POST | `/api/notes` | 新建笔记 |
| PUT / DELETE | `/api/notes/:id` | 更新 / 删除笔记 |
| GET | `/api/graph?category=&subject=` | 知识图谱（节点 + 边） |
| GET | `/api/graph/neighbors/:id?depth=` | 某节点的邻居子图 |
| GET | `/api/outline?category=&subject=` | 知识框架（MOC 树） |
| GET | `/api/docs` | 文档列表（含 `aiDone / aiTotal`） |
| GET / DELETE | `/api/docs/:id` | 文档详情（含 `chapters[].ai`） |
| POST | `/api/import/doc` | 整份文档导入并按标题分章（text 或 base64，md/txt/pdf/docx） |
| GET | `/api/llm/status` | 本地模型状态（可用性 / 模型名） |
| POST | `/api/llm/enrich` | 精读若干章（单章逐次调用，见上文） |
| POST | `/api/llm/to-card` | 把某章的精读结果落成卡片草稿（自动挂当前文档的卡片组） |
| GET | `/api/roles` | 目标岗位列表（`data/roles.js`） |
| GET | `/api/plan?role=` 或 `?subjects=` | 岗位知识地图：技能组覆盖率、卡片掌握、缺哪些考点 |
| GET | `/api/directions` | 学习方向预设（`data/directions.js`）+ 每个方向能推出多少张卡 |
| GET / PUT | `/api/agent/profile` | 长期档案（目标岗位 / 常问主题 / 薄弱卡 / **每日目标与方向**，跟登录用户走） |
| POST | `/api/agent/ask` | AI 问答。`mode` 取 flow/react，`stream:true` 走 SSE（可带 `history`、`profile`） |

上表两版都实现了，返回结构和状态码一致。用 FastAPI 版时可以直接在 `/docs` 里点着调
（唯一例外是超大请求体：FastAPI 版 413、标准库版 400）。

改卡数据的正规流程：改 `data/*.js` → `node back_study/scripts/check.js`。
用了 MySQL 的话再加一步 `python back_study/scripts/dbseed.py --sync`（把内容同步进库）。

---

## 复习间隔（SM-2 简化版）

| 标记 | 行为 |
|---|---|
| 会 | 间隔 1 → 3 → 之后 ×记忆因子（2.5 起步，答对上调，上限 2.6） |
| 模糊 | 间隔砍半，连续答对次数不清零 |
| 不会 | 回到 1 天后重来，记忆因子下调 |

**这套规则在 `back_study/core/db.py` 和 `index.html` 里各有一份，改要一起改**，
否则会出现「网页说明天复习、后端说后天」。

---

## 大模型：两件事，两条通道

通道优先级（`back_study/core/llm.py` 里的 `provider()`）：
1. `AI=off` —— 直接关闭精读模块（服务器上没显卡 / 不想付费时用）
2. **OpenAI 兼容云端** —— 只在设了 `LLM_PROVIDER=cloud` **且**有 `LLM_API_KEY` 时才走
3. **本机 Ollama（默认兜底）** —— `http://127.0.0.1:11434`，离线、免费、不要 key

（`/api/llm/status` 返回 `ok:false` 是**正常状态**不是错误，前端据此换成提示文字，
其余功能照常 —— 部署取舍见 [DEPLOY.md](DEPLOY.md)。）

```bash
ollama serve                        # 起本机模型服务
ollama pull qwen2.5:7b-instruct     # 推荐：指令跟随好、不吐思考链
ollama pull deepseek-r1:7b          # 也可以，但它是推理模型，出字慢一些
export LLM_MODEL=qwen2.5:7b-instruct      # 可选，不设就按内置优先级自动挑
# export LLM_PROVIDER=cloud LLM_API_KEY=sk-xxx LLM_BASE_URL=https://api.deepseek.com
```

`deepseek-r1` 这类推理模型必须关掉思考链（代码里传了 `think: false`），否则
token 全烧在思考段、正文是空的 —— 这是踩过的坑，有降级重试兜底。

### 一、导入资料 → 卡片草稿

```bash
curl -X POST localhost:8080/api/import -H "Content-Type: application/json" \
  -d '{"text":"# 标题\n说明\n1. 步骤一\n2. 步骤二","domain":"求职·Java","topicPath":["并发"],"useLLM":true}'
```

不带 `useLLM` 就走本地启发式（按标题行切段，连续编号行识别为步骤），零成本。
产出是**草稿**，落在 `data/store/drafts.json`；草稿的 `scene` 是占位符，
补齐 2 条真实场景才能入库 —— 硬规矩，防止半自动的脏数据污染卡库。

### 二、整份文档 → 逐章精读（一句话 / 类比 / 重点 / 原理拆解）

导入一份 md/txt/pdf/docx 后，每一章可以单独「AI 精读」，把原文整理成：

| 字段 | 要求 |
| --- | --- |
| `oneLine` | 一句话结论，说清它是什么、有什么用 |
| `analogy` | 生活类比（排队/图书馆/快递/做饭），**不许出现技术词** |
| `points` | 重点 3-5 条，必须带原文的具体名词或数字 |
| `mechanism` | 原理拆解 3-5 步，讲清"它怎么跑"的因果链 |

```bash
curl localhost:8080/api/llm/status                      # 能不能用、用的哪个模型
curl -X POST localhost:8080/api/llm/enrich -H "Content-Type: application/json" \
  -d '{"docId":"doc-20260922-1","index":2}'             # 精读第 3 章
curl -X POST localhost:8080/api/llm/enrich -H "Content-Type: application/json" \
  -d '{"docId":"doc-20260922-1"}'                       # 全文（前端不用，见下）
curl -X POST localhost:8080/api/llm/to-card -H "Content-Type: application/json" \
  -d '{"docId":"doc-20260922-1","index":2}'             # 把这一章落成卡片草稿
```

精读结果写在 `documents.json` 每章自己的 `ai` 字段里，逐章落盘 ——
所以「精读一章看一章」，中途关页面也不会白跑。`aiDone / aiTotal` 用来画进度。

**两个刻意的设计决定：**

1. **前端逐章调用，不用批量接口。** 批量（`batch` 参数）一次送 4 章是快 3 倍，
   但章节又短又相邻时，7B 模型会把 A 章的内容安到 B 章头上（实测串味，且随机复现）。
   单章调用永远不串，还能显示 `3/10` 的进度。后端保留了批量能力，
   并且带**对齐质检**：用返回值与原文的字符二元组重合度打分，
   对不上、或类比写成说明书的，自动退回单章重跑。

2. **不引 LangChain / LangGraph。** 这里要的只是「一次结构化抽取 + 解析失败重试
   + 类比不合格重问」，三个函数就写完了（`llm.enrich()` 内部一个带条件的重试）。
   引框架会给零依赖后端塞进几十 MB 依赖，而收益是负的 ——
   单次 LLM 调用不需要编排，编排的价值在「多步、有分支、要维护状态」的场景。
   真要跑多步 agent（抽取 → 自检 → 修补 → 合并），那应该是独立脚本，
   而不是塞进平台主链路。整个后端仍然只用标准库 `urllib`。

### 三、PDF / docx 说明

标准库解析不了 PDF。`pypdf` 是**可选依赖**：装了就能传 PDF，没装会明确提示
`pip install pypdf`（不报 500）。`.md` / `.txt` / `.docx` 开箱即用 —— docx 用
标准库 `zipfile` + `ElementTree` 直接拆 `word/document.xml`，`outlineLvl` /
`Heading` 样式按层级转 markdown `#` 复用同一套分章规则，不依赖 Word 和第三方库；
老 `.doc` 会被明确要求另存为 `.docx`。

---

## 已知限制

- **单机自用**：没有登录、没有多用户、没有权限。谁连得上谁就能读写，
  只适合局域网或本机。上了 MySQL 也一样 —— 数据库解决的是「存哪儿、怎么查」，
  不是「谁能看」。要做多用户得先有鉴权，那是另一件事。
- **内置卡的内容仍以 `data/*.js` 为准**，MySQL 里那份是查询副本。改了源文件要
  `dbseed.py --sync`，否则 `/api/storage` 会报 `stale`（接口会回落到文件，不会端旧内容）。
- **JSON 文件后端在几千张卡以内够用**，再大就明显慢 —— 因为它每次都把全部卡读进内存。
  到这个量级请切 MySQL（切法见上文「存储层」）。
- **离线缓存已排除 `/api/*`**，复习进度永远读实时数据。
- **没有后端时**（直接双击 HTML 打开），笔记只写 localStorage，换浏览器就没了 —— 而且
  **导入功能完全不可用**（切分逻辑在 Python 那边）。
- **手机端实测截图在 `_shot/`**，是用 headless Chromium 按 390×844 渲染的，不是真机。
  真机上的滚动惯性和点击热区只有你上手才知道。
- **本地 7B 模型的精读质量明显不如云端大模型**：类比偶尔会跑偏、`mechanism`
  有时只是把 `points` 换个说法。够用但不惊艳；对质量要求高就切 `LLM_PROVIDER=cloud`。

---

## 部署到手机 / 服务器（AI 起不来怎么办）

完整说明见 **[DEPLOY.md](DEPLOY.md)**。核心一句话：
**AI 精读是最后一道可选工序，少了它只是少一个按钮，不是少半个应用。**

| 形态 | 怎么起 | AI 能不能用 |
|---|---|---|
| 电脑当服务器，手机同 WiFi | `python back_study/run.py 8080 --lan` | 能（复用本机 Ollama，离线免费） |
| 云服务器（1核2G 跑不动 7B） | `AI=off python3 back_study/run.py 8080`，或配云端 key | 关掉 / 换云端 |
| 纯静态托管（连服务器都不要） | 整个目录丢静态空间 | 不能（没后端）—— 但卡片/复习/笔记照用 |

`AI=off` 会关掉精读那一块，前端把它换成说明文字 + 「重新检测」按钮，其余接口全部 200。
实测（`OLLAMA_HOST` 指向死端口模拟服务器没装 Ollama）：health / stats / cards / docs /
graph / outline / notes / review 全部 200，**只有 `/api/llm/enrich` 返回 502 + 人话文案**。

**关于局域网地址探测**（`back_study/core/netinfo.py`，两版共用）踩过两次坑，现在用打分排序：

1. 不能用 `socket.gethostbyname(hostname)` —— 装了 VirtualBox / Hyper-V 的机器上它会返回
   Host-Only 网卡地址（本机实测 `192.168.56.1`，手机连它必然超时）。
2. 也**不能只靠 UDP 出口 IP**。改用出口优先后确实好过一阵，直到这台机器上开了 TUN 模式的
   代理软件：默认路由被虚拟网卡劫持，出口 IP 变成 `198.18.0.1`（代理的 fake-ip 段）——
   按出口 IP 排最前，恰好把最不可能连上的那个排到了第一位。

现在的规则：真实内网段（10/8、192.168/16、172.16/12）加分，代理 fake-ip / Host-Only /
link-local / CGNAT / Docker 网桥重扣分，出口 IP 只小幅加分。实测真实地址 `10.71.215.180`
稳定排第一，虚拟网卡沉底但**不删除** —— 万一你确实要在虚拟网络里访问。

---

## 力导向布局：为什么不能写死斥力常数

图谱的力导向实现在 `web/src/views/graph/`（Vue 版）。规则只有一处要改 —— 旧版单文件页已删除。

**踩过的坑**：最初把斥力写成常数 `REP = 9000/24000`。这组值是按大画布调的，
放到手机（343×430）上斥力远大于画布能容纳的尺度，实测结果：

| | 中心区域节点占比 | 贴边节点 | 最近两节点净间距 |
| --- | --- | --- | --- |
| 写死常数 | **0.00**（中间空一大块） | **0.94**（全挤在四条边） | **-9.7px**（重叠） |
| 动态 k | 0.37 | 0.00 | +14.7px |

**现在的做法**（三条，缺一不可）：
1. 理想边长 `k = 0.95 * sqrt(W * H / n)`，由画布面积和节点数算出来 —— 换画布尺寸自动适配。
2. 斥力用平方反比 `k² / d²`、引力用 `d² / k` 的量纲，两者同阶结构才收得住。
   （用 `k²/d` 时斥力量级远大于中心回拉，节点会被顶到四边。）
3. **不硬夹边**，改为收尾时把节点云等比缩放居中铺满画布（`gFit`）。
   夹边是「空心方框」的直接原因。

调参不能靠肉眼：`_shot/` 之外我留了个数值基准的做法 ——
同一份数据跑多个参数组合，打印「中心占比 / 贴边比例 / 最小净间距」三个指标取中位数，
比反复截图快得多，也能防住力导向本身的随机性。

---

## 图谱为什么改成 Canvas 粒子（2026-09-22）

原来是 SVG：一个节点一个 `<g>`，每帧 `setAttribute` 改 transform。
静态图上没问题，但要做粒子效果（每帧都得变）就撑不住了 —— 几十个节点就是每帧改上百个
DOM 属性，手机上肉眼可见地卡。现在换成 Canvas 2D，一次绘制，代价与节点数无关。

**粒子构成**（都在 `gDraw()` 里）：

| 元素 | 做法 |
| --- | --- |
| 节点本体 | 实心圆 + 左上角高光点（点出球感） |
| 外光晕 | 预生成的径向渐变贴图 `glowTex(颜色)`，`drawImage` 缩放复用 + `globalCompositeOperation='lighter'` |
| 环绕粒子 | 每节点 5~8 颗小光点绕核心公转，轨道 Y 轴压到 0.78 模拟倾斜的环 |
| 边的光点流 | 每条边一颗光点沿线走，到终点回到起点；语义边比层级边快一倍、亮一倍 |
| 背景尘埃 | 屏幕坐标的浮尘，缓慢漂移 + 一亮一暗（`sin` 相位），不跟随平移缩放 |
| 选中涟漪 | 两圈相位差 0.5 的扩散环 |

**「在动」是怎么保证的**：`gStart()` 里的 `requestAnimationFrame` 循环**不设终止条件**。
跑满 240 帧后不是停机，而是 `G.live = true` 转入**静息态** ——
力学步长压到 5.5%，每颗节点带自己的呼吸相位做气泡式浮动。
所以收敛之后整张图仍然是活的，而不是「咔」一下定死。

**两个必须守住的性能点**：
1. 光晕贴图按颜色缓存（`_GLOW`），不能每帧 `createRadialGradient` ——
   60 节点 × 8 颗粒子 × 每帧 = 每帧几百次渐变对象创建，GC 顶不住。
2. `gBind()` 里有 `if (G._bound) return;`。`renderGraph()` 每次切标签 / 重置 / 切局部图谱
   都会调用，不拦一道的话 window 上的监听会一份份往上堆：拖一次节点触发 N 次 `gMove`，
   旧闭包还攥着上一批节点的引用，等于持续泄漏。

**切走必须停帧**：`switchTab()` 里 `if (t !== 'graph') gStop();`。
动画循环永不结束这件事，只在图谱可见时才是好事。

**切回来不重排**：`renderGraph()` 会记下上一轮各节点的坐标，画布尺寸没变就直接沿用，
并从静息态接着跑（`G.frame = 240`）。只有「重置布局」按钮（把 `G.W` 置 0 让复用失效）
才真的从头排一遍。

**各向异性归一化**：斥力是各向同性的，节点云天然趋近圆形，在扁画布（桌面 1440×630）
或竖画布（手机 390×660）上会空掉一大半。`gFit()` 允许两个方向各自多铺一点，
但封顶 1.45 倍 —— 拉过头节点会挤成一排，比留白更难看。

**验证「真的在动」**：截图工具只能拿到某一帧，所以留了 `?debug=1`，
它把帧数 / FPS 写进标签标题。另一招是截 `--virtual-time-budget=7000` 和 `=11000`
两张图做像素 diff：实测有 32.9% 的像素发生变化（4.07% 为强变化），
说明收敛之后画面仍在持续演进。

> 旧单文件版（`web/public/legacy.html`）里那份**仍是 SVG**，只同步了上面那三条布局规则。
> 粒子效果和双指缩放手势需要真机调试，无头环境验不了手感，所以没跟着改。

---

## 图谱的分层下钻（2026-09-22 二次改）

**问题**：图谱"乱"。根因不是画得不好，是**四层同屏** —— 领域 / 科目 / 主题 / 卡片全画在一起，
20 张卡就是 27 个节点 55 条边，边交叉、标签互压，第一眼看不出结构。

**做法**：切成几个 `scope`，一层一屏，默认只给最上面那层（`ST.gscope`，默认 `top`）。

| scope | 内容 | 规模（当前数据） |
| --- | --- | --- |
| `top` | 领域 → 科目。**空科目也画**（空心虚线圈 + 「待补」标签） | 10 节点 / 8 边 |
| `sub:<科目id>` | 科目 → 主题（主题上标着卡片数），**不展开卡片** | 5~6 节点 |
| `topic:<科目>\|<主题路径>` | 这一级主题 + 下一级 + 挂在这级的卡片 | 5~7 节点 |
| `all` | 四层同屏，留作补充，默认不进 | 53 节点 / 117 边 |
| `local` | 某张卡 + 它的直接邻居（从卡片侧栏点进来） | 5 节点 |

界面上的入口：

- **面包屑**（`renderGCrumb()`）在工具栏左侧，显示"现在在哪一层"，点它退回去。
- **同级科目切换条**（`renderGSubs()`）在工具栏下面，下钻之后横着点就能换科目，
  不用先退回总览 —— 比在图上找那个节点可靠（空科目在图上只有一个小圈）。
- 侧栏点到科目/主题会出现「展开这个科目 / 这个主题（N 张卡）」按钮（`data-scope`）。

### 三个必须知道的实现点

1. **`roots` 不能写成「category 或 subject 都算根」**。
   那样子目也成了根，一整个模块的点会全叠在同一个中心上（表现是"图上什么都没有"，
   因为所有节点都在同一坐标）。顺序是：有 category 用 category，否则用 subject，
   否则用最靠上的那一层 topic。

2. **模块总览层不走通用的力学积分**（`G.anchor`）。斥力按 `k²` 走，而这一层只有十个点、`k` 很大，
   累积几十帧就能把簇摊成一张稀网 —— 又变回"空心方框"。这一层直接向设计好的锚点回弹
   （`n.x += (n.ax - n.x) * .18 + n.vx * .02`），斥力只贡献一点抖动用来防止标签重叠。
   位置是按画布算的：宽屏模块并排、竖屏上下叠，模块内根在中心、其余节点围一圈，
   卡片跟着自己的主题的角度走。

3. **链式前缀要折叠**（`foldStart()`）。`topicPath` 的第一段常常就是科目名本身
   （AI工程 / SpringBoot），分层视图里它跟科目节点重名；而且 java 的 `SpringBoot`
   底下才并排展开 5 个主题，这一层对科目视图没有信息量。判据：这一层只有一个孩子、
   且没有卡片挂在这一层（有卡就说明这层是要看的）。折叠后 java 直接连到 5 个主题、
   ai 直接连到 4 个。

另外两个小坑：`renderGCrumb()` / `renderGSubs()` 必须**在量画布尺寸之前**调用 ——
那排 chip 是"有才显示"的（`:empty` 时 `display:none`），量完再插进去画布高度就是过期的，
底部会露出画面外一截。`gDraw()` 外面包了一层 `try`，出错就存进 `G.err` 由 `?debug=1` 显示 ——
绘制里抛异常的表现只是"画面定住"，而且 rAF 一抛就不再重排，很难查。

---

## 视觉层（外观）

极光背景 + 玻璃拟态 + 微动效，全部集中在 `index.html` 的「视觉层」那一段 CSS 里，
**插在 `@media (max-width:820px)` 之前** —— 写在后面会把手机端的覆盖规则压掉。

- `.aurora` 三团大模糊光斑缓慢漂移。中间用 `mask-image` 径向淡出，
  因为正文区在画面中央，极光糊在那儿会把字压得发虚（笔记页最初就是一片褐色脏污）。
- 顶栏 / 底栏 `backdrop-filter: blur()` 做毛玻璃。
- 内容面板补一层 `rgba(15,17,21,.45)` 的薄底，极光只作氛围若隐若现，不牺牲阅读对比度。

改配色先改 `:root` 里那几个变量（`--ac` 是主色，`--bg` 是最底色），
别在规则里散写 hex。

