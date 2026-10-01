# -*- coding: utf-8 -*-
"""算法对拍台 —— 用同一串评级喂给每个算法，看它们各自排出什么复习计划。

为什么要有这个：换算法的理由不能是「FSRS 听起来更先进」，得是
「在同样的学习过程下，它安排的复习次数更少 / 间隔增长更稳」。这个脚本
就是产出那句话的地方。

三种跑法：

    python back_study/algo/demo.py --list
    python back_study/algo/demo.py                     # 默认序列，365 天
    python back_study/algo/demo.py --seq 3,3,2,1,3 --days 180
    python back_study/algo/demo.py --algo fsrs --retention 0.85

评级：1=不会 2=模糊 3=会。序列循环使用（复习次数多于序列长度时从头再来）。
"""

import os
import sys

_BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACK_DIR not in sys.path:
    sys.path.insert(0, _BACK_DIR)

import algo                                                # noqa: E402
from algo import diff_days                                 # noqa: E402

#: 默认序列：一段比较真实的学习过程 —— 连着会、偶尔模糊、一次彻底忘掉。
DEFAULT_SEQ = (3, 3, 3, 2, 3, 3, 1, 3, 3, 3)

_LV_TEXT = {1: '不会', 2: '模糊', 3: '会'}
_START = '2026-01-01'


def simulate(alg, seq, horizon=365, retention=None):
    """按算法自己排的到期日一路复习下去，直到超出 horizon 天。

    「今天」是**真实推进**的（每次跳到算法给的 nextAt），所以 FSRS 算
    可提取性 R 用的天数是真的，不是编的。
    """
    # ★ 不要直接改 alg.retention：那会绕开 FSRS.__init__ 里的
    # `_clamp(retention, 0.7, 0.99)`，而且 algo.get('fsrs') 返回的是**共享单例**，
    # 改完不还原 —— 同一进程里后续任何 algo.get('fsrs') 都继承这个坏值。
    # 实测：--retention 0 → interval_for 里 0.0 ** (1/-0.5) → ZeroDivisionError；
    # --retention 1.2 → k<0 → 所有间隔都算成 1 天，打出「200 次复习」的假象。
    # 正确做法是给自己造一个实例（构造器会 clamp）。
    if retention is not None and hasattr(alg, 'retention'):
        if type(alg).__name__ == 'FSRS':
            from .fsrs import FSRS
            alg = FSRS(retention)
        else:
            alg.retention = retention

    day = _START
    prev = None
    steps = []
    for i in range(200):                             # 保险丝，别把终端刷爆
        level = seq[i % len(seq)]
        rec = alg.schedule(prev, level, today=day)
        steps.append({
            'n': i + 1,
            'level': level,
            'interval': rec['interval'],
            'ef': rec['ef'],
            'reps': rec['reps'],
            'at': day,
            'nextAt': rec['nextAt'],
        })
        if diff_days(_START, rec['nextAt']) > horizon:
            break
        day = rec['nextAt']
        prev = rec
    # 把最终用的算法实例一起返回：指定 retention 时换过实例，
    # 调用方拿原来的 `a` 打出的标签就不准了（会以为跑的是默认保持率）。
    return steps, alg


def show(title, steps, horizon):
    print('\n=== %s ===' % title)
    print('   #   评级   间隔(天)  ef/D    复习日        下次到期')
    for s in steps[:12]:
        print('   %-3d %-5s %-8s %-7s %-12s %s'
              % (s['n'], _LV_TEXT.get(s['level'], s['level']),
                 s['interval'], s['ef'], s['at'], s['nextAt']))
    if len(steps) > 12:
        print('   ... 还有 %d 次' % (len(steps) - 12))
    last = steps[-1]
    print('   —— %d 天内复习 %d 次，末次间隔 %d 天，末次 ef/D=%s'
          % (horizon, len(steps), last['interval'], last['ef']))


def main():
    args = sys.argv[1:]

    if '--list' in args:
        for d in algo.describe_all():
            print('%-6s %s' % (d['name'], d['label']))
            print('       数据需求：%s' % d['needs'])
        return

    def opt(flag, cast, default):
        if flag in args:
            return cast(args[args.index(flag) + 1])
        return default

    horizon = opt('--days', int, 365)
    retention = opt('--retention', float, None)
    seq = (tuple(int(x) for x in args[args.index('--seq') + 1].split(','))
           if '--seq' in args else DEFAULT_SEQ)
    picked = [args[args.index('--algo') + 1]] if '--algo' in args else algo.names()

    print('评级序列：%s（循环）      模拟跨度：%d 天'
          % (' '.join(_LV_TEXT.get(x, str(x)) for x in seq), horizon))
    if retention:
        print('目标保持率：%s' % retention)

    summary = []
    for n in picked:
        a = algo.get(n)
        steps, used = simulate(a, seq, horizon, retention)
        show('%s（%s）' % (used.label, n), steps, horizon)
        summary.append((n, len(steps), steps[-1]['interval']))

    if len(summary) > 1:
        print('\n=== 对比 ===')
        base_cnt = summary[0][1]
        for n, cnt, iv in summary:
            if n == summary[0][0]:
                tag = '基准'
            elif cnt < base_cnt:
                tag = '少 %d 次' % (base_cnt - cnt)
            elif cnt > base_cnt:
                tag = '多 %d 次' % (cnt - base_cnt)
            else:
                tag = '一样多'
            print('   %-6s 复习 %d 次（%s），末次间隔 %d 天' % (n, cnt, tag, iv))
        print('\n   注意：复习次数少 ≠ 更好。FSRS 排得少是因为它**认为**你记得住；'
              '\n   真正的判据是实际回忆成功率 —— 那需要事件流，现在还没有。')


if __name__ == '__main__':
    main()
