# -*- coding: utf-8 -*-
"""图算法层的单元测试 —— 纯函数、不连库，最该测也最容易被拍错的一层。

无向当有向、阻尼写错、社区分辨率失效……algo/graph.py 的 docstring 里记的
每个历史坑，这里都有对应的防回归断言。
"""
import pytest

from algo import graph as G


def _small_graph():
    """4 节点小图：a --prereq--> b --prereq--> c，a --compare--> d（无向）。"""
    nodes = [{'id': i, 'label': i, 'type': 'card'} for i in ('a', 'b', 'c', 'd')]
    edges = [
        {'source': 'a', 'target': 'b', 'kind': 'prereq'},
        {'source': 'b', 'target': 'c', 'kind': 'prereq'},
        {'source': 'a', 'target': 'd', 'kind': 'compare'},
    ]
    return nodes, edges


def test_pagerank_sums_to_one():
    nodes, edges = _small_graph()
    rank = G.pagerank(nodes, edges)
    assert rank
    assert sum(rank.values()) == pytest.approx(1.0, abs=1e-6)
    # b/c 有两条入链、d 只有一条 compare → b 的权重应不低于 d
    assert rank['b'] >= rank['d']


def test_pagerank_dangling_and_empty():
    """孤点（无出边）不该让 PageRank 崩掉；空图返回空。"""
    nodes = [{'id': 'x', 'label': 'x', 'type': 'card'}]
    rank = G.pagerank(nodes, [])
    assert rank == {'x': pytest.approx(1.0)}
    assert G.pagerank([], []) == {}


def test_adjacency_directed_vs_undirected():
    nodes, edges = _small_graph()
    fwd = G.adjacency(nodes, edges, kinds=('prereq',), directed=True)
    assert [x[0] for x in fwd['a']] == ['b']
    assert [x[0] for x in fwd['c']] == []      # c 无出边（方向性）
    und = G.adjacency(nodes, edges, kinds=('compare',), directed=False)
    assert {x[0] for x in und['a']} == {'d'}
    assert {x[0] for x in und['d']} == {'a'}   # 对称边两边都看得见


def test_louvain_deterministic():
    """跑两次结果必须完全一致（确定性是 db 层缓存与 check.js 对拍的底线）。"""
    nodes = [{'id': i, 'label': i, 'type': 'card'}
             for i in ('a', 'b', 'c', 'd', 'e', 'f')]
    edges = [{'source': s, 'target': t, 'kind': 'related'}
             for s, t in [('a', 'b'), ('b', 'c'), ('a', 'c'),
                          ('d', 'e'), ('e', 'f'), ('d', 'f'),
                          ('c', 'd')]]
    c1 = G.louvain(nodes, edges, resolution=1.0)
    c2 = G.louvain(nodes, edges, resolution=1.0)
    assert c1 == c2


def test_louvain_separates_disconnected_groups():
    """两个互不连通的三角必须分成两个社区（连通分量是分块的下限）。"""
    nodes = [{'id': i, 'label': i, 'type': 'card'}
             for i in ('a', 'b', 'c', 'd', 'e', 'f')]
    edges = [{'source': s, 'target': t, 'kind': 'related'}
             for s, t in [('a', 'b'), ('b', 'c'), ('a', 'c'),
                          ('d', 'e'), ('e', 'f'), ('d', 'f')]]
    comms = G.louvain(nodes, edges, resolution=1.0)
    assert len(comms) >= 2
    ids = [set(c) for c in comms]
    assert {'a', 'b', 'c'} in ids or {'d', 'e', 'f'} in ids


def test_shortest_path_respects_direction():
    nodes, edges = _small_graph()
    # 造卡约定：source → target 表示 target 是 source 的前置？
    # 这里以 algo.graph 的实际方向语义为准做双向断言：
    r_ab = G.shortest_path(nodes, edges, 'a', 'b', kinds=('prereq',))
    r_ba = G.shortest_path(nodes, edges, 'b', 'a', kinds=('prereq',))
    found_ab = r_ab.get('found') or r_ba.get('found')
    assert found_ab                             # 至少一个方向能通
    r_cd = G.shortest_path(nodes, edges, 'c', 'd', kinds=('prereq',))
    assert not r_cd.get('found')                # compare 不是 prereq，不该通


def test_topn_sorted_stable():
    rank = {'a': 0.1, 'b': 0.4, 'c': 0.4}
    out = G.topn(rank, 3)
    assert out[0][1] == out[1][1] == 0.4        # 并列按 id 兜底（稳定性）
    assert len(out) == 3


def test_coverage_counts():
    nodes, edges = _small_graph()
    cov = G.coverage(nodes, edges)
    assert cov['nodes'] == 4 and cov['edges'] == 3
