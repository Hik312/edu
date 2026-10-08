# -*- coding: utf-8 -*-
"""MCP 服务端（stdio）—— 把"执行 Python 代码"作为标准 MCP 工具暴露出去。

这是协议的**服务端**：用 FastMCP 声明一个工具 `run_python`，在**隔离子进程**里
跑用户（模型）给的 Python 代码，把 stdout/stderr 返回给 Agent。

为什么这个工具值得加 —— 对你的 CS 学习产品价值最高：
  以前 QA Agent 只能"检索卡片 + 生成文字"，遇到"这段代码对不对 / 这个算法跑出来
  是什么结果 / 这个复杂度怎么算"这类问题，它只能凭参数知识猜。现在它能**真跑一下
  验证自己的答案**：跑个排序算法看结果、算个复杂度、演示个数据结构例子。这一步让
  Agent 从"检索器"升级成"会动手验证的助教"。

安全边界（必须看清，别当成万能沙箱）：
  - 代码在**独立子进程**里跑（不是 agent 进程内），进程隔离已经有一层；
  - 有超时（默认 10s，上限 30s）和输出截断（4000 字符），防死循环 / 刷屏；
  - 但**没有**文件系统配额、没有禁网、没有禁 syscall —— 它用的是 venv 里的
    python，能 import numpy 等已装包，也**能读写你机器上的文件、能联网**。
  - 所以这个工具只用于「自己本地、可信」的场景，绝不能把它接到不可信输入上。
    要对外/多租户，请换成真正的沙箱（容器 / gVisor / 受限 syscall）。

运行方式（被 MCP 客户端以子进程拉起，走 stdio JSON-RPC）：
  .venv/Scripts/python.exe agent/servers/code_exec_mcp.py
"""
import os
import sys
import json
import tempfile
import subprocess

# 让这个子进程的 stdout 只能有 JSON-RPC 报文，框架调试日志必须关掉，
# 否则会污染协议流（接到 stderr 才安全）。
import logging
for _n in ("mcp", "mcp.server", "mcp.server.lowlevel"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("code-exec")

# ---- 执行参数（安全相关的硬上限，改这里即可收紧）-----------------------------
MAX_OUTPUT = 4000        # 返回文本最多多少字符，超出只留末尾
DEFAULT_TIMEOUT = 10     # 默认超时（秒）
MAX_TIMEOUT = 30         # 超时硬上限（秒）
# ---------------------------------------------------------------------------


@mcp.tool()
def run_python(code: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """在隔离子进程里执行一段 Python 代码，返回它的标准输出与标准错误。

    当问题需要"算一下 / 跑一下验证答案 / 演示算法或数据结构"时用这个 ——
    比如验证排序算法、跑个复杂度例子、演示链表操作、算个数值结果。
    模型生成答案后若想确认对不对，可以调用它实跑验证。

    参数:
      code    : 要执行的完整 Python 代码（多行用换行分隔）；
                可以 import 本项目 venv 里已装的包（如 numpy）。
      timeout : 最长运行秒数（默认 10，上限 30），超时会被强制终止。

    返回: 程序的 stdout + stderr（合并文本）；超过 4000 字符截断到末尾；
          超时 / 出错会明确说明，不会编造运行结果。

    注意: 这是本地代码执行，会真实运行你给的代码，只用于可信的本地环境。"""
    if not code or not code.strip():
        return "（没有收到要执行的代码）"

    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    if timeout <= 0:
        timeout = DEFAULT_TIMEOUT
    timeout = min(timeout, MAX_TIMEOUT)

    # 写到临时文件再跑：支持多行代码、def/class/import，比 -c 稳。
    fd, path = tempfile.mkstemp(suffix=".py", prefix="mcp_exec_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            # ★ 关键：这个 server 自己是通过 stdio 跑的（stdin/stdout 是 JSON-RPC 管道）。
            #   如果在 Windows 下不显式重定向三路 stdio，子进程会**继承**这俩管道 ——
            #   尤其继承了 JSON-RPC 的 stdin 读端，会导致子进程启动/读取时挂起，
            #   表现就是 run_python 一定超时（已实测：隔离跑没问题，塞进 stdio 服务就挂）。
            #   所以这里强制：stdin→DEVNULL、stdout/stderr→PIPE、close_fds 关掉继承的句柄。
            run_kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
                close_fds=True,
            )
            if sys.platform == "win32":
                run_kwargs["creationflags"] = getattr(
                    subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.run([sys.executable, path], **run_kwargs)
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0:
                out = "（进程退出码 %d）\n%s" % (proc.returncode, out)
        except subprocess.TimeoutExpired as e:
            # e.stdout / e.stderr 在超时前可能已经产出一部分
            head = (getattr(e, "stdout", "") or "") + (getattr(e, "stderr", "") or "")
            out = "（执行超时，已在 %d 秒后终止）\n%s" % (timeout, head)
        except Exception as e:
            out = "（执行出错：%s）" % e
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    if not out:
        return "（代码执行完成，无输出）"
    if len(out) > MAX_OUTPUT:
        out = "...(输出过长，仅保留末尾 %d 字符)\n" % MAX_OUTPUT + out[-MAX_OUTPUT:]
    return out


if __name__ == "__main__":
    # transport 默认 "stdio"：从 stdin 读 JSON-RPC 请求，往 stdout 写响应。
    # 不要在这里 print 调试信息到 stdout —— 会污染协议流，只能写 stderr。
    mcp.run()
