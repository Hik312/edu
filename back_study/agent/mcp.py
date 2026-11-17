# -*- coding: utf-8 -*-
"""MCP 客户端桥接层 —— 把"外部 MCP server"接进本项目的 Agent。

这一层做四件事，对应你学 MCP 时最该弄清的四个点：

  1. 启动外部 server（子进程，stdio 传输）
  2. 走 MCP 握手：initialize → tools/list，拿到对方声明了哪些工具
  3. 把每个 MCP 工具包成本项目用的 langchain Tool（含参数 schema）
  4. 调用时走 tools/call，把结果回填给模型

为什么需要"桥接"而不是直接 import：
  MCP server 是**另一个进程**（可能用别的语言、别的依赖写）。Agent 通过
  JSON-RPC（走 stdin/stdout）和它通信，彼此解耦——换搜索源、加新工具，只要
  对方是合规的 MCP server，本项目零改动。这正是"外部工具"能即插即用的原因。

设计取舍（和项目一脉相承）：
  - **可选依赖**：没装 mcp / 没配置文件 / 某个 server 起不来，都只是"少几个工具"，
    绝不拖垮主链路（和 websearch / VLM 的降级哲学一致）。
  - **工具预算**：qwen3:8b 工具多了会选错（见 qa/tools.py 顶部注释），所以
    build_tools() 默认最多放 3 个 MCP 工具（web-search + code-exec + github-resource）；
    cards server 属内容生产动作，默认不进每轮 QA 列表。要更稳就调小
    load_mcp_tools 的 max_tools。
  - **同步封装**：Agent 运行时是同步的（runtime 用 invoke/stream），但 MCP 客户端
    是 async 的。这里用一个后台线程常驻一个事件循环来保活 session，对外暴露
    **同步** call_tool()，避免去改 runtime 的异步模型。
"""
import json
import os
import sys
import threading
import asyncio
import logging

logger = logging.getLogger("agent.mcp")

# back_study 根目录（本文件在 back_study/agent/mcp.py）
BACK_STUDY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "mcp_servers.json")

# 已连上的 server 桥接，按 name 缓存：build_tools() 多次调用只起一次子进程
_BRIDGES = {}
_BRIDGES_LOCK = threading.Lock()


def _load_config():
    """读 mcp_servers.json。文件不存在 / 坏 JSON → 返回空列表（降级）。"""
    if not os.path.exists(CONFIG_PATH):
        return []
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, list):
            return []
        return [c for c in cfg if c.get("enabled", True)]
    except Exception as e:
        logger.warning("读 mcp 配置失败，MCP 工具全部跳过: %s", e)
        return []


class MCPServerBridge:
    """一个外部 MCP server 的常驻桥接。

    生命周期：子线程里 new 一个事件循环 → run_until_complete(_connect) →
    _connect 内部 `async with stdio_client` 拉起子进程、initialize、list_tools，
    最后 `await asyncio.Future()` 让循环一直转（保持 session 活着）。
    主线程通过 run_coroutine_threadsafe 把 tools/call 调度到这个循环上执行。
    """

    def __init__(self, name, command, args, cwd=None, env=None,
                 ready_timeout=20):
        self.name = name
        self._ready = threading.Event()
        self._ok = False
        self._session = None          # 后台循环里的 ClientSession
        self._loop = None             # 后台事件循环
        self._thread = None
        self._tools = {}              # tool_name -> MCP Tool 对象（含 schema）
        self._closed = False

        from mcp import StdioServerParameters
        # command 若是相对路径，按 back_study 根目录解析（配置文件里写的就是相对路径）
        if command and not os.path.isabs(command):
            command = os.path.join(BACK_STUDY_DIR, command)
        self._params = StdioServerParameters(
            command=command,
            args=args or [],
            cwd=cwd or BACK_STUDY_DIR,
            env=env,                  # None = 继承当前环境变量
        )
        self._ready_timeout = ready_timeout
        self._start()

    def _start(self):
        self._thread = threading.Thread(target=self._run, name="mcp-%s" % self.name,
                                        daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=self._ready_timeout):
            logger.warning("MCP server [%s] 在 %ds 内未就绪，跳过",
                           self.name, self._ready_timeout)
            self._ok = False
            return
        self._ok = bool(self._session)

    def _run(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect())
        except Exception as e:
            logger.warning("MCP server [%s] 连接失败: %s", self.name, e)
            self._ok = False

    async def _connect(self):
        from mcp.client.stdio import stdio_client
        from mcp import ClientSession
        # async with 会负责拉起/回收子进程与传输通道
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                # ① 握手：交换协议版本、能力。MCP 规定必须先 initialize 再 list
                await session.initialize()
                # ② 问对方有哪些工具
                resp = await session.list_tools()
                for t in resp.tools:
                    self._tools[t.name] = t
                self._session = session
                self._ready.set()      # 通知主线程"可以用了"
                logger.info("MCP server [%s] 就绪，工具: %s",
                            self.name, ", ".join(self._tools.keys()))
                # ③ 保持循环运转：session 必须在事件循环存活期间才有效。
                #    用一个永远不完成的 future 把循环占住，直到 close() 取消它。
                await asyncio.Future()

    @property
    def ok(self):
        return self._ok

    @property
    def tool_names(self):
        return list(self._tools.keys())

    def call_tool(self, tool_name, arguments):
        """同步调用一个 MCP 工具，返回纯文本结果。

        内部把 async 的 call_tool 调度到后台循环上等结果——这就是
        "异步 MCP 客户端" 适配 "同步 Agent 运行时" 的关键一脚。"""
        if not self._ok or self._session is None:
            return "（MCP 工具 [%s] 未就绪）" % tool_name
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._session.call_tool(tool_name, arguments or {}),
                self._loop,
            )
            result = fut.result(timeout=60)
        except Exception as e:
            return "（MCP 调用 [%s] 出错：%s）" % (tool_name, e)
        return _text_of(result)

    def close(self):
        self._closed = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)


def _text_of(result):
    """从 MCP CallToolResult 里抽出文本。

    content 是一串 block，我们只取 type=='text' 的；isError 时同样取文本，
    但让调用方知道这是错误信息（前端展示可标红）。"""
    if result is None:
        return ""
    if getattr(result, "isError", False):
        pass  # 文本照常抽，交给上层判断是否标红
    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 把 MCP 工具包成 langchain Tool
# ---------------------------------------------------------------------------
import typing
from pydantic import create_model, Field

# JSON Schema 基础类型 → Python 类型。复杂嵌套不在本项目工具范围内，按 str 兜底。
_TYPE_MAP = {
    "string": str, "integer": int, "number": float,
    "boolean": bool, "object": dict, "array": list,
}


def _build_args_model(tool_name, input_schema):
    """把 MCP 工具的 inputSchema（JSON Schema）动态编译成 pydantic 模型，
    这样 langchain 能把模型生成的参数正确校验后传进来。

    没有声明任何形参的工具（少见）：给一个宽松的 args:dict 兜底。"""
    props = (input_schema or {}).get("properties", {}) or {}
    required = set((input_schema or {}).get("required", []) or [])
    fields = {}
    for pname, pspec in props.items():
        pspec = pspec or {}
        ptype = _TYPE_MAP.get(pspec.get("type", "string"), str)
        desc = pspec.get("description", "")
        if pname in required:
            fields[pname] = (ptype, Field(..., description=desc))
        else:
            fields[pname] = (ptype, Field(pspec.get("default", ""), description=desc))
    if not fields:
        fields["args"] = (dict, Field(default_factory=dict,
                                      description="参数（任意 JSON 对象）"))
    return create_model("%s_Schema" % tool_name, **fields)


def _wrap_as_langchain_tool(bridge, tool_spec):
    """把一个 MCP 工具规格包成 langchain StructuredTool。"""
    from langchain_core.tools import StructuredTool

    tool_name = tool_spec.name
    model = _build_args_model(tool_name, getattr(tool_spec, "inputSchema", None))

    def _func(**kwargs):
        # 无参兜底：把唯一的 args 解开传给 server
        if set(kwargs.keys()) == {"args"} and isinstance(kwargs.get("args"), dict):
            arguments = kwargs["args"]
        else:
            arguments = kwargs
        return bridge.call_tool(tool_name, arguments)

    return StructuredTool(
        name=tool_name,
        description=(getattr(tool_spec, "description", "") or "").strip()
                    or ("MCP 工具: " + tool_name),
        func=_func,
        args_schema=model,
    )


def _get_bridge(spec):
    """按配置拿（或起）一个 server 桥接，失败返回 None。"""
    name = spec.get("name")
    if not name:
        return None
    with _BRIDGES_LOCK:
        if name in _BRIDGES:
            return _BRIDGES[name]
    try:
        bridge = MCPServerBridge(
            name=name,
            command=spec.get("command"),
            args=spec.get("args"),
            cwd=spec.get("cwd"),
            env=spec.get("env"),
        )
    except Exception as e:
        logger.warning("MCP server [%s] 启动异常，跳过: %s", name, e)
        return None
    if not bridge.ok:
        logger.warning("MCP server [%s] 未就绪，跳过", name)
        return None
    with _BRIDGES_LOCK:
        _BRIDGES[name] = bridge
    return bridge


def load_mcp_tools(max_tools=3):
    """返回若干个 langchain Tool（来自所有启用且成功连上的 MCP server）。

    max_tools：受"小模型工具选错"约束，默认最多 3 个
    （web-search + code-exec + github-resource）。要全要就传大数。
    任意失败都吞掉，返回已经能用的那部分——绝不能因为 MCP 挂了让 Agent 起不来。

    ★ 够数就别再起新 server 子进程：起进程 + 握手有成本，尤其 cards server
    会 import 重型依赖（agent.cards / core.llm）。首个 QA 请求付一次启动代价，
    之后靠 _BRIDGES 缓存复用，这里提前 break 避免白拉一个用不上的 server。"""
    tools = []
    for spec in _load_config():
        if len(tools) >= max_tools:
            break
        bridge = _get_bridge(spec)
        if bridge is None:
            continue
        for tname in bridge.tool_names:
            if len(tools) >= max_tools:
                break
            spec_tool = bridge._tools[tname]
            try:
                tools.append(_wrap_as_langchain_tool(bridge, spec_tool))
            except Exception as e:
                logger.warning("包装 MCP 工具 [%s] 失败，跳过: %s", tname, e)
    return tools


def mcp_status():
    """给 /agent/status 看的状态：连上了几个 server、各有哪些工具。"""
    out = []
    for spec in _load_config():
        name = spec.get("name")
        with _BRIDGES_LOCK:
            b = _BRIDGES.get(name)
        out.append({
            "name": name,
            "connected": bool(b and b.ok),
            "tools": b.tool_names if b else [],
        })
    return out


def shutdown():
    """进程退出时关掉所有 server 子进程。"""
    with _BRIDGES_LOCK:
        bridges = list(_BRIDGES.values())
        _BRIDGES.clear()
    for b in bridges:
        try:
            b.close()
        except Exception:
            pass
