# -*- coding: utf-8 -*-
"""cards Agent 的两张图 —— 连线（节点是 nodes.py）。

    build_refine()   structure：refine 一条直路。失败不重试（增强可选）。
    build_chapter()  chapter：captions → draft → ground → 条件边
                     合格/超次 → END，不合格 → 回 draft 重写。

为什么要两张图而不是一张：
    structure 是文档级（一次），chapter 是章节级（一章一跑）。
    chapter 独立成图，runtime 才能逐章 invoke、逐章落盘 ——
    中途断了重跑也只跳过已有的草稿（幂等），不会整篇文档重来。
    这也是和 qa/qa_refine（一次会话一个状态）结构上的关键差别。
"""
from langgraph.graph import StateGraph, START, END

from . import nodes


def build_refine():
    g = StateGraph(nodes.RefineState)
    g.add_node('refine', nodes.refine)
    g.add_edge(START, 'refine')
    g.add_edge('refine', END)
    return g.compile()


def build_chapter():
    g = StateGraph(nodes.ChapterState)
    g.add_node('captions', nodes.captions)
    g.add_node('draft', nodes.draft)
    g.add_node('ground', nodes.ground)
    g.add_edge(START, 'captions')
    g.add_edge('captions', 'draft')
    g.add_edge('draft', 'ground')
    g.add_conditional_edges('ground', nodes.route, {
        'end': END,
        'retry': 'draft',        # 重写：把 ground 的 msg 带回 draft 的提示词
    })
    return g.compile()
