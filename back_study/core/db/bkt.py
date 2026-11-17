# -*- coding: utf-8 -*-
"""数据层 · 拟合与掌握度域 —— BKT 四参数、FSRS 个性化 21 权重、回放、队列重排。

这是「BKT 定优先级、SM-2/FSRS 定时间」里 BKT 那一半的家；
FSRS 的个性化权重（fit-fsrs）也接在这里 —— 两者共用同一套
algostore params / cache 拿手架，拆两个文件反而要复制缓存失效的口径。
数据地基（事件流）在 progress.py，这里只做「事件 → 参数 → 概率」。
"""
from .base import algo, algostore, cache, diff_days
from .cards import all_cards
from .progress import EVENTS_ALL, _RANK, events_of


# ---------- BKT 掌握度 ----------
def _params_key(user_id=None):
    return 'bkt:params:' + (str(user_id) if user_id else 'global')


def bkt_params(user_id=None):
    """BKT 四参数。拟合过就用拟合值，没拟合过就用默认。

    缓存在 Redis：这个值只在你重新拟合时才变，但「算掌握度」每次都要读它，
    不缓存就是每次请求多打一次 PG/文件。
    """
    key = _params_key(user_id)
    c = cache.get()
    got = c.get(key)
    if got:
        return dict(got)
    params = algostore.get().params_get(key) or dict(algo.BKT_DEFAULT_PARAMS)
    c.set(key, params, ttl=3600)
    return dict(params)


def fit_bkt(user_id=None):
    """用自己的事件流拟合 BKT 四参数，拟合成功就存起来。

    返回 `(params, info)`。数据不够时**返回默认参数并说明原因**，不硬拟合——
    20 条记录拟合 4 个参数必然过拟合，那时候默认参数反而预测得更准。
    """
    evs = events_of(str(user_id), limit=EVENTS_ALL) if user_id else []
    by_kc = {}
    for e in evs:
        by_kc.setdefault(e.get('kc'), []).append(e)
    seqs = []
    for rows in by_kc.values():
        # 回放必须严格按时间序，同一天按写入序（id）—— BKT 是马尔可夫的，
        # 顺序错了算出来的 p 就是错的，而且错得很隐蔽。
        rows.sort(key=lambda r: (str(r.get('at') or ''), r.get('id') or 0))
        seqs.append(algo.bkt.from_events(rows))

    params, info = algo.bkt_fit(seqs)
    if info.get('fitted'):
        algostore.get().params_put(_params_key(user_id), params)
        cache.get().set(_params_key(user_id), params, ttl=3600)
        # ★ 参数一换，之前算出来的掌握度**全部作废**。
        #   漏掉这一步的症状非常阴：拟合完立刻查掌握度，拿到的是拟合之前
        #   用旧参数算的缓存值，于是「重新拟合了但结果没变」——
        #   你会以为是模型没生效，其实是缓存没失效。
        cache.get().clear('bkt:p:%s:' % user_id if user_id else 'bkt:p:')
        # mastery 表里那批同样是旧参数下的派生值，一起清掉，下次读时重算。
        algostore.get().mastery_clear(user_id)
    return params, info


def mastery_of(user_id, kc, refresh=False):
    """这个人在某个知识点上的掌握度 p ∈ [0,1]。

    为什么必须缓存：算一次要把这个人的整条事件流从头回放一遍，
    而到期队列、看板、AI 助手每次都要读。不缓存 = 每次都在扫表。

    refresh=True 表示「刚产生了新事件，缓存的那份已经过期」。
    """
    key = 'bkt:p:%s:%s' % (user_id, kc)
    c = cache.get()
    if not refresh:
        got = c.get(key)
        if got is not None:
            return float(got)

    p = algo.bkt.predict(
        algo.bkt.from_events(events_of(user_id, kc=kc, limit=EVENTS_ALL)),
        bkt_params(user_id))
    c.set(key, p, ttl=600)
    algostore.get().mastery_put(user_id, kc, p)
    return p


def mastery_all(user_id):
    """{kc: p}。只返回**已经算过**的；没算过的 kc 不在这里。

    要拿全量就先对每张卡调一次 `mastery_of()`，别在这里偷偷补算——
    那会让一个看起来是「读」的函数去做 N 次重放，慢得莫名其妙。
    """
    return algostore.get().mastery_all(user_id)


def mastery_map(user_id, cards=None):
    """{card_id: p} **覆盖全库**的掌握度（没练过的卡给先验 p_init）。

    和 mastery_all 的区别：那个只回「已经算过」的，这个把没练过的补成先验，
    这样队列排序 / 前端看板能拿到覆盖每张卡的 p，而不用对每张卡调一次
    mastery_of（那是 N 次全量事件回放，慢得莫名其妙 —— 这正是
    mastery_all 文档里警告过的事）。

    刻意**不**在这里触发重放：没练过的卡没有事件流，它的 p 本来就等于先验，
    重放也重放不出东西。真正算过的那些 p 直接读缓存 / mastery 表。
    """
    stored = mastery_all(user_id) or {}
    p0 = float(bkt_params(user_id).get('p_init', 0.25))
    out = {}
    for c in (all_cards() if cards is None else cards):
        cid = c.get('id') if isinstance(c, dict) else c
        if not cid:
            continue
        v = stored.get(cid)
        # mastery 表里只可能存 0~1 的 float；读到别的（非数 / NaN）就当没算过
        try:
            out[cid] = float(v) if v is not None else p0
        except (TypeError, ValueError):
            out[cid] = p0
    return out


def sort_by_mastery(items, user_id):
    """按 BKT 掌握度重排队列：**掌握度低的先学**。

    这是「BKT 定优先级、SM-2/FSRS 定时间」真正落地的那一半 —— 时间仍然
    由 schedule() 按主调度算法算，这里只改**顺序**，不动任何复习时间。

    为什么要挂在队列上而不是做成默认：现有排序（不会→模糊→未标记→会）
    是三档自评的粗糙近似，它答不了「模糊到底多模糊」。BKT 有连续的概率，
    能把「模糊」区分成 p=0.35 和 p=0.85 —— 前者该今天看，后者可以先放着。
    排序键取 (p 四舍五入三位, level 档位, 逾期) 三级：p 相同就退回老规则，
    保证**不会**因为共用一个 BKT 分数就把原有的确定性顺序弄乱。
    """
    pm = mastery_map(user_id, [x['card'] for x in items])
    for x in items:
        x['p'] = pm.get(x['card']['id'], 0.0)
    items.sort(key=lambda x: (round(x['p'], 3), _RANK.get(x['level'], 2),
                              -x['overdue'], x['card']['id']))
    return items


# ---------- FSRS 个性化权重（fit-fsrs，2026-11-15 加） ----------
# 拟合本体在 algo/fsrs_fit.py（纯标准库 SPSA+Adam）。这里只做两件事：
# 按人存取（algostore params + cache）和把事件流整理成拟合要的序列。

def _fsrs_key(user_id=None):
    return 'fsrs:params:' + (str(user_id) if user_id else 'global')


def fsrs_params(user_id=None):
    """当前用户的 FSRS 个性化权重。没拟合过返回 **None**（调度用默认权重）。

    缓存 1h，口径与 bkt_params 一致：这个值只在重新拟合时才变，
    但 set_level 每次都要读它。
    """
    key = _fsrs_key(user_id)
    c = cache.get()
    got = c.get(key)
    if got:
        return dict(got)
    params = algostore.get().params_get(key)
    if params:
        c.set(key, params, ttl=3600)
        return dict(params)
    return None


def fit_fsrs(user_id=None):
    """用自己的事件流拟合 FSRS-6 的 21 个权重，拟合成功就存起来。

    返回 `(weights, info)`。数据不够 / 全对一个答案时**返回默认权重并说明
    原因**（info.fitted=false）—— 30 条记录拟合 21 个参数必然过拟合，
    那时候默认权重反而预测得更准。口径与 fit_bkt 完全一致。

    ★ y 的口径与 BKT 不同（这不是笔误）：FSRS 的「记得」= level≥2
    （Again 才算忘），与 srs-benchmark 一致；BKT 的「答对」= level=3。
    两套口径答的是不同的问题 —— BKT 问「掌握没」，FSRS 问「记不记得」。
    """
    evs = events_of(str(user_id), limit=EVENTS_ALL) if user_id else []
    by_card = {}
    for e in evs:
        by_card.setdefault(e.get('card_id') or e.get('kc'), []).append(e)
    seqs = []
    for rows in by_card.values():
        # 回放必须严格按时间序，同一天按写入序（id）—— 与 fit_bkt 同一条纪律
        rows.sort(key=lambda r: (str(r.get('at') or ''), r.get('id') or 0))
        seq_i = []
        prev_at = None
        for r in rows:
            at = str(r.get('at') or '')
            g = int(r.get('level') or 1)
            y = 0.0 if g == 1 else 1.0
            t = -1 if prev_at is None else max(0, diff_days(prev_at, at))
            seq_i.append((t, g, y))
            prev_at = at
        seqs.append(seq_i)

    # ★ 显式 import 子模块：`import algo` 不会自动把 algo.fsrs_fit 挂到
    #   algo 命名空间上（除非别处 import 过它）——冒烟时 500 就是这么来的。
    #   纯脚本测试没炸是因为测试文件自己 import 了 algo.fsrs_fit。
    import algo.fsrs_fit as fsrs_fit
    weights, info = fsrs_fit.fit(seqs)
    if info.get('fitted'):
        algostore.get().params_put(_fsrs_key(user_id), weights)
        cache.get().set(_fsrs_key(user_id), weights, ttl=3600)
    return weights, info
