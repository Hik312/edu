# -*- coding: utf-8 -*-
"""模型工厂 —— agent 层唯一「决定用哪个模型、什么参数」的地方。

为什么不直接在业务代码里写 ChatOllama(model='qwen3:8b')：
  模型名写死在业务里，换台机器就要全局搜索替换。而且 core/llm.py 早就
  实现了「本机装了哪些模型、按什么优先级挑」，这里直接复用它，
  保证网页端精读和 agent 用的是同一个模型 —— 不会出现 A 页面用 qwen3、
  agent 里悄悄用了另一个、然后你以为是模型不行。

参数默认取 config.py 的值，调用方想覆盖就传参。
"""
from . import config as C

# core/llm.py 用标准库写的那套：OLLAMA 地址、PREFER 优先级、模型探测缓存。
# 复用它，不重新实现一遍模型选择。
import llm as _llm


def _require():
    """延迟导入 langchain_ollama —— 见 agent/__init__.py 的分层说明：
    模块级 import 会让后端每次冷启动替 AI 功能多花 2-3 秒。

    缺依赖时给能直接动手的提示，别抛裸 ImportError。"""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise RuntimeError(
            '缺 langchain-ollama。装一次就够：\n'
            '  .venv/Scripts/pip.exe install langgraph langchain langchain-ollama'
        )
    return ChatOllama


def pick():
    """挑一个本机可用的模型名。没装 Ollama / 没拉模型就返回空字符串。

    和 core/llm.pick_model() 同源：LLM_MODEL 环境变量优先，其次按 PREFER 顺序。"""
    try:
        return _llm.pick_model()
    except Exception:
        return ''


def chat(model=None, temperature=None, num_ctx=None, num_predict=None, **kw):
    """造一个 ChatOllama。所有节点 / agent 都从这里拿模型，不要各自 new。

    **kw 透传给 ChatOllama（keep_alive、format='json' 之类）。"""
    ChatOllama = _require()
    name = model or pick()
    if not name:
        raise RuntimeError(
            '本机没有可用模型。先拉一个：\n'
            '  ollama pull qwen3:8b\n'
            '或者设 LLM_MODEL 指定已装的模型。'
        )
    opts = dict(
        model=name,
        base_url=_llm.OLLAMA,
        temperature=C.TEMPERATURE if temperature is None else temperature,
        num_ctx=num_ctx or C.NUM_CTX,
        num_predict=num_predict or C.NUM_PREDICT,
        # 推理模型（qwen3 / deepseek-r1）不关这个会把 token 全烧在 <think> 里，
        # 表现是「等了十几秒，返回空字符串」。
        think=False,
    )
    opts.update(kw)
    return ChatOllama(**opts)


def status():
    """给前端 / CLI 看的状态。ok=False 是正常状态，不是故障
    —— 平台没有一处核心功能依赖 AI。

    通道那部分直接转发 core/llm.status()：它已经把「AI=off / 云端 / 本地 Ollama」
    三种情况和对应建议写清楚了，没必要维护第二份说法。
    这里只补一段 agent 层自己的依赖是否就绪。"""
    st = _llm.status()
    try:
        _require()
        st['agent'] = True
    except RuntimeError as e:
        st['agent'] = False
        st['agentMsg'] = str(e)
    return st
