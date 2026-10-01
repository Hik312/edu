# -*- coding: utf-8 -*-
"""路径规划 Agent —— 服务 `/path` 今日路径页。

    取候选 → 排序 → 写理由（唯一调模型） → 自检 → 没过检就重来

★ 现状：`planner.py` 里 `collect` / `score` / `verify` / `route` 已写好并验证过，
只有 **`write`**（写理由，唯一调模型的节点）留了 3 处 `TODO(你)`。

动手前先跑（不调模型，几秒出结果，用来验地基对不对）：

    .venv/Scripts/python.exe back_study/agent/planner/run.py --dump

填完 `write` 再跑全图：

    .venv/Scripts/python.exe back_study/agent/planner/run.py --top 5
"""
