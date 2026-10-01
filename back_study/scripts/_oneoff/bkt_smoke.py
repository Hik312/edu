# -*- coding: utf-8 -*-
"""一次性验证：BKT 的四行公式对不对，以及 fit() 能不能从数据里反推出参数。

最关键的是第 3 组：**用已知参数造一批答题记录，再看 fit 能不能把它找回来**。
这一步不过的话，「在自己数据上拟合」就是自欺欺人 —— 拟合出的数看着挺像，
其实只是网格里碰巧最贴合噪声的那一组。
"""
import os
import random
import sys

_BACK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _BACK not in sys.path:
    sys.path.insert(0, _BACK)

import algo                                                # noqa: E402
from algo.bkt import (DEFAULT_PARAMS, fit, from_events,    # noqa: E402
                      log_likelihood, predict, replay, step)

ok = True


def check(name, cond, extra=''):
    global ok
    ok &= bool(cond)
    print('%-46s %s %s' % (name, 'OK' if cond else '**FAIL**', extra))


# ---- 1. 公式的定性行为 ----
print('---- 1. 定性行为 ----')
p = DEFAULT_PARAMS['p_init']
up = [p]
up.append(step(up[0], 1, DEFAULT_PARAMS))
up.append(step(up[1], 1, DEFAULT_PARAMS))
dn = step(p, 0, DEFAULT_PARAMS)
check('答对后掌握度上升', up[1] > up[0], '%.3f → %.3f' % (up[0], up[1]))
check('连续答对继续上升', up[2] > up[1], '%.3f → %.3f' % (up[1], up[2]))
check('答错后掌握度下降', dn < p, '%.3f → %.3f' % (p, dn))
check('掌握度始终在 [0,1]',
      all(0.0 <= x <= 1.0 for x in replay([1, 0, 1, 1, 0, 0, 1, 1] * 5)))

# 单调性：全对应该一路涨到接近 1
seq_all_right = replay([1] * 30)
check('连答 30 次对 → 掌握度接近 1', seq_all_right[-1] > 0.95,
      '%.4f' % seq_all_right[-1])
# 一直答错时不会降到 0：BKT 里每次练习都有 transit 的概率让人学会，
# 所以掌握度的下界是 transit（这里 0.10），不是 0。这是模型的本意，
# 不是 bug —— 断言写 0 会误判。
seq_all_wrong = replay([0] * 30)
floor = DEFAULT_PARAMS['p_transit']
check('连答 30 次错 → 掌握度收敛到 transit 下界',
      abs(seq_all_wrong[-1] - floor) < 0.05,
      '%.4f（下界 %.2f）' % (seq_all_wrong[-1], floor))

# ---- 2. 契约：塞进 schedule() ----
print('\n---- 2. 统一契约 ----')
b = algo.get('bkt')
prev = None
for lv in (3, 3, 1, 3, 3, 3):
    prev = b.schedule(prev, lv)
check('返回正好 6 个键', set(prev) == set(algo.REC_KEYS), str(sorted(prev)))
check('ef 落在 [0,1]（ef 在这里是掌握度）', 0.0 <= prev['ef'] <= 1.0,
      'ef=%s' % prev['ef'])

# SM-2 的 ef(2.5) 混进来时不能把 BKT 带崩
weird = b.schedule({'ef': 2.5, 'reps': 3}, 3)
check('旧 SM-2 的 ef=2.5 被夹回 [0,1]', 0.0 <= weird['ef'] <= 1.0,
      'ef=%s' % weird['ef'])
check('间隔随掌握度增长',
      b.interval_of(0.9) > b.interval_of(0.3) > b.interval_of(0.0),
      'p=0→%d天 p=0.3→%d天 p=0.9→%d天'
      % (b.interval_of(0.0), b.interval_of(0.3), b.interval_of(0.9)))

# ---- 3. 拟合：能不能把真值找回来 ----
print('\n---- 3. 参数拟合（最关键）----')
TRUTH = {'p_init': 0.20, 'p_transit': 0.15, 'p_slip': 0.10, 'p_guess': 0.25}


def gen(params, n_seq=14, n_step=12, seed=7):
    """按给定参数生成答题记录：掌握度决定答对概率，再按这个概率抛硬币。"""
    rnd = random.Random(seed)
    seqs = []
    for _ in range(n_seq):
        p = params['p_init']
        seq = []
        for _i in range(n_step):
            pc = p * (1 - params['p_slip']) + (1 - p) * params['p_guess']
            c = 1 if rnd.random() < pc else 0
            seq.append(c)
            p = step(p, c, params)
        seqs.append(seq)
    return seqs


seqs = gen(TRUTH)
n_step = sum(len(s) for s in seqs)
fitted, info = fit(seqs)
print('真值  %s' % TRUTH)
print('拟合  %s' % fitted)
print('info  %s' % info)
check('数据够时真的做了拟合', info.get('fitted') is True)
ll_fit = sum(log_likelihood(s, fitted) for s in seqs)
ll_truth = sum(log_likelihood(s, TRUTH) for s in seqs)
check('拟合结果的似然不低于真值参数的似然', ll_fit >= ll_truth - 1e-9,
      '拟合=%.3f 真值=%.3f' % (ll_fit, ll_truth))
# 参数不必逐位相同（网格有粒度），但量级要接近
for k in ('p_transit', 'p_slip', 'p_guess'):
    check('%s 拟合值接近真值（±0.2）' % k,
          abs(fitted[k] - TRUTH[k]) <= 0.2,
          '真值=%.2f 拟合=%.2f' % (TRUTH[k], fitted[k]))

# ---- 4. 数据不够时必须拒绝拟合 ----
print('\n---- 4. 数据门槛 ----')
small = [[1, 0, 1]] * 3
p2, info2 = fit(small)
check('数据不足时返回默认参数', p2 == DEFAULT_PARAMS and not info2['fitted'],
      info2.get('reason', ''))

# ---- 5. 事件流 → 序列 ----
print('\n---- 5. 事件流转换 ----')
evs = [{'correct': 1}, {'correct': 0}, {'correct': 1}]
check('from_events 正确转二值', from_events(evs) == [1, 0, 1])
check('空序列返回先验', abs(predict([], TRUTH) - TRUTH['p_init']) < 1e-9)

print('\n结果：%s' % ('全部通过' % () if ok else '**有失败项**'))
sys.exit(0 if ok else 1)
