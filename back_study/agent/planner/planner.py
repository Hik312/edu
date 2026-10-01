# -*- coding: utf-8 -*-
"""学习路径规划 Agent —— 你要亲手实现的那张图。

它服务的是 `/path` 今日路径页。那页顶部的注释原文写着：

    后期 BKT 接进来以后，替换的是分段的依据（现在是三档标记，
    以后是掌握度概率 + 前置依赖），这一页的结构不用动。

BKT 已经落地了，但到现在只在 `bkt_e2e.py` 里跑过，没有任何地方「看见」它。
这就是这张图存在的理由。

─────────────────────────────────────────────────────────────
图长这样（★ 的是留给你的，其余已写好）：

    START → collect → score → ★ write → verify ──┬─→ END
                                  ↑              │
                                  └─── 没过检 ───┘   （最多 C.MAX_TRIES 次）

    collect  取候选    db.due_list()                    【已写好】
    score    排序      db.mastery_of() + db.neighbors() 【已写好】
    write    写理由    ★ 唯一调模型的节点               【TODO 你填】
    verify   自检      纯规则，不调模型                  【已写好】

─────────────────────────────────────────────────────────────
★ 建议的动手顺序（别一上来就写 write）：

    1. 先跑 `run.py --dump`  —— 只用 collect + score，不调模型，
       确认取出来的候选卡、掌握度、前置关系是对的。数据错了，
       后面模型写得再好也是错的。
    2. 再填 write 的 3 处 TODO。
    3. 最后跑 `run.py --top 5`，看 verify 会不会把模型的幻觉 id 拦下来。
─────────────────────────────────────────────────────────────
"""
import os
import sys
from typing import TypedDict

# planner/ 现在是 agent/ 的子包，理论上可以 `from .. import config`，
# 但那样直接 `python planner.py` 会报 "no known parent package"。
# 所以还是挂 sys.path + 绝对导入 —— 两种跑法都能活。
_HERE = os.path.dirname(os.path.abspath(__file__))       # .../back_study/agent/planner
_BACK = os.path.dirname(os.path.dirname(_HERE))          # 两次 dirname 才到 back_study/
_CORE = os.path.join(_BACK, 'core')                       # core/db.py 自己 import security/store，也要挂
for _p in (_CORE, _BACK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import db                                # noqa: E402  core/db.py
from agent import config as C            # noqa: E402  共享参数（温度/重试上限），别复制一份
# M 现在看着没用，是因为 write() 里调模型的那行还是 TODO —— 你填完就会用到。
# 别删：自己 new 一个模型会出现「网页精读用 qwen3、planner 用另一个」的分裂。
from agent import model as M             # noqa: E402,F401  共享模型工厂

# ★ langchain / langgraph 的 import 一律写在**函数内部**（见 build()）。
# 模块级 import 要 2-3 秒，会给每个 import 本文件的人平白加上这段延迟。


# ---------------------------------------------------------------------------
# 状态
# ---------------------------------------------------------------------------
class PlanState(TypedDict):
    """这张图里流动的东西。

    用 TypedDict 而不是裸 dict：langgraph 据此知道有哪些字段，
    拼错字段名会直接报错，不会静默丢数据 —— 那种 bug 查起来要命。"""
    user_id: str        # 谁的计划（掌握度是 per-user 的，BKT 的硬前提）
    top_n: int          # 最终出几张
    candidates: list    # collect+score 产出：[{id,title,level,overdue,p,prereq,score}]
    plan: list          # write 产出：[{id, reason}]
    tries: int          # write 已尝试次数，防止死循环
    ok: bool            # verify 的质检结果
    msg: str            # 没过检时的原因，回炉重造时喂给模型


# ---------------------------------------------------------------------------
# 取数（已写好 —— 先跑 --dump 验证这一段）
# ---------------------------------------------------------------------------
def load_candidates(user_id, include_all=True):
    """候选卡 = 到期队列里的每一张。

    返回 [{id, title, level, overdue, p, prereq, never}]。

    两个字段坑，我踩过：
    · `due_list()` 是**嵌套**结构：卡片在 `x['card']`、进度在 `x['progress']`，
      只按顶层取 `x['id']` 会拿到一堆 None。
    · `overdue == 999` 是哨兵值，意思是**这张卡从没复习过**，
      不是「逾期 999 天」。它的掌握度要从 p_init 算起（mastery_of 已经处理了）。
    """
    rows = db.due_list(include_all=include_all)
    out = []
    for x in rows:
        c = x.get('card') or {}
        cid = c.get('id')
        if not cid:
            continue
        out.append({
            'id': cid,
            'title': c.get('title') or cid,
            'level': x.get('level') or 0,          # 0=未标记 1=不会 2=模糊 3=会
            'overdue': x.get('overdue') or 0,
            'never': x.get('overdue') == db.OVERDUE_NEVER,   # 从没复习过
            'p': db.mastery_of(user_id, cid),      # 走 Redis 缓存，便宜
            'prereq': find_prereq(cid),
            'score': 0.0,                          # score 节点填
        })
    return out


def find_prereq(cid):
    """cid 的前置卡 id 列表。

    ★ 边的方向：`db.build_graph()` 里是 `link(当前卡, 关联卡, kind)`，
    所以 related 里的 `{id: Y, kind: 'prereq'}` 生成的是
    source=当前卡 → target=Y。**Y 才是前置**。
    如果你实测发现反了（表现为「学完 A 才学 B」说不通），把 target 换成 source。
    """
    nb = db.neighbors(cid, depth=1)
    return [e['target'] for e in nb.get('edges') or []
            if e.get('kind') == 'prereq' and e.get('source') == cid]


def score_candidates(cands, user_id):
    """排序：给每张候选算一个优先级分，越高越该先学。就地排序并返回。

    现在的规则（纯规则，你可以改）：
        score = 0.65 * (1 - p)       掌握度越低越急
              + 0.25 * 逾期程度       逾期越久越急（从没复习过算 1.0）
              + 0.10 * 前置没掌握     它的前置越生，越该先把前置学了

    为什么「前置没掌握」要加分而不是直接把它自己排后面：
    正确的做法是**先把前置卡推上去**，而不是把这张卡压下去 —— 后者会
    让用户永远看不到这张卡，而前者才叫「路径」。
    """
    by_id = {c['id']: c for c in cands}

    for c in cands:
        overdue_norm = 1.0 if c['never'] else min(1.0, (c['overdue'] or 0) / 30.0)
        prereq_gap = 0.0
        for pid in c['prereq']:
            pc = by_id.get(pid)
            pp = pc['p'] if pc else db.mastery_of(user_id, pid)
            prereq_gap = max(prereq_gap, 1.0 - pp)
        c['score'] = round(0.65 * (1.0 - c['p'])
                           + 0.25 * overdue_norm
                           + 0.10 * prereq_gap, 4)

    cands.sort(key=lambda c: (-c['score'], c['id']))
    return cands


# ---------------------------------------------------------------------------
# 节点
# ---------------------------------------------------------------------------
def collect(state: PlanState) -> dict:
    """取候选。不调模型 —— 纯查库，快且确定。"""
    return {'candidates': load_candidates(state['user_id']),
            'plan': [], 'tries': 0, 'ok': False, 'msg': ''}


def score(state: PlanState) -> dict:
    """排序。也不调模型。"""
    return {'candidates': score_candidates(list(state['candidates']),
                                           state['user_id'])}


# 让模型只输出 JSON。8B 模型很爱在 JSON 外面裹一层「好的，这是你的计划：」，
# 那层话会让 json.loads 直接炸，所以要写死「不要解释」。
WRITE_SYS = '''你是学习规划助手。下面是一批待复习的卡片，按「该先学」的程度排序给出。

规则：
- 只能从【候选】里选，绝对不许自己编造 id —— 编的 id 会被程序拦下重来。
- 每条给一句话理由，说清「为什么现在学它」，20 字以内。
- 只输出 JSON 数组，不要任何解释、不要 markdown 代码块。

输出格式：
[{"id": "卡片id", "reason": "一句话理由"}]'''


def write(state: PlanState) -> dict:
    """★ TODO(你) —— 这是全图唯一调模型的节点，也是你真正要写的部分。

    要干三件事，下面标了 TODO 1/2/3。参考答案在 `agent/nodes.py` 的
    `answer()`（同样是「拼提示词 → 调模型 → 取文本」）。

    提示词和候选摘要我都拼好了，你直接拿去用。
    """
    top = state.get('top_n') or 5
    cands = state['candidates'][:max(top * 2, top + 3)]   # 多给几个，让模型有得挑

    # 候选摘要：模型不需要整张卡，给它做判断用得上的那几列就够了。
    # 给太多它反而抓不住重点（实测超过 6 条 8B 就开始顾此失彼）。
    brief = '\n'.join(
        '%-28s 掌握度=%.2f 优先分=%.2f %s' % (
            c['id'], c['p'], c['score'],
            '（从没复习过）' if c['never'] else '（逾期%d天）' % (c['overdue'] or 0))
        for c in cands)

    # 消息拼好了，TODO(你) 1/3 直接拿去用（现在没引用是正常的）
    user_msg = ('【候选】\n%s\n\n【上次被驳回的原因】\n%s\n\n'
                '请选出最该先学的 %d 张。' % (
                    brief, state.get('msg') or '（无，这是第一次）', top))  # noqa: F841

    # ---- TODO(你) 1/3：拼消息并调模型 ----
    # 提示（参考答案在 agent/nodes.py 的 answer()）：
    #   from langchain_core.messages import SystemMessage, HumanMessage
    #   llm = M.chat()                            # 共享工厂，别自己 new
    #   resp = llm.invoke([SystemMessage(WRITE_SYS), HumanMessage(user_msg)])
    #   text = resp.content
    raise NotImplementedError(
        'TODO(你) 1/3：write 节点还没实现 —— 调模型拿到 text。'
        '提示词已拼好（候选 %d 张，共 %d 字），填完把本行 raise 删掉。'
        '参考 agent/nodes.py 的 answer()。' % (len(cands), len(user_msg)))

    # ---- TODO(你) 2/3：从 text 里抠出 JSON ----
    # 提示：模型可能裹 ```json ... ``` 或者前后带解释，先 strip 掉再 json.loads。
    #       解析失败别抛异常，返回 {'ok': False, 'msg': '输出不是合法 JSON'}
    #       让 verify 把它打回去重来 —— 这正是这张图的价值。
    plan = []          # ← 换成你解析出来的 [{'id':..., 'reason':...}]

    # ---- TODO(你) 3/3：返回要修改的字段 ----
    # 提示：tries 一定要 +1，否则 route 判断不了重来次数、可能死循环。
    return {'plan': plan, 'tries': (state.get('tries') or 0) + 1}


def verify(state: PlanState) -> dict:
    """自检（已写好 —— 它是你的安全网，不是练习题）。

    8B 模型在「列 N 个 id」这类任务上编造率不低：它会返回听起来很像真的
    id，而库里根本没有。不校验，用户就点到一个不存在的卡片。
    这也是整张图**真正的价值** —— 前面的排序用几行 Python 也写得出来，
    但「答完自己检查一遍、不合格就重来」是编排才有的东西。
    """
    plan = state.get('plan') or []
    allowed = {c['id'] for c in state['candidates']}
    top = state.get('top_n') or 5

    if not plan:
        return {'ok': False, 'msg': '计划是空的 —— 必须至少选 1 张。'}
    if len(plan) > top:
        return {'ok': False, 'msg': '选了 %d 张，超过要求的 %d 张。' % (len(plan), top)}

    bad = [it.get('id') for it in plan if it.get('id') not in allowed]
    if bad:
        return {'ok': False,
                'msg': '这几张不在候选里（编造的 id）：%s。只能从【候选】里选。'
                       % '、'.join(str(b) for b in bad)}

    dup = len(plan) != len({it.get('id') for it in plan})
    if dup:
        return {'ok': False, 'msg': '有重复的卡片，每张最多出现一次。'}

    empty = [it.get('id') for it in plan if not (it.get('reason') or '').strip()]
    if empty:
        return {'ok': False, 'msg': '这几张没写理由：%s。'
                                    % '、'.join(str(e) for e in empty)}

    return {'ok': True, 'msg': ''}


def route(state: PlanState) -> str:
    """verify 之后去哪。过了就结束，没过且还有次数就回 write 重来。"""
    if state.get('ok'):
        return 'end'
    return 'retry' if (state.get('tries') or 0) < C.MAX_TRIES else 'end'


# ---------------------------------------------------------------------------
# 图
# ---------------------------------------------------------------------------
def build():
    """编译图。★ langchain 的 import 必须在函数内（模块级 import 要 2-3 秒）。"""
    from langgraph.graph import StateGraph, START, END

    g = StateGraph(PlanState)
    g.add_node('collect', collect)
    g.add_node('score', score)
    g.add_node('write', write)
    g.add_node('verify', verify)
    g.add_edge(START, 'collect')
    g.add_edge('collect', 'score')
    g.add_edge('score', 'write')
    g.add_edge('write', 'verify')
    g.add_conditional_edges('verify', route, {'end': END, 'retry': 'write'})
    return g.compile()


def plan(user_id, top_n=5):
    """跑一次完整规划。返回 PlanState。

    开局先探一次活：模型没起时，与其让用户在 20 秒超时里猜发生了什么，
    不如第一秒就告诉他原因。（后面接路由时这条更重要 —— 那个接口是
    async 的，一次卡 30 秒很容易把连接池拖住。）
    """
    st = M.status()
    if not st.get('ok'):
        raise RuntimeError('模型不可用：%s' % (st.get('msg') or '未知原因'))

    return build().invoke({'user_id': user_id, 'top_n': top_n,
                           'candidates': [], 'plan': [], 'tries': 0,
                           'ok': False, 'msg': ''})
