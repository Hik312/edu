# -*- coding: utf-8 -*-
"""卡片校验 / 自纠 Agent。

把「联网搜索」+「快速执行」两个能力合成一条流水线：
  ① 查数据库（卡片库检索定位本地卡）
  ② 联网找知识点（web_search + github_search —— 即之前加的两个 MCP 工具背后的能力）
  ③ 验证本地知识（LLM 把本地卡 vs 网络资料对一遍）
  ④ 发现不对 → 给出「哪张卡 / 哪个字段 / 建议改什么 / 理由」，交由前端确认
  ⑤ 用户确认 → 调 db.apply_card_patch 把卡片原文改掉（内置卡走同 id 自定义覆盖）

半自动：模型只给建议（proposed_patch），落库必须由用户点「应用」触发。
"""
from . import runtime
