# -*- coding: utf-8 -*-
"""图算法层 —— 中心性 / 社区发现 / 学习路径。

**为什么单独一层**：和间隔重复算法（sm2/fsrs/bkt）同规矩 —— 不 import core、
不连库、不起服务，拿 nodes+edges 两个 list 就能跑。这是能对拍、能单测、能
在 notebook 里调参的前提。图算法比间隔重复更容易拍错（无向当成有向、
阻尼系数手滑写成 0.7），不隔离出来根本没法验证。

**为什么不能把所有边一起算**：图里有两类性质完全不同的边 ——

  - `belong`（1268 条）：卡片挂在主题下、主题挂在科目下。这是**骨架**，
    是一棵树。它保证图连通，但也意味着中心性算法只要看到它就会全被
    吸到 subject / category 那几个节点上（一个 subject 能连着上百张卡，
    度数碾压一切），PageRank、Betweenness 全部失效。
  - `prereq` / `extends` / `compare`（846 条）：这才是知识之间的**语义关系**，
    是图算法真正该算的对象。

所以本模块的规矩是：**中心性和路径只用语义边，社区发现才用全部边**
（分模块本来就得靠骨架那棵树）。

**输入契约**：nodes 是 build_graph 那种 dict 列表，每项至少有 id / label / type；
edges 每项至少有 source / target / kind。都不许改 —— 改了就破坏与 db 层的约定。

```python
import algo.graph as G

r = G.analyze(nodes, edges, seeds=['card-x', 'card-y'])
r['pagerank']['card-a']        # 0.0312
r['communities']               # [[id, ...], [id, ...]]
r['path']['to']['nodes']       # 最短学习路径
```
"""

from __future__ import annotations

import math
from collections import defaultdict, deque

# ---------- 边的分类 ----------

#: 语义边：知识与知识之间的关系，中心性 / 路径只算这些。
SEMANTIC_KINDS = ('prereq', 'extends', 'compare', 'related')

#: 有向语义的边：`source` 必须先于 `target` 学。
#: `compare` / `related` 是对称的（Java 对比 Go，谁先都行），不设方向。
DIRECTED_KINDS = ('prereq', 'extends')

#: 骨架边：仅参与社区发现。
STRUCTURAL_KINDS = ('belong',)

#: 每个节点的语义度上限。真实图里有个别卡 related 写了十几条，
#: 度数碾压会让 PageRank 退化成「谁的 related 填得多谁就是权威」——
#: 这不是知识重要，是造数据时手勤。截断后影响力才有区分度。
MAX_SEM_DEGREE = 8


# ---------- 邻接表 ----------
def adjacency(nodes, edges, kinds=None, directed=False, cap=None):
    """建邻接表。

    nodes : list[dict]，只要 id
    edges : list[dict]，每项 {source, target, kind, weight?}
    kinds : 只收这些 kind；None = 全部边
    directed : 有向（只加 source→target）。prereq 必须传 True。
    cap : 每个节点的出边上限（先按权重降序，再按 id 兜底，保证结果稳定）

    返回 {nid: [(nid2, weight), ...]}。所有 nodes 都会出现（没有边也给空 list），
    这样 PageRank 里「出度为 0」和「节点不存在」不会混为一谈。
    """
    ids = [n['id'] for n in nodes]
    idset = set(ids)
    adj = {i: [] for i in ids}
    for e in edges:
        k = e.get('kind')
        if kinds is not None and k not in kinds:
            continue
        a, b = e.get('source'), e.get('target')
        if a not in idset or b not in idset or a == b:
            continue
        w = float(e.get('weight') or 1.0)
        adj[a].append((b, w))
        if not directed:
            adj[b].append((a, w))
    if cap:
        # 权重降序；权重相同按目标 id 升序 —— 不加这个 tiebreak 的话，
        # dict 顺序一变结果就飘，测试会间歇性挂
        for a in adj:
            adj[a].sort(key=lambda t: (-t[1], t[0]))
            del adj[a][cap:]
    return adj


# ---------- PageRank ----------
def pagerank(nodes, edges, damping=0.85, iters=60, eps=1e-6,
             kinds=SEMANTIC_KINDS, cap=MAX_SEM_DEGREE):
    """无向语义图上的 PageRank（power iteration）。

    damping = 0.85 是 PageRank 原论文的值，改成别的数会让「权威卡」的
    定义悄悄变了 —— 别为了好看调它。

    ★ 和「度中心性」的区别，也是这一页存在的意义：
       degree 数的是「我连着几个知识点」，PageRank 数的是「连着我的知识点
       有多重要」。一张连接 10 张废卡的卡，degree 很高但 PageRank 很低；
       一张只被 3 张废卡指向、但那 3 张自己都很重要的卡，degree 很低
       PageRank 很高。造卡的 related 关系是有噪声的，PageRank 比度数抗噪。
    """
    ids = [n['id'] for n in nodes]
    n = len(ids)
    if n == 0:
        return {}
    adj = adjacency(nodes, edges, kinds=kinds, directed=False, cap=cap)
    # 无向图对称加权：邻居也按 w 累加回来，这样 A-B 的强弱是双向一致的
    sym = {}
    for a, lst in adj.items():
        for b, w in lst:
            sym.setdefault(a, []).append((b, w))
    for a, lst in sym.items():
        for b, w in list(lst):
            if a not in adj.get(b, ()):  # 反向没被 cap 留下就补上，保持对称
                sym[b].append((a, w))

    base = (1.0 - damping) / n
    rank = {i: 1.0 / n for i in ids}
    for _ in range(iters):
        nxt = {i: base for i in ids}
        dangling = 0.0
        for a in ids:
            out = sym.get(a) or []
            tot = sum(w for _, w in out)
            if tot <= 0:
                dangling += rank[a]
                continue
            ra = rank[a]
            for b, w in out:
                nxt[b] += damping * ra * (w / tot)
        if dangling:
            # 悬挂节点的 rank 不能凭空消失（否则总概率会掉下去，收敛到错误值），
            # 惯例是均摊回全图。这段漏了的话孤立卡会一路把总质量吞掉。
            share = damping * dangling / n
            for i in ids:
                nxt[i] += share
        delta = sum(abs(nxt[i] - rank[i]) for i in ids)
        rank = nxt
        if delta < eps:
            break
    return rank


def personalized_pagerank(nodes, edges, seeds, damping=0.85, iters=60,
                          eps=1e-6, kinds=SEMANTIC_KINDS, cap=MAX_SEM_DEGREE):
    """个性化 PageRank：以 seeds（通常是「我该复习的卡」）为起点做随机游走。

    **这是本页最实用的一个函数**。全局 PageRank 回答「这门学科里最权威的
    知识点是什么」，个性化回答「**从我不会的地方往外走，最该先补哪张**」。

    做法是把 teleport 向量换成均匀分布在 seeds 上，于是 rank 高的节点 =
    「在不会的那几张卡附近、且自己也重要」的卡。这不是最短路（最短路只
    看连通性，会推荐一串一碰就忘的边角），也不是协同过滤，是**从已知
    不会的知识点扩散出学习优先级**。

    seeds 不在图里就当没给（不抛）—— 卡片被删、进度里有孤儿 id 时，
    推荐列表还是该出得来，只是退化成全局 rank。
    """
    ids = [n['id'] for n in nodes]
    n = len(ids)
    if n == 0:
        return {}
    seed = [s for s in seeds if s in set(ids)]
    sym = adjacency(nodes, edges, kinds=kinds, directed=False, cap=cap)
    for a, lst in sym.items():
        for b, w in list(lst):
            if a not in sym.get(b, ()):
                sym[b].append((a, w))

    if not seed:
        # 没有种子就退化成全局 PageRank，而不是返回空 —— 调用方（接口、
        # 前端）不该因为「今天没到期卡」就看到一张空图
        return pagerank(nodes, edges, damping=damping, iters=iters,
                        eps=eps, kinds=kinds, cap=cap)

    seed_set = set(seed)
    tele = {i: (1.0 / len(seed) if i in seed_set else 0.0) for i in ids}
    rank = dict(tele)
    for _ in range(iters):
        nxt = dict(tele)
        for a in ids:
            out = sym.get(a) or []
            tot = sum(w for _, w in out)
            if tot <= 0:
                for i in ids:
                    nxt[i] += damping * rank[a] / n
                continue
            ra = rank[a]
            for b, w in out:
                nxt[b] += damping * ra * (w / tot)
        delta = sum(abs(nxt[i] - rank[i]) for i in ids)
        rank = nxt
        if delta < eps:
            break
    return rank


# ---------- Betweenness ----------
def betweenness(nodes, edges, kinds=('prereq',), cap=None):
    """介数中心性（Brandes 算法，只算最短路径条数不记长度）。

    **回答什么问题**：「哪张卡是必经之路？」

    用在知识图谱上特别直观：AQS、Java 锁、JVM GC 这类卡会横跨很多条
    学习路径 —— 走哪条路都要过它，它就是枢纽。而某张只有 related 指向
    别人的边角卡，介数是 0，因为它不在任何路径上。

    ★ 为什么不把它和 PageRank 混成一个「重要性」指标：
       两个算法问的问题不一样（PageRank = 被多少重要节点指向；
       Betweenness = 是否在别人的必经之路上），实际排序也不同。
       界面里分开给，别合成一个数 —— 合成之后就说不清在讲什么了。

    只跑有向图（prereq 是有向的：先学 A 才能学 B），无向会把「互为前置」
    的两张卡算成双倍，对称图上这属于制造数据不存在的关系。
    """
    ids = [n['id'] for n in nodes]
    idset = set(ids)
    adj = adjacency(nodes, edges, kinds=kinds, directed=True, cap=cap)
    score = {i: 0.0 for i in ids}

    for s in ids:
        # stack 里存 (节点, 最短路径条数)，sigma 是「从 s 到它有几条最短路」
        sigma = {s: 1.0}
        dist = {s: 0}
        pred = defaultdict(list)
        stack = []
        q = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            dv = dist[v]
            sv = sigma[v]
            for w, _ in adj.get(v) or ():
                if w not in dist:
                    dist[w] = dv + 1
                    sigma[w] = sv
                    q.append(w)
                elif dist[w] == dv + 1:
                    sigma[w] += sv
                    pred[w].append(v)
        # 回溯累积依赖：δ(v) = Σ δ(w)·σ(v)/σ(w)，δ(s) 不计
        if not pred and len(stack) == 1:
            continue
        delta = dict.fromkeys(dist, 0.0)
        while stack:
            w = stack.pop()
            sw = sigma[w]
            for v in pred.get(w, ()):
                delta[v] += (sigma[v] / sw) * (1.0 + delta[w])
            if w != s:
                score[w] += delta[w]
    # 无向语义边（prereq 之外）会重复计数一半，这里除回去
    n = len(ids) or 1
    undirected = all(k not in DIRECTED_KINDS for k in kinds) if kinds else False
    if undirected:
        score = {k: v / 2.0 for k, v in score.items()}
    _ = idset  # 保留引用，避免后续维护时误删这个校验
    return score


# ---------- Louvain 社区发现 ----------
def louvain(nodes, edges, resolution=1.0, kinds=None, cap=None):
    """Louvain 两阶段社区发现（贪心模块度优化 + 图聚合）。

    **这一层用全部边**（含 belong 骨架）：分模块这件事本来就得靠骨架那棵
    树，否则 416 张卡之间只有稀疏 related，会碎成一堆单点社区。

    resolution > 1 拆得更碎、< 1 合并得更狠（默认 1 = 标准模块度）。

    返回 list[list[id]]，按社区规模降序。

    ★ 为什么不用带随机数的版本：Louvain 经典实现靠随机遍历顺序打破
      对称，结果就不可复现 —— 同一份数据两次跑可能给出不同分块，测试
      会间歇性挂，界面上「社区」也会莫名其妙变一次。这里改成按 id 排序
      遍历，确定性换来的稳定性比那点随机性有用得多。416 节点不需要更快
      的实现，单线程实测 < 0.5s。
    """
    ids = [n['id'] for n in nodes]
    if not ids:
        return []
    adj = adjacency(nodes, edges, kinds=kinds, directed=False, cap=cap)

    # m2 = 图的总边权（无向图算两次）。这是模块度公式的分母，
    # 它为 0 只有一种情况：一条边都没有 → 每个节点自成一社区。
    m2 = sum(w for lst in adj.values() for _, w in lst)
    if m2 <= 0:
        return [[v] for v in ids]

    def one_level(cur_adj, cur_ids, cur_self):
        """一轮贪心移动。返回 list[list[cur_id]]。

        ★ 2m 必须**每轮重算**：聚合阶段社区内部的边变成了自环，
          自环按 2×self 计入总边权。第一阶段算出来的 m2 拿到第二阶段用，
          分母偏小 → 所有增益恒为负 → 一个都合并不了，表现为
          「社区数 == 节点数，每个节点自成一社区」。
        """
        m2l = (sum(w for lst in cur_adj.values() for _, w in lst)
               + 2.0 * sum(cur_self.values()))
        if m2l <= 0:
            return [[v] for v in cur_ids]
        comm = {v: v for v in cur_ids}
        # k[v] = 节点度数（自环算两次，与 2m 口径一致）
        k = {v: sum(w for _, w in cur_adj.get(v) or ()) + 2.0 * cur_self.get(v, 0.0)
             for v in cur_ids}
        moved = True
        rounds = 0
        while moved and rounds < 20:
            moved = False
            rounds += 1
            for v in cur_ids:
                kv = k[v]
                sv = cur_self.get(v, 0.0)
                # 先摘出来算基准：留在原地（单点社区）的增益是 0。
                # ★ 这个基准不能省，也不能把第一个候选无条件设成最优：
                #   「best_gain is None 就直接采纳第一个候选」等价于
                #   「按字典序选社区」—— gain 算得再对也不影响结果，
                #   症状是 resolution 从 1.0 调到 4.0 分块结果一模一样。
                old = comm[v]
                k[old] -= sv
                best, best_gain = old, 0.0
                neigh = defaultdict(float)
                for w, weight in cur_adj.get(v) or ():
                    if w != v:
                        neigh[comm[w]] += weight
                for c, k_in in sorted(neigh.items()):
                    # 移入 c 的增益 = k_in − k_v·Σ_tot(c)·γ/2m
                    #   k_in  : v→c 的边权和
                    #   Σ_tot : c 的度数和（含即将并入的 k_in）
                    #   γ (resolution)：>1 拆得更碎，<1 合并更狠
                    gain = k_in - kv * (k[c] + k_in) * resolution / m2l
                    if gain > best_gain + 1e-12:
                        best, best_gain = c, gain
                comm[v] = best
                if best != old:
                    k[best] += sv
                    moved = True
                else:
                    k[old] += sv
        groups = defaultdict(list)
        for v in cur_ids:
            groups[comm[v]].append(v)
        return [sorted(g) for g in groups.values()]

    self_w = {v: 0.0 for v in ids}
    groups = one_level(adj, ids, self_w)

    # --- 第二阶段：社区聚成超点，在超点图上继续跑 ---
    # ★ members 记着「超点 → 原始 id 列表」的映射。不记的话最后拿到的是
    #   0..N-1 的编号，前端拿这个 id 去 /api/cards 查会全部 404。
    members = [{v} for v in ids]
    cur_adj, cur_ids, cur_self = adj, ids, self_w
    for _ in range(8):
        if len(cur_ids) <= 1 or len(groups) == len(cur_ids):
            break
        # cur_ids 是 id 字符串、members 是按位置排的列表 —— 两者要靠
        # 这个位置映射对上。直接 members[v] 会拿字符串去索引列表，
        # 报「list indices must be integers」。
        pos = {v: i for i, v in enumerate(cur_ids)}
        idx = {}
        for i, c in enumerate(groups):
            for v in c:
                idx[v] = i
        nxt = list(range(len(groups)))
        nxt_adj = {i: [] for i in nxt}
        nxt_self = {i: 0.0 for i in nxt}
        for a, lst in cur_adj.items():
            for b, w in lst:
                ca, cb = idx[a], idx[b]
                if ca == cb:
                    nxt_self[ca] += w / 2.0   # 无向边遍历两次，各记一半
                else:
                    nxt_adj[ca].append((cb, w))
        nxt_members = []
        for c in groups:
            s = set()
            for v in c:
                s |= members[pos[v]]
            nxt_members.append(s)
        cur_ids, cur_adj, cur_self = nxt, nxt_adj, nxt_self
        members = nxt_members
        groups = one_level(cur_adj, cur_ids, cur_self)

    communities = [sorted(m) for m in members]
    communities.sort(key=lambda c: (-len(c), c[0]))
    return communities


# ---------- 最短学习路径 ----------
def shortest_path(nodes, edges, src, dst, kinds=('prereq',), max_depth=12,
                   directed=True):
    """从 src 到 dst 的最短依赖链（BFS，层数即深度）。

    只走 prereq（和可选的 extends），因为「该按什么顺序学」这个问题
    只能沿依赖边回答；沿 related 找路径会得到 A→B→C 但 A 和 C 毫无
    关系的假链条。

    返回 {'found': bool, 'nodes': [...], 'edges': [...], 'hops': int}
    —— 找不到时 nodes/edges 是空 list 而不是 None，前端少一个判空分支。
    """
    ids = {n['id']: n for n in nodes}
    if src not in ids or dst not in ids:
        return {'found': False, 'nodes': [], 'edges': [], 'hops': 0}
    eidx = defaultdict(list)
    for e in edges:
        if e.get('kind') in kinds:
            eidx[e['source']].append((e['target'], e))
            if not directed:
                eidx[e['target']].append((e['source'], e))
    if src == dst:
        return {'found': True, 'nodes': [src], 'edges': [], 'hops': 0}

    prev = {src: None}
    queue = deque([(src, 0)])
    while queue:
        cur, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for nxt, e in sorted(eidx.get(cur, []), key=lambda t: t[0]):
            if nxt in prev:
                continue
            prev[nxt] = (cur, e)
            if nxt == dst:
                path, hops = [dst], 1
                node = dst
                while node != src:
                    node = prev[node][0]
                    path.append(node)
                    hops += 1
                path.reverse()
                es = [prev[p][1] for p in path[1:]]
                return {'found': True, 'nodes': path, 'edges': es, 'hops': hops - 1}
            queue.append((nxt, depth + 1))
    return {'found': False, 'nodes': [], 'edges': [], 'hops': 0}


# ---------- k-core ----------
def kcore(nodes, edges, k=2, kinds=SEMANTIC_KINDS):
    """k-core 分解：返回 {'core': {id: 层数}, 'peripheral': [id, ...]}。

    k-core = 「反复删掉语义度 < k 的节点，删完剩下的那批」。
    k=2 时剩下的是图里嵌得比较稳的骨架（互相关联至少 2 次），
    被删掉的是**边缘知识**：只和一张卡 related 一下、谁也没指向它。

    实际用途是**体检**：peripheral 里就是该补 related 的那些卡。
    比人工翻 416 张卡找「哪张是孤岛」快得多，而且能定期跑成报表。
    """
    adj = adjacency(nodes, edges, kinds=kinds, directed=False)
    deg = {i: len([1 for _ in v]) for i, v in adj.items()}
    core = dict(deg)
    removed = []
    alive = set(deg)
    while True:
        low = sorted(i for i in alive if core[i] < k)
        if not low:
            break
        for v in low:
            alive.discard(v)
            removed.append(v)
            for w, _ in adj.get(v) or ():
                if w in alive:
                    core[w] -= 1
    return {
        'core': {i: (len(adj[i]) if i in alive else 0) for i in deg},
        'peripheral': sorted(removed, key=lambda i: (core[i], i)),
    }


# ---------- 一把跑 ----------
def analyze(nodes, edges, seeds=None, kinds=SEMANTIC_KINDS, k=2):
    """一次算完所有指标。接口直接调它，前端拿一个 payload 渲染。"""
    pr = personalized_pagerank(nodes, edges, seeds=seeds, kinds=kinds) if seeds \
        else pagerank(nodes, edges, kinds=kinds)
    return {
        'pagerank': pr,
        'pagerankTop': topn(pr, 12),
        'betweenness': betweenness(nodes, edges),
        'betweennessTop': topn(betweenness(nodes, edges), 12),
        'communities': louvain(nodes, edges),
        'kcore': kcore(nodes, edges, k=k, kinds=kinds),
        'semanticKinds': list(kinds),
        'seeded': bool(seeds),
    }


def topn(d, n=10):
    """取前 n 个 (id, 值)，值降序、同值按 id 升序 —— 保证可复现。"""
    return [[i, round(v, 5)] for i, v in sorted(d.items(), key=lambda t: (-t[1], t[0]))[:n]]


def coverage(nodes, edges):
    """图的体检报告：规模、连通性、孤岛率。

    界面顶部那行「N 张卡 / M 条关系 / 覆盖率 X%」就是它。
    连通分量数 > 1 意味着有些卡连不到别的知识点 —— 那不是 bug，
    是数据没建完，这个数字要能在界面上看见，不能靠猜。
    """
    ids = [n['id'] for n in nodes]
    adj = adjacency(nodes, edges, kinds=None, directed=False)
    seen, comps = set(), 0
    biggest = 0
    for s in ids:
        if s in seen:
            continue
        comps += 1
        q, size = deque([s]), 0
        seen.add(s)
        while q:
            v = q.popleft()
            size += 1
            for w, _ in adj.get(v) or ():
                if w not in seen:
                    seen.add(w)
                    q.append(w)
        biggest = max(biggest, size)
    cards = [n['id'] for n in nodes if n.get('type') == 'card']
    sem = adjacency(nodes, edges, kinds=SEMANTIC_KINDS)
    orphan = [i for i in cards if len(sem.get(i) or ()) <= 1]
    return {
        'nodes': len(nodes),
        'cards': len(cards),
        'edges': len(edges),
        'components': comps,
        'largest': biggest,
        'coverage': round(biggest / len(nodes), 4) if nodes else 0.0,
        'orphanCards': len(orphan),
        'orphanRate': round(len(orphan) / len(cards), 4) if cards else 0.0,
        'orphanList': orphan[:20],
    }


__all__ = ['SEMANTIC_KINDS', 'DIRECTED_KINDS', 'STRUCTURAL_KINDS',
           'adjacency', 'pagerank', 'personalized_pagerank', 'betweenness',
           'louvain', 'shortest_path', 'kcore', 'analyze', 'topn', 'coverage']

_ = math  # 保留：调试时用来手算收敛步数
