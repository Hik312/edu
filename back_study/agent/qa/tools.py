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

现在只有 4 个**内部**工具是刻意的：工具越多，小模型选错的概率越高。
实测 qwen3:8b 在 4 个工具下选得挺准。要加新的，先想清楚它和现有的是不是真不同。
另外还可通过 MCP 接入**外部**工具（见 mcp_servers.json + agent/mcp.py）。
目前配了 4 个 MCP server：web-search / code-exec / github-resource / cards。
其中 web-search + code-exec + github-resource 这 3 个"回答增强"工具进每轮 QA 工具集，
总数 7（4 内部 + 3 MCP）；cards 属"内容生产"动作，默认不进每轮 QA 列表
（避免 8B 模型在每轮都面对过多工具），可由导入/管理流或另一个 Agent 直接调。
qwen3:8b 在 7 个工具下偶有选错，但"联网搜 + 跑代码 + 拉外部资源"的教学收益更高，
可接受；若实测选错变多，把 build_tools 里的 max_tools 调小即可（少一个外部工具）。
"""
import contextvars
import json

from .. import config as C           # 公共层：agent/config.py

# db 是纯标准库的，随便 import，不拖慢启动
import db

#: 当前提问者。工具函数的签名是给**模型**看的，不能加参数 ——
#: 模型不知道 user_id 是什么，硬加会进 tool schema，反而降低工具调用成功率。
#: 所以走 contextvar：路由层 set_current_user(uid) 写进来，
#: 工具内部读。必须用 ContextVar 而不是模块级全局 ——
#: FastAPI 同步端点在线程池里跑，模块级全局会被并发的两个请求互相覆盖
#: （A 问「我该复习什么」，B 问同一句，A 就会拿到 B 的队列）。
_current_user = contextvars.ContextVar('qa_user_id', default=None)


def set_current_user(user_id):
    """路由层在处理问答请求前调一次。返回 token，必要时可 reset。"""
    return _current_user.set(user_id)


# ===========================================================================
# 一、数据函数 —— 返回结构化数据，工具层和 graph 的检索节点共用
# ===========================================================================
#: 中文疑问词与虚词。**单独出现没有检索价值**，但混进单字匹配里
#: 会把几乎每一张卡都拉进来 ——「什么是布隆过滤器」里的「是」，
#: 让「考研英语中非谓语动词如何使用？」这种卡也能命中（实测的坑）。
_STOP_CHARS = set('的是什么怎么如何哪些哪个是否吗呢在有和与对于把被将从到会能要')

#: 命中这个词的权重。标题最重，其次标签、路径，最后一句话结论。
_W_TITLE, _W_KEY, _W_PATH, _W_ONE = 10, 6, 4, 3


def _terms(q):
    """把查询切成可匹配的片段（中文没有分词器，用 bigram 兜底）。

    为什么不是原来的「整串匹配 + 单字兜底」：
      - 整串匹配在中文几乎永远不命中（「什么是布隆过滤器」不会原样出现在
        任何一张卡的标题里）；
      - 于是全靠单字兜底，而单字里混着「是」「的」「怎」这种字，
        结果是**几百张卡全部命中**，真正相关的卡被埋在噪声里。

    bigram（「布隆」「隆过」「过滤」「滤器」）既能定位专有名词，
    又天然过滤掉单字噪声。查询只有一两个字时退回原串。
    """
    q = (q or '').strip().lower()
    if not q:
        return []
    cleaned = ''.join(ch for ch in q if ch not in _STOP_CHARS)
    if len(cleaned) < 2:
        return [cleaned or q]
    return [cleaned[i:i + 2] for i in range(len(cleaned) - 1)]


def _score(q, c):
    """关键词打分：按 bigram 片段在各字段的命中累加，标题权重最高。

    真到了几千张卡再换全文索引（`ft_cards` 已建），
    到时只改这一处，调用方接口不用变。
    """
    terms = _terms(q)
    if not terms:
        return 0
    t = (c.get('title') or '').lower()
    k = ' '.join(c.get('keywords') or []).lower()
    o = (c.get('oneLine') or '').lower()
    p = ' '.join(c.get('topicPath') or []).lower()
    s = 0
    for term in terms:
        if term in t:
            s += _W_TITLE
        elif term in k:
            s += _W_KEY
        elif term in p:
            s += _W_PATH
        elif term in o:
            s += _W_ONE
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


def due_rows(limit=15, user_id=None):
    user_id = user_id if user_id is not None else _current_user.get()
    """今日到期队列。

    ★ 坑：db.due_list() 有**两种返回结构** —— 文件后端把整张卡塞在 row['card'] 里，
    MySQL 快路径返回扁平行。只按顶层取 id 会全是 null，模型拿到一堆 null 就得出
    「卡片库是空的」的结论，然后理直气壮地告诉用户假话（真踩过）。"""
    out = []
    for r in db.due_list(include_all=False, user_id=user_id)[:limit]:
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
    rows = due_rows(user_id=_current_user.get())
    if not rows:
        return '今天没有到期的卡片（都背完了，或者还没标记过）。'
    return json.dumps(rows, ensure_ascii=False)


def build_tools():
    """把上面 4 个函数包成 langchain 工具。graph.py 和 runtime.py 从这里拿。

    为什么工具函数在模块级定义、这里只做包装：
      模块级意味着它们就是普通函数 —— 能单测、IDE 能给类型提示、
      不看 langchain 文档也读得懂。用 @tool 装饰器写在函数上的话，
      每次 test / import 都要先装好 langchain，平白多一层耦合。

    延迟 import 是为了 agent 层「可选依赖」的约定（见 agent/__init__.py）。

    MCP 工具（外部 server）：在内部 4 个之后 extend。受"小模型工具选错"约束，
    目前最多再放 3 个（web-search + code-exec + github-resource，见顶部注释：
    7 个工具下 qwen3:8b 偶有选错但可接受；cards server 默认不进每轮 QA 列表）。
    MCP 不可用 / 配置缺失 / server 起不来，都静默降级——build_tools 照常返回
    内部 4 个，主链路一行不挂。"""
    from langchain_core.tools import tool

    tools = [tool(search_cards), tool(card_detail),
             tool(related_cards), tool(due_today)]
    try:
        from ..mcp import load_mcp_tools
        mcp_tools = load_mcp_tools(max_tools=3)
        if mcp_tools:
            tools.extend(mcp_tools)
    except Exception as e:
        # 失败绝不能拖垮问答：降级成纯内部工具，只留个痕迹
        import sys
        sys.stderr.write('[mcp] 未加载外部工具（已降级为内部 4 个）：%s\n' % e)
    return tools
