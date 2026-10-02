# 原理卡片学习平台 — 架构约定（精简版，2026-10-02 对齐）

三份文档：README · docs/技术架构.md · docs/学习路线.md。目录 study/{back_study,web,data,docs}。小程序端 2026-09-26 删，但后端新增 mini/ 路由组（重做小程序后端）。

## 启动与后端装配
- 入口 `back_study/run.py` → `uvicorn app.main:app`。`app/main.py` 只收横切：CORS 白名单、请求体上限 16MB(超 413)、Cache-Control no-store、异常→{ok:false,msg}、SPA 回落、启动横幅(卡片数/AI/降级必须可见)。
- 路由拆两组：`app/routers/web/`（agent ai auth cards docs imports learning notes system 共 9）+ `app/routers/mini/`（auth learn）。`app/routers/__init__.py` 导出 ALL。

## 两个 Agent 子系统
- `agent/cards/`：文档→卡片生成 Agent。graph 只流转、runtime 落盘、router 定 HTTP。LLM 定切分点(structure/refine/chapter) + `dedup.py` 去重（解决"近重标题"）。id=`ag-`+md5(docId:idx)。
- `agent/qa/`：问答 Agent，已升级为**工具调用 + 联网**。`tools.py` 4 个工具(search_cards 等，docstring 给模型看)、`websearch.py` 360 搜索(免key、失败返回[]不抛)。`retrieval.py` 混合检索仍可用。

## 卡片库（2026-10-02：398 张，61→398）
新增：gen_interview_agent(112)/java(115)/cs(47)/redis(45) 面试卡；gen_python(6)+gen_latest_ai/java/python(各4) 最新技术卡；python 成正式科目。原 gen_* 8 科目(45) + springboot/aizhuan(各10) 保留。

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
74 文件未提交(uncommitted)；check.js 全绿状态未验证；向量检索未装 nomic-embed-text(仍走关键词降级)；progress/notes 无 user_id(BKT 前必补)；无单测/CI。
