# -*- coding: utf-8 -*-
"""问答 Agent —— 已跑通的那个，也是**写新 Agent 时的参考答案**。

    检索 → 回答 → 自检 → 没过检就重来（最多 C.MAX_TRIES 次）

对外接口在 `runtime.py`（`ask` / `run_react` / `stream_react`），
HTTP 端点在 `app/routers/agent.py`。

文件顺序就是数据流顺序，改行为按这个顺序找：

    tools.py     能做什么 —— 4 个工具查 core/db
    nodes.py     每步做什么 —— 检索 / 回答 / 自检
    graph.py     按什么顺序做 —— 连线（固定流程 & ReAct 两条）
    runtime.py   怎么跑起来 —— 实例缓存 / 多轮历史 / 流式
    demo.py      命令行入口
"""
