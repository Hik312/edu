# -*- coding: utf-8 -*-
"""MCP 服务端（stdio）—— 把"造卡能力"作为标准 MCP 工具暴露出去。

这是协议的**服务端**：用 FastMCP 声明一个工具 `generate_card`，复用项目已有的
cards Agent 造卡逻辑（`agent/cards/nodes.draft`：CARD_SYS 提示词 + 本地 LLM + 清理），
给定「知识点主题」（+ 可选资料原文）产出一张原理卡片 JSON。

为什么这个工具值得加 —— 对应"造卡能力的 MCP server"诉求：
  造卡原来只在「导入 PDF → 逐章转卡」这条内部流水线里发生。把它包成 MCP 工具后，
  **任何能调 MCP 的客户端/另一个 Agent** 都能直接说"帮我造一张关于 X 的卡"，
  不必走完整的文档导入流程。这也是"外部工具不只是检索，也能是生产动作"的示范。

边界（必须看清）：
  - 这是**真实调用本地 LLM（Ollama）** 生成内容，需要模型服务可用；
    不可用 / 输出非 JSON → 返回说明文案，不抛异常、不污染协议流。
  - 复用既有 CARD_SYS 的"事实红线"：有 source 时内容尽量贴原文，
    没 source 就靠模型自身知识（卡片会更泛，适合做草稿再人工补）。
  - 产出是**草稿卡**（_draft=True），走和导入草稿一样的"人工确认才入库"链路。

运行方式（被 MCP 客户端以子进程拉起，走 stdio JSON-RPC）：
  .venv/Scripts/python.exe agent/servers/cards_mcp.py
"""
import os
import sys
import json

# 让这个子进程能 import 到项目根目录的 agent / core 等模块
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if os.path.join(_ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "core"))

# stdio server 的 stdout 只能有 JSON-RPC 报文，框架调试日志必须关掉。
import logging
for _n in ("mcp", "mcp.server", "mcp.server.lowlevel"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cards")


@mcp.tool()
def generate_card(topic: str, source: str = "") -> str:
    """根据一个知识点主题（和可选的资料原文），生成一张「原理卡片」。

    当用户 / 另一个 Agent 说"帮我造一张关于 X 的卡""把这个知识点做成卡片"时用这个——
    它复用项目已有的造卡逻辑（和 PDF 导入走同一条链路），不必走完整文档导入。

    参数:
      topic  : 知识点名称（如 "布隆过滤器"、"TCP 三次握手"、"SM-2 间隔算法"）
      source : 可选的资料原文 / README / 博客（建议从 github_search 拉来的内容喂进来），
               不给就用模型自己的知识生成（卡片会更泛，适合做草稿）。

    返回一张卡片的 JSON：title / oneLine / analogy / why / mechanism / keywords /
    scene / interviewQ。注意：产出是草稿，需人工确认才入库。
    注意：这会真实调用本地 LLM（Ollama），需要模型服务可用。"""
    if not topic or not topic.strip():
        return "（没有给出要造卡的知识点）"
    try:
        from agent import config as C
        from agent import model as M
        from agent.cards import nodes
    except Exception as e:
        return "（造卡模块加载失败：%s）" % e

    # 合成一份最小 state 喂给 draft 节点（它本来吃 chapter 级 state）
    doc = {"id": "mcp-%s" % topic.strip()[:20], "title": topic.strip(),
           "subject": "", "domain": "MCP造卡", "category": ""}
    chapter = {"title": topic.strip(), "body": (source or topic).strip()}
    state = {"doc": doc, "chapter": chapter, "index": 0,
             "captions": {}, "tries": 0, "msg": ""}
    try:
        # draft 节点：CARD_SYS 提示词 → M.chat().invoke() → _clean_card 收尾
        res = nodes.draft(state)
        card = (res or {}).get("card") or {}
    except Exception as e:
        return "（造卡失败（LLM 不可用或输出非 JSON）：%s）" % e

    # 只回核心卡片字段，不把 _draft/_from/deck 等内部字段透传给模型
    keep = ["title", "oneLine", "analogy", "why", "mechanism",
            "keywords", "scene", "interviewQ"]
    out = {k: card.get(k) for k in keep if k in card and card.get(k)}
    if not out.get("title"):
        return "（造卡未产出有效卡片）"
    return json.dumps(out, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # transport 默认 "stdio"：从 stdin 读 JSON-RPC 请求，往 stdout 写响应。
    # 不要在这里 print 调试信息到 stdout —— 会污染协议流，只能写 stderr。
    mcp.run()
