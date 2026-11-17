# -*- coding: utf-8 -*-
"""cards Agent —— 文档 → 卡片的那条链（按 qa/ 的五文件结构抄的第四件）。

    structure（结构精修）   规则初切的章节清单 → LLM 定切分点 → 重切分章
    chapter（逐章出卡）     图注（VLM）→ 生成卡片 → 对齐自检 → 不过重写
                            → 去重（embedding 语义比对，重复不入池）

对外接口：`runtime.py`（`run_structure` / `run_chapter`），
HTTP 端点：`app/routers/agent.py` 的 `/api/agent/cards/*`。

和 qa Agent 的分工：
    qa     回答问题，靠卡片库检索做依据（读）
    cards  生产卡片，靠原文 grounding 防文不对题（写）

文件顺序就是数据流顺序：

    nodes.py     每步做什么 —— 结构精修 / 图注 / 生成 / 对齐自检
    graph.py     按什么顺序做 —— 两张图（structure 与 chapter）
    runtime.py   怎么跑起来 —— 装图、幂等、落盘（草稿 + 图片拷贝）
    dedup.py     出卡前查重 —— 本地 embedding 余弦比对，模型缺失时放行

硬约定和 qa 一致（见 agent/__init__.py）：不进主链路（路由函数内 import）、
模型选择复用 core/llm.py、config/model 走公共层不自己另起一套。
"""
