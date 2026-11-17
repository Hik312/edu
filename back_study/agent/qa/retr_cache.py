# -*- coding: utf-8 -*-
"""检索结果缓存（Redis）。

## 为什么缓存这个（实测依据）

`retrieval.retrieve('布隆过滤器')` **实测 378 ms**，而一次问答要跑 1~2 次检索。
拆开看，耗时几乎全在 `db.all_cards()`（**59 ms**，MySQL 路径每次都查 416 行，
文件路径有 `_src_cache`、MySQL 没有）加上向量/关键词打分上。

而检索结果对「同一个查询 + 同一份卡片库」是**确定的** —— 换句话说，
缓存一次能省掉一整轮几十到几百毫秒的重复计算。

## 失效：靠**卡片库指纹**，靠它就要算指纹

这里有个和别处不同的取舍：指纹必须是**全库**的（检索底料就是全库 416 张卡）。
全库指纹 = 所有 (id + 会影响检索的字段) 的hash。
- 改一张卡的正文 → 指纹变 → 重新检索（正确）
- 只是 `level` 变了（用户标了「会」）→ **不影响检索底料**，所以**不进指纹**，
  这样标了卡不会导致整库检索缓存全废（否则每标一张卡就重检索一次，很浪费）。

★ 指纹的成本要算清楚：算一次全库指纹本身要读一遍all_cards()（59ms），
所以**先查一次短 TTL 的"库指纹"缓存**，命中就直接用；
库指纹本身的失效靠短 TTL（默认 30s）而不是每次重算——
「改了卡 30 秒内检索缓存还没失效」这个代价远小于每次都算指纹的收益。
"""
import hashlib
import json
import os
import sys

import cache as core_cache

PREFIX = 'study:retr:'
FINGER_PREFIX = 'study:retrfp:'
DEFAULT_TTL = 1800# 30 分钟：检索结果是"当下可用"的，不需要很久
FINGER_TTL = 30          # 全库指纹缓存30 秒 —— 见上面注释里的取舍
MAX_QUERY = 100

# 只有这些字段参与**检索**指纹：title/oneLine/keywords/tags/mechanism/analogy/subject。
# ★ level/nextAt 不进 —— 那是掌握度/排期，不影响"能不能检索到这张卡"。
_FP_FIELDS = ('title', 'oneLine', 'keywords', 'tags', 'mechanism', 'analogy', 'subject')


def _enabled():
    return os.environ.get('RETR_CACHE', '1').strip().lower() not in ('0', 'false', 'off')


def _all_cards():
    import db
    return db.all_cards()


def library_fingerprint():
    """全库检索指纹。

    带30 秒的短缓存：算指纹本身要读一遍全库（59ms），每次检索都重算
    就把缓存省下的时间又还回去了。所以指纹本身也缓存一会儿，
    用 TTL 换计算 —— 改了卡最多30 秒后才反映到检索缓存，可接受。
    """
    if not _enabled():
        return 'nocache'
    key = FINGER_PREFIX + 'v1'
    try:
        hit = core_cache.get().get(key)
    except Exception:
        hit = None
    if hit:
        return hit
    parts = []
    try:
        for c in _all_cards():
            if not c or not c.get('id'):
                continue
            seg = []
            for f in _FP_FIELDS:
                v = c.get(f)
                if isinstance(v, (list, tuple)):
                    v = ','.join(str(x) for x in v)
                seg.append('%s=%s' % (f, '' if v is None else str(v)[:200]))
            parts.append(c['id'] + '|' + '|'.join(seg))
    except Exception:
        return 'err'
    raw = '\n'.join(sorted(parts)).encode('utf-8')
    fp = hashlib.md5(raw).hexdigest()[:12]
    try:
        core_cache.get().set(key, fp, ttl=FINGER_TTL)
    except Exception:
        pass
    return fp


def _key(query, k):
    raw = '%s|%s|%s' % (query.strip().lower(), k, library_fingerprint())
    return '%s%s' % (PREFIX, hashlib.md5(raw.encode('utf-8')).hexdigest()[:16])


def get(query, k):
    """读缓存。命中返回 list（可能是空列表 —— 空结果也要缓存，
    否则「这张库里确实没有」的查询会每次都跑一遍全量检索）。"""
    if not _enabled():
        return None
    if not query or len(query) > MAX_QUERY:
        return None
    try:
        raw = core_cache.get().get(_key(query, k))
    except Exception:
        return None
    if raw is None:
        return None
    try:
        obj = json.loads(raw)
    except Exception:
        return None
    if not isinstance(obj, list):
        return None
    # 反序列化回 SearchHit 需要的最小形状
    out = []
    for it in obj:
        if isinstance(it, dict) and it.get('id'):
            out.append(it)
    return out


def put(query, k, hits):
    """写缓存。hits 是 SearchHit 列表。

    ★ ★ SearchHit 只有 __slots__ = (id, card, score)，
      **它没有 .get() 方法**（不是 dict！）。之前这里写成 h.get('id')
      会抛 AttributeError，而外面包着 `except: pass` → **缓存从来没写进去过，
      却完全静默**，表现为"加了缓存但一点没变快"。
      这类"读缓存/写缓存"的代码不要吞异常，至少要把异常打出来。
      所以：显式用属性访问，且**任何字段取不到都给默认值，不抛**。
    """
    if not _enabled():
        return
    if not query or len(query) > MAX_QUERY:
        return
    try:
        slim = []
        for h in (hits or []):
            cid = getattr(h, 'id', None)
            if not cid:
                continue
            card = getattr(h, 'card', None) or {}
            slim.append({'id': cid,
                         'score': float(getattr(h, 'score', 0) or 0),
                         'title': (card.get('title') or '')[:120]})
        core_cache.get().set(_key(query, k), json.dumps(slim, ensure_ascii=False),
                             ttl=DEFAULT_TTL)
    except Exception as e:
        print('[retr_cache] 写缓存失败（不影响检索）: %s' % e, file=sys.stderr)


def stats():
    c = core_cache.get()
    return {'enabled': _enabled(), 'backend': type(c).__name__,
            'degraded': core_cache.degraded(),
            'ttl_minutes': DEFAULT_TTL // 60, 'fingerprint_ttl_s': FINGER_TTL}