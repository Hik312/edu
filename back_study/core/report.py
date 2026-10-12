# -*- coding: utf-8 -*-
"""个人中心：错题本 / 复盘 / 遗忘曲线 / 学习时长的**聚合层**。

**这一层为什么不碰 HTTP**：三个报表的算法（按周月聚合、按日期算掌握度曲线、
按科目汇总时长）都是纯数据变换，跟 FastAPI 无关。放这里可以：
① 不起服务直接 `python -c "import core.report"` 就能跑；
② 单元测试不用 mock 请求；
③ 路由层只做「取参数 → 调这里 → 返响应」，和项目其它路由一个规矩。

**数据来源全部复用已有的三张表/流，一件新表都不加**：
- `algostore.events_of()`  —— 复习事件流（level / at），错题本与遗忘曲线的地基
- `algostore.sessions_of()` —— 学习时长会话（前端埋点），专注度报表的地基
- `db.get_progress()` / `db.mastery_map()` —— 当前掌握度与排期

**★ 贯穿全文件的一条口径决策**：「不会」= level 1、「模糊」= level 2、「会」= level 3。
错题本只收 1/2（把「会」也算进错题本等于没筛选）；遗忘曲线画全部三档。
"""

from collections import defaultdict

# 档位常量（与 algo/base.py 一致；这里不 import algo 是为了保持 report 零依赖可独立跑）
LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD = 1, 2, 3

#: 一条学习会话记多久算「有效」。低于 2 秒的多半是误触/切页面，
#: 全记进去会把「专注度」稀释成噪声，所以直接不计。
MIN_SESSION_SECONDS = 2

#: 单张卡单次超过这个秒数就按它截断。防「页面开着忘了关」贡献 8 小时。
MAX_SESSION_SECONDS = 1800


def _day(ts):
    """把各种时间戳归一成 'YYYY-MM-DD'。

    入参可能是 `2026-10-09`（事件流的 `at`）、也可能是 ISO 带 T/Z 的
    `ts`（会话埋点的时间戳）。这里只取日期部分——
    报表按天聚合，不关心几点几分。
    """
    s = str(ts or '').strip()
    if not s:
        return ''
    return s[:10] if len(s) >= 10 else s


def _month_of(day):
    return day[:7] if len(day) >= 7 else ''


def _week_range(day, weeks_back=0):
    """返回 day 所在周的 (周一, 周日) 字符串。

    ★ 用**周一**作一周之始： learners 的「本周复盘」按自然周（周一到周日）
    才对得上日历，而 `date.weekday()` 的 0 就是周一。
    """
    import datetime
    try:
        d = datetime.date.fromisoformat(day)
    except (ValueError, TypeError):
        return day, day
    monday = d - datetime.timedelta(days=d.weekday() - weeks_back * 7)
    sunday = monday + datetime.timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


# ---------- 错题本 / 复盘 ----------

def mistake_book(events, cards_by_id=None, period='week', today=None):
    """从复习事件流汇总「不会 / 模糊」的卡，按次数降序。

    events: `db.events_of()` 的返回，每条含 card_id / level / at。
    cards_by_id: `{card_id: card}`，用来补 title/subject；没有也能跑（title 回退成 id）。
    period: 'week' | 'month' | 'all'，只影响 `reviewSessions` 的时间窗。

    **返回形状直接对齐前端 `ProfileCenterView.vue` 的期望**：
    { period, totalReviews, weakCards[], fuzzyCards[], reviewSessions[] }
    每张卡 `{ cardId, title, domain, subject, level, count, lastReviewed }`。
    """
    cards_by_id = cards_by_id or {}
    today = today or ''
    week_start, week_end = _week_range(today) if today else ('', '')

    weak = defaultdict(lambda: {'count': 0, 'last': '', 'level': LEVEL_AGAIN})
    fuzzy = defaultdict(lambda: {'count': 0, 'last': '', 'level': LEVEL_HARD})
    per_day = defaultdict(lambda: {'count': 0, 'weak': 0, 'fuzzy': 0})

    total = 0
    for ev in events or []:
        try:
            lvl = int(ev.get('level') or 0)
        except (TypeError, ValueError):
            continue
        cid = ev.get('card_id') or ev.get('cid')
        if not cid or lvl not in (LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD):
            continue
        day = _day(ev.get('at'))
        total += 1

        bucket = per_day[day]
        bucket['count'] += 1
        if lvl == LEVEL_AGAIN:
            bucket['weak'] += 1
        elif lvl == LEVEL_HARD:
            bucket['fuzzy'] += 1

        if lvl in (LEVEL_AGAIN, LEVEL_HARD):
            tgt = weak if lvl == LEVEL_AGAIN else fuzzy
            row = tgt[cid]
            row['count'] += 1
            row['level'] = lvl
            if day > row['last']:
                row['last'] = day

    def _rows(table, kind):
        out = []
        for cid, r in table.items():
            card = cards_by_id.get(cid) or {}
            out.append({
                'cardId': cid,
                'title': card.get('title') or cid,
                'domain': card.get('domain') or card.get('subject') or '',
                'subject': card.get('subject') or '',
                'level': r['level'],
                'count': r['count'],
                'lastReviewed': r['last'],
                'kind': kind,
            })
        # 次数降序；同次数按最近复习过的排前面，最后用 id 兜底保证稳定排序
        out.sort(key=lambda x: (-x['count'], _neg_date(x['lastReviewed']), x['cardId']))
        return out

    # 「最近」用负字符串技巧实现日期倒序（'2026-10-09' 这种 ISO 串可直接比大小）
    sessions = []
    for day in sorted(per_day):
        if period == 'week' and week_start and not (week_start <= day <= week_end):
            continue
        if period == 'month' and today and _month_of(day) != _month_of(today):
            continue
        b = per_day[day]
        sessions.append({'date': day, 'count': b['count'],
                         'weakCount': b['weak'], 'fuzzyCount': b['fuzzy']})

    return {
        'period': period,
        'totalReviews': total,
        'weakCards': _rows(weak, 'weak'),
        'fuzzyCards': _rows(fuzzy, 'fuzzy'),
        'reviewSessions': sessions,
    }


def _neg_date(s):
    """给 ISO 日期串做「倒序键」，让 sorted 能按日期从新到旧排。"""
    return ''.join(chr(255 - ord(ch)) if ord(ch) < 255 else ch for ch in (s or ''))


def review_summary(events, period='week', today=None):
    """周/月复盘的**汇总数字**（给概览卡片用，不含明细列表）。

    返回 { period, from, to, totalReviews, goodCount, weakCount, fuzzyCount,
    goodRate, activeDays, dailyCounts }。
    `goodRate` = 会/总，weakCount = 不会次数。
    """
    today = today or ''
    if period == 'month':
        start = (today[:8] + '01') if len(today) >= 8 else ''
        end = today
    elif period == 'week':
        start, end = _week_range(today) if today else ('', '')
    else:
        start, end = '', ''

    n = good = weak = fuzzy = 0
    days = set()
    daily = defaultdict(int)
    for ev in events or []:
        day = _day(ev.get('at'))
        if start and end and not (start <= day <= end):
            continue
        try:
            lvl = int(ev.get('level') or 0)
        except (TypeError, ValueError):
            continue
        if lvl not in (LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD):
            continue
        n += 1
        daily[day] += 1
        days.add(day)
        if lvl == LEVEL_GOOD:
            good += 1
        elif lvl == LEVEL_AGAIN:
            weak += 1
        else:
            fuzzy += 1
    return {
        'period': period,
        'from': start,
        'to': end,
        'totalReviews': n,
        'goodCount': good,
        'weakCount': weak,
        'fuzzyCount': fuzzy,
        'goodRate': (good / n) if n else 0.0,
        'activeDays': len(days),
        'dailyCounts': [{'date': d, 'count': daily[d]} for d in sorted(daily)],
    }


# ---------- 遗忘曲线 ----------

def forgetting_curve(events, progress=None, mastery=None,
                     card_id=None, days=30, today=None):
    """画「掌握度 / 排期」随时间的变化。

    card_id 为空 → 返回**整体聚合**（全库平均掌握度 + 三档分布，按天）。
    card_id 有值 → 返回**单卡**明细点 `{date, p, nextAt, level, reviews}`。

    ★ 为什么 p 不等于「预测的遗忘概率」而是「掌握度」：
    BKT 的 p 是「你已经掌握了这个知识点的概率」，它**不随时间自己衰减**——
    衰减是调度算法（FSRS/SM-2）通过不断把 nextAt 往后推来表达的。
    所以这里画的是「复习事件驱动的 p 变化」，每个点对应一次真实复习；
    没有复习的那天不会凭空产生点。**这是原理，别画成一条平滑衰减曲线骗人。**
    """
    progress = progress or {}
    mastery = mastery or {}
    cutoff = _shift_days(today, -int(days)) if today else ''

    if card_id:
        pts = []
        for ev in events or []:
            if card_id and ev.get('card_id') != card_id:
                continue
            day = _day(ev.get('at'))
            if cutoff and day < cutoff:
                continue
            lvl = int(ev.get('level') or 0)
            pts.append({'date': day, 'p': mastery.get(card_id, 0.0),
                        'nextAt': progress.get(card_id, {}).get('nextAt', ''),
                        'level': lvl, 'reviews': 1})
        # 按天合并成累计复习次数
        merged = defaultdict(lambda: {'p': 0.0, 'level': 0, 'reviews': 0, 'nextAt': ''})
        for pt in pts:
            m = merged[pt['date']]
            m['reviews'] += pt['reviews']
            m['p'] = pt['p']
            m['level'] = pt['level']
            m['nextAt'] = pt['nextAt']
        points = [{'date': d, 'p': merged[d]['p'], 'nextAt': merged[d]['nextAt'],
                   'level': merged[d]['level'], 'reviews': merged[d]['reviews']}
                  for d in sorted(merged)]
        return {'cardId': card_id, 'points': points}

    # 整体聚合：按天算平均掌握度 + 三档分布
    by_day = defaultdict(lambda: {'ps': [], 'weak': 0, 'mid': 0, 'strong': 0})
    for ev in events or []:
        day = _day(ev.get('at'))
        if cutoff and day < cutoff:
            continue
        cid = ev.get('card_id')
        try:
            lvl = int(ev.get('level') or 0)
        except (TypeError, ValueError):
            continue
        b = by_day[day]
        p = mastery.get(cid)
        if p is not None:
            b['ps'].append(float(p))
        if lvl == LEVEL_AGAIN:
            b['weak'] += 1
        elif lvl == LEVEL_HARD:
            b['mid'] += 1
        else:
            b['strong'] += 1
    agg = []
    for d in sorted(by_day):
        b = by_day[d]
        agg.append({'date': d,
                    'avgP': (sum(b['ps']) / len(b['ps'])) if b['ps'] else 0.0,
                    'weakCount': b['weak'], 'midCount': b['mid'],
                    'strongCount': b['strong']})
    return {'cardId': None, 'points': agg}


def _shift_days(day, delta):
    import datetime
    try:
        d = datetime.date.fromisoformat(day)
    except (ValueError, TypeError):
        return ''
    return (d + datetime.timedelta(days=delta)).isoformat()


# ---------- 学习时长 ----------

def study_time(sessions, cards_by_id=None, period='week', today=None):
    """学习时长聚合（专注度报表）。

    sessions: `algostore.sessions_of()` 的返回，每条含 card_id / duration_seconds / ts。
    返回 { period, totalMinutes, totalSessions, dailyMinutes[], heatmap[],
    byDomain[], byCard[] } —— 对齐前端期望。

    ★ 热力图（heatmap）用 'YYYY-MM-DD' → 当天分钟数，前端直接上色。
    ★ 脏数据（负时长/超长/无卡）一律在 `_clean_seconds` 里夹住，
      不让一条坏记录把「日均分钟」这种均值指标带偏。
    """
    cards_by_id = cards_by_id or {}
    today = today or ''
    if period == 'month':
        start = (today[:8] + '01') if len(today) >= 8 else ''
    elif period == 'week':
        start, _ = _week_range(today) if today else ('', '')
    elif period == 'year':
        start = today[:4] + '-01-01' if len(today) >= 4 else ''
    else:
        start = ''

    daily = defaultdict(lambda: {'minutes': 0.0, 'sessions': 0})
    by_dom = defaultdict(float)
    by_card = defaultdict(lambda: {'minutes': 0.0, 'reviews': 0})
    total_sec = 0.0
    kept = 0

    for s in sessions or []:
        sec = _clean_seconds(s.get('duration_seconds'))
        if sec <= 0:
            continue
        day = _day(s.get('ts'))
        if start and day and day < start:
            continue
        kept += 1
        total_sec += sec
        mins = round(sec / 60.0, 2)
        b = daily[day]
        b['minutes'] += mins
        b['sessions'] += 1
        cid = s.get('card_id') or ''
        card = cards_by_id.get(cid) or {}
        dom = card.get('domain') or card.get('subject') or '未分类'
        by_dom[dom] += mins
        cb = by_card[cid or '(unknown)']
        cb['minutes'] += mins
        cb['reviews'] += 1

    by_domain = [{'domain': k, 'minutes': round(v, 2)} for k, v in
                 sorted(by_dom.items(), key=lambda x: -x[1])]
    tot_min = round(total_sec / 60.0, 2)
    for row in by_domain:
        row['percentage'] = (round(row['minutes'] / tot_min * 100, 1)
                             if tot_min else 0.0)

    top_cards = []
    for cid, cb in sorted(by_card.items(), key=lambda x: -x[1]['minutes'])[:20]:
        card = cards_by_id.get(cid) or {}
        top_cards.append({'cardId': cid,
                          'title': card.get('title') or cid,
                          'minutes': round(cb['minutes'], 2),
                          'reviews': cb['reviews']})

    return {
        'period': period,
        'totalMinutes': tot_min,
        'totalSessions': kept,
        'dailyMinutes': [{'date': d, 'minutes': round(v['minutes'], 2),
                          'sessions': v['sessions']} for d, v in sorted(daily.items())],
        'heatmap': [{'date': d, 'value': round(v['minutes'], 2)}
                    for d, v in sorted(daily.items())],
        'byDomain': by_domain,
        'byCard': top_cards,
    }


def _clean_seconds(v):
    """把时长夹到 [0, MAX_SESSION_SECONDS]，非数返回 0。"""
    try:
        x = float(v or 0)
    except (TypeError, ValueError):
        return 0
    if x != x or x < 0:      # x != x 排掉 NaN
        return 0
    return min(x, float(MAX_SESSION_SECONDS))