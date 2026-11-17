# -*- coding: utf-8 -*-
"""数据层 · 图谱域 —— 四层知识图谱的构建、局部邻居、结构洞察、PPR 推荐、学习路径。

节点：领域 / 科目 / 主题 / 卡片四层；边：层级归属 + 卡片间的语义关联。
层级边是骨架（否则图会散成互不相连的孤岛）；语义边来自卡片的 related 字段。

build_graph 只算了 degree（「我连着几个知识点」）；中心性 / 社区 / 路径
全在 algo/graph.py 里（纯函数、不连库、可单测），这里只做三件事：
取图、传参、把结果翻译成界面能直接渲染的形状。

**为什么不把算法直接写进路由**：图算法要调参（阻尼、社区度、边类型
权重），写在路由里就没法离线对拍，也没法单测。分层之后
`python -c "import algo.graph"` 就能验证，不用起服务。
"""
import json
import os
import time as _time

from .base import DATA_DIR, STORE_DIR, algostore, today_str
from .cards import all_cards
from .catalog import cat_name, subject_name
from .progress import get_progress


def build_graph(category=None, subject=None, user_id=None):
    """节点：领域 / 科目 / 主题 / 卡片四层；边：层级归属 + 卡片间的语义关联。

    层级边是骨架（否则图会散成互不相连的孤岛）；
    语义边来自卡片的 related 字段，必须带 kind 与 note——不做关键词自动连，
    那样得到的只是毛线球，不是知识图谱。
    """
    prog = get_progress(user_id)
    cards = all_cards(category=category, subject=subject)
    ids = set(c['id'] for c in cards)

    nodes = {}
    edges = []

    def node(nid, label, ntype, **kw):
        if nid not in nodes:
            nodes[nid] = dict({'id': nid, 'label': label, 'type': ntype,
                               'degree': 0}, **kw)
        return nodes[nid]

    def link(a, b, kind, **kw):
        if a not in nodes or b not in nodes:
            return
        edges.append(dict({'source': a, 'target': b, 'kind': kind}, **kw))
        nodes[a]['degree'] += 1
        nodes[b]['degree'] += 1

    # --- 层级骨架 ---
    for c in cards:
        cat = c.get('category') or 'other'
        sub = c.get('subject') or 'other'
        path = c.get('topicPath') or ['未归档']

        node('cat:' + cat, cat_name(cat), 'category', cat=cat)
        node('sub:' + cat + '/' + sub, subject_name(sub), 'subject',
             cat=cat, sub=sub)

        # 主题按完整路径逐层建节点，相邻层相连（SpringBoot → 核心原理 → 自动装配）
        parent = 'sub:' + cat + '/' + sub
        for i, seg in enumerate(path):
            nid = 'topic:' + sub + '/' + '/'.join(path[:i + 1])
            node(nid, seg, 'topic', cat=cat, sub=sub, depth=i)
            link(parent, nid, 'belong')
            parent = nid

        node(c['id'], c.get('title'), 'card',
             cat=cat, sub=sub, topic=path[-1],
             oneLine=c.get('oneLine', ''),
             keywords=c.get('keywords', []),
             level=(prog.get(c['id']) or {}).get('level', 0))
        link(c['id'], parent, 'belong')

    # --- 语义关联（去重：无向，A-B 与 B-A 视为同一条） ---
    seen = {}                              # 卡对 → 它在 edges 里的下标
    for c in cards:
        for r in (c.get('related') or []):
            tid = r.get('id') if isinstance(r, dict) else r
            if tid not in ids or tid == c['id']:
                continue                        # 指向已删除的卡就静默跳过
            note = r.get('note', '') if isinstance(r, dict) else ''
            kind = r.get('kind', 'rel') if isinstance(r, dict) else 'rel'
            key = tuple(sorted([c['id'], tid]))
            i = seen.get(key)
            if i is None:
                seen[key] = len(edges)
                link(c['id'], tid, kind, note=note)
                continue
            # 同一对卡只留一条关系，但 **prereq 必须赢**：学习路径只认 prereq
            # （见 db.graph_path），而同一对卡上经常同时声明了 compare/extends。
            # 老写法是「谁先遍历到谁留下」，于是 343 对前置关系里有 109 对
            # 被另一条 compare 静默吃掉 —— 表面上图正常，路径却凭空断了。
            if kind == 'prereq' and edges[i]['kind'] != 'prereq':
                edges[i].update(source=c['id'], target=tid, kind='prereq',
                                note=note)
            # 其余（同类重复 / 非 prereq 撞上 prereq）都跳过

    return {'nodes': list(nodes.values()), 'edges': edges}


def neighbors(cid, depth=1, until_cards=False):
    """局部图谱：给定卡片，返回它的 n 层邻居子图。
    Obsidian 的经验是——全局图谱到了几百节点就是毛线球，
    真正有用的是「这张卡周围有什么」。

    ★ until_cards：展开到「见到卡为止」，不再按跳数停。
      点章节节点（subject / topic）时必须开这个 —— 层级是
      subject → topic → topic → … → card，卡挂的层数**不固定**，
      固定跳数会出现「满屏章节节点、一张卡都没有」（点 AI 工程 1 跳
      就只看得见它下面的十几个章节）。对卡节点本身无效（它自己就是卡），
      所以前端只对非卡节点传 True。
    """
    g = build_graph()
    nodes = {n['id']: n for n in g['nodes']}
    adj = {}
    for e in g['edges']:
        adj.setdefault(e['source'], []).append((e['target'], e))
        adj.setdefault(e['target'], []).append((e['source'], e))

    if cid not in nodes:
        return {'nodes': [], 'edges': [], 'center': None}

    def is_card(i):
        return nodes[i].get('type') == 'card'

    visited = {cid}
    frontier = [cid]
    keep_edges = {}
    # until_cards 至少要走 1 跳；深度上限防「从章节一路摊到全库」
    rounds = max(1, depth) if not until_cards else 8
    for _ in range(rounds):
        nxt = []
        for cur in frontier:
            for nb, e in adj.get(cur, []):
                ek = tuple(sorted([e['source'], e['target']])) + (e['kind'],)
                if ek not in keep_edges:
                    keep_edges[ek] = e
                if nb not in visited:
                    visited.add(nb)
                    nxt.append(nb)
        frontier = nxt
        if not frontier:
            break
        # 已经铺到卡就不再往外扩了 —— 再扩只是给章节网加边，对「看卡」没用
        if until_cards and any(is_card(i) for i in visited):
            break

    return {
        'center': cid,
        'nodes': [dict(nodes[i], isCenter=(i == cid)) for i in visited],
        'edges': list(keep_edges.values())
    }


# ---------- 图算法（结构洞察 / 推荐 / 路径） ----------
#: 图结构级的缓存。key 是 (category, subject)，value 是 (ts, nodes, edges)。
#: ★ 为什么能缓存：节点和边完全由 all_cards() 决定，**与用户无关**
#:   （level 是 build_graph 里从 progress 贴上去的，属于个人数据，
#:   不进这个缓存 —— 否则 A 的缓存会被 B 读到，正好是 P0-1 刚修掉的那类 bug）。
#:   卡片集变了（造卡/删卡/导入文档）时间戳才会变，靠 mtime 判定。
_GRAPH_CACHE = {}
_GRAPH_CACHE_TTL = 300.0        # 秒。结构类接口变更频率极低，5 分钟足够


def _graph_mtime():
    """卡片数据的最新 mtime。用来在造卡后自动作废缓存。

    取三个来源的最大值：内置 js、store 目录、data 目录。
    只看其中一个会漏 —— 造脚本可能只写 store，不碰 js。
    ★ 2026-11-15 补 os.walk：目录 mtime 只在**直接子项**增删改名时变，
      深层文件（store/files/<id>/xxx.png）改内容它纹丝不动 —— 只看目录
      mtime 会漏掉「造卡脚本只写 store 深处」的场景。walk 每次全扫太贵，
      折衷：目录 mtime + data/*.js + store 顶层 json 文件的 mtime。
    """
    newest = 0.0
    for d in (DATA_DIR, STORE_DIR):
        try:
            newest = max(newest, os.path.getmtime(d))
        except OSError:
            pass
    try:
        import glob
        for f in glob.glob(os.path.join(DATA_DIR, '*.js')):
            newest = max(newest, os.path.getmtime(f))
        # store 目录的直接子文件（cards.custom / cards.override / progress 等
        # 都在这层）；子目录交给下面的 walk—— 只多扫一层，代价可忽略。
        for f in glob.glob(os.path.join(STORE_DIR, '*.json')):
            newest = max(newest, os.path.getmtime(f))
    except OSError:
        pass
    return newest


def graph_raw(category=None, subject=None):
    """给算法层用的**裸图**（不含个人 level），带 mtime 失效的缓存。

    返回 (nodes, edges)。调用方拿到的是**同一份对象**，改它会污染缓存
    —— 所以只在算法层内部用，要改先 deepcopy。
    """
    key = (category or '', subject or '')
    now = _time.time()
    hit = _GRAPH_CACHE.get(key)
    if hit and now - hit[0] < _GRAPH_CACHE_TTL and hit[3] == _graph_mtime():
        return hit[1], hit[2]
    g = build_graph(category=category, subject=subject)   # 不传 user_id → 无 level
    nodes, edges = g['nodes'], g['edges']
    _GRAPH_CACHE[key] = (now, nodes, edges, _graph_mtime())
    return nodes, edges


def graph_insight(category=None, subject=None, k=2, resolution=4.0):
    """结构洞察：中心性 + 社区 + 图的体检报告。

    给界面顶部那排指标和「这块知识长什么样」用。三块内容各自的用处：

    - **pagerank**   ：全局权威知识点（抗造卡噪声，比 degree 准）
    - **betweenness**：必经之路（prereq 图上的关卡）
    - **communities**：Louvain 自动分块 —— 不用手点 chips 也能看出
                       「这几张卡其实是一伙的」
    - **coverage**   ：连通分量 / 孤岛率。这是**数据体检**，
                       orphanRate 高说明该补 related，不是算法出错

    ★ resolution 为什么是 4.0 而不是标准的 1.0：
      这张图的主体是 belong 骨架树（1268/2114 条边），模块内的卡天然连成
      一整块。标准模块度下 Louvain 把「Java+Python」合成 265 节点、
      「AI 工程」181 节点 —— 11 个社区里两个就占了 446 个，这种分块
      等于没分。实测扫参（567 节点，0.01s 一次）：

          res   社区数  最大块   结果
          1.0     11     265    Java+Python 糊成一坨
          2.2     12     229    还是太大
          3.0     14     181    AI 工程仍 165
          4.0     17     181    Java 53 / AI 139 / Python 84 / 专业课 56 ✓

      4.0 之后块边界和真实科目对上了。这是「多大的模块才算一个社区」
      的显式取值，不是试出来的魔数 —— 用户来图谱就是看细节的，我们要细。

    ⚠️ 改这个值之前先确认 gain 公式的基准增益是对的：Louvain 里
      「best_gain 初始 None + 第一个候选无条件胜出」会让 resolution
      完全失效（1.0 和 5.0 分块一模一样），2026-10-03 修过一次。
      改参数没反应时先查那个。
    """
    import algo.graph as G
    nodes, edges = graph_raw(category=category, subject=subject)
    if not nodes:
        return {'ok': True, 'empty': True, 'pagerank': [], 'betweenness': [],
                'communities': [], 'coverage': {'nodes': 0, 'cards': 0, 'edges': 0}}
    pr = G.pagerank(nodes, edges)
    bt = G.betweenness(nodes, edges)
    label = {n['id']: n for n in nodes}

    def brief(i, v, metric):
        n = label[i]
        return {'id': i, 'label': n.get('label'), 'type': n.get('type'),
                'metric': metric, 'value': v,
                'degree': n.get('degree', 0),
                'oneLine': n.get('oneLine', '')}

    comms = G.louvain(nodes, edges, resolution=resolution)
    # 极小的社区（1~2 个节点）单独列出来：它们对「分块」这个功能没有
    # 意义，但**值得知道** —— 那正是孤岛卡所在。塞进主列表只会占图例。
    small = [c for c in comms if len(c) <= 2]
    main = [c for c in comms if len(c) > 2]

    # members 只给前 60 个（前端图例用不着更多），但**顺序要重排**：
    # 结构节点（category/subject/topic）排在前面。
    # ★ 不重排的话，一个 265 节点的大社区里 subject 根节点可能排在第 80 位，
    #   被 60 的截断切掉 —— 前端 communityName 拿不到根，只能拿首张卡的标题
    #   去命名，结果 265 张卡的大社区被叫成「ArrayBlockingQueue …」。
    #   排序键：层级越浅越靠前，同层按 id 排（保证两次调用输出一致）。
    def rank_key(i):
        t = (label.get(i) or {}).get('type')
        order = {'category': 0, 'subject': 1, 'topic': 2}.get(t, 3)
        depth = (label.get(i) or {}).get('depth', 9)
        return (order, depth if order == 2 else 0, i)

    return {
        'ok': True,
        'empty': False,
        'pagerank': [brief(i, v, 'pagerank') for i, v in G.topn(pr, 15)],
        'betweenness': [brief(i, v, 'betweenness') for i, v in G.topn(bt, 15)],
        'communities': [{'size': len(c), 'members': sorted(c, key=rank_key)[:60]}
                        for c in main],
        'tinyCount': len(small),
        'coverage': G.coverage(nodes, edges),
        'semanticKinds': list(_G_SEMANTIC),
        'resolution': resolution,
    }


#: 语义边类型（图算法真正该算的那些）。跟 algo.graph 保持一致，
#: 在这里复制一份是为了 db 层不必 import 就能用（seed 筛选要用）。
_G_SEMANTIC = ('prereq', 'extends', 'compare', 'related')


def graph_recommend(user_id=None, limit=8, category=None, subject=None,
                    seeds=None, exclude_done=True, max_seeds=12):
    """**从「我不会的」往外推「该学什么」** —— 个性化 PageRank。

    seeds 的取法就是「level ≤ 1 或压根没记录」的卡：这批卡就是当前的
    薄弱点。PPR 以它们为 teleport 起点做随机游走，rank 高的就是
    「在这些薄弱点附近、而且自己也很重要」的卡。

    ★★ max_seeds 为什么必须有（这是实测踩出来的坑）：
       冷启动用户几乎**所有卡都是 level 0**，薄弱点集合 = 全库 415 张。
       teleport 向量铺在 415 个点上就等于均匀分布 = 全局 PageRank，
       rank 全被种子自己占满（实测 seedCount=415 时推荐列表整个是空的）。
       PPR 只在「少数几个明确的薄弱点」这个前提成立时才是个性化 ——
       它本质是「以少数几个已知点为重心做扩散」。
       所以这里把种子**按到期紧急度取前 max_seeds 个**：宁可推荐得糙一点，
       也不能给一个退化成全局 PR 的接口起个「个性化推荐」的名字。
       候选池 = 未掌握的卡（排除已掌握 level 3 + seed 自身）。

    ★ 为什么不用协同过滤 / 最短路：
       最短路只看连通性，会推一串一碰就忘的边角；协同过滤要历史交互
       量，冷启动阶段（每个用户 10 条以内）根本不可用。PPR 只需要
       「当前不会哪些」这一条信息，冷启动友好，而且能给出理由
       （它是从哪张不会的卡走过来的）。
    """
    import algo.graph as G
    nodes, edges = graph_raw(category=category, subject=subject)
    if not nodes:
        return {'ok': True, 'empty': True, 'items': [], 'seeds': []}

    prog = get_progress(user_id)
    label = {n['id']: n for n in nodes}
    cards = [n['id'] for n in nodes if n.get('type') == 'card']

    if seeds is None:
        # 「不会」的判定：没记录 或 level ≤ 1（模糊）。level 2 也算会。
        weak = [c for c in cards if (prog.get(c) or {}).get('level', 0) <= 1]
        # 排序键：到期日早的先当种子（越该复习的越像真正的薄弱点）。
        # nextAt 缺失排最后 —— 用 '9999-99-99' 而不是 ''，字符串比较下
        # 空串会排在任何日期前面，那正好是反的。
        weak.sort(key=lambda c: ((prog.get(c) or {}).get('nextAt') or '9999-99-99', c))
        seeds = weak[:max_seeds]
    else:
        seeds = [s for s in seeds if s in label][:max_seeds]

    if not seeds:
        # 没有薄弱点 → 没东西可推。返回一个说得清的状态，而不是空数组
        # 让前端猜「是没数据还是都学完了」。
        return {'ok': True, 'empty': False, 'allDone': True, 'items': [],
                'seeds': [], 'reason': '所有卡片都已掌握（level ≥ 2）'}

    rank = G.personalized_pagerank(nodes, edges, seeds=seeds)
    sem = G.adjacency(nodes, edges, kinds=_G_SEMANTIC)
    seedset = set(seeds)

    items = []
    for cid, score in sorted(rank.items(), key=lambda t: (-t[1], t[0])):
        if len(items) >= limit:
            break
        if label[cid].get('type') != 'card' or cid in seedset:
            continue
        if exclude_done and (prog.get(cid) or {}).get('level', 0) >= 3:
            continue
        items.append({
            'id': cid, 'label': label[cid].get('label'),
            'oneLine': label[cid].get('oneLine', ''),
            'score': round(score, 5), 'level': (prog.get(cid) or {}).get('level', 0),
            # 「为什么推荐它」：与哪张不会的卡语义相连。给不出理由的推荐
            # 用户不会信 —— 界面上要把这条路径显示出来。
            'because': _why_recommended(cid, seedset, sem),
        })
    return {'ok': True, 'empty': False, 'items': items,
            'seeds': [{'id': s, 'label': label[s].get('label')} for s in seeds[:10]],
            'seedCount': len(seeds), 'weakCount': len(
                [c for c in cards if (prog.get(c) or {}).get('level', 0) <= 1]),
            'algo': 'personalized-pagerank',
            'note': ('薄弱点超过 %d 张，PPR 已按到期紧急度取前 %d 个作种子'
                     % (max_seeds, len(seeds))) if len(seeds) >= max_seeds else ''}


def _why_recommended(cid, seedset, sem):
    """推荐理由：与哪张「不会的卡」有语义边。

    只取一跳邻居 —— 两跳的路径用户看不出因果，讲了等于没讲。
    """
    hit = []
    for nb, _w in sem.get(cid) or ():
        if nb in seedset:
            hit.append(nb)
    return sorted(hit)[:3]


def graph_path(src, dst, kinds=('prereq',), max_depth=12):
    """两张卡之间的最短学习路径（只走 prereq）。

    ★ 两个方向都要试：造卡数据里 `source → target` 的含义是 **target 是
      source 的前置**（agent/planner 同一约定），BFS 只顺这个方向走。
      用户按直觉「先点基础卡、再点进阶卡」点出来的正好是反方向 ——
      只搜一边的话，直觉顺序 100% 报「没有依赖链」，看着像功能坏了。
      所以反向再搜一次，任一方向命中即算找到。

    ★ 返回的 nodes **一律是学习顺序**（基础在前、进阶在后）：BFS 的原始
      路径永远是「进阶卡 → 它的前置」，必须整体反转。侧栏逐站列表和
      「下一步学」的箭头都按这个顺序读，前端不用再翻。

    数据现状：去重后 343 对 prereq（同一对卡上声明两次只算一条），链最长
    5 跳；多数两张卡之间确实没有依赖链，接口返回 found=false + reason ——
    那是数据现实，不是算法 bug。
    """
    import algo.graph as G
    nodes, edges = graph_raw()
    r = G.shortest_path(nodes, edges, src, dst, kinds=kinds, max_depth=max_depth)
    if not r.get('found'):
        alt = G.shortest_path(nodes, edges, dst, src, kinds=kinds, max_depth=max_depth)
        if alt.get('found'):
            r = alt
    label = {n['id']: n for n in nodes}
    if r.get('found'):
        r['nodes'] = list(reversed(r['nodes']))          # BFS 序 → 学习序
    r['nodes'] = [{'id': i, 'label': label[i].get('label'),
                   'type': label[i].get('type')} for i in r['nodes'] if i in label]
    r['reason'] = '' if r['found'] else '两卡之间没有前置依赖（已按两个方向找过）'
    return r


def graph_rank_of(ids, category=None, subject=None):
    """批量查一批卡在图里的排名（PageRank / Betweenness / 所属社区）。

    给卡片详情页用：想让「这张卡有多重要」在卡片页也看得见，
    就得能按 id 反查，而不是每次为一张卡重算全图。

    ★ 返回 (结果, 缺失id列表) 而不是只返回 dict：id 是主键，重复了也没
      意义。查不到的 id **不出现在结果里**（而不是塞一份全 0 的假数据），
      但缺失列表要一并返回 —— 静默少返回一项，调用方会以为
      「这张卡没有排名」，实际上很可能是 id 写错了。
    """
    import algo.graph as G
    nodes, edges = graph_raw(category=category, subject=subject)
    want = [i for i in (ids or []) if i]
    if not want or not nodes:
        return {}, list(want)
    pr = G.pagerank(nodes, edges)
    bt = G.betweenness(nodes, edges)
    order = {i: r for r, (i, _v) in enumerate(G.topn(pr, len(nodes)), start=1)}
    com = {}
    for ci, c in enumerate(G.louvain(nodes, edges)):
        for i in c:
            com[i] = ci
    total = len(nodes)
    out = {}
    for i in want:
        if i not in pr:
            continue
        out[i] = {
            'pagerank': round(pr[i], 6),
            # 名次从 1 开始；pct 是「超过全图多少比例的节点」，
            # 0-100 比「第几名」好读 —— 416 张卡里第 3 名和第 200 名
            # 用户看不出差别，但「前 8%」一眼就知道分量
            'pagerankRank': order.get(i),
            'pagerankPct': round(100.0 * (1 - (order.get(i, total)) / total), 1),
            'betweenness': round(bt.get(i, 0.0), 4),
            'community': com.get(i),
        }
    # 查不到的 id 单独返回（见 docstring）：调用方拼 URL 时把它算进
    # 过滤条件里，别把这几个也送去查
    return out, [i for i in want if i not in pr]


# ---------- 社区摘要（2026-11-15 加，GraphRAG 式「这是一块什么知识」） ----------
_SUMMARY_KEY = 'graph:summary:'
#: 喂给模型时每个社区最多列多少个成员名。太多token浪费，太少看不出主题。
_SUMMARY_MATERIAL = 22
#: 最多摘要多少个社区。graph_insight 的 communities 按规模降序，小的没意义。
_SUMMARY_MAX = 12

_SUMMARY_SYS = (
    '你是知识图谱分析助手。输入是知识图谱按社区检测（Louvain）分出的若干社区，'
    '每个社区列出它包含的知识点名称。请为每个社区写一段「这是一块什么知识」：\n'
    '- title：≤14 字，概括这块知识的主题（别照抄成员名，要往上抽象一层）；\n'
    '- desc：40-90 字，说明这块知识整体讲什么、适合什么阶段的人学、内部大概'
    '怎么分组。不逐个复述成员。\n'
    '只输出 JSON，不要 markdown 代码块、不要解释：\n'
    '{"items":[{"index":1,"title":"...","desc":"..."}]}，'
    'index 对应输入里的社区编号，必须每个社区都给。'
)


def community_summary(category=None, subject=None, refresh=False,
                      timeout=180):
    """AI 社区摘要：对每个 louvain 社区生成一段「这是一块什么知识」。

    这是 GraphRAG「社区检测 → 分层摘要」思路的轻量落地 —— 算法半边
    （louvain，resolution=4.0 的实测调参）在 graph_insight 里早就有了，
    这里只补摘要半边。产出两个用途：图谱页的社区图例不再只是冷冰冰的
    「社区 3（139 节点）」；将来也能当章节化八股文的章节骨架。

    缓存：结果存 algostore params（json/pg 双后端都支持，不用动 store 表
    契约），键里带图谱 mtime —— 卡片库一变摘要自动失效，不靠人记得清。

    AI 未启用 / 模型没吐对 JSON：返回 available:false + msg（200），
    这是「状态不是故障」，照 /api/llm/status 的口径。
    refresh=1 强制重新生成（要跑本地模型，几十秒量级，前端按钮触发）。
    """
    import llm as core_llm

    ins = graph_insight(category=category, subject=subject)
    if ins.get('empty'):
        return {'ok': True, 'available': False, 'items': [],
                'msg': '图谱为空，没有可摘要的社区'}
    comms = ins.get('communities') or []
    if not comms:
        return {'ok': True, 'available': False, 'items': [],
                'msg': '没有成规模的社区（全是零散节点）'}
    if core_llm.AI_OFF:
        return {'ok': True, 'available': False, 'items': [],
                'msg': 'AI 未启用（AI=off 或没装 Ollama），摘要不可用'}

    mtime = _graph_mtime()
    key = _SUMMARY_KEY + '%s|%s' % (category or '', subject or '')
    if not refresh:
        cached = algostore.get().params_get(key)
        if (isinstance(cached, dict) and cached.get('mtime') == mtime
                and cached.get('items')):
            return {'ok': True, 'available': True, 'cached': True,
                    'items': cached['items'], 'generatedAt': cached.get('at')}

    # 摘要素材：members 在 graph_insight 里已按「结构节点优先」排过序
    nodes, _edges = graph_raw(category=category, subject=subject)
    label = {n['id']: n.get('label') or n['id'] for n in nodes}
    lines = []
    for ci, c in enumerate(comms[:_SUMMARY_MAX]):
        names = [label.get(m, m) for m in (c.get('members') or [])[:_SUMMARY_MATERIAL]]
        lines.append('%d. [%d 个节点] %s' % (ci + 1, c.get('size'), '、'.join(names)))
    raw = core_llm._call(
        [{'role': 'system', 'content': _SUMMARY_SYS},
         {'role': 'user', 'content': '\n'.join(lines)}],
        model=None, timeout=timeout, temperature=0.2, max_tokens=1800)
    try:
        data = core_llm._clean_json(raw)
    except RuntimeError:
        return {'ok': False, 'available': False, 'items': [],
                'msg': '模型这次没吐对 JSON，点「重新生成」再试一次'}
    by_idx = {}
    for it in (data.get('items') or []):
        if isinstance(it, dict) and isinstance(it.get('index'), int):
            by_idx[it['index']] = it
    items = []
    for ci, c in enumerate(comms[:_SUMMARY_MAX]):
        hit = by_idx.get(ci + 1) or {}
        items.append({
            'index': ci + 1,
            'size': c.get('size'),
            'members': c.get('members'),
            # 对位收货：模型漏了哪个社区就给空串，前端按空串显「未生成」
            'title': str(hit.get('title') or '')[:24],
            'desc': str(hit.get('desc') or '')[:160],
        })
    out = {'mtime': mtime, 'at': today_str(), 'items': items}
    algostore.get().params_put(key, out)
    return {'ok': True, 'available': True, 'cached': False,
            'items': items, 'generatedAt': out['at']}
