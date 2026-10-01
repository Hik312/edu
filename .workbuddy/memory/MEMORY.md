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

## web 前端
四层 view→store→api→client。单一主题暖牛皮纸(tokens.css :root，无data-theme)。★chartBase legend 显式 show:false；EChart 懒初始化(0×0 init 力导向图收敛原点)；AI 可用性唯一依据 /api/llm/status。vite.config 写死 host 127.0.0.1+strictPort。

## 命令/清理
全量校验 node back_study/scripts/check.js（py编译+pyflakes+39冒烟+json/mysql队列一致）。★pyFiles 手维护，加新 py 必回补。★删目录别吞错误（删完 ls 复核）。curl 必加 --noproxy '*'。

## 待补 P0
progress/notes 无 user_id（多账号共享进度，做BKT前必补）。无单测/CI/refresh令牌/复习提醒。向量检索未装 nomic-embed-text（仍走关键词降级）。gen 卡有少量近重标题需人工去重。
