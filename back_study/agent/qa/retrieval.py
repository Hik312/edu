# -*- coding: utf-8 -*-
"""混合检索层：向量为主 + 关键词兜底，分数融合。可插拔。

设计（和用户定的方向一致：混合检索）
- KeywordRetriever：复用 tools._score 的子串打分，零依赖，永远可用。
- VectorRetriever：本地 Ollama embedding（默认 nomic-embed-text）把卡片与查询向量化，
  余弦相似度排序。索引落 data/store/embeddings.json，按卡片集合指纹懒构建、变化即重建。
  embedding 模型没装时**自动退化**为空结果，不报错。
- HybridRetriever：两者都跑，分数各自归一化后加权融合（向量 VECTOR_WEIGHT / 关键词 1-）。
- get_retriever()：按 config.RETRIEVER 出实例；hybrid 在向量不可用时会自动只用关键词。

可插拔的意义：v1 用关键词先把端到端问答跑通；哪天想上语义检索，
`ollama pull nomic-embed-text` 后设 AGENT_RETRIEVER=vector（或不改，hybrid 自动启用向量）。
"""
import json
import os
import time

from .. import config as C
import db
from . import rerank as rerank_module   # 重排（cross-encoder 精排）
from . import retr_cache      # 检索结果缓存（Redis；库指纹变了自动失效）
from . import tools


class SearchHit:
    """一次检索命中：卡片 id、卡片本体、融合后的得分。"""
    __slots__ = ('id', 'card', 'score')

    def __init__(self, cid, card, score):
        self.id = cid
        self.card = card
        self.score = score


def _all_cards():
    return db.all_cards()


def _card_text(c):
    """喂给 embedding 的文本：标题 + 一句话 + 关键词 + 原理拆解。"""
    parts = [c.get('title') or '', c.get('oneLine') or '',
             ' '.join(c.get('keywords') or []),
             ' '.join(c.get('mechanism') or [])]
    return ' '.join(p for p in parts if p)


# ---------- 卡片集合指纹 + 缓存 ----------
_FP_CACHE = {'fp': None, 'cards': None}
_CARD_CACHE = {'fp': None, 'map': None}
#: 'at' = 这次尝试的时间戳，用于失败后的冷却判断（见 _get_index）
_VEC_CACHE = {'fp': None, 'index': None, 'at': 0.0}

#: 重建失败后的冷却时间（秒）。模型没拉/没起时，不要每个请求都去试一次 ——
#: 一次 7~8 秒，QPS 一上来就是灾难。冷却期内直接返回 None（降级）。
_VEC_RETRY_COOLDOWN = 300

_EMBED_DIR = os.path.join(db.DATA_DIR, 'store')
_EMBED_FILE = os.path.join(_EMBED_DIR, 'embeddings.json')


def _fingerprint():
    """卡片集合指纹。带 v2 前缀标记。

    v2 = 2026-10-03 补上 nomic-embed-text 的文档/查询前缀（见 _embed 注释）。
    索引内容变了而 card id 集合没变，指纹必须变，否则磁盘上那份**没有前缀的
    旧索引**会被当成有效缓存继续加载 —— 改前缀这件事就白改了。
    以后再动 embedding 输入（比如换模型）也照样 +v3、+v4。
    """
    return 'v2|' + '|'.join(sorted(c.get('id', '') for c in _all_cards()))


def _card_map():
    fp = _fingerprint()
    if _CARD_CACHE['fp'] == fp and _CARD_CACHE['map'] is not None:
        return _CARD_CACHE['map']
    m = {c.get('id'): c for c in _all_cards()}
    _CARD_CACHE['fp'] = fp
    _CARD_CACHE['map'] = m
    return m


# ---------- embedding（懒 import llm，避免顶层耦合） ----------
#: nomic-embed-text 的**检索前缀**，文档侧和查询侧必须不同。
#:
#: 这个模型是拿 Matryoshka + 检索任务微调过的，官方用法硬性要求：
#: 建索引时每条文本前缀 `search_document: `，查询时前缀 `search_query: `。
#:
#: 为什么这在**本项目**里尤其要紧（症状→病因的完整链条）：
#: 原来 `_embed()` 两边共用、且**不加前缀**。查询被编码进了文档空间，
#: 余弦相似度整体失真 —— 表现就是所有卡的分数全挤在 0.67 附近、
#: top5 之间差不到 0.05，看起来"向量检索开了但没效果"。
#: 前缀一加，同样查询的分数会散开，检索才真的开始按语义排序。
#:
#: 代价是索引内容变了 → 指纹必须跟着变（见 _fingerprint 的 v2），
#: 否则旧的坏索引会被当成有效缓存继续用，改了等于没改。
DOC_PREFIX = 'search_document: '
QUERY_PREFIX = 'search_query: '


def _embed(texts, kind='document'):
    """调本地 Ollama /api/embed。模型不可用返回 None（调用方据此退化）。

    kind: 'document' 建索引用；'query' 检索用。**两边前缀不同**，别合并。
    """
    if not texts:
        return []
    pfx = QUERY_PREFIX if kind == 'query' else DOC_PREFIX
    try:
        import llm as _llm
        j = _llm._post(_llm.OLLAMA + '/api/embed',
                       {'model': C.EMBED_MODEL,
                        'input': [pfx + t for t in texts]}, None, timeout=60)
        embs = j.get('embeddings') if isinstance(j, dict) else None
        return embs or None
    except Exception:
        # 模型没拉 / Ollama 没起：退化信号，不是故障
        return None


def _cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _build_index():
    cards = _all_cards()
    texts = [_card_text(c) for c in cards]
    vecs = _embed(texts)
    if vecs is None:
        return None
    return {'fp': _fingerprint(), 'model': C.EMBED_MODEL,
            'vecs': {c.get('id'): v for c, v in zip(cards, vecs)}}


def _get_index():
    fp = _fingerprint()
    # 命中条件：指纹一致，且「要么有索引、要么失败还在冷却期内」。
    # 原守卫要求 index is not None，导致失败后每次都重试（一次 7~8 秒）。
    if _VEC_CACHE['fp'] == fp:
        if _VEC_CACHE['index'] is not None:
            return _VEC_CACHE['index']
        if time.time() - _VEC_CACHE['at'] < _VEC_RETRY_COOLDOWN:
            return None                     # 冷却中，别再白等一次重建
    index = None
    if os.path.exists(_EMBED_FILE):
        try:
            data = json.load(open(_EMBED_FILE, encoding='utf-8'))
            if data.get('fp') == fp and data.get('vecs'):
                index = data
        except Exception:
            index = None
    if index is None:
        index = _build_index()
        if index is not None:
            try:
                os.makedirs(_EMBED_DIR, exist_ok=True)
                json.dump(index, open(_EMBED_FILE, 'w', encoding='utf-8'))
            except Exception:
                pass
    # ★ 失败也缓存住（下面这行 2026-10-09 加的）。
    #   原来 `if _VEC_CACHE['index'] is not None` 的守卫让「重建失败 → None」
    #   变成**每次调用都重试**：一次 527 张的重建要 7~8 秒，
    #   而检索本身只要 300ms —— 也就是说模型没就绪时，
    #   每次搜索都在白等 10 秒（实测向量检索 10615ms、混合 4657ms）。
    #   现在失败结果也记进进程内缓存，让本次进程只试一次；
    #   下次重启还能再试（重启 = 新进程，_MODEL 缓存自然失效）。
    _VEC_CACHE['fp'] = fp
    _VEC_CACHE['index'] = index
    _VEC_CACHE['at'] = time.time()
    return index


# ---------- 三种检索器 ----------
class KeywordRetriever:
    def search(self, query, k=C.TOP_K):
        scored = [(tools._score(query, c), c) for c in _all_cards()]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda x: -x[0])
        return [SearchHit(c.get('id'), c, sc) for sc, c in scored[:k]]


class VectorRetriever:
    def search(self, query, k=C.TOP_K):
        index = _get_index()
        if not index:
            return []                         # 向量不可用：返回空，交给 hybrid 退化
        qv = _embed([query], 'query')      # 查询侧前缀，别用文档侧的
        if not qv:
            return []
        qv = qv[0]
        cmap = _card_map()
        hits = []
        for cid, v in index['vecs'].items():
            card = cmap.get(cid)
            if card is None:
                continue
            hits.append(SearchHit(cid, card, _cosine(qv, v)))
        hits.sort(key=lambda h: -h.score)
        return hits[:k]


def rrf_fuse(rank_lists, k=None):
    """RRF（Reciprocal Rank Fusion，倒数排名融合）。

    score(d) = Σ 1 / (k + rank_i(d))

    ★ 为什么用它，而不是「各自 min-max 归一化再加权」（原来的做法）：
      两路的**分数量纲根本不同** —— 余弦相似度挤在 0.6~0.9，
      关键词子串分是整数计数 0~20。min-max 归一化虽然把两边都拉到 [0,1]，
      但**谁的分更分散谁就主导融合结果**：关键词路经常是「唯一命中 = 满分、
      其余都是 0」，归一化后噪声被放大。
      实测查「RRF和Rerank」时，「Redis 有哪几种持久化方式」被排到第 1
      （只因为它字面命中了「Rerank」这个词）。
      RRF 只看**名次**不看分数，天然免疫量纲差异 —— 这是它被广泛使用的根本原因。

    ★ k=60 是惯例值（Cormack 等人的论文里就是 60）：
      它控制「头部排名的统治力」。k 越小，第1 名的权重越大、越容易被
      单路的错误判断带跑；k 越大，各路越民主。60 是在「单路强相关」
      和「单路误命中」之间实测比较稳的折中。

    rank_lists: [[SearchHit,...], ...]，**已按分数降序**。
    返回 {id: rrf_score}（不含命中的 id 就不会出现）。
    """
    k = k if k is not None else C.RRF_K
    fused = {}
    for hits in rank_lists:
        for rank, h in enumerate(hits):
            # rank 从 0 开始，名次1 排在第 0 位 —— 公式里用 rank+1
            fused[h.id] = fused.get(h.id, 0.0) + 1.0 / (k + rank + 1)
    return fused


class HybridRetriever:
    """两阶段检索：召回（关键词 + 向量，RRF 融合）→ 重排（cross-encoder）。"""

    def __init__(self):
        self.kw = KeywordRetriever()
        self.vec = VectorRetriever()

    def _recall(self, query, k):
        """只做召回+RRF 融合，不管重排。拆出来是为了让retrieve() 能复用。"""
        kw = self.kw.search(query, k * 3)
        vec = self.vec.search(query, k * 3)
        if not vec:
            return kw[:k], 'keyword-only'# 向量不可用：纯关键词
        if not kw:
            return vec[:k], 'vector-only'
        cmap = _card_map()
        fused = rrf_fuse([kw, vec])
        out = [SearchHit(i, cmap.get(i), s)
               for i, s in fused.items() if cmap.get(i)]
        out.sort(key=lambda h: -h.score)
        return out[:k], 'rrf'

    def search(self, query, k=C.TOP_K):
        hits, how = self._recall(query, k)
        if not C.RERANK_ENABLED:
            return hits
        return apply_rerank(query, hits, k)


# ---------- 重排接入 ----------
def apply_rerank(query, hits, k):
    """对召回结果做 cross-encoder 精排。**永远返回可用结果**，不会失败。

    ★ 这里不做模型可用性判断的短路，而是无条件调用 rerank.rerank()：
      它内部自己处理加载失败 / 超时 / 推理异常，一律返回 None。
      本函数只在拿到 None 时**原样返回召回顺序**。
      —— 「降级必须看得见」：降级信息通过 return_meta 带出去。
    """
    cand = hits[:C.RERANK_CANDIDATES]      # 只精排前 N，N 之外的不动
    tail = hits[C.RERANK_CANDIDATES:]
    scores = rerank_module.rerank(query, cand)
    if scores is None:
        return hits                       # 降级：保留召回顺序
    out = [SearchHit(h.id, h.card, scores.get(h.id, h.score)) for h in cand]
    out.sort(key=lambda h: -h.score)
    # 候选外的条目保持原相对顺序接在后面 —— 它们本来就没被重排过，
    # 拿召回分插进精排结果里会污染排序，所以只保留原序。
    return out + tail


# ★ 原 _norm()（min-max 归一化）已随 RRF 一起删掉 —— 留着会让人以为
#   融合还在用它，而它的量纲问题正是 RRF 要解决的那个坑。


# ---------- 工厂 + 便捷入口 ----------
def get_retriever():
    mode = (C.RETRIEVER or 'hybrid').lower()
    if mode == 'keyword':
        return KeywordRetriever()
    if mode == 'vector':
        return VectorRetriever()
    return HybridRetriever()


def last_meta():
    """最近一次检索的**元信息**（降级必须看得见）。

    为什么不放进 SearchHit：SearchHit 有 __slots__，加字段会影响
    所有构造点；而「这次检索有没有重排/走的是哪条路」属于**运行状态**，
    不是命中本身的属性，用模块级 dict 存最省事。

    键：
      stage    实际走到的阶段：rrf / rerank / keyword-only / vector-only
      reranked 是否真的重排了（False = 模型没就绪或超时）
      costMs   本次检索总耗时
      degrade  降级原因列表（空列表= 没降级）
    """
    return dict(_LAST_META)


_LAST_META = {'stage': 'none', 'reranked': False, 'costMs': 0,
              'degrade': []}


def retrieve(query, k=None):
    """对外统一入口：返回 [SearchHit]。节点和工具都走这。

    ★ 带检索缓存（retr_cache.py）：实测一次混合检索 **378ms**
      （几乎全耗在 all_cards() 的 59ms + 打分上），而问答一次要跑 1~2 次。
      命中时只回 id+score，卡片本体从全库现取 —— 卡片内容刚变就能反映出来，
      不受缓存影响（缓存的是"哪些卡命中了、排第几"，不是卡的内容）。
    """
    k = k or C.TOP_K
    t0 = time.time()
    cached = retr_cache.get(query, k)
    if cached:
        # 重建 SearchHit：卡片本体一定现取，缓存里不存它
        table = {}
        try:
            for c in _all_cards():
                if c and c.get('id'):
                    table[c['id']] = c
        except Exception:
            table = {}
        out = []
        for it in cached:
            card = table.get(it.get('id'))
            if card is None:
                continue      # 卡已经不在库里（被删了）→ 丢掉这条命中
            try:
                score = float(it.get('score') or 0)
            except (TypeError, ValueError):
                score = 0.0
            out.append(SearchHit(it['id'], card, score))
        if out:
            # ★ 命中缓存 = 整条检索（含重排）都省了，所以**不标降级**。
            #   缓存里存的是重排后的 id 顺序和分数，重排结果已在其中。
            _LAST_META.update(stage='cache', reranked=True,
                              costMs=round((time.time() - t0) * 1000),
                              degrade=[])
            return out
        # 缓存里的卡全没了（库被大改）→ 落到下面重算，顺便让旧条目自然过期

    hits, stage = _recall_with_meta(query, k)
    _LAST_META.update(stage=stage,
                      reranked=(stage == 'rerank'),
                      costMs=round((time.time() - t0) * 1000),
                      degrade=degrade_list())
    retr_cache.put(query, k, hits)   # 写失败只打日志，不影响检索
    return hits


def degrade_list():
    """当前降级原因。空 = 没有降级。"""
    d = []
    if not C.RERANK_ENABLED:
        d.append('重排已关闭(AGENT_RERANK=0)')
    elif not rerank_module.available():
        d.append('重排模型未就绪(%s)' % rerank_module.model_path())
    return d


def _recall_with_meta(query, k):
    """走检索器并记录「走到了哪一步 / 有没有降级」。返回 (hits, stage)。

    单独拆出来是因为 HybridRetriever.search() 只返回 hits，
    而阶段信息要么进 last_meta()、要么随结果一起返回 ——
    后者会污染 SearchHit 的接口，前者让 retrieve() 自己掌握更清晰。
    """
    r = get_retriever()
    if not isinstance(r, HybridRetriever):
        # keyword / vector 模式：没有两阶段，直接算
        hits = r.search(query, k)
        return hits, (r.__class__.__name__.replace('Retriever', '').lower()
                     or 'single')

    hits, stage = r._recall(query, k)
    degrade = []
    if not C.RERANK_ENABLED:
        degrade.append('重排已关闭(AGENT_RERANK=0)')
        return hits[:k], 'rrf'
    if not rerank_module.available():
        degrade.append('重排模型未就绪(%s)' % rerank_module.model_path())
        return hits[:k], stage
    scored = rerank_module.rerank(query, hits[:C.RERANK_CANDIDATES])
    if scored is None:
        degrade.append('重排失败或超时(保留召回顺序)')
        return hits[:k], stage
    cand = hits[:C.RERANK_CANDIDATES]
    out = [SearchHit(h.id, h.card, scored.get(h.id, h.score)) for h in cand]
    out.sort(key=lambda h: -h.score)
    return out[:k], 'rerank'
