# -*- coding: utf-8 -*-
"""MCP 服务端（stdio）—— 把一个"联网搜索"能力作为标准 MCP 工具暴露出去。

这是协议的**服务端**：用 FastMCP 声明一个工具 `web_search`，底层复用项目已有的
`websearch.web_search`（360 爬虫逻辑，免 key、失败返回 [] 不抛）。

为什么值得单独成一个 server：
  以前 360 爬虫是写死在 agent 进程里的函数（`agent/qa/websearch.py`），模型只能
  "被灌"搜索结果，不能自己决定去搜。现在把它包成 MCP 工具，模型在 ReAct 里就能
  **自己决定调不调、搜什么**——这才是"Agent 能对外行动"的一步。而且换搜索源
  （Tavily/SerpAPI/Brave）只改这个文件，agent 侧一行不用动（同 websearch 的设计）。

运行方式（被 MCP 客户端以子进程拉起，走 stdio JSON-RPC）：
  .venv/Scripts/python.exe agent/servers/web_search_mcp.py

★ 学习要点（对照 MCP 协议）：
  - `@mcp.tool()` 装饰的函数 = 一个 tool；函数签名 + 类型注解自动变成工具的
    inputSchema（JSON Schema），docstring 变成工具描述（给模型看，决定何时调用）。
  - `mcp.run()` 默认走 stdio 传输：客户端写 stdin、我们写 stdout，报文是
    JSON-RPC：initialize → tools/list → tools/call。这些握手 FastMCP 替我们做了，
    所以服务端代码看起来"只是个函数"。
"""
import os
import sys

# 让这个子进程能 import 到项目根目录的 websearch / db 等模块
# （cwd 由客户端设为 back_study，但这里也兜底加一遍，避免路径问题）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from mcp.server.fastmcp import FastMCP

# stdio server 的 stdout 只能有 JSON-RPC 报文，框架那句 "Processing request of
# type ..." 调试日志必须关掉，否则会污染协议流（接到 stderr 才安全）。
import logging
for _n in ("mcp", "mcp.server", "mcp.server.lowlevel"):
    logging.getLogger(_n).setLevel(logging.WARNING)

mcp = FastMCP("web-search")


@mcp.tool()
def web_search(query: str, limit: int = 6) -> str:
    """联网搜索实时资料。当用户问"最新的 / 现状 / 某版本发布时间 / 官网怎么说"
    这类卡片库覆盖不到、需要查活网的问题时用这个。
    参数 query 是搜索关键词或一句话（如"Spring Boot 4 发布时间"）；
    limit 是最多返回几条结果（默认 6）。
    返回若干条结果的标题、链接和摘要；搜不到会明确说没搜到，不会编造。"""
    try:
        # websearch 在 agent/qa/websearch.py，不是 back_study 顶层模块，
        # 所以用包路径导入（back_study 已在 sys.path 里，见文件顶部）。
        from agent.qa import websearch
    except Exception as e:                       # 极端情况下 import 失败也要兜底
        return "（搜索模块加载失败：%s）" % e
    rows = websearch.web_search(query, limit=limit)
    if not rows:
        return ("联网搜索这次没有结果（网络不通 / 被限流 / 该关键词无收录），"
                "回答请以卡片资料为准。")
    out = []
    for i, r in enumerate(rows, 1):
        out.append("%d. %s\n   链接：%s\n   摘要：%s"
                   % (i, r.get('title', ''), r.get('url', ''),
                      r.get('snippet') or '（无摘要）'))
    return "\n\n".join(out)


if __name__ == "__main__":
    # transport 默认 "stdio"：从 stdin 读 JSON-RPC 请求，往 stdout 写响应。
    # 不要在这里 print 调试信息到 stdout——会污染协议流，只能写 stderr。
    mcp.run()
