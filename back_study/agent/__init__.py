# -*- coding: utf-8 -*-
"""AI Agent 层（LangGraph + LangChain + 本地 Ollama）。

**这是可选的旁支，不是后端主链路的一部分：**

    主链路   app/routers/*  →  core/db.py  →  core/store/*     必装，缺了起不来
    旁支     agent/*                                           可选，缺了只是没有 AI

## 目录按业务分，公共的只在根上放一份

    agent/
    ├── config.py     【公共】所有可调参数（温度 / 重试上限 / 检索条数）
    ├── model.py      【公共】造模型，唯一决定「用哪个模型」
    │
    ├── qa/           【业务】问答 —— 已跑通，接口 /api/agent/ask
    │   ├── tools.py    能做什么（查卡片）
    │   ├── nodes.py    每步做什么（检索 / 回答 / 自检）
    │   ├── graph.py    按什么顺序做
    │   ├── runtime.py  怎么跑起来（实例缓存 / 多轮 / 流式）
    │   └── demo.py     命令行
    │
    └── planner/      【业务】学习路径规划 —— 服务 /path 今日路径页
        ├── planner.py  图 + 节点（write 节点待填）
        └── run.py      命令行

**为什么要按业务分**：`nodes.py` / `graph.py` 这类名字是**一个 Agent 的内部结构**，
放在包级别会让人不知道这到底是谁的 nodes。业务子目录 + 公共层在根，
才能一眼看出「哪些是大家共用的、哪些是这个 Agent 自己的」。

**加新 Agent**：建一个子目录，抄 `qa/` 的五文件结构，
`from .. import config, model` 拿公共层，其余自己写。**不要复制 config / model**，
否则会出现「网页精读用 qwen3、这个 Agent 用另一个」。

## 三条硬约束

1. **不进主链路。** langchain 全家桶 import 一次 2-3 秒，塞进 app/main.py
   等于让每次后端冷启动都替 AI 买单 —— 而多数请求根本不碰 AI。
   所以 FastAPI 侧（app/routers/agent.py）在函数内部 import 本模块。

2. **零成本 import。** model.py 和 qa/tools.py 把 langchain 的 import 写在函数里
   —— 因为 `/api/agent/status` 探活端点要用它们，而探活不该拉起整棵依赖树。
   nodes / graph / runtime 是「真要跑 agent 才加载」，可以在顶部 import。

3. **模型选择复用 core/llm.py。** 不在 agent 里另起一套模型优先级，
   否则会出现网页端精读用 qwen3、agent 用另一个、然后你以为是模型不行。
"""
import os
import sys

# 把 core/ 挂进 sys.path，这样 qa/tools.py 里能 `import db`。
# 和 app/__init__.py 的做法一致（那个文件里写了为什么非要动 sys.path）。
# 放在这里是让 agent 能被独立运行，不必先 import app。
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(os.path.dirname(_HERE), 'core'), os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
