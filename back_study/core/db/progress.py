# -*- coding: utf-8 -*-
"""数据层 · 进度域 —— 复习进度、复习事件流、到期队列、全库统计。

★ user_id 是**必填**语义（可以显式传 None 落匿名桶，但业务端点不许不传）。
以前这些函数不收user_id，progress 主键也只有 card_id，于是两个用户
复习同一张卡互相覆盖 —— 现在签名强制它，漏传会在 TypeError 处当场炸，
而不是安静地吃掉别人的数据。
"""
import sys

from .base import (algostore, backend, diff_days, safe_next_at, schedule,
                   today_str)
from .builtin import builtin_stale
from .cards import all_cards
from .catalog import card_hit, direction_kws
from .docs import load_docs_brief, load_drafts
from .notes import load_notes
from .profiles import get_today_pick

# ---------- 进度 ----------
def get_progress(user_id=None):
    return backend().progress_all(user_id)


def set_level(cid, level, user_id=None):
    """标记掌握程度 + 追加一条复习事件。

    **为什么是双写**：`progress` 是**状态**（只留最新一条，覆盖式），
    而知识追踪模型（BKT/DKT/AKT）要的是**历史**。两者用途不同，不能互相替代 ——
    硬把历史塞进 progress 会把「查到期」这个最频繁的查询拖慢，
    而只留状态、不留历史，就永远训不出任何模型。

    `user_id` 现在同时是**事件归属**和**进度归属**（2026-10-03 起）——
    以前只写事件、进度是全局一份，所以探针账号的测试能把本人进度盖掉。
    """
    # ★ 个性化 FSRS 权重（fit-fsrs 的产物）：这个用户拟合过就用拟合值算，
    #   没拟合过 fsrs_params() 返回 None、走算法默认权重，行为不变。
    #   放在 progress_put 之前：算出的 rec 本身就该带个性化参数的印记。
    from .bkt import fsrs_params
    prog_map = get_progress(user_id)
    rec = schedule(prog_map.get(cid), level, w=fsrs_params(user_id))
    # ★ Load Balance（默认关，algo/loadbalance.py）：主调度算「隔几天」，
    #   这一步只调「具体排哪天」—— 当日过载时把 nextAt 推到 window 内
    #   最闲的一天，避免「今天 300 张、明天 0 张」。确定性实现（无随机源），
    #   不破坏 check.js 的双存储逐位对照。糖衣逻辑坏了绝不拖累核心写路径。
    try:
        import algo.loadbalance as loadbalance
        cfg = loadbalance.config()
        if cfg.get('enabled'):
            day_load = {}
            for oc, p in (prog_map or {}).items():
                if oc == cid:
                    continue                   # 这张卡的旧排期不算负载
                na = (p or {}).get('nextAt')
                if isinstance(na, str) and na:
                    day_load[na] = day_load.get(na, 0) + 1
            rec = loadbalance.balance_next_at(rec, day_load,
                                              window=cfg.get('window', 2),
                                              cap=cfg.get('cap'))
    except Exception as e:
        sys.stderr.write('[set_level] load balance 失败（用原始排期）：%s\n' % e)
    backend().progress_put(cid, rec, user_id)
    if user_id is not None:
        # ★ log_review 和 mastery_of 必须在**同一个 try** 里。
        # 它们打的是算法库（PG 或文件），和 progress 是两套存储；
        # 从前只包住了 mastery_of，而 log_review 裸在 try 外面 ——
        # pg 掉线 / 算法库文件只读时：进度已经改完、事件没写、请求返回 500。
        # 用户看到失败就会重试，而重试是从**已经推进过的**进度再算一次
        # （连续两次「会」本该 1→3 天，重试后直接跳到 3×ef≈8 天），
        # 状态和他的认知对不上，而且没有任何地方提示这件事。
        # 掌握度、事件流都是**派生数据**，丢了能重算；进度的正确性优先。
        try:
            log_review(user_id, cid, level)
            # 惰性 import：bkt.py 要从本模块取 events_of（回放事件流），
            # 这里又要在写事件后失效它的缓存 —— 反向引用只能在函数体内做。
            from .bkt import mastery_of
            mastery_of(user_id, cid, refresh=True)
        except Exception as e:
            sys.stderr.write('[set_level] 派生数据写入失败（进度已保存）：%s\n' % e)
    return rec


# ---------- 复习事件流（知识追踪的数据地基） ----------
#: 「模糊」算答对还是答错？BKT 只吃二值，这里定 **模糊 = 没答对**。
#: 理由：模糊说明没真正掌握，按错处理的结果是「多复习一次」，按对处理的结果是
#: 「可能永远不再见面」。两种错误里，前者的代价小得多。
CORRECT_LEVEL = 3


def log_review(user_id, card_id, level, kc=None, at=None, elapsed_ms=None):
    """追加一条复习事件。

    kc（知识点）默认就是 card_id —— 一期没做知识点粒度，一张卡一个知识点。
    等 `topicPath` 末级能用之后，这里换成真正的 kc，事件流的其它部分不用动。
    """
    return algostore.get().events_append({
        'user_id': str(user_id),
        'card_id': card_id,
        'kc': kc or card_id,
        'level': int(level),
        'correct': 1 if int(level) >= CORRECT_LEVEL else 0,
        'at': at or today_str(),
        'elapsed_ms': elapsed_ms,
    })


#: 回放类调用（BKT 拟合 / 掌握度）要**全量**事件，不是默认的最近 500 条。
#: 0 = 不截断（见 algostore.base.events_of 的 limit 契约）。
#: 为什么必须显式写：默认 500 会在卡库×复习次数上去之后悄悄截断，
#: 表现为「掌握度算到一半就不动了」，而且换后端症状还不一样。
EVENTS_ALL = 0


def events_of(user_id, kc=None, card_id=None, limit=500):
    """某人的复习事件，按时间正序（BKT 要按序回放）。

    `limit` 语义：取**最近** limit 条再正序返回；`limit=0`/`None` 表示全量。
    回放路径请显式传 `EVENTS_ALL`，别用默认值。
    """
    return algostore.get().events_of(user_id, kc=kc, card_id=card_id,
                                     limit=limit)


def events_count(user_id=None):
    return algostore.get().events_count(user_id)


def reset_progress(cid, user_id=None):
    backend().progress_del(cid, user_id)


def clear_progress(user_id=None):
    backend().progress_clear(user_id)


# ---------- 到期队列 ----------
#: 「从没复习过」的哨兵值。前端/接口把它翻译成 null，别让 999 漏出去。
OVERDUE_NEVER = 999
_RANK = {1: 0, 2: 1, 0: 2, 3: 3}


def due_list(domain=None, include_all=False, category=None, subject=None,
             user_id=None):
    """到期队列。未标记过 = 待学（永远在队列里）。

    排序：不会(1) → 模糊(2) → 未标记(0) → 会(3)，同档里逾期久的优先。
    为什么未标记排在「会」前面、却在「不会」后面：先补漏，再学新，
    最后才是巩固 —— 「不会」的卡再不看就白背了，「没背过」的卡明天开始也不迟。
    顺带修掉一个老 bug：原来写成 `x['level'] or 9`，未标记(0) 会被算成 9，
    整批「从没背过」的新卡被排到「已经会了」的后面，队列里翻半天见不到新内容。

    MySQL 后端会走 SQL 快路径（LEFT JOIN + 索引排序）；内容副本过期或
    用的是文件后端时，回落到下面这段等价的 Python 实现。两条路径的排序
    规则必须一致 —— check.js 的冒烟就是拿同一批断言同时打两边的。
    """
    st = backend()
    if st.holds_builtin and not builtin_stale():
        try:
            rows = st.due_cards(category=category, subject=subject,
                                domain=domain, include_all=include_all,
                                user_id=user_id)
        except Exception as e:
            print('[db] SQL 队列失败，回落 Python 路径: %s' % e, file=sys.stderr)
            rows = None
        if rows is not None:
            # 卡片内容不在 SQL 里带（2026-10-13 改）：一是 payload 全量拉回 +
            # 解析实测 59ms/次，二是 SQL 拿的是 cards 表的**原始卡**，吃不到
            # cards.override.json 的修正 —— 复习队列会显示修正前的旧内容
            # （实测标题/机制/关键词三处不一致，就是个 bug）。
            # 内容统一从合并缓存附上，SQL 只管「谁到期、什么顺序」。
            m = {c['id']: c for c in all_cards()}
            items = []
            for x in rows:
                card = m.get(x['cid'])
                if card is None:
                    continue                     # 理论到不了：两路同源
                items.append({'card': card, 'progress': x['progress'],
                              'level': x['level'],
                              'overdue': OVERDUE_NEVER if x['overdue'] is None
                              else x['overdue'],
                              'due': x['due']})
            return items

    today = today_str()
    prog = get_progress(user_id)
    items = []
    for c in all_cards(category=category, subject=subject):
        if domain and c.get('domain') != domain:
            continue
        p = prog.get(c['id'])
        if p is None:
            overdue = OVERDUE_NEVER
            due = True
        else:
            overdue = diff_days(safe_next_at(p, today), today)
            due = overdue >= 0
        if not include_all and not due:
            continue
        items.append({
            'card': c,
            'progress': p,
            # p['level'] 会在记录缺 level 键时 KeyError 500；
            # 同一份数据在 build_outline / role_plan 里都用 p.get('level')，
            # 口径要一致。
            'level': p.get('level', 0) if p else 0,
            'overdue': overdue,
            'due': due
        })
    items.sort(key=lambda x: (_RANK.get(x['level'], 2), -x['overdue'], x['card']['id']))
    return items


def review_queue(user_id=None, limit=None, domain=None, dirs=None,
                 include_all=False, pick=False, by='level', with_due_total=False):
    """web `/api/review/due` 与 mini `/api/mini/review/queue` 的**共用实现**。

    ★ 为什么要抽出来：这两段逻辑（pick 收窄 → dirs 筛选 → BKT 重排 → 截断
      → p 附加）原来在两个 router 里逐行重复，而 routers/__init__.py 明文
      规定「跨端共用逻辑放 db/deps」。重复的代价已经兑现过一次：
      两边的口径一旦各改各的，web 和小程序的队列顺序就会悄悄分叉。
      2026-11-15 拆包时收进来。

    参数（与两个 router 的查询参数一一对应）：
      user_id      归属人（必传语义）
      limit        截断数；None = 不截断（router 自己决定默认值：
                   web 50，mini 按每日目标 / all=1 时 100）
      domain       按领域过滤（传了就交给 due_list，走 SQL 快路径）
      dirs         学习方向 id 列表；**截断前筛**（顺序反了方向卡会被挤掉）
      include_all  =True 把没到期的也带上（「全部过一遍」用）
      pick         =True 只回今日自选清单里的卡（清单空回空队列）
      by           'level'（默认，老排序）| 'bkt'（掌握度低的优先）
      with_due_total =True 时顺带返回全库到期数（mini 的 dueTotal 口径：
                   不带 domain/dirs/include_all）。

    返回 `(items, due_total)`；不需要 due_total 时它为 None。

    ★ 顺序契约（改前先读）：dirs 筛、bkt 排都必须发生在**截断之前** ——
    先截断再排等于没排；先截断再筛会让方向卡被基础卡挤出队列。
    check.js 对两端队列顺序的断言兜底这条契约。
    """
    if pick:
        # 自选模式：清单就是队列。仍走 due_list(include_all=True) 拿全量再按 id
        # 收窄，这样 level/nextAt/overdue 字段口径和普通队列完全一致。
        ids = set(get_today_pick(user_id))
        items = [x for x in due_list(include_all=True, user_id=user_id)
                 if x['card']['id'] in ids]
    else:
        items = due_list(domain=domain or None, include_all=include_all,
                         user_id=user_id)

    due_total = None
    if with_due_total:
        # 「今天还有多少张没刷」的全库口径。没带 domain/pick/include_all 时
        # items 本身就是那份全量，别为它再查一遍（mini 首页实测省 59ms）。
        if not pick and not domain and not include_all:
            due_total = len(items)
        else:
            due_total = len(due_list(user_id=user_id))

    if dirs:
        # 方向筛必须在截断**之前**。传了查不到的方向 id → 当没筛，别返回空队列。
        kws = direction_kws(dirs)
        if kws:
            items = [x for x in items if card_hit(x['card'], kws)]

    if by == 'bkt':
        # BKT 优先级排序必须在截断**之前**：否则只对「已经取到的前 limit 张」
        # 排序，等于没排。默认 by=level 时这段不执行，返回顺序和以前逐字一致。
        from .bkt import sort_by_mastery
        sort_by_mastery(items, user_id)

    if limit is not None:
        items = items[:limit]
    return items, due_total


def stats(user_id=None, cards=None):
    """全库统计。

    `cards`：调用方手里已有 all_cards() 结果时传进来，省一次取数
    （小程序首页就是先取卡再要统计的）。不传就自己取，行为不变。
    ## dueToday 拆成两个数（2026-10-03）
    原来只有一个 `dueToday`，把两类完全不同的东西加在一起：
      · `dueLearned` —— **学过的卡排期到了**，该复习了。这是真·到期。
      · `fresh`     —— **从没背过的卡**。它们没有 nextAt、也永远不会
        「逾期」，但用户第一次打开应用看到的就是它们。
    两者加在一起动辄几百（400 张库里 398 张没标过）→ 界面显示「今日待复习 400」，
    而复习页实际只给 dailyTarget（默认 20）张。**用户点进去发现要学 20，
    出来的数字是 400，同一套系统两个矛盾口径。**
    拆开后语义各自干净：到期就是到期，新卡就是新卡。
    ⚠️ `dueToday` 保留且仍 = dueLearned + fresh（老调用方不改也能继续跑，
    check.js 的 `typeof dueToday === 'number'` 断言也照旧成立）。
    """
    prog = get_progress(user_id)
    cards = all_cards() if cards is None else cards
    today = today_str()
    s = {'total': len(cards), 'custom': 0, 'known': 0, 'fuzzy': 0,
         'weak': 0, 'unmarked': 0, 'dueToday': 0, 'dueLearned': 0, 'fresh': 0,
         'notes': len(load_notes(user_id)),
         # 只数个数别读全文：load_docs() 会把每篇的 chapters/doc_text 整个
         # 读回来（2026-10-13 实测是 stats 里仅次于卡片装载的开销）。
         # docs_brief 同表同数行、只取轻列（见 load_docs_brief 的注释）。
         'drafts': len(load_drafts()), 'docs': len(load_docs_brief()),
         'domains': {}, 'byCategory': {}, 'bySubject': {}}
    for c in cards:
        if c.get('_custom'):
            s['custom'] += 1
        d = c.get('domain', '未分类')
        s['domains'][d] = s['domains'].get(d, 0) + 1
        cat = c.get('category') or '未分类'
        sub = c.get('subject') or '未分类'
        s['byCategory'][cat] = s['byCategory'].get(cat, 0) + 1
        key = cat + '/' + sub
        s['bySubject'][key] = s['bySubject'].get(key, 0) + 1
        p = prog.get(c['id'])
        if p is None:
            s['unmarked'] += 1
            s['fresh'] += 1
            s['dueToday'] += 1
            continue
        lv = p.get('level')
        if lv == 3:
            s['known'] += 1
        elif lv == 2:
            s['fuzzy'] += 1
        else:
            s['weak'] += 1
        if diff_days(safe_next_at(p, today), today) >= 0:
            s['dueLearned'] += 1
            s['dueToday'] += 1
    return s


def mastery_report(user_id, cards=None):
    """一遍扫出「每张卡的 BKT 明细 + 分布汇总」，返回 `(rows, summary)`。

    网页端 `/api/mastery` 和小程序 `/api/mini/mastery` 共用这里：阈值
    （<0.4 薄弱、<0.8 一般、其余扎实）、没算过的算 `untouched`、均值按
    四舍五入后的 p 求 —— 这些口径两端各写一份，迟早算出两个「薄弱卡数」。

    `cards` 同 `stats()`：调用方手里已有 all_cards() 结果时传进来省一次取数。

    刻意不对每张卡跑事件回放（那是 N 次全量扫描，见 bkt.mastery_all 的警告）：
    只读 mastery 表 + 缓存，没算过的补先验 —— 所以 `computed=false` 的卡
    那个 p 是先验，不代表真的不会。
    """
    # 惰性 import：bkt.py 模块级要从本文件取事件流（events_of），
    # 这里反过来在模块级 import 会成环。
    from .bkt import mastery_all, mastery_map

    cards = all_cards() if cards is None else cards
    pm = mastery_map(user_id, cards)
    stored = mastery_all(user_id) or {}
    rows = []
    buckets = {'weak': 0, 'mid': 0, 'strong': 0, 'untouched': 0}
    for c in cards:
        p_raw = float(pm.get(c['id'], 0.25))
        p = round(p_raw, 4)
        computed = c['id'] in stored
        if not computed:
            buckets['untouched'] += 1
        elif p_raw < 0.4:
            buckets['weak'] += 1
        elif p_raw < 0.8:
            buckets['mid'] += 1
        else:
            buckets['strong'] += 1
        rows.append({'id': c['id'], 'title': c.get('title'),
                     'domain': c.get('domain'), 'p': p, 'computed': computed})
    avg = (sum(r['p'] for r in rows) / len(rows)) if rows else 0.0
    summary = {'total': len(rows), 'avgP': round(avg, 4),
               'events': events_count(user_id), 'computed': len(stored),
               **buckets}
    return rows, summary
