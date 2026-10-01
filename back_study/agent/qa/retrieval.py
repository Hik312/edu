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
import urllib.error

from .. import config as C
import db
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
_VEC_CACHE = {'fp': None, 'index': None}

_EMBED_DIR = os.path.join(db.DATA_DIR, 'store')
_EMBED_FILE = os.path.join(_EMBED_DIR, 'embeddings.json')


def _fingerprint():
    return '|'.join(sorted(c.get('id', '') for c in _all_cards()))


def _card_map():
    fp = _fingerprint()
    if _CARD_CACHE['fp'] == fp and _CARD_CACHE['map'] is not None:
        return _CARD_CACHE['map']
    m = {c.get('id'): c for c in _all_cards()}
    _CARD_CACHE['fp'] = fp
    _CARD_CACHE['map'] = m
    return m


# ---------- embedding（懒 import llm，避免顶层耦合） ----------
def _embed(texts):
    """调本地 Ollama /api/embed。模型不可用返回 None（调用方据此退化）。"""
    if not texts:
        return []
    try:
        import llm as _llm
        j = _llm._post(_llm.OLLAMA + '/api/embed',
                       {'model': C.EMBED_MODEL, 'input': texts}, None, timeout=60)
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
    if _VEC_CACHE['fp'] == fp and _VEC_CACHE['index'] is not None:
        return _VEC_CACHE['index']
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
    _VEC_CACHE['fp'] = fp
    _VEC_CACHE['index'] = index
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
        qv = _embed([query])
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


class HybridRetriever:
    def __init__(self):
        self.kw = KeywordRetriever()
        self.vec = VectorRetriever()

    def search(self, query, k=C.TOP_K):
        kw = self.kw.search(query, k * 3)
        vec = self.vec.search(query, k * 3)
        if not vec:
            return kw[:k]                    # 向量退化：纯关键词
        if not kw:
            return vec[:k]
        merged = {}
        for h in _norm(kw):
            merged[h.id] = (1 - C.VECTOR_WEIGHT) * h.score
        for h in _norm(vec):
            merged[h.id] = merged.get(h.id, 0.0) + C.VECTOR_WEIGHT * h.score
        cmap = _card_map()
        out = [SearchHit(i, cmap.get(i), s) for i, s in merged.items() if cmap.get(i)]
        out.sort(key=lambda h: -h.score)
        return out[:k]


def _norm(hits):
    """min-max 归一化到 [0,1]；全相等时给 1.0（避免除零）。"""
    if not hits:
        return []
    mx = max(h.score for h in hits)
    mn = min(h.score for h in hits)
    if mx - mn < 1e-9:
        for h in hits:
            h.score = 1.0
        return hits
    for h in hits:
        h.score = (h.score - mn) / (mx - mn)
    return hits


# ---------- 工厂 + 便捷入口 ----------
def get_retriever():
    mode = (C.RETRIEVER or 'hybrid').lower()
    if mode == 'keyword':
        return KeywordRetriever()
    if mode == 'vector':
        return VectorRetriever()
    return HybridRetriever()


def retrieve(query, k=None):
    """对外统一入口：返回 [SearchHit]。节点和工具都走这。"""
    return get_retriever().search(query, k or C.TOP_K)
