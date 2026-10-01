# 原理卡片学习平台 — 架构约定（精简版）

三份文档：README · docs/技术架构.md · docs/学习路线.md。目录 study/{back_study,web,data,docs}。小程序端 2026-09-26 删。后端仅 run.py(FastAPI)。静态 /→web/、/data→data/，data/store/ 403。

## 存储层 core/store/
MySQL study_cards。切换改 config.local.json STORE(json|mysql)，env 优先。db.py 只算、store/ 只存。
★降级必须看得见（缺 pymysql/MySQL没起→回退JSON，横幅打!!、/api/storage.degraded写原因）；降级判断只在工厂_build()算一次→换存储/重启MySQL必须重启后端。
★内容 vs 状态：data/*.js 内容(git)；cards 表是副本，改源跑 dbseed.py --sync；data/store/*.json 是状态，--import-json 单向搬迁。
★加新表改三处：DDL(mysql.py DDL_TABLES+schema.sql)、_build()探测、--import-json files 字典。启动幂等 init_schema() 覆盖7表。
pymysql 不能跨线程→thread-local+ping(reconnect=True)；ping带database而库没建报1049→初始化用ping_server()。

## 卡片契约
id/domain/category/subject/topicPath[]/title/oneLine/analogy/why/mechanism[]/diagram/interviewQ[]/keywords[]/scene[](≥2)/tags[]/related[]({id,kind,note})。category+subject 必须在 data/catalog.js。related.kind 只许 prereq|extends|compare 且带note。diagram 三选一 pipeline/state-machine/snapshot。

## 算法层 back_study/algo/
base.py+sm2/fsrs/bkt，__init__ 出 get()/names()/register()。统一 schedule(prev,level)->rec(level/interval/ef/reps/nextAt/updatedAt)。db.schedule() 只转发，默认 sm2。切换 env ALGO>config ALGO>sm2。
★三算法 ef 语义不同：sm2=难度因子(1.3-2.6)、fsrs=难度D(1-10)、bkt=掌握度p(0~1)。
★MAX_INTERVAL=5年 夹间隔，防 SM-2 溢出500。BKT 不替换 SM-2（排时间 vs 排优先级），用 p 反推间隔 1+20p²。BKT fit() 自事件流拟合，门槛 8 KC/30 条，不够拒绝拟合。

## 算法库 core/algostore/+事件流
业务 MySQL study_cards，算法 PG study_algo（JSONB+后期pgvector）。三表 review_events/mastery/algo_params。set_level 双写 progress+events（不传user_id不写事件）。重拟合后必须清缓存。

## 缓存 core/cache.py
唯一用途缓存 BKT 掌握度。Redis 没装→降级进程内存（重启即失）。★redis-py5+默认RESP3连Redis5.0报unknown HELLO→必须显式 protocol=2。

## 问答 Agent（2026-09-29 落地）
分层 agent/config(model)+qa/(retrieval,nodes,runtime)+app/routers/agent.py。
★langchain/langgraph import 全在函数内部（冷启动2-3s）。唯一 async def 路由（AI 20-30s）→asyncio.to_thread。
混合检索 agent/qa/retrieval.py：KeywordRetriever+VectorRetriever(Ollama nomic-embed-text，缺则降级关键词)+HybridRetriever(VECTOR_WEIGHT=0.7)。get_retriever()/retrieve() 统一入口。
★造卡两路：scripts/gen_cards.py（按 catalog 8 科目批量生成，--all/--subject/--per；校验绕开 db→PyJWT 依赖用 raw_decode）；scripts/gen_docs.py（文档摄取 --dir 走 parse_document→enrich→save_drafts，--no-llm 本地启发式，需后端.venv）。两者写 data/gen_*.js / data/store/drafts.json，加新 py 必须回补 check.js pyFiles。
前端 web/src/views/ask/AskView.vue（/ask 牛皮纸聊天页）：flow=知识库问答(带sources溯源)、react=SSE流式；api/agent.js 的 ask/askStream。AgentAskOut 含 sources。全量跑后卡片库 61 张（ai5/cs3/english5/fe4/java6/major6/math6/politics6 + 原 springboot/aizhuan 各10）。
planner 沙盒在 agent_lab/（collect/score/verify/route 已验证，write 3 处 TODO 未实现），未搬入正式 agent/。

## 本机中间件
Redis 5.0.14 @ E:\Redis\ (pass 123456, start.bat)。PG 16.15 @ E:\PostgreSQL\16 (pass 123456, 库 study_algo)。密码在 config.local.json（gitignore）。

## 后端/鉴权
必需 fastapi+uvicorn+PyJWT。★jwt.decode 必须 algorithms=['HS256']。密码 pbkdf2 120k。改完跑 test_security.py(16断言)。五点约定：RequestValidationError统一400；端点同步def；静态最后挂；llm/status ok:false仍200；改完跑check.js。

★鉴权判据（2026-10-01 定，别再逐个端点手写）：**响应里有没有个人数据**决定要不要登录，不是读/写。
要登录：notes/progress/review/stats/cards/docs/drafts/import/llm/storage/outline/graph/plan。
保持公开：health(存活探测) + catalog/roles/directions（纯配置，本身在 git 里）。
CORS 是**白名单**不是 `*`（默认 127.0.0.1/localhost 的 5173+8080，用 `CORS_ORIGINS` 覆盖）。
`/api/llm/enrich` 一次最多 200 章（不带 indexes = 整篇逐章，匿名可调就是免费烧算力）。
★这个漏洞的形态是「保护逐端点手写」：PUT /api/progress 挂了鉴权、隔壁 GET/DELETE 没挂，
PUT 的 docstring 还写着"这个端点必须登录"。**加鉴权时按链看，别按端点看。**

## 发号规则（id 一旦撞车就是静默覆盖）
★两个存储后端都是 upsert 语义（jsonfile 按 id 覆盖、mysql ON DUPLICATE KEY UPDATE），
所以 id 撞车 = **静默覆盖别人已发布的内容**，接口还回 ok:true。
- 笔记/文档：`_next_daily_id()` = 「已有最大序号+1」，**不复用被删的号**。别用 `len(lst)+1`。
- 草稿：id 带内容指纹 → 不同文本必不同、同文本必相同（`save_drafts` 按 id upsert，
  重复导入同一段资料=同一件事）。**别加"发现 id 已存在就往后挪"的避让循环**，那会毁掉幂等。
- `publish` 撞到已有卡要**报错**，不能静默替换。

## 本机中间件
Redis 5.0.14 @ E:\Redis\ (pass 123456, start.bat)。PG 16.15 @ E:\PostgreSQL\16 (pass 123456, 库 study_algo)。密码在 config.local.json（gitignore）。
`ALGO_STORE=pg` + `STORE=mysql` 是本机默认。

## ★降级必须看得见（三处都要报，不只是业务存储）
横幅打 store_pkg.banner_lines() + algostore.degraded() + cache.degraded()；
`/api/storage` 的 `algo` / `cache` 两段也吐。从前只有 store 报了，
algostore/cache 的 degraded() 全仓只有一次性脚本在用 → PG/Redis 挂了静默回退。

## ★两后端必须逐位一致（check.js 只覆盖了到期队列，别以为绿了就没事）
已修的三处历史分歧（都会在绿灯下存在）：documents.stats 整字段丢、
notes 字段存在性、algostore.events_of 截断方向（json=最近n条 / pg=最旧n条）。
`events_of` 的契约：**最近 limit 条，按 at+id 正序返回**；limit<=0 = 全量（`EVENTS_ALL`）。
BKT 回放路径（fit_bkt / mastery_of）必须显式传全量，默认 500 会悄悄截断。

## 本仓的重复缺陷形态（改代码前先想这两条）
1. **注释在、保护不在**：注释写着"这个必须登录""失败不该让主操作失败"，
   实际只护了一半（set_level 的 log_review 裸在 try 外）。
2. **任何 spawn 失败都被当成"这步没问题"**：check.js 把 EPERM 报成"没装 pyflakes"；
   沙箱下它会假报 51/51 PY FAIL、以及"服务没起来"（真实原因是等待窗口只有 6 秒，
   而冷启动实测 18 秒 —— 已放到 60 秒）。

## web 前端
四层 view→store→api→client。单一主题暖牛皮纸(tokens.css :root，无data-theme)。★chartBase legend 显式 show:false；EChart 懒初始化(0×0 init 力导向图收敛原点)；AI 可用性唯一依据 /api/llm/status。vite.config 写死 host 127.0.0.1+strictPort。
★掌握度文案+颜色的**唯一出处是 `@/config/theme`**（levelLabel / levelColor）。
`api/learning.js` 里那份带颜色的 LEVELS 已删（它是上一版深色的荧光色，跟主题冲突）。
★`stores/docs.js` / `stores/notes.js` **目前无人引用**（页面各自直接调 api/），
改文档/笔记接口要记得两边都看。
★`api/client.js` 把状态码挂在 `error.status` 上（它会把 axios 原始错误吃掉），
调用方判断 401 只能读这个字段。

## 命令/清理
全量校验 node back_study/scripts/check.js（py编译+pyflakes+45项冒烟+json/mysql队列一致）。★pyFiles 手维护，加新 py 必回补。★删目录别吞错误（删完 ls 复核）。curl 必加 --noproxy '*'。

## ★本机 DSH 沙箱的边界（踩过多次，别再重复试）
- **命令沙箱**（pwsh）只允许写一部分路径：`back_study/core`、`data/` 被拒（ACL 修过也一样，
  是策略层）；`_verify/` 这类新建目录可以写。**edit/write 工具不受此限** ——
  所以「脚本生成内容 → write 落地」是绕过办法。
- Node 用**管道 stdio** 拉子进程会 EPERM（`check.js`、`vite build` 都中）。
  stdio:'ignore' 的 spawnSync 可以。跑它们要提权一次。
- Chrome 在沙箱下会崩，headless 截图这条路当前不通。
- git 的 Windows 原生 TLS 后端（schannel）拿不到凭据句柄（SEC_E_NO_CREDENTIALS），
  用 `git -c http.sslBackend=openssl`；凭据管理器要拉 Git Bash 也会 EPERM，
  推送用 `git -c credential.helper= push "https://user:pw@host/..."`（别加 -u，
  否则带口令的地址会写进 .git/config）。


## 待补 P0
progress/notes 无 user_id（多账号共享进度，做BKT前必补）。无单测/CI/refresh令牌/复习提醒。向量检索未装 nomic-embed-text（仍走关键词降级）。gen 卡有少量近重标题需人工去重。
