# -*- coding: utf-8 -*-
"""一次性回归：证明搬到 algo/sm2.py 后的输出与 db.py 里的旧实现**逐位一致**。

旧实现是 2026-09-29 之前的原式子（下方 OLD_schedule），新实现是 algo/sm2.py。
用随机组合对拍，并且**按数据是否合法分组统计**：

- clean   ：字段类型都对（interval/reps 是 int，ef 是 int/float）→ 必须 0 差异
- 其余四组：脏数据（float/str/None/Decimal）→ 差异是**有意的行为改进**，
            本脚本要把它们摆出来让人看清改了什么、为什么改，而不是糊过去。
"""
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

_BACK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _BACK not in sys.path:
    sys.path.insert(0, _BACK)

import algo                                                 # noqa: E402


def today_str(d=None):
    return (d or date.today()).strftime('%Y-%m-%d')


def add_days(s, n):
    y, m, d = [int(x) for x in s.split('-')]
    return today_str(date(y, m, d) + timedelta(days=n))


# ---- 旧实现：core/db.py 2026-09-29 之前的原样 ----
def OLD_schedule(prev, level):
    p = prev or {}
    ef = p.get('ef') if isinstance(p.get('ef'), (int, float)) else 2.5
    reps = p.get('reps') if isinstance(p.get('reps'), int) else 0
    iv = p.get('interval') if isinstance(p.get('interval'), int) else 0

    if level == 3:
        reps += 1
        if reps == 1:
            iv = 1
        elif reps == 2:
            iv = 3
        else:
            iv = max(1, round(iv * ef))
        ef = min(2.6, ef + 0.1)
    elif level == 2:
        iv = max(1, round(iv / 2)) if iv > 1 else 1
        ef = max(1.3, ef - 0.15)
    else:
        reps = 0
        iv = 1
        ef = max(1.3, ef - 0.2)

    return {
        'level': level, 'interval': iv, 'ef': round(ef, 2), 'reps': reps,
        'nextAt': add_days(today_str(), iv), 'updatedAt': today_str()
    }


def make_prev(kind, rng):
    if kind == 'none':
        return None
    if kind == 'empty':
        return {}
    if kind in ('clean', 'clean_edge'):
        hi = 3 if kind == 'clean_edge' else 400
        return {'level': rng.choice([0, 1, 2, 3]),
                'interval': rng.randint(0, hi),
                'ef': rng.choice([round(rng.uniform(1.3, 2.6), 2), 2.5, 1.3, 2.6]),
                'reps': rng.randint(0, 30),
                'nextAt': '2026-10-01', 'updatedAt': '2026-09-01'}
    if kind == 'float_int':          # interval/reps 存成了 float（老 JSON 常见）
        return {'interval': float(rng.randint(1, 60)),
                'ef': round(rng.uniform(1.3, 2.6), 2),
                'reps': float(rng.randint(0, 10))}
    if kind == 'str':                # 全字符串（手改过的 JSON）
        return {'interval': str(rng.randint(1, 60)), 'ef': '2.5',
                'reps': str(rng.randint(0, 10))}
    if kind == 'none_vals':          # 字段在但值是 None
        return {'interval': None, 'ef': None, 'reps': None}
    if kind == 'decimal':            # MySQL DECIMAL 列取回来的 ef
        return {'interval': rng.randint(1, 60),
                'ef': Decimal(str(round(rng.uniform(1.3, 2.6), 2))),
                'reps': rng.randint(0, 10)}
    raise ValueError(kind)


KINDS = ['none', 'empty', 'clean', 'clean_edge', 'float_int', 'str',
         'none_vals', 'decimal']


def main():
    rng = random.Random(20260929)
    sm2 = algo.get('sm2')
    stat = {k: {'n': 0, 'bad': 0, 'sample': None} for k in KINDS}

    for _ in range(40000):
        kind = rng.choice(KINDS)
        prev = make_prev(kind, rng)
        level = rng.choice([1, 2, 3])
        old = OLD_schedule(prev, level)
        new = sm2.schedule(prev, level)
        diff = [k for k in old if old[k] != new.get(k)]
        stat[kind]['n'] += 1
        if diff:
            stat[kind]['bad'] += 1
            if stat[kind]['sample'] is None:
                stat[kind]['sample'] = (prev, level, {k: (old[k], new.get(k))
                                                      for k in diff})

    print('%-12s %8s %8s %s' % ('数据形态', '总例数', '不一致', '结论'))
    print('-' * 72)
    for k in KINDS:
        s = stat[k]
        rate = (100.0 * s['bad'] / s['n']) if s['n'] else 0
        ok = '一致' if s['bad'] == 0 else ('%.0f%% 不同' % rate)
        print('%-12s %8d %8d %s' % (k, s['n'], s['bad'], ok))

    print('\n--- 有差异的组，样例（旧 → 新）---')
    for k in KINDS:
        s = stat[k]
        if s['sample']:
            prev, level, d = s['sample']
            print('\n[%s] prev=%r level=%s' % (k, prev, level))
            for f, (o, n) in d.items():
                print('    %-9s %r → %r' % (f, o, n))

    bad_clean = stat['clean']['bad'] + stat['clean_edge']['bad'] \
        + stat['none']['bad'] + stat['empty']['bad']
    print('\n===== 判据 =====')
    print('合法数据（clean/clean_edge/none/empty）不一致数：%d —— %s'
          % (bad_clean, '通过' if bad_clean == 0 else '**失败，搬错了**'))
    return 0 if bad_clean == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
