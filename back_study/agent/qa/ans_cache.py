# -*- coding: utf-8 -*-
"""问答答案缓存（Redis）。

## 为什么缓存这个

实测本地qwen3:8b 回答一句要 **40~103 秒**（flow 流式实测：
首帧0.1s、出字跨度 103.67s）。同一个问题重复问一遍，
答案在「同样的卡片底料 + 同样的问题」下是确定的 —— 重跑一遍极不划算。

## ★ 为什么这个缓存比校验缓存风险高得多

校验缓存错了，最坏是**少提一条建议**；
答案缓存错了，是**直接给用户一段错答案**。所以这里的失效条件更严：

1. **卡片集指纹进key**：检索底料变了（改了卡、导入了新卡）→ 指纹变 → 重答。
   这一点至关重要 —— 卡片库是活的，不把指纹算进去就会"改了卡还答旧的"。
2. **提问 + 模式 + 联网开关** 都进key：不同问题、不同模式答案不同。
3. **多轮历史不进key**：历史不同答案就不同，所以只要 hist 非空就**不缓存**。
   这是个刻意的保守选择 —— 多轮追问命中缓存会给出跑偏的答案，代价太大。
4. TTL 只有 1 天，且可用环境变量 `QA_CACHE=0` 全局关掉。

## 降级

只用 `core/cache.get()`（Redis 挂了自动回退进程内 cache、读失败返回 None），
所以 Redis 不可用时功能照常，只是每次重算。
"""
import hashlib
import json
import os

import cache as core_cache

PREFIX = 'study:qa:'
DEFAULT_TTL = 24 * 3600        # 1 天
MAX_ANSWER = 8000              # 超长答案不缓存：占内存不划算


def _enabled():
    return os.environ.get('QA_CACHE', '1').strip().lower() not in ('0', 'false', 'off')


def card_fingerprint(ids):
    """卡片集指纹：把这次引用到的卡片的**实际内容**算成一个短hash。

    ★ 必须用**内容**而不是光有 id：只把 id 拼进 key 的话，
    改了一张卡的标题但 id 不变 → 指纹不变 → 缓存一直返回旧答案，
    而用户明明已经改过卡了。这比慢严重得多。
    所以现查 db 取每个 id 的正文字段再算 hash。
    取不到（卡被删）就把 'missing' 算进去 —— 至少能产生变化。
    """
    if not ids:
        return 'none'
    import db
    # 只取「模型实际看到的那些字段」：底料就是这些拼出来的。
    # 别的字段（比如 tags）变了不影响答案，不该让缓存失效。
    fields = ('id', 'title', 'oneLine', 'mechanism', 'why', 'analogy', 'scene')
    # ★ **一次全量取，再查表** —— 不要在循环里对每个 id 调 db.all_cards()。
    #   实测 all_cards() 约 59ms（MySQL 路径每次都查 416 行，没有缓存），
    #   3 张卡就是 3×59=177ms 的纯浪费，而且指纹算得越慢越容易成为瓶颈。
    try:
        table = {}
        for c in db.all_cards():
            if c and c.get('id'):
                table[c['id']] = c
    except Exception:
        table = {}
    parts = []
    for cid in sorted(set(ids)):
        card = table.get(cid)
        if not card:
            parts.append('%s=missing' % cid)
            continue
        seg = []
        for f in fields:
            v = card.get(f)
            if isinstance(v, (list, tuple)):
                v = ','.join(str(x) for x in v)
            seg.append('%s=%s' % (f, '' if v is None else str(v)[:400]))
        parts.append('|'.join(seg))
    raw = '||'.join(parts).encode('utf-8')
    return hashlib.md5(raw).hexdigest()[:10]


def _key(question, mode, web, ids, user_id=None):
    # ★ key 必须带 user_id：答案可能含有**个人数据**（due_rows 工具会把
    #   当前用户的复习队列写进回答），不带用户维度就是 A 缓存的答案
    #   原样吐给 B（问同一句话就命中）。匿名调用统一归 'anon' 共享。
    raw = '|'.join([question.strip(), mode, '1' if web else '0',
                    str(user_id) if user_id is not None else 'anon',
                    card_fingerprint(ids)])
    return '%s%s' % (PREFIX, hashlib.md5(raw.encode('utf-8')).hexdigest()[:16])


def get(question, mode, web, ids, user_id=None):
    """读缓存。命中返回 {'answer','sources'}，未命中/出错返回 None。"""
    if not _enabled():
        return None
    try:
        raw = core_cache.get().get(_key(question, mode, web, ids, user_id))
    except Exception:
        return None
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except Exception:
        return None
    if not isinstance(obj, dict) or not obj.get('answer'):
        return None
    return obj


def put(question, mode, web, ids, answer, sources, user_id=None):
    """写缓存。写失败不影响主流程。"""
    if not _enabled():
        return
    if not answer or len(answer) > MAX_ANSWER:
        return
    try:
        core_cache.get().set(
            _key(question, mode, web, ids, user_id),
            json.dumps({'answer': answer, 'sources': sources or []},
                       ensure_ascii=False),
            ttl=DEFAULT_TTL)
    except Exception:
        pass


def stats():
    c = core_cache.get()
    return {'enabled': _enabled(), 'backend': type(c).__name__,
            'degraded': core_cache.degraded(), 'ttl_hours': DEFAULT_TTL // 3600}