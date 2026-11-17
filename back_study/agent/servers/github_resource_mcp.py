# -*- coding: utf-8 -*-
"""MCP 服务端（stdio）—— 把"Github 学习资源检索"作为标准 MCP 工具暴露出去。

这是协议的**服务端**：用 FastMCP 声明一个工具 `github_search`，调 Github 公开 API
（api.github.com）检索**仓库**（适合找学习路线 / 官方实现 / roadmap）与**代码**
（适合找具体实现示例）。

为什么这个工具值得加 —— 回答了用户的核心诉求：
  以前学生问一个知识点，Agent 只能在**自己卡片库**里检索；库里没有就答不出活的、
  外部的、紧跟社区的写法。现在它能**拉外部资源**——给学生指一条"去 Github 上看
  xxx 的官方实现 / 优质学习路线"，从封闭检索变成"卡片库 + 全网"的混合供给。

安全 / 边界：
  - 只读检索，不发任何写请求；不碰 token 写权限（只读 public 搜索）。
  - code 检索需要 GITHUB_TOKEN（Github 强制），repo 检索免 token（限流 10 次/分）。
  - 网络不通 / 被限流 / 命中墙 → 返回说明文案，**不抛异常、不污染协议流**。
  - 用标准库 urllib，零新依赖；走系统代理（HTTPS_PROXY 等）与浏览器同策略。

运行方式（被 MCP 客户端以子进程拉起，走 stdio JSON-RPC）：
  .venv/Scripts/python.exe agent/servers/github_resource_mcp.py
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

# stdio server 的 stdout 只能有 JSON-RPC 报文，框架调试日志必须关掉。
import logging
for _n in ("mcp", "mcp.server", "mcp.server.lowlevel"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github-resource")

API = "https://api.github.com"
MAX_PER_CALL = 10


def _request(url, token):
    """发一个 Github API GET，返回解析后的 dict；任何网络/HTTP 错误都向上抛，
    由调用方决定怎么降级（不在这里吞掉，方便上层给出精确文案）。"""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "edu-path-mcp",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer %s" % token
    req = urllib.request.Request(url, headers=headers)
    # timeout 卡死保护：网络抽风不能让 Agent 一直等
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def _search_repos(q, limit, token):
    url = "%s/search/repositories?q=%s&sort=stars&order=desc&per_page=%d" % (
        API, urllib.parse.quote(q), min(limit, MAX_PER_CALL))
    data = _request(url, token)
    items = (data or {}).get("items") or []
    out = []
    for it in items[:limit]:
        out.append("%s\n   ⭐ %s | 语言 %s\n   链接：%s\n   简介：%s" % (
            it.get("full_name"),
            it.get("stargazers_count"),
            it.get("language") or "—",
            it.get("html_url"),
            (it.get("description") or "（无简介）")[:200]))
    return out


def _search_code(q, limit, token):
    url = "%s/search/code?q=%s&per_page=%d" % (
        API, urllib.parse.quote(q), min(limit, MAX_PER_CALL))
    data = _request(url, token)
    items = (data or {}).get("items") or []
    out = []
    for it in items[:limit]:
        repo = it.get("repository") or {}
        out.append("%s\n   文件：%s\n   链接：%s" % (
            repo.get("full_name"), it.get("path"), it.get("html_url")))
    return out


@mcp.tool()
def github_search(query: str, kind: str = "repo", limit: int = 5) -> str:
    """在 Github 上检索学习资源。学生问一个知识点、库里卡片不够、需要外部代码示例
    或优质学习路线/roadmap 时用这个——让 Agent 从"只查卡片库"升级成"卡片库 + 全网"。

    参数:
      query : 检索词（如 "raft consensus"、"python asyncio tutorial"、"kubernetes 学习路线"）
      kind  : 检索类型 ——
               "repo" = 搜仓库（默认，适合找学习路线 / 官方实现 / roadmap，免 token）；
               "code" = 搜代码片段（适合找具体实现示例，**需要 GITHUB_TOKEN**）。
      limit : 最多返回几条（默认 5，上限 10）。

    返回若干仓库/代码的名称、链接和简介；搜不到会明确说明，不会编造。"""
    if not query or not query.strip():
        return "（没有给出检索词）"
    try:
        limit = max(1, min(int(limit) if str(limit).isdigit() else 5, MAX_PER_CALL))
    except (TypeError, ValueError):
        limit = 5
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        if kind == "code":
            if not token:
                return ("（Github 代码检索需要 GITHUB_TOKEN：在环境变量里配置一个 "
                        "Github 个人访问令牌（只读 public_repo 即可）后重试；"
                        "仓库检索无需 token，可改用 kind=\"repo\"。）")
            rows = _search_code(query, limit, token)
        else:
            rows = _search_repos(query, limit, token)
    except urllib.error.HTTPError as e:
        if e.code == 403 and not token and kind == "code":
            return "（Github 代码检索需要 GITHUB_TOKEN，请配置后重试；仓库检索无需 token）"
        if e.code == 403:
            return "（Github 限流了（未认证 10 次/分），稍等一会儿再试）"
        return "（Github 检索失败：HTTP %s）" % e.code
    except urllib.error.URLError as e:
        return "（连不上 Github（网络/代理问题）：%s）" % e.reason
    except Exception as e:
        return "（Github 检索失败：%s）" % e

    if not rows:
        return "（Github 上没有检索到和「%s」相关的%s，换个关键词试试）" % (
            query, "代码" if kind == "code" else "仓库")
    head = "在 Github 上找到以下%s（共 %d 条）：\n\n" % (
        "代码" if kind == "code" else "仓库", len(rows))
    return head + "\n\n".join(rows)


if __name__ == "__main__":
    # transport 默认 "stdio"：从 stdin 读 JSON-RPC 请求，往 stdout 写响应。
    # 不要在这里 print 调试信息到 stdout —— 会污染协议流，只能写 stderr。
    mcp.run()
