# -*- coding: utf-8 -*-
"""图 —— 只负责「把节点按什么顺序连起来」，具体每步干什么在 nodes.py。

这里有两个图，各自解决不同的问题：

    build_qa()     流程固定：检索 → 回答 → 自检 → 不合格重来
                   每一步干什么你说了算，能在任意一步插手。
                   适合「该查什么」是确定的场景。

    build_react()  现成的 ReAct agent：让模型自己决定要不要查、查什么、查几次。
                   灵活，但你控制不了它绕几圈 —— 所以一定要设 recursion_limit，
                   而且工具别给太多（小模型容易选错或者反复调同一个）。

★ 什么时候**不该**用 LangGraph：
  只有一问一答（比如把一章正文整理成 JSON），它就是纯负担 ——
  core/llm.py 里那种活三个函数写完了，它也真就这么写的。
  判断标准：**你的流程里有箭头吗？没有就别上。**
"""
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

from .. import config as C          # 公共层：agent/config.py
from .. import model as M           # 公共层：agent/model.py
from .nodes import QAState, retrieve, answer, grade, route
from .tools import build_tools


# ReAct 的整体人设。和 nodes.py 里那些单步提示词不同 —— 这个是 agent 级别的，
# 放在它所属的图旁边。
#
# 「工具返回什么就是什么，不要补充工具里没有的内容」这句原来把回答掐得死死的
# （实测 155~196 字，用户反馈"太空"）。放开的方式和 flow 模式的 ANSWER_SYS 一致：
# **事实受卡片约束，展开放给模型** —— 依据还在，话匣子也打开了。
REACT_SYS = '''你是「原理卡片」学习助手，可以调用工具查用户的卡片库。

规则：
- 随问题附带的「卡片库检索结果」是已经替你查好的底料：涉及知识的问题**先依据
  这些卡**展开回答；细节不够就用 card_detail 按 id 补看；一条结果都没有时凭自己的
  知识正常答，并说明卡片库里没有对应卡片。"我有几张 / 今天复习什么 / 这张卡讲了啥"
  这类要查工具的问题仍然必须自己调工具，不许凭空回答。
  （底料为什么由代码代搜：提示词光写"先 search_cards"时 8B 实测两轮都不查，
  直接凭参数知识答 —— 一条 sources 都没有，还编库里不存在的卡名。）
- 卡片是**依据**，不是**上限**：底料 / 工具返回的结论照用，在此基础上用自己的知识
  展开 —— 为什么是这样、中间怎么推的、和什么相关、举个例子、指出容易搞混的点。
  但不许编造查不到的具体事实（数字、日期、接口名、概率），也不许给出与底料矛盾的结论。
- **出处只能是真实查到的**：卡片标题只能写检索结果或工具返回里出现过的；
  不许编造卡名、书名、章节号、页码、统计数字当出处（实测它编过"《TCP/IP详解》
  第18章"和一个库里根本没有的卡名）。
- 底料里没有的，先明说"你的卡片库里没有这一条"，然后照常把概念讲清楚。

回答结构（段落别省）：结论 → 分点展开（主体，要具体，别只堆小标题）→
例子或类比 → 易错点（有就写）。篇幅把问题讲透为准，一般 300~600 字，别用三两句打发。

输出要求（必须遵守）：
- 只输出回答正文。不要输出卡片 id、工具名、工具参数、JSON、【xxx】标记。
- 正文里不写出处标注：「（参考《…》）」「引用卡片：…」这类括注、落款一律
  不写，《卡片标题》也不当引用写进正文 —— 出处由系统单独展示（前端渲染
  引用条），正文只管说通顺；相应的，不许编造书名、章节号、页码当出处。
- 用户上一句在问什么要接得上，别答非所问。'''


def build_qa():
    """问答图：检索 → 回答 → 自检，没过检就回炉重造（有次数上限）。

    invoke({'question': '...'}) 直接用，其余字段给初值即可。"""
    g = StateGraph(QAState)
    g.add_node('retrieve', retrieve)
    g.add_node('answer', answer)
    g.add_node('grade', grade)
    g.add_edge(START, 'retrieve')
    g.add_edge('retrieve', 'answer')
    g.add_edge('answer', 'grade')
    # 条件边：grade 之后去哪由 route 说了算
    g.add_conditional_edges('grade', route, {'end': END, 'retry': 'answer'})
    return g.compile()


def build_react(model=None, tools=None):
    """ReAct agent。模型自己决定调哪个工具、调几次。

    步数上限在 config.RECURSION_LIMIT，运行时（runtime.py）负责传。"""
    llm = model if model is not None else M.chat()
    ts = tools if tools is not None else build_tools()
    return create_react_agent(llm, ts, prompt=REACT_SYS)


def recursion_config():
    """给 invoke 用的运行配置。单独拎出来是因为**每个调用都必须带**
    —— 少了它，ReAct 遇到死循环模型能跑到天荒地老。"""
    return {'recursion_limit': C.RECURSION_LIMIT}
