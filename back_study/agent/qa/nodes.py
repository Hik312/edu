# -*- coding: utf-8 -*-
"""节点 —— 每一步具体干什么。图（graph.py）只负责把它们连起来。

这样拆是为了让人一眼能分清两件事：
  「这一步做什么」看这里
  「按什么顺序做、什么条件走哪条路」看 graph.py

每个节点的契约都一样：收到整个 state，返回**要修改的字段**（不用返回全部）。
langgraph 会拿返回值去更新 state，没返回的字段保持原样。

本文件顶部就 import langchain —— 它只会在真正跑 agent 时被加载
（graph → nodes），不会拖慢后端冷启动。需要「零成本 import」的是
model.py 和 tools.py，那两个才是延迟导入。
"""
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage

from .. import config as C          # 公共层：agent/config.py
from .. import model as M           # 公共层：agent/model.py
from . import retrieval             # 本 Agent 自己的检索层（混合检索）


class QAState(TypedDict):
    """问答图里流动的东西。

    用 TypedDict 而不是裸 dict：langgraph 据此知道有哪些字段，
    拼错字段名会直接报错，不会静默丢数据 —— 那种 bug 查起来要命。"""
    question: str      # 用户问的
    context: str       # retrieve 检索到的卡片内容
    answer: str        # answer 生成的回答
    sources: list      # 这次回答引用了哪些卡片 id（溯源用，M3 透传给前端）
    tries: int         # 已尝试次数，防止死循环
    ok: bool           # grade 的质检结果
    history: str       # L1：裁剪后的多轮对话（runtime.format_history 压成纯文本）
    profile: str       # L3：长期档案（runtime.format_profile），没有就空串


# ---------------------------------------------------------------------------
# 提示词。和用它的节点放一起 —— 分开存到 prompts.py 反而要来回跳着看
# ---------------------------------------------------------------------------
# 篇幅这条原来写的是「控制在 150 字以内」，实测回答 134 字、三两句话完事，
# 用户反馈"回答太空"。根因有三个，一起改的（别只改一处就以为好了）：
#   ① 篇幅硬上限 150 字 → 改成"讲透为准，一般 300~600 字"，并明确不许压成摘要；
#   ② "只根据资料回答" 把模型自己的思考整个掐掉了 → 拆成两层：
#      **事实**（数字/日期/结论）必须来自卡片，**展开**（为什么/推理/类比/延伸）
#      鼓励用自己的知识，只要不和资料打架；
#   ③ 资料只喂 title/oneLine/mechanism，模型没东西可展开 → retrieve 补
#      why / analogy / scene（见下面 retrieve 节点）。
ANSWER_SYS = '''你是「原理卡片」学习助手。回答要**以卡片为依据，以讲透为目的**，两层分开做，都别省：

一、底座（不许含糊）
- 核心结论、机制、具体数字必须来自下面【资料】里的卡片。
- 资料里没有的**事实**（数字、日期、接口名、结论性断言）不许编；
  **问题本身**在资料里没有对应卡片时才说"卡片库里还没有这一条" ——
  这句只用于承认没查到，不要当落款挂在答案末尾（实测它会照挂）。

二、展开（不许省略）
- 允许并且鼓励用你自己的知识把答案讲透：为什么是这样、中间怎么推出来的、
  和哪些概念相关、常见坑在哪、面试时会怎么追问。
- 展开必须和资料的结论一致，不许和资料打架。

输出结构（按顺序，段落别省）：
1. 结论：一两句直接回答"是什么 / 为什么"。
2. 展开：分点把机制或推理过程讲具体 —— 这是主体，别只堆小标题。
3. 例子或类比：一个贴切的比方，或一个具体场景。
4. 易错点 / 边界：容易搞混的地方、什么情况下不成立（有就写）。

篇幅：把问题讲透为准，一般 300~600 字。**不要压成 150 字的摘要** ——
用户要的是能看懂、能记住的讲解，不是结论清单。写完自查一遍内容全不全、有没有漏答。

输出要求（违反会被系统丢弃重来）：
- 只输出回答正文，不要输出卡片 id、【xxx】标记、JSON、工具名。
- 正文里**不写出处标注**：「（参考《…》）」「（出处：…）」「引用卡片：…」这类
  括注和落款一律不写，《卡片标题》也不当引用写进正文 —— 出处由系统在回答
  下方单独展示（前端渲染引用条），正文只管把话说通顺；相应的，不许编造
  书名、章节号、页码当出处。
- 资料里有多轮对话时，先接上用户上一句的语境再回答。'''

# 自检原来判的是「回答里**每一条**是否都能在资料中找到依据」—— 上面把展开
# 放开之后，这条会让每次回答都判 NO，白白烧掉 MAX_TRIES 次重试（本地 8B 一次
# 二十秒）。判据改成**核心结论**：展开不算跑偏，编造事实才算。
GRADE_SYS = ('判断下面回答的**核心结论**是否都有资料依据。'
             '在资料基础上展开的解释、类比、延伸不算跑偏，不要因此判 NO；'
             '只有当回答编造了资料里查不到的具体事实、或结论与资料矛盾时才答 NO。'
             '只回答 YES 或 NO，不要解释。')


# ---------------------------------------------------------------------------
# 节点
# ---------------------------------------------------------------------------
def retrieve(state: QAState) -> dict:
    """检索：从本地卡片库找相关卡片。**不调模型** —— 纯查库，快且确定。

    走混合检索（向量为主 + 关键词兜底）；embedding 模型没装时自动退化成纯关键词，
    不报错。返回的 hits 是 retrieval.SearchHit（含卡片本体），顺手把 id 列表记到
    sources 字段，供 answer 引用、最后透传给前端做溯源。

    **用问题 + 最近一句用户话一起检索**：多轮里"那第二个呢？"单独检索必然空手，
    把上一句带进去才有得匹配（取 history 的最后一条 user 发言）。

    为什么不把检索交给模型去调工具：这个问题「该查什么」是确定的
    （就是用户问题里的关键词），让模型绕一圈决定调哪个工具没必要，
    而且它可能不调。确定的事情就写死。"""
    q = state['question']
    hist = state.get('history') or ''
    if hist:
        last_user = [ln for ln in hist.split('\n') if ln.startswith('我：')]
        if last_user:
            q = '%s %s' % (state['question'], last_user[-1][2:].strip())
    hits = retrieval.retrieve(q, C.TOP_K)
    if not hits:
        return {'context': '（卡片库里没有相关内容）', 'sources': []}
    # 资料里用**标题**而不是卡片 id —— 模型会照抄这段，抄 id 进正文就是
    # 用户反馈的"回答里打印了 id"。溯源走 sources 字段，不靠正文里的标记。
    #
    # 喂 title/oneLine/mechanism 之外还要 why / analogy / scene：只给结论和步骤，
    # 模型就没东西可展开（实测回答 134 字、很空）。这三样正好是它展开的原料 ——
    # why 给"为什么"，analogy 给例子，scene 给"什么时候用得上"。
    # 空字段直接跳过，别在提示词里留一堆空的"类比："占位。
    parts = []
    for h in hits:
        c = h.card
        block = ['【%s】' % (c.get('title') or h.id)]
        for label, val in (('一句话', c.get('oneLine')),
                           ('为什么', c.get('why')),
                           ('原理', ' / '.join(c.get('mechanism') or [])),
                           ('类比', c.get('analogy')),
                           ('场景', '；'.join((c.get('scene') or [])[:2]))):
            if val:
                block.append('%s：%s' % (label, val))
        parts.append('\n'.join(block))
    return {'context': '\n\n'.join(parts),
            'sources': [h.id for h in hits]}


def answer(state: QAState) -> dict:
    """生成回答。「不许编」这句约束必须写进提示词 —— 否则 8B 模型看到
    检索结果为空时，会很乐意给你编一段很像真的答案。"""
    blocks = []
    if state.get('profile'):
        blocks.append(state['profile'])
    if state.get('history'):
        blocks.append('【此前对话】\n%s' % state['history'])
    blocks.append('【资料】\n%s' % state['context'])
    blocks.append('【问题】\n%s' % state['question'])
    user = '\n\n'.join(blocks)
    r = M.chat().invoke([SystemMessage(content=ANSWER_SYS),
                         HumanMessage(content=user)])
    return {'answer': (r.content or '').strip(), 'tries': state.get('tries', 0) + 1}


def grade(state: QAState) -> dict:
    """质检：答案是不是有依据。

    这是整个流程里「值回票价」的一步 —— 本地小模型最常犯的错就是无中生有，
    这一步把大部分幻觉挡在返回给用户之前。"""
    # 诚实承认不会，也算通过（本来就该这么答）
    if '没有相关内容' in state['context'] or '没有这一条' in state['answer']:
        return {'ok': True}
    # 1600 而不是 800：资料现在带 why / analogy / scene，800 字正好把第三张卡的
    # 结论切掉 —— 质检看不到依据就判 NO，白重试一轮（本地 8B 一次二十秒）。
    p = '资料：\n%s\n\n回答：\n%s' % (state['context'][:1600], state['answer'])
    # 质检要稳定，温度给 0
    r = M.chat(temperature=0).invoke([SystemMessage(content=GRADE_SYS),
                                      HumanMessage(content=p)])
    return {'ok': 'YES' in (r.content or '').upper()}


def route(state: QAState) -> str:
    """条件边的判定：过了就结束，没过就回去重写。

    次数用完也放行 —— 宁可给一个没过检的答案，也不要卡死在循环里。"""
    if state.get('ok') or state.get('tries', 0) >= C.MAX_TRIES:
        return 'end'
    return 'retry'
