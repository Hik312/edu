# -*- coding: utf-8 -*-
"""工具层 —— agent 能"动手"的部分，全部挂在 core/db.py 上。

文件分两节，别混着写：

    第一节  数据函数（rank / find_card / ...）返回 dict / list
    第二节  工具函数（search_cards / ...）返回 str，包一层给模型看

为什么拆两层：
  模型要的是字符串，但代码里要的是结构化数据 —— graph 的检索节点也要用
  同一套打分逻辑，如果工具直接返回字符串，节点那边就得再解析一遍 JSON。
  数据函数同时服务两边，工具函数只负责「转成模型能读的样子」。

★ 写工具最容易踩的坑：docstring 不是给人看的注释，是给模型看的**说明书**。
  模型靠它决定「这个问题该不该调这个工具、参数填什么」。写得含糊（"查询卡片"）
  的结果就是模型要么不用、要么乱用。每条都要说清：什么时候用、参数怎么填、返回什么。

现在只有 4 个工具是刻意的：工具越多，小模型选错的概率越高。
实测 qwen3:8b 在 4 个工具下选得挺准。要加新的，先想清楚它和现有的是不是真不同。
"""
import json

from .. import config as C           # 公共层：agent/config.py

# db 是纯标准库的，随便 import，不拖慢启动
import db


# ===========================================================================
# 一、数据函数 —— 返回结构化数据，工具层和 graph 的检索节点共用
# ===========================================================================
def _score(q, c):
    """关键词打分：标题命中权重最高，其次关键词标签、路径，最后一句话结论。

    中文没有分词，就用子串匹配 —— 二十来张卡的量级足够。
    真到了几千张再换检索（embedding 或全文索引），接口不用变。"""
    q = (q or '').strip().lower()
    if not q:
        return 0
    t = (c.get('title') or '').lower()
    k = ' '.join(c.get('keywords') or []).lower()
    o = (c.get('oneLine') or '').lower()
    p = ' '.join(c.get('topicPath') or []).lower()
    s = 0
    if q in t:
        s += 10
    if q in k:
        s += 6
    if q in p:
        s += 4
    if q in o:
        s += 3
    if not s:                                    # 拆不成词时退到单字命中
        s = sum(1 for ch in q if ch and (ch in t or ch in k))
    return s


def rank(query, limit=None):
    """按关键词给全库卡片打分，返回从高到低的卡片列表（原始 dict）。"""
    cards = [( _score(query, c), c) for c in db.all_cards()]
    cards = [c for c in cards if c[0] > 0]
    cards.sort(key=lambda x: -x[0])
    return [c for _, c in cards[:limit or C.SEARCH_LIMIT]]


def find_card(card_id):
    """按 id 取一张卡，没有就 None。"""
    for c in db.all_cards():
        if c.get('id') == card_id:
            return c
    return None


def neighbors_of(card_id):
    """知识图谱里的邻居：前置 / 延伸 / 对比。返回 [{id, title, kind, note}]。"""
    g = db.neighbors(card_id, depth=1)
    if not g.get('nodes'):
        return []
    out = []
    for e in g.get('edges') or []:
        other = e['target'] if e['source'] == card_id else e['source']
        out.append({
            'id': other,
            'title': next((n.get('title') for n in g['nodes'] if n['id'] == other), other),
            'kind': e.get('kind'),
            'note': e.get('note'),
        })
    return out


def due_rows(limit=15):
    """今日到期队列。

    ★ 坑：db.due_list() 有**两种返回结构** —— 文件后端把整张卡塞在 row['card'] 里，
    MySQL 快路径返回扁平行。只按顶层取 id 会全是 null，模型拿到一堆 null 就得出
    「卡片库是空的」的结论，然后理直气壮地告诉用户假话（真踩过）。"""
    out = []
    for r in db.due_list(include_all=False)[:limit]:
        c = r.get('card') if isinstance(r.get('card'), dict) else r
        lv = r.get('level')
        out.append({
            'id': c.get('id'),
            'title': c.get('title') or c.get('id'),
            'level': lv,
            'levelText': {0: '未标记', 1: '不会', 2: '模糊', 3: '会'}.get(lv, '未标记'),
            'overdueDays': r.get('overdue'),
        })
    return out


def _brief(c):
    """卡片摘要。给模型看的要短 —— 全文塞进上下文，几张卡就把窗口吃满了。"""
    return {
        'id': c.get('id'), 'title': c.get('title'),
        'oneLine': c.get('oneLine'), 'category': c.get('category'),
        'subject': c.get('subject'),
    }


# ===========================================================================
# 二、工具函数 —— 返回 str，这才是模型真正看到的东西
# ===========================================================================
def search_cards(query: str) -> str:
    """按主题搜索原理卡片。想知道某知识点有没有卡、或者要找某张卡的 id 时用这个。
    参数 query 是关键词（如"索引"、"三次握手"、"Spring 事务"），不要填整句话。
    返回若干张卡片的 id / 标题 / 一句话结论。没找到会说没找到。"""
    cards = db.all_cards()
    # 防御：模型经常把参数填成空串（实测它就填过 {'query': ''}）。
    # 这时候别回「没找到」——那会让它以为卡片库是空的，然后告诉用户一句假话。
    if not (query or '').strip():
        # 总数写在**最后**：模型对开头的数字经常视而不见（实测它列完了 20 张，
        # 还是说"没有统计张数的功能"）。放末尾它就能直接引用。
        return ('没有给关键词，下面是卡片库里的卡片：\n%s\n以上共 %d 张。'
                % (json.dumps([_brief(c) for c in cards[:20]], ensure_ascii=False),
                   len(cards)))
    hits = rank(query)
    if not hits:
        return '没有找到和「%s」相关的卡片。' % query
    return json.dumps([_brief(c) for c in hits], ensure_ascii=False)


def card_detail(card_id: str) -> str:
    """获取一张卡片的完整内容：类比、原理拆解、面试追问、使用场景、关键词。
    必须先知道 id —— 先用 search_cards 找到 id，再用这个看细节。
    参数 card_id 是卡片 id（如 "mysql-index"），不是标题。"""
    c = find_card(card_id)
    if not c:
        return '没有 id 为「%s」的卡片。先用 search_cards 找一下正确的 id。' % card_id
    # id 必须带上：runtime 从工具返回里抽引用卡（react 模式的溯源靠它）。
    # 少了它，模型明明点了 detail 却一条 sources 都认不出来。
    return json.dumps({
        'id': c.get('id'),
        'title': c.get('title'), 'oneLine': c.get('oneLine'),
        'analogy': c.get('analogy'), 'why': c.get('why'),
        'mechanism': c.get('mechanism'), 'interviewQ': c.get('interviewQ'),
        'scene': c.get('scene'), 'keywords': c.get('keywords'),
        'topicPath': c.get('topicPath'),
    }, ensure_ascii=False)


def related_cards(card_id: str) -> str:
    """查一张卡片的前置知识、延伸知识和对比知识（知识图谱里的邻居）。
    用户问「学这个之前要先懂什么」「和 X 有什么区别」时用这个。
    参数 card_id 是卡片 id，不是标题。"""
    rows = neighbors_of(card_id)
    if not rows:
        return '没有 id 为「%s」的卡片，或者这张卡还没有关联。' % card_id
    return json.dumps(rows, ensure_ascii=False)


def due_today() -> str:
    """查今天该复习哪些卡片，以及每张卡当前的掌握程度。
    用户问「今天该复习什么」「我还有多少没背」时用这个。不需要参数。"""
    rows = due_rows()
    if not rows:
        return '今天没有到期的卡片（都背完了，或者还没标记过）。'
    return json.dumps(rows, ensure_ascii=False)


def build_tools():
    """把上面 4 个函数包成 langchain 工具。graph.py 和 runtime.py 从这里拿。

    为什么工具函数在模块级定义、这里只做包装：
      模块级意味着它们就是普通函数 —— 能单测、IDE 能给类型提示、
      不看 langchain 文档也读得懂。用 @tool 装饰器写在函数上的话，
      每次 test / import 都要先装好 langchain，平白多一层耦合。

    延迟 import 是为了 agent 层「可选依赖」的约定（见 agent/__init__.py）。"""
    from langchain_core.tools import tool

    return [tool(search_cards), tool(card_detail),
            tool(related_cards), tool(due_today)]
