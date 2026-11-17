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
import json
import os
import re
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
    # ★ user_id 必须透传：进度是 per-user 的（2026-10-03 起），
    #   不传就读匿名桶（永远空）→ 候选队列全是「未标记」，
    #   页面于是给一个从没复习过的人排出「巩固已学」的路径。
    rows = db.due_list(include_all=include_all, user_id=user_id)
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
            'p': None,                             # ★ 下面批量填
            'prereq': find_prereq(cid),
            'indeg': 0,
            'score': 0.0,                          # score 节点填
        })

    # ★ **批量取掌握度，别在循环里调 mastery_of**。
    #   mastery_of 每张卡都要走一遍缓存/事件回放，逐张调 400+ 次能跑到分钟级
    #   （实测 --dump 直接超时）。mastery_map 一次覆盖全库，正是 web 端
    #   为这件事封的函数。
    pm = db.mastery_map(user_id, [c for c in out])
    p0 = float(db.bkt_params(user_id).get('p_init', 0.25))
    for c in out:
        v = pm.get(c['id'])
        try:
            c['p'] = float(v) if v is not None else p0
        except (TypeError, ValueError):
            c['p'] = p0
    return out


def find_prereq(cid):
    """cid 的前置卡 id 列表。

    ★ 边的方向：`db.build_graph()` 里是 `link(当前卡, 关联卡, kind)`，
    所以 related 里的 `{id: Y, kind: 'prereq'}` 生成的是
    source=当前卡 → target=Y。**Y 才是前置**。

    ★ 为什么要预取（2026-10-09）：原来每张候选都调一次
    `db.neighbors(cid, depth=1)`，400 张卡 = 400 次取图，
    实测 `--dump` 直接跑到超时。改成一次 build_graph 建反向表，
    之后每张卡只是查字典。
    """
    if _PREREQ is None:
        _build_prereq()
    return _PREREQ.get(cid, [])


_PREREQ = None
_INDEG = None


def _build_prereq():
    """从图里一次抽出「前置表」+「入度表」，模块级缓存。

    两张表用同一个build_graph() 结果算出来，别调两次。
    """
    global _PREREQ, _INDEG
    pre, ind = {}, {}
    g = db.build_graph()
    for e in (g.get('edges') or []):
        if e.get('kind') != 'prereq':
            continue
        s, t = e.get('source'), e.get('target')
        if not s or not t:
            continue
        pre.setdefault(s, []).append(t)
        ind[t] = ind.get(t, 0) + 1
    _PREREQ, _INDEG = pre, ind


def prereq_indegree():
    """全局入度表：{卡id: 有多少张卡把它当前置}。

    ★ 为什么必须单独算（2026-10-09）：
    `prereq_gap` 看的是「**我的**前置有多生」，而新用户所有卡的掌握度
    都等于先验 p_init，于是 prereq_gap 恒等于 0.75 —— 416 张候选算出
    2 个不同分数，排序退化成字母序。
    入度是**唯一对新用户也有区分度的图结构信号**：它回答
    「有多少东西依赖我」，入度高的卡（`myisam-innodb` 有 8 个后继）
    是枢纽，学它的收益最大。实测入度分布 0~8：230 张卡入度 0。
    """
    if _INDEG is None:
        _build_prereq()
    return _INDEG


def score_candidates(cands, user_id):
    """排序：给每张候选算一个优先级分，越高越该先学。就地排序并返回。

        score = 0.34 * (1 - p)掌握度越低越急
              + 0.12 * 逾期程度        逾期越久越急（从没复习过算 1.0）
              + 0.30 * 前置没掌握      它该先学的前置有多生
              + 0.24 * 入度            有多少张卡把它当前置（枢纽）

    为什么是这四个数（2026-10-09 改，原来 0.65/0.25/0.10）：
    **原权重对新用户完全没有区分度**。实测 416 张候选只有 2 个不同分数
    （0.812 有 239 张、0.738 有 177 张），因为新用户：
      · 掌握度全是先验 p_init=0.25 → 第一项恒为常数
      · 没复习过 → 逾期全是哨兵值，第二项恒为常数
    两项加起来是常数，排序退化成「按 id 字母序」，write 节点拿到的候选
    毫无意义（模型只能瞎选）。

    改法是**把权重挪到有区分度的两项上**：
      · prereq_gap 从「取 max」改成「取平均」——「前置很生」和「前置
        生一点点」不该挤成同一个值。
      · 新增入度维度——这是唯一对新用户也区分得出高下的结构信号。
      · 无前置的卡给 0.35 而非 0：图谱覆盖不全是事实，给 0 等于惩罚孤立卡。

    为什么「前置没掌握」加分，而不是把这张卡压下去：
    正确的做法是**先把前置卡推上去** —— 前者才叫「路径」，
    后者只会让这张卡永远不出现。
    """
    by_id = {c['id']: c for c in cands}
    indeg = prereq_indegree()
    # 入度归一化：实测最大 8，用 log 压一下避免枢纽卡一家独大
    import math
    imax = max(indeg.values()) if indeg else 1
    imax = max(imax, 1)

    for c in cands:
        overdue_norm = 1.0 if c['never'] else min(1.0, (c['overdue'] or 0) / 30.0)
        gaps = []
        for pid in c['prereq']:
            pc = by_id.get(pid)
            pp = pc['p'] if pc else db.mastery_of(user_id, pid)
            gaps.append(1.0 - pp)
        prereq_gap = (sum(gaps) / len(gaps)) if gaps else 0.35
        hub = math.log1p(indeg.get(c['id'], 0)) / math.log1p(imax)
        c['indeg'] = indeg.get(c['id'], 0)
        c['score'] = round(0.34 * (1.0 - c['p'])
                           + 0.12 * overdue_norm
                           + 0.30 * prereq_gap
                           + 0.24 * hub, 4)

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
    """★ 全图唯一调模型的节点：让模型在候选里挑 N 张，每张给一句理由。

    这节点的价值不在「写理由」（那用规则也能写），而在它**会编造 id**——
    8B模型在「列 N 个 id」这种任务上编造率不低。所以它必须和 verify 配对：
    **这里出的任何问题都不抛异常，而是让 verify 打回重来**，
    这正是这张图存在的意义：自己答完检查一遍，不合格重造。
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

    user_msg = ('【候选】\n%s\n\n【上次被驳回的原因】\n%s\n\n'
                '请选出最该先学的 %d 张。' % (
                    brief, state.get('msg') or '（无，这是第一次）', top))

    # ★ 无论成败都要 +1，route 靠它判断要不要再来一次（忘了 +1 会死循环）
    tries = (state.get('tries') or 0) + 1

    # ---- 1/3 调模型 ----
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = M.chat()          # 共享工厂，别自己 new（否则会出现模型分裂）
        resp = llm.invoke([SystemMessage(content=WRITE_SYS),
                           HumanMessage(content=user_msg)])
        text = resp.content or ''
    except Exception as e:
        # 模型不可用/超时不是「计划不合格」，但也不该让整个请求炸掉：
        # 退化成「按分数取前 N 张」，图照样出结果（少个理由而已）。
        return {'plan': _fallback_plan(state, top), 'tries': tries, 'ok': False,
                'msg': '模型不可用（%s），已退回按分数排序' % str(e)[:80]}

    # ---- 2/3 从 text 里抠出 JSON ----
    plan = _parse_plan_json(text)
    if not plan:
        # 解析失败**不要抛**，交 verify 打回。msg 会进下一轮提示词，
        # 模型能看到「上次被驳回的原因」并修正格式。
        return {'plan': [], 'tries': tries, 'ok': False,
                'msg': '输出不是合法 JSON（前 120 字：%s）'
                       % (text or '')[:120].replace('\n', ' ')}

    # ---- 3/3 返回要修改的字段 ----
    return {'plan': plan, 'tries': tries}


def _fallback_plan(state, top):
    """模型不可用时的兜底：按 score 取前 N 张，理由用规则生成。

    ★ 为什么要有兜底而不是直接报错：路径规划是「锦上添花」，
    模型挂了不该让整个页面开天窗。少一句理由比没有路径好得多。
    """
    out = []
    for c in (state.get('candidates') or [])[:top]:
        bits = []
        if c.get('never'):
            bits.append('还没学过')
        elif (c.get('overdue') or 0) > 0:
            bits.append('逾期%d天' % c['overdue'])
        if c.get('indeg'):
            bits.append('%d 张卡把它当前置' % c['indeg'])
        out.append({'id': c['id'],
                    'reason': '，'.join(bits) if bits else '按优先级排在前面'})
    return out


def _parse_plan_json(text):
    """从模型输出里抠出 JSON 数组。**抠不出就返回空 list，不抛异常。**

    三种脏法都见过（8B 全都犯过），逐层剥离：
      1. 裹 ```json ... ``` 代码块
      2. 前面加一句「好的，这是计划：」
      3. 用单引号（Python 风格）而不是双引号
    """
    if not text:
        return []
    s = text.strip()

    # 1) 剥代码块围栏
    if '```' in s:
        blocks = re.findall(r'```(?:json)?\s*(.*?)```', s, re.S)
        if blocks:
            s = blocks[0].strip()

    # 2) 直接 json.loads
    try:
        return _normalize(json.loads(s))
    except Exception:
        pass

    # 3) 抠出第一个 [...] 片段再试
    m = re.search(r'\[.*\]', s, re.S)
    if not m:
        return []
    frag = m.group(0)
    try:
        return _normalize(json.loads(frag))
    except Exception:
        pass
    # 4) 退到单引号：把 JSON 里的**单引号**换成双引号。
    #    判据是「左邻是分隔符」：`{` `,` `:` `[` 或空白 —— 这些位置出现
    #    的引号一定是键或值的引号；而`don't` 这种词内撇号左邻是字母，
    #    不会被换。原写法用 `(?![\w])` 当右邻条件是**错的**：
    #    值引号右边紧跟内容（`['a'`），正好被它排除掉了。
    try:
        fixed = re.sub(r"(?<=[\s{[:,])'", '"', frag)
        fixed = re.sub(r',\s*([\]}])', r'\1', fixed)
        return _normalize(json.loads(fixed))
    except Exception:
        return []


def _normalize(obj):
    """把模型输出收拾成 [{id, reason}]。字段不对就丢那条，不让脏数据进 state。"""
    if not isinstance(obj, list):
        return []
    out = []
    for it in obj:
        if not isinstance(it, dict):
            continue
        cid = (it.get('id') or '').strip()
        if not cid:
            continue
        out.append({'id': cid, 'reason': (it.get('reason') or '').strip()})
    return out


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
