# 原理卡片学习平台 — 架构约定（精简版，2026-10-02 对齐）

## ★ 项目全名：智径 EduPath · 多 Agent 自适应学习平台（2026-10-03 用户两次纠正）
**全名 = 智径 EduPath · 多 Agent 自适应学习平台**。
权威出处三处一致，别再猜：
- `app/config.py:60-61` → `API_DESC = "自适应学习平台的后端接口…"`
- `web/src/views/login/LoginView.vue:104` → 「多 Agent 自适应学习平台 ·
  把「我该学什么」交给它，你只管看懂」← **这句 slogan 就是最好的项目描述**
- `docs/学习路线.md:223` → 「EduPath 的定位是自适应学习平台。
  没有 BKT，"自适应"就只是"按你的手感排个序"」

「原理卡片」只是其中一个**内容品类**（卡片库），不是项目名。
⚠️ 改名只改了一半：`README.md:1` 标题仍是「原理卡片 · 学习平台」、
目录名还是 `study`，这两处待改（目录名不建议动）。

三份文档：README · docs/技术架构.md · docs/学习路线.md · **docs/开发者文档.md**（新增，最全）
目录 study/{back_study,web,data,docs}。小程序端 2026-09-26 删，但后端新增 mini/ 路由组（重做小程序后端）。

## 启动与后端装配
- 入口 `back_study/run.py` → `uvicorn app.main:app`。`app/main.py` 只收横切：CORS 白名单、请求体上限 16MB(超 413)、Cache-Control no-store、异常→{ok:false,msg}、SPA 回落、启动横幅(卡片数/AI/降级必须可见)。
- 路由拆两组：`app/routers/web/`（agent ai auth cards docs imports learning notes system 共 9）+ `app/routers/mini/`（auth learn）。`app/routers/__init__.py` 导出 ALL。

## 两个 Agent 子系统
- `agent/cards/`：文档→卡片生成 Agent。graph 只流转、runtime 落盘、router 定 HTTP。LLM 定切分点(structure/refine/chapter) + `dedup.py` 去重（解决"近重标题"）。id=`ag-`+md5(docId:idx)。
- `agent/qa/`：问答 Agent，已升级为**工具调用 + 联网**。`tools.py` 4 个工具(search_cards 等，docstring 给模型看)、`websearch.py` 360 搜索(免key、失败返回[]不抛)。`retrieval.py` 混合检索仍可用。

## 数据隔离（2026-10-03 已做，P0-1 完成）
`progress` PK `(user_id,card_id)`、`notes` PK `(user_id,id)`；jsonfile 两文件多一层 uid，老格式自动升级到匿名桶 `''`。db 层所有个人数据函数一律收 `user_id`。QA 工具走 `tools.set_current_user()`（ContextVar，因签名给模型看不能加参数）+ `runtime.ask_full(..., user_id)`。
**两条坑**：①光加列不改主键=没隔离（ON DUPLICATE KEY 只看主键，写路径静默覆盖）；②LEFT JOIN 的 user_id 必须写 `ON` 里，放 WHERE 会把未标记的卡滤掉。回归跑 `back_study/_verify_isolation.py`（14 项，自动清场）。

## 卡片库（2026-10-03 实测：416 张）
分布：java 180 / ai 139 / cs 50 / python 18 / major 6 / math 6 / politics 6 / english 5 / fe 4 / 导入 2。
来源：gen_interview_agent/java/cs/redis 面试卡、gen_python + gen_latest_ai/java/python、gen_* 8 科目、springboot/aizhuan。

## 规模与图（2026-10-03 实测，别再写旧数）
- 87 个 py / 18388 行；前端 50 文件 / 13883 行
- 图 **567 节点 / 2114 边**（416 card + 138 topic + 10 subject + 3 category），234 条先修边
- 卡片字段：id/title/oneLine/mechanism/why/analogy/scene/diagram/keywords/tags/topicPath(是**list**)/related/interviewQ/subject/category/domain/_src

## 算法层 back_study/algo/（纯标准库，不 import core）
- 契约 `base.py`，注册表 `__init__.py`（`get()/names()/register()`，传**实例**）
- 4 个：`sm2`(默认) / `fsrs`(FSRS-4.5) / `bkt`(不排期！答"掌握没") / `hlr`
- `graph.py`：pagerank / personalized_pagerank / betweenness / louvain / shortest_path / kcore + analyze/topn/coverage
- `eval.py`：**BKT 在 compare() 里被显式跳过**（不让它排期），所以是**三算法**排期对比
  种子实测 seed=7：FSRS 效率 0.0186 最优 / HLR 留存 66.52% 最高 / SM-2 留存 56.36%
  ⚠️ 三者 AUC 都在 0.51≈随机 —— 引用时必须主动说这是局限
  `demo.py` 是对拍台 CLI，`--algo/--retention/--days/--seq`

## 向量检索（2026-10-03 已跑通，不再是降级状态）
`nomic-embed-text:latest` 已装。索引 `data/store/embeddings.json` 416 条 / 4.1MB，
按卡片集合指纹懒构建、变化即重建；文档侧 `search_document:` / 查询侧 `search_query:` **前缀必须不同**。
实测：首建索引 2.9s → 命中 0.296s；向量能召回关键词漏掉的语义近邻卡。
`AGENT_RETRIEVER` = vector|keyword|hybrid（hybrid 默认）。

## OLLAMA 本地模型
qwen3:8b（默认对话）、deepseek-r1:7b、qwen2.5vl:7b（识图）、nomic-embed-text（检索）。


## 岗位/方向功能（实现用户"选岗位推知识点"）
- `data/directions.js`(DIRECTIONS)：学习方向，keywords 子串匹配卡片(topicPath/title/keywords)。
- `data/roles.js`(ROLES)：目标岗位(如 agent-dev=Java+Python Agent 开发)，skills={subject,weight,keywords} 对账"库里有没有这块卡"。
- 导出必须是对象非数组（否则被 check.js 当卡片校验）。

## 存储/算法/缓存（不变）
MySQL study_cards(json 降级，降级必须横幅可见)；PG study_algo + Redis(掌握度缓存，protocol=2)；算法 SM-2/FSRS/BKT。

## 鉴权/安全（不变）
jwt algorithms=['HS256']；**鉴权看"响应有没有个人数据"不是读写**；CORS 白名单非*；/api/llm/enrich 限 200 章。

## 发号/降级/沙箱（不变，踩过的坑）
id upsert 静默覆盖 → 草稿带指纹、publish 撞车报错；降级三处(store/algo/cache)都要横幅；DSH 沙箱写路径受限、stdio 管道 EPERM、Chrome 崩、git schannel 用 openssl。

## 待补 P0
- ⚠️ **git 提交历史损坏**（2026-10-03，`unable to read tree`，160 对象缺失）。
  代码/工作区 100% 完好，但 `git status/add/log` 部分不可用、无法回滚。
  完整备份 `D:\09-Backup\study-git-20261003\`（5297 文件），恢复方案待用户拍板。
- 无单测/CI（`_verify_isolation.py` + `scripts/check.js` 是仅有的自动化）
- 181 节点力导向图仍很糊 —— 物理极限非 bug，等拍板社区聚合视图
- AI 工程 6 张卡语义孤立（需补 `related`，算法救不了）
- check.js 每次跑会建 `zz_*` 探针账号（隔离后不污染他人数据，但会留垃圾账号）

