# -*- coding: utf-8 -*-
"""运行时 —— 怎么把图跑起来。缓存、会话历史、流式输出都收在这一层。

为什么和 graph.py 分开：
  graph.py 只管「图长什么样」（纯构建，无副作用），
  runtime.py 管「什么时候建、建几次、怎么跑」（有状态）。

  分开之后，编译好的图可以被复用 —— 否则每个请求都重建一次图，
  在 FastAPI 里就是每个请求都白跑一遍构建。

三层的关系一眼能看清：

    tools.py    能做什么（查卡片）
    nodes.py    每步做什么（检索 / 回答 / 自检）
    graph.py    按什么顺序做
    runtime.py  怎么跑起来（本文件）
"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from .. import config as C
from . import ans_cache       # 答案缓存（Redis；单轮+无卡命中才用）
from . import nodes          # 流式 sink（set_token_sink）要经它装/还原
from . import retrieval
from . import tools
from . import websearch
from .graph import build_qa, build_react, recursion_config


# ---------------------------------------------------------------------------
# 实例缓存
# ---------------------------------------------------------------------------
# 图是无状态的（状态每次 invoke 时传入），所以共享一个实例是安全的。
# 换了模型 / 改了配置要调 reset()，否则还在用旧实例。
_qa = None
_react = None


def qa_app():
    """问答图的单例。"""
    global _qa
    if _qa is None:
        _qa = build_qa()
    return _qa


def react_app():
    """ReAct agent 的单例。"""
    global _react
    if _react is None:
        _react = build_react()
    return _react


def reset():
    """丢弃缓存的图。改了模型、改了 config 之后调一下。"""
    global _qa, _react
    _qa = None
    _react = None


# ---------------------------------------------------------------------------
# 记忆（三层里的 L1 会话历史 + L3 长期档案）
# ---------------------------------------------------------------------------
def trim_history(history):
    """裁剪多轮历史：按字符预算从**最旧**开始丢，但至少留最近 HISTORY_KEEP 轮。

    为什么不做好看的 LLM 摘要：本地 8B 一次调用 20 秒，为省 1500 字上下文
    多等 20 秒，用户等的是回答不是摘要。真上了云端大模型再换（config 里有注释）。

    输入输出都是 [{role, content}]（前端发什么形状就用什么形状），
    调用方不需要知道有裁剪这回事。
    """
    out = []
    for m in (history or []):
        if not isinstance(m, dict):
            continue
        role = m.get('role')
        content = m.get('content')
        if role not in ('user', 'assistant') or not isinstance(content, str):
            continue
        out.append({'role': role, 'content': content})
    if not out:
        return []

    budget = C.HISTORY_MAX_CHARS
    keep = max(1, C.HISTORY_KEEP) * 2          # 一轮 = 一问一答
    total = sum(len(m['content']) for m in out)
    if total <= budget:
        return out

    # 从最旧开始丢，但保底留 keep 条（最近的问答对）
    kept = out[-keep:]
    used = sum(len(m['content']) for m in kept)
    for m in reversed(out[:-keep]):
        n = len(m['content'])
        if used + n > budget:
            break
        kept.insert(0, m)
        used += n
    return kept


def format_history(history):
    """把多轮历史压成一段给提示词看的纯文本（flow 模式用）。

    有长度上限是防御性的：trim_history 已经裁过，这里再截一道，
    是因为传进来的 history 可能来自绕过 trim 的调用方（比如 demo 脚本）。
    """
    lines = []
    for m in (trim_history(history) or []):
        tag = '我' if m['role'] == 'user' else '助手'
        lines.append('%s：%s' % (tag, m['content']))
    return '\n'.join(lines)[:C.HISTORY_MAX_CHARS]


def format_profile(profile):
    """长期档案（L3）→ 一段注入 system 的话。

    档案是「关于这个用户的事实」，不是对话内容 —— 所以它进 system 提示，
    而不是混进历史。没有档案就返回空串，调用方据此不加这一段。
    """
    if not isinstance(profile, dict):
        return ''
    parts = []
    if profile.get('role'):
        parts.append('目标岗位：%s' % profile['role'])
    topics = profile.get('topics') or []
    if topics:
        parts.append('常问主题：%s' % '、'.join(str(t) for t in topics[:6]))
    weak = profile.get('weak') or []
    if weak:
        parts.append('薄弱卡片（回答时可主动提醒先补）：%s'
                     % '、'.join(str(w) for w in weak[:6]))
    if not parts:
        return ''
    return '【用户档案】\n' + '\n'.join(parts)


# ---------------------------------------------------------------------------
# 输出清洗：回答只留正文
# ---------------------------------------------------------------------------
def clean_answer(text):
    """剥掉模型照抄进正文的内部标识：卡片 id、【id】引用标记、JSON、工具名。

    为什么必须做（提示词压不住）：retrieve 节点把资料拼成 `【卡片id】标题`
    喂给模型，8B 模型会原样抄进答案 —— 光靠"不许输出 id"这句话它照抄不误。
    提示词是第一道，这里是第二道，前端还有第三道兜底。
    """
    if not text:
        return ''
    s = str(text)
    lines = []
    for ln in s.split('\n'):
        t = ln.strip()
        # 行首的【xxx】引用标记（模型常把整行写成【java-jvm】标题：...）
        if t.startswith('【'):
            close = t.find('】')
            if 0 < close <= 60:
                t = t[close + 1:].lstrip(' ：:')
        # 整行就是一个 id / id 列表（"引用卡片：a、b、c"）
        if t.startswith(('引用卡片', '引用：', '引用:', '来源：', '来源:')):
            continue
        lines.append(t)
    s = '\n'.join(x for x in lines if x).strip()

    # 正文中间夹着的 `【some-id】`（含空格、下划线的英文短横线串）
    s = re.sub(r'【\s*[A-Za-z][A-Za-z0-9_\-]{1,60}\s*】', '', s)
    # 模型把整段 JSON 结果（含内嵌的单个对象）贴出来的情况
    s = re.sub(r'\{[^{}]*"id"\s*:\s*"[^"]+"[^{}]*\}', '', s)
    # "卡片 id 为 xxx"、"卡 ID：xxx"、"ID: xxx" 这类句式里的 id
    # ★ 第二个分支必须带 \b：没有词边界时，任何以 id 结尾的英文词后跟冒号
    # 都会被吃掉一段（`valid: true` → `val`、`solid: …`、`grid: …`），
    # 中英混排的技术回答里很常见 —— 那是「清洗把答案改坏」。
    # web/src/api/agent.js 是同一份正则（流式边生成边渲染，后端洗不到），
    # 两边必须一起改。
    s = re.sub(r'(?i)(卡\s*片?\s*id\s*[:：为]?\s*|\bid\s*[:：]\s*)'
               r'[A-Za-z][A-Za-z0-9_\-]{1,60}', '', s)
    # 「（参考《xxx》的内嵌容器机制）」这类括号出处标注：正文里读着突兀、
    # 把句子切得不通顺（用户反馈）。出处走 sources 字段，不靠正文括注。
    # 只删**括号包住且以参考/参见/引自/出自开头**的 —— 正文里正常引用
    # 《手册》安装这类句子不带这个开头，不会被误伤。
    s = re.sub(r'[（(]\s*(?:参考|参见|引自|出自|出处\s*[:：])[^（()）]{0,100}[）)]',
               '', s)
    # 连续空行压成一个
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def _ids_in(text):
    """从工具返回（JSON 或文本）里抽卡片 id。抽不到就返回空表。"""
    if not text:
        return []
    ids = []
    t = str(text)
    try:
        obj = json.loads(t)
    except Exception:
        obj = None
    if isinstance(obj, dict):
        # card_detail 返回的单对象没有 id 字段（工具拼的时候漏了），
        # 从 topicPath 拿不到 id，所以这里只认明确的 id / cards / rows
        if isinstance(obj.get('id'), str):
            ids.append(obj['id'])
        for k in ('cards', 'rows', 'items'):
            for it in obj.get(k) or []:
                if isinstance(it, dict) and isinstance(it.get('id'), str):
                    ids.append(it['id'])
    elif isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict) and isinstance(it.get('id'), str):
                ids.append(it['id'])
    else:
        # 文本形态：抓 `xxx-yyy` 这种短横线 id（限制在已知卡 id 上由调用方做）
        ids.extend(re.findall(r'"id"\s*:\s*"([A-Za-z][A-Za-z0-9_\-]+)"', t))
    return ids


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------
def ask(question: str, mode: str = 'flow', web: bool = False) -> str:
    """最简单的入口：问一句，拿回答。不保留上下文，每次独立。

    web  联网开关（可选增强）：true 时检索追加【网页】资料，搜不到不影响回答"""
    if mode == 'react':
        return run_react(question, web=web)['answer']
    st = qa_app().invoke(
        {'question': question, 'context': '', 'answer': '', 'sources': [],
         'tries': 0, 'ok': False, 'history': '', 'profile': '', 'web': web},
        config=recursion_config(),
    )
    return st.get('answer') or ''


def stream_flow(question: str, on_token, history=None, profile=None,
                web: bool = False, user_id=None, on_step=None):
    """flow（固定流程）模式的**流式**版本。

    为什么要单独做一个：flow 的 answer 节点原来是 `invoke()` 一次性返回，
    本地 8B 生成一段要20~40 秒 —— 用户盯着空白页，只能判断"坏了"。
    现在answer 节点改成边生成边回调（见 nodes.answer 的 token sink），
    本函数把 sink 装上、把增量往外吐，最后仍返回完整结果（给 sources）。

    ⚠️ **流式只是"提前看到字"，质检逻辑没变**：grade 拿到的仍是完整答案，
    没过检照样会重写一轮 —— 所以用户可能看到答案被覆盖重写，这是设计如此。

    ★ **带答案缓存**（qa/ans_cache.py）：单轮问题（没有 history）时，
    先查一次「同用户 + 同问题 + 同卡片底料 + 同模式 + 同联网开关」的缓存，命中就把
    答案按 chunk 吐出来（假装流式，用户几百毫秒就看到完整回答）。
    有 history 一律不查缓存 —— 历史不同答案就不同，命中会答偏。
    """
    tools.set_current_user(user_id)

    # ---- 缓存路径：只对「单轮 + 完整问题」生效 ----
    if not history:
        hit = ans_cache.get(question, 'flow', web, [], user_id=user_id)
        if hit:
            ans = hit.get('answer') or ''
            if on_step:
                on_step('回答（命中缓存）…')
            # 按块吐出，让前端体验和真流式一致（几十毫秒就铺满）
            CH = 24
            for i in range(0, len(ans), CH):
                on_token(ans[i:i + CH])
            return {'answer': ans, 'sources': hit.get('sources') or [],
                    'steps': None, 'cached': True}

    if on_step:
        on_step('检索卡片库…')
    old = nodes.set_token_sink(on_token)
    try:
        if on_step:
            on_step('组织回答…')
        st = qa_app().invoke(
            {'question': question, 'context': '', 'answer': '', 'sources': [],
             'tries': 0, 'ok': False,
             'history': format_history(history), 'profile': format_profile(profile),
             'web': web},
            config=recursion_config(),
        )
    finally:
        # 必须还原：线程池会复用线程，不还原会让下一次调用读到上次的 sink。
        nodes.reset_token_sink(old)

    # ---- 写缓存：只写「检索没命中任何卡」的答案 ----
    # ★ 有命中卡的答案**故意不缓存**：底料随时会变（改了卡），
    #   而这里拿不到"用了哪几张卡"（answer 节点不写 state），
    #   拿不到就意味着无法构造正确的失效指纹 —— 那就宁可不缓存。
    #   纯参数回答（没查到卡）反而不受卡片变动影响，缓存最安全。
    sources = st.get('sources') or []
    answer = clean_answer(st.get('answer'))
    if not sources:
        ans_cache.put(question, 'flow', web, [], answer, [], user_id=user_id)
    return {'answer': answer,
            'sources': sources,
            'steps': None}


def ask_full(question: str, mode: str = 'flow', history=None, profile=None,
             web: bool = False, user_id=None):
    """带溯源的入口：返回 {'answer', 'sources', 'steps'}。

    history  L1 会话历史（[{role, content}]），超预算自动裁剪
    profile  L3 长期档案（{role, topics, weak}），注入 system
    web      联网开关：true 时资料追加【网页】搜索结果（可选增强）

    sources 是这次回答引用到的卡片 id：flow 由 retrieve 节点写入 state；
    react 这次改成**从工具返回里抽** —— 模型自己查的卡本来就是引用，
    以前留空等于白给了引用能力却没接上（用户反馈"知识库没有带引用"）。
    前端拿 sources 渲染「引用卡片」，点开跳到对应卡片详情。"""
    # 工具（due_today）要读当前人的进度，而它的签名给模型看、不能带user_id。
    # 这里 set 一次，下面 run_react / qa_app().invoke 在同一线程里跑，能读到。
    tools.set_current_user(user_id)
    if mode == 'react':
        out = run_react(question, history=history, profile=profile, web=web)
        return {'answer': out['answer'], 'sources': out['sources'],
                'steps': out['steps']}
    st = qa_app().invoke(
        {'question': question, 'context': '', 'answer': '', 'sources': [],
         'tries': 0, 'ok': False,
         'history': format_history(history), 'profile': format_profile(profile),
         'web': web},
        config=recursion_config(),
    )
    return {'answer': clean_answer(st.get('answer')),
            'sources': st.get('sources') or [],
            'steps': None}


def _react_ground(question, web=False):
    """react 的"先搜后答"——在代码里替模型把底料搜好塞进上下文。

    提示词里写了"先 search_cards 再答"，实测 qwen3:8b 两轮都没查：直接凭参数
    知识答，一条 sources 都没有，还编了个库里不存在的卡名。检索是纯 Python、
    毫秒级的，没有理由指望 8B 自觉 —— 直接搜好喂给它，和 flow 模式的 retrieve
    节点**同一套检索、同一套口径**（sources 也按命中的算）。

    web 开着时把【网页】块也拼进底料（同 flow 的 retrieve 节点）——网页结果
    不进 sources（sources 只认卡片 id，前端要拿去跳卡片详情的）。

    返回 (text, ids)：text 是给模型看的检索结果，ids 是这次要登记成 sources 的
    卡 id。卡片没命中、也没开联网时返回 ('', set())，别把空提示塞进去占地方。"""
    try:
        hits = retrieval.retrieve(question, C.TOP_K)
    except Exception:
        hits = []
    lines = []
    for h in hits:
        c = h.card or {}
        block = '《%s》%s' % (c.get('title') or h.id, c.get('oneLine') or '')
        # why / 原理也喂进去，和 flow 模式 retrieve 节点对齐 —— 只给一句话结论的
        # 实测后果是模型答完说"卡片库未直接提及该算法细节"，明明机制里写着。
        # 原理限长：底料是每轮都带的，不能把上下文窗口喂爆。
        if c.get('why'):
            block += '\n  为什么：' + c['why']
        if c.get('mechanism'):
            block += '\n  原理：' + ' / '.join(c['mechanism'])[:180]
        lines.append(block)
    parts = []
    if lines:
        parts.append('卡片库检索结果（回答优先依据这些卡；细节不够用 '
                     'card_detail 按 id 查）：\n' + '\n'.join(lines))
    if web:
        parts.append(websearch.web_context(question))
    if not parts:
        return '', set()
    return '\n\n'.join(parts), {h.id for h in hits}


def run_react(question: str, history=None, profile=None, on_step=None,
              web: bool = False):
    """跑一次 ReAct，返回 {'answer', 'history', 'steps', 'sources'}。

    history：上一轮的 messages 列表（[{role,content}] 或 langchain 消息），
             传进来就是多轮对话。
    profile：L3 长期档案，会作为一条 system 消息插在最前面。
    on_step：回调，收到每一步的事件 dict —— 调试和 SSE 都靠它。
             模型「查了但没用上」和「压根没查」是两种完全不同的病，
             不看过程根本分不清。

    多轮历史这里自己维护一个 list，没用 langgraph 的 checkpointer：
    目前够用且可控。真要跨进程持久化（重启后还能接着聊）再换
    checkpointer + Redis —— 那是路线里的第 7 步。"""
    steps = []
    msgs = []
    fp = format_profile(profile)
    if fp:
        msgs.append(SystemMessage(content=fp))
    for m in (trim_history(history) or []):
        if m['role'] == 'user':
            msgs.append(HumanMessage(content=m['content']))
        else:
            msgs.append(_ai(m['content']))
    # 底料拼在问题后面（不进 history）：下一轮不重复带，用户也看不到
    gtext, gids = _react_ground(question, web=web)
    msgs.append(HumanMessage(content=question if not gtext
                             else question + '\n\n' + gtext))

    out = react_app().invoke({'messages': msgs}, config=recursion_config())
    msgs = out.get('messages') or msgs

    seen_ids = set(gids)
    for m in msgs:
        for tc in (getattr(m, 'tool_calls', None) or []):
            ev = {'type': 'tool_call', 'name': tc.get('name'), 'args': tc.get('args')}
            steps.append(ev)
            if on_step:
                on_step(ev)
            # 从调用参数里抓 id（card_detail / related_cards 的入参就是 card_id）
            a = tc.get('args') or {}
            for v in a.values():
                if isinstance(v, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_\-]{1,60}', v):
                    seen_ids.add(v)
        if getattr(m, 'type', '') == 'tool':
            ev = {'type': 'tool_result', 'content': str(getattr(m, 'content', ''))}
            steps.append(ev)
            if on_step:
                on_step(ev)
            for i in _ids_in(ev['content']):
                seen_ids.add(i)

    last = msgs[-1] if msgs else None
    answer = clean_answer((getattr(last, 'content', '') or '').strip())
    # 抽到的 id 里可能有模型瞎编的（工具参数瞎填）——只保留真在库里的
    valid = {c.get('id') for c in _all_cards_ids()}
    sources = [i for i in sorted(seen_ids) if i in valid]
    return {'answer': answer, 'history': msgs, 'steps': steps, 'sources': sources}


def _all_cards_ids():
    import db
    return db.all_cards()


def _ai(text):
    """构造一条 AI 消息：优先 AIMessage，兼容不同 langchain 版本的导入路径。"""
    from langchain_core.messages import AIMessage
    return AIMessage(content=text or '')


def stream_react(question: str, history=None, profile=None, on_sources=None,
                 web: bool = False, user_id=None):
    """流式版本：一边生成一边 yield 文本块，给 FastAPI 的 StreamingResponse / SSE 用。

    本地 8B 模型出字慢（实测整答要 20 秒以上），让用户盯着空白等 20 秒
    基本等于坏了。流式是本地模型**必需**的体验补偿，不是锦上添花。

    on_sources：可选回调，生成**结束后**调一次，把这次用到的卡片 id 列表交给
    调用方 —— SSE 用它在 done 帧之前补发一个 sources 帧。"""
    tools.set_current_user(user_id)
    app = react_app()
    msgs = []
    fp = format_profile(profile)
    if fp:
        msgs.append(SystemMessage(content=fp))
    for m in (trim_history(history) or []):
        msgs.append(HumanMessage(content=m['content']) if m['role'] == 'user'
                    else _ai(m['content']))
    # 同 run_react：底料拼在问题后面，命中的卡直接算进 sources
    gtext, gids = _react_ground(question, web=web)
    msgs.append(HumanMessage(content=question if not gtext
                             else question + '\n\n' + gtext))

    # 流式里捞引用：tool 消息（工具返回）会逐条流出来，边流边记 id。
    # 走的是和 run_react 同一套 _ids_in()，保证两种模式的 sources 口径一致。
    seen = set(gids)
    args_buf = {}                       # 工具参数是分片流出的，按 index 攒起来再解析
    # stream_mode='messages' 会逐个 token 产出，token 里带 content 的才往下发
    for chunk, _meta in app.stream({'messages': msgs}, config=recursion_config(),
                                   stream_mode='messages'):
        ctype = getattr(chunk, 'type', '')
        if ctype == 'tool':
            for i in _ids_in(getattr(chunk, 'content', '')):
                seen.add(i)
            continue
        for tc in (getattr(chunk, 'tool_call_chunks', None) or []):
            i = tc.get('index')
            buf = args_buf.setdefault(i, {'name': tc.get('name') or '', 'args': ''})
            if tc.get('name'):
                buf['name'] = tc['name']
            buf['args'] += tc.get('args') or ''
        text = getattr(chunk, 'content', None)
        if isinstance(text, str) and text:
            yield text
        elif isinstance(text, list):            # 某些模型返回分块列表
            for part in text:
                if isinstance(part, dict) and part.get('type') == 'text':
                    yield part.get('text') or ''

    # 攒齐的工具参数（card_detail 的 card_id 等）
    for buf in args_buf.values():
        try:
            a = json.loads(buf['args'] or '{}')
        except Exception:
            continue
        if isinstance(a, dict):
            for v in a.values():
                if isinstance(v, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_\-]{1,60}', v):
                    seen.add(v)

    valid = {c.get('id') for c in _all_cards_ids()}
    if on_sources:
        on_sources([i for i in sorted(seen) if i in valid])
