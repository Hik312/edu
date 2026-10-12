# 智径 EduPath · 多 Agent 自适应学习平台 — 架构约定（精简版）

## ★ 项目全名（2026-10-03 用户两次纠正，别再猜）
全名 = **智径 EduPath · 多 Agent 自适应学习平台**（"原理卡片"只是其中一个内容品类，不是项目名）。
权威出处：`app/config.py:60-61` API_DESC / `web/.../LoginView.vue:104` slogan / `docs/学习路线.md:223`。
目录 `study/` 不建议改名；`README.md:1` 标题仍是旧名待改。
文档三件套：README · docs/技术架构.md · docs/学习路线.md · docs/开发者文档.md（最全）。
结构 `study/{back_study,web,data,miniapp,docs}`。miniapp 端存在（36 文件 + 后端 9 端点），与 web 共用卡片库/调度算法。

## 启动与装配
- 入口 `back_study/run.py` → `uvicorn app.main:app`。`app/main.py` 只收横切：CORS 白名单、16MB 上限、no-store、异常→{ok:false,msg}、SPA 回落、启动横幅(卡片数/AI/降级必须可见)。
- 路由：`app/routers/web/`（agent ai auth cards docs imports learning notes system 共 9）+ `app/routers/mini/`（auth learn）。导出 `ALL`。

## Agent 子系统
- `agent/cards/`：文档→卡片 Agent。LLM 定切分(structure/refine/chapter) + `dedup.py` 去重。id=`ag-`+md5(docId:idx)。
- `agent/qa/`：问答 Agent，工具调用 + 联网（360 搜索免 key）。`rerank.py` 用 bge-reranker-v2-m3（CPU 无 GPU，`rerank()` 与 `rerank_texts()` 两版）。`retrieval.py` 混合检索。

## 关键数据
- 卡片库 527 = 内置 525(`data/*.js`，漏 `module.exports` 静默跳过) + 自定义 2(`ag-*`)。科目：ai139/java104/middleware82/cs61/python60/algorithm29/fe27/其他。图 819 节点/2713 边，语义孤岛已清零。
- 算法 `algo/`：`fsrs`(默认)/`sm2`/`bkt`(不排期，答"掌握没")/`hlr`。`eval.py` 三算法排期对比（BKT 跳过），AUC≈0.51 随机是局限。**开发者文档 §5/§6 写"默认 SM-2"已错**。
- 向量：`nomic-embed-text` 已装；索引 `data/store/embeddings.json`；`search_document:`/`search_query:` 前缀须不同。
- OLLAMA：qwen3:8b(默认) / deepseek-r1:7b / qwen2.5vl:7b(识图) / nomic-embed-text(检索)。
- 存储：MySQL study_cards(json 降级) / PG study_algo + Redis(掌握度缓存,protocol=2)。

## 数据隔离（P0-1 完成）
`progress` PK `(user_id,card_id)`、`notes` PK `(user_id,id)`。db 个人数据函数一律收 `user_id`。QA 走 `tools.set_current_user()`(ContextVar) + `runtime.ask_full(...,user_id)`。回归 `_verify_isolation.py`(14 项)。
⚠️ documents 与 kb_tree **没有** user_id 隔离（新账号见全部），与 progress/notes 不一致。

## 知识库 documents（2026-10-11 修）
`app/routers/web/docs.py` + `KnowledgeView.vue` + `web/src/api/knowledge.js`。论文显示原件/改名/导入选类型已落地。
- `documents` 表原 4 字段 `raw_file/is_paper/tags/doc_text` 从没建过 → 写过即丢不报错 → `canShowOriginal` 恒 false。已在 schema.sql + mysql.py 的 DDL_TABLES + _ADDED_COLUMNS 三处同步。
- `docparse.raw_path(did, ext)` 的 ext 须容忍前导点 `'.pdf'`。
- 论文也留 `text`（之前留空=排除 RAG，白导入）。原件走 iframe、抽取文本供检索/RAG。
- `docType` 手动选优先于 `_looks_like_paper` 自动判据。

## 知识库树 + PDF 阅读器
- 后端 `core/kbtree.py`(存 `meta.kb_tree` 单例) + 7 树端点；每次写回传整棵 tree，前端只覆盖。
- `PdfViewer.vue`(pdf.js 4.10.38)：`GlobalWorkerOptions.workerSrc` 必填；无头降级用 `await import('pdf.worker.min.mjs')` 走 fake worker；`renderAll` 必须串行化(否则两调用交错整篇空白且控制台干净)；ResizeObserver 首次 observe 必回调；缩放做整页/适宽开关别替用户选默认；vite build 清空 dist 后 token/引导页要重生成。

## 文档问答 / 翻译（2026-10-12 重构中）
- `core/docqa.py`：切块按句边界+120 字重叠；跨语言检索(术语表 zh→en + LLM 译英文词)解决中文问英文论文；`rerank_texts` 两阶段重排；自进化记忆落盘 `data/store/qa_log/<docId>.json`(similar_qa 注入 / 👎 feedback_qa 标记)。
- 翻译 `core/translate.py`：`_PROTECT_RULES` 正则占位保护数字/公式/引用/图片 token `![](media:..)`；`SYS_TRANS` 反垄断模板；`transjob.py` 低温度。
- 前端 `BilingualView.vue` 解析 `![](media:..)` 渲染图片+"原文图片·未译"徽标；`knowledge.js` 加 feedbackQa/captionFigure；QA 面板加 👍/👎。

## 通用陷阱（永久记住）
1. **写路径写了库里没有的字段 = 静默失败**：INSERT 该列直接丢弃不报错，`_doc_of` 读不出。判定法：`SHOW COLUMNS` 逐字比对；新字段三处同步(schema.sql + mysql.py DDL_TABLES + _ADDED_COLUMNS)；写读成对加后打真 HTTP 看返回体。
2. **校验通过 ≠ 测到了**：`check.js` 靠 `require()`+Array.isArray，漏 `module.exports` 的文件后端读得到、check 静默跳过，核对 `cards loaded: N` 与后端卡片数。
3. **改 subject 等字段前先查消费方**（stats.domains / roles.js 技能词），对账是按科目过滤后匹配，关键词须是卡里真写法。
4. **端点参数名须与前端一致**（如 `alias='cardId'`），否则返 200 但静默退化。
5. 重排/向量超时降级必须保留召回顺序并打日志，不可抛异常中断主链路。

## 待补 P0
无单测/CI（建议 pyflakes+check.js+smoke_profile 进 pre-push）。`ProfileCenterView.vue` 1172 行超 700 上限 + Options API。

## 新增脚本（back_study/scripts/，用 .venv 跑）
migrate_middleware / fix_domain / fix_related_islands / fix_frame_kind / dbseed.py --sync / backfill_doc_fields / test_kbtree.py / probe_kbtree.py / probe_docqa.py。正则取宽松 `(\\[.*\\])\\s*;`。
