# -*- coding: utf-8 -*-
"""算法评测层 —— 把「哪个算法更好」从感觉变成数字。

## 为什么需要这一层

`algo/demo.py` 之前只能比一件事：**365 天里安排了多少次复习**。
少不代表好 —— 也可能是把间隔拉得过长、复习次数少但忘得一样多。
真正的算法评测要回答两个不同的问题：

1. **同一次投入，谁让你记住更多？**  → `compare()` 里的
   `efficiency` / `finalRetention` / `mastered`
2. **它能不能预测「我这次会不会记住」？** → `logLoss` / `auc` / `calibration`

第 2 个问题顺带暴露了一个行业事实，值得单独说：
**SM-2 根本不预测留存概率**（它只有 ef 和 iv，没有概率模型），
BKT 的 p 答的是「掌握没」而不是「记不记得」——语义不同。
所以概率评测这一栏，**只有 FSRS 和 HLR 能参加**。
这不是本文件的 bug，是这些算法真实的能力边界。评测的价值就在于把边界画出来。

## 「真实世界」是怎么来的

评测需要 ground truth（这条卡到底什么时候会忘），但拿不到真人数据，
所以用一条**遗忘曲线**造：`R(t) = 2^(-t/h)`（半衰期 h 天），
答对概率再加手滑/蒙对两项（和 BKT 的 slip/guess 同一套假设）。

- 每张卡抽一个真实半衰期 h（异质：有人记得牢有人忘得快）
- 用户只在算法给的 `nextAt` 到期时才复习（真实行为：到期才看）
- 复习时能否答对 = 按上面那条曲线掷硬币
- 答对标「会」、答错标「不会」，再喂给算法算下一个间隔

**这不是真人数据，是仿真。** 它衡量的是「在这条遗忘曲线下谁排期排得好」，
不是「谁对你的学生最好」。要后者，必须接真实 review log（`evaluate()` 就是
为接真实 log 准备的），而那需要先攒数据 —— 这也是 FSRS 的 `fit()` 一直
空着的原因。同一条曲线对所有算法一致，所以**相对**比较仍然公平。

## 用法

```python
from algo import eval as ev

ev.compare(['sm2', 'fsrs', 'hlr', 'bkt'], n_cards=300, horizon=365, seed=7)
# → {'sm2': {'totalReviews': ..., 'efficiency': ...}, ...}

ev.calibration(log, 'hlr', bins=5)   # 留存率校准曲线
ev.evaluate(real_log, 'fsrs')        # 接真实 review log
```

刻意只用标准库（math / random / datetime）：这个包到今天为止
`不 import core、不 import 第三方`，评测层也不破坏这条规矩。
"""

import math
import random
from datetime import date, timedelta

from .base import LEVEL_AGAIN, LEVEL_GOOD, LEVEL_HARD
from .hlr import H0 as HLR_H0, retrievability as hlr_retrievability

#: 造「真实」记忆时用的手滑/蒙对率。量级取文献常见值。
SLIP, GUESS = 0.10, 0.10
#: 期末留存率高于这个值算「还记着」。
#: 刻意**不用 0.9**：这是「一年后还记得多少」的指标，365 天没碰过的卡
#: 记忆衰减到 0.9 不现实，用 0.9 会让所有算法的「掌握卡数」恒为 0，
#: 一列常数等于没这一列。0.7 = 一年下来还记得七成，是个有区分度的线。
MASTERED_AT = 0.70
#: 概率评测里 p 的截断，防止 log(0)。
EPS = 1e-6

#: 参与概率评测的算法 → 各自怎么算出「距上次复习 t 天的留存概率」。
#: **没有列进来的算法这一栏是空的**，这是能力边界，不是漏写。
_PREDICTORS = ('fsrs', 'hlr')


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)


# ---------- 概率预测：谁能预测「记不记得」 ----------
def predict(algo_name, prev, t):
    """该算法对「距上次复习 t 天」的留存概率预测。

    返回 None = **该算法不做概率预测**（SM-2 没有概率模型；
    BKT 的 p 是掌握度不是留存概率，语义不同不算）。
    """
    prev = prev or {}
    if algo_name == 'hlr':
        return hlr_retrievability(t, _numf(prev.get('ef'), HLR_H0))
    if algo_name == 'fsrs':
        from .fsrs import FSRS
        f = FSRS()
        s = f.stability_of(_numf(prev.get('interval'), 0))
        return f.retrievability(t, s) if s > 0 else 1.0
    return None


def _numf(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------- 指标 ----------
def log_loss(samples):
    """对数损失。越小越好，0.69 ≈ 瞎猜（二分类）。"""
    if not samples:
        return None
    tot = 0.0
    for p, y in samples:
        p = _clamp(p, EPS, 1 - EPS)
        tot += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return tot / len(samples)


def brier(samples):
    """Brier 分数 = 均方误差，越小越好。"""
    if not samples:
        return None
    return sum((_clamp(p) - y) ** 2 for p, y in samples) / len(samples)


def auc(samples):
    """AUC（Mann-Whitney U），0.5 = 瞎猜，1.0 = 完美。

    手写而不是 sklearn：这个包不引第三方依赖是硬规矩。
    """
    pos = [p for p, y in samples if y == 1]
    neg = [p for p, y in samples if y == 0]
    n_p, n_n = len(pos), len(neg)
    if n_p == 0 or n_n == 0:
        return None
    # 逐对比较 O(n²)：评测样本是几千条量级，完全够用。
    wins = sum((1.0 if a > b else 0.5 if a == b else 0.0) for a in pos for b in neg)
    return wins / (n_p * n_n)


def calibration(samples, bins=5):
    """留存率校准曲线：把样本按预测概率分桶，比对预测值 vs 实际留存。

    理想情况下每个桶的实际留存率应贴近它的预测概率（贴对角线 = 校准好）。
    这是「算法说 80% 记得，剩下 20% 到期时真的忘了」这句话能不能兑现。

    返回 `[{bin, n, predicted, actual}, ...]`，空桶不返回。
    """
    if not samples:
        return []
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        # 最后一桶要含 1.0，否则 p=1.0 永远落不进来
        bucket = [(p, y) for p, y in samples
                  if (lo <= p < hi) or (i == bins - 1 and p == 1.0)]
        if not bucket:
            continue
        out.append({'bin': '%d-%d%%' % (round(lo * 100), round(hi * 100)),
                    'n': len(bucket),
                    'predicted': sum(p for p, _ in bucket) / len(bucket),
                    'actual': sum(y for _, y in bucket) / len(bucket)})
    return out


# ---------- srs-benchmark 口径的 RMSE(bins)（2026-11-15 对齐） ----------
def _bin_grid(x, base, growth):
    """srs-benchmark 的对数网格取整：bin = round(base·growth^floor(ln x/ln growth))。

    三条特征轴各有一组 (base, growth)：间隔 2.48/2.57、复习数 1.52/1.58、
    遗忘数 1.4/1.48（数值逐字取自 srs-benchmark / awesome-fsrs wiki）。
    x<=0 落 0 号格。不 import 第三方 —— 分箱只是几行对数运算。
    """
    if x is None or x <= 0:
        return 0
    try:
        k = math.floor(math.log(x) / math.log(growth))
        return round(base * (growth ** k))
    except (ValueError, OverflowError):
        return 0


def rmse_bins(pairs):
    """RMSE(bins)：srs-benchmark 现行的主指标（旧的「RMSE(b-log retention)」
    已改名演进为它）。

    pairs : `(p, y, delta_t[, n_reviews[, n_lapses]])`
        p/y 同 log_loss；后三个是分箱特征，缺省 None 时该轴全部落同一箱
        （真实日志一时拿不到计数器也能用，只是分箱粗一点）。

    按 (间隔格, 复习数格, 遗忘数格) 联合分箱；每箱内算「平均预测留存 vs
    实际留存率」之差的平方，按箱内样本数加权：

        RMSE = sqrt( Σ w_i·(p̄_i − ȳ_i)² / Σ w_i )     范围 0–1，越低越好

    为什么不直接算逐样本 MSE：逐样本口径会惩罚「说了 0.95 结果忘」的样本
    远多于「说了 0.2 结果忘了」——但后者才是真正的失准。分箱口径量的是
    **每一类处境下的系统性偏差**，这才是排期算法真正该负责的东西。
    """
    bins = {}
    for tup in pairs:
        p, y = tup[0], tup[1]
        dt = tup[2] if len(tup) > 2 else None
        nr = tup[3] if len(tup) > 3 else None
        nl = tup[4] if len(tup) > 4 else None
        key = (_bin_grid(dt, 2.48, 2.57),
               _bin_grid(nr, 1.52, 1.58),
               _bin_grid(nl, 1.4, 1.48))
        acc = bins.setdefault(key, [0.0, 0.0, 0])
        acc[0] += _clamp(p, EPS, 1 - EPS)
        acc[1] += y
        acc[2] += 1
    if not bins:
        return None
    sw = sp = 0.0
    for ps, ys, n in bins.values():
        sw += n
        sp += n * (ps / n - ys / n) ** 2
    return math.sqrt(sp / sw)


# ---------- 仿真：造一个可控的「真实世界」 ----------
def _truth_rate(t, h, slip=SLIP, guess=GUESS):
    """t 天后真实答对概率。半衰期模型 + 手滑/蒙对。"""
    r = hlr_retrievability(t, h)
    return _clamp(r * (1.0 - slip) + (1.0 - r) * guess)


def _delay(rng):
    """真实用户不会准时到秒复习：多数按期，少数拖延几天。

    **这是整个仿真里最关键的一个 realism 补丁。**
    假设人人准时在 nextAt 复习的话，各算法都会把间隔卡在「刚好还没忘」
    的边界上 → 到期时几乎必答对 → 遗忘次数恒为 0、期末留存恒等于目标保留率、
    AUC 恒等于瞎猜 0.5。三个指标同时饱和，评测就白做了。
    加上拖延之后「实际经过天数」有了方差，遗忘真的会发生，
    概率预测才有东西可预测，AUC 才量得出差异。
    """
    r = rng.random()
    if r < 0.70:
        return 0
    if r < 0.85:
        return 1
    if r < 0.94:
        return 2
    if r < 0.98:
        return 4
    return 7


def simulate(algo, n_cards=300, horizon=365, seed=7,
             h_min=5.0, h_max=60.0, max_reviews=80):
    """让一个算法在仿真世界里调度 n_cards 张卡 horizon 天。

    返回 `{'reviews': [...], 'cards': [...]}`：
      reviews  每一次复习 {card, t, correct, rate, day, predicted}
      cards    每张卡 {h, nReviews, lapses, lastDay, retention}
    """
    rng = random.Random(seed)
    base = date(2026, 1, 1)
    reviews, cards = [], []

    for cid in range(n_cards):
        # 每张卡的真实记忆半衰期：异质，才看得出算法能不能因人/因卡调整
        h_true = rng.uniform(h_min, h_max)
        prev, day, lapses, n = None, 0, 0, 0
        last_review = 0
        while day < horizon and n < max_reviews:
            iv_prev = 0 if prev is None else max(1, int(prev['interval']))
            # 实际过了多少天 = 算法排的间隔 + 用户拖延
            actual_t = 0 if prev is None else iv_prev + _delay(rng)
            rate = _truth_rate(actual_t, h_true)
            correct = 1 if rng.random() < rate else 0
            # 复习体验：答对 → 会(3)，答错 → 不会(1)。
            # 「模糊」是用户主观的中间态，这里不加随机噪声 ——
            # 加了就等于给算法白送信息，评测会偏乐观。
            level = LEVEL_GOOD if correct else LEVEL_AGAIN
            today = (base + timedelta(days=day)).strftime('%Y-%m-%d')
            rec = algo.schedule(prev, level, today=today)
            # 预测要喂**实际**经过的天数（含拖延），否则量的是「算法预测
            # 自己排的间隔」——而它当然知道那个间隔，等于拿答案考自己。
            pred = predict(algo.name, prev, actual_t)
            reviews.append({'card': cid, 't': actual_t, 'correct': correct,
                            'rate': rate, 'day': day, 'level': level,
                            'predicted': pred, 'hTrue': h_true,
                            # RMSE(bins) 的分箱特征：本次复习**之前**的累计数
                            'nReviews': n, 'nLapses': lapses})
            if correct == 0 and actual_t > 0:
                lapses += 1
            last_review = day
            day += max(1, int(rec['interval']))
            prev = rec
            n += 1
        # 期末留存：从**最后一次复习**到期末（horizon）过了多少天，
        # 按真实遗忘曲线算还剩多少记忆。不能用「排出来的间隔」当已过天数 ——
        # 那是算法对自己的预测，不是真实发生的事。
        cards.append({'card': cid, 'h': h_true, 'nReviews': n, 'lapses': lapses,
                      'lastDay': day, 'retention': _truth_rate(horizon - last_review, h_true)})
    return {'reviews': reviews, 'cards': cards}


def evaluate(algo_name, log, get_algo=None):
    """给一份已有的 review log 打分。

    log: [{prev, t, correct, level[, nReviews][, nLapses]}, ...]，
    prev 是那次复习前的进度记录。真实数据接入时（`/api/review/events` +
    progress 历史）走这条路；现在的仿真里也可以复用 —— 见 `compare()`。

    ★ 2026-11-15 对齐 srs-benchmark：输出加 `rmseBins`（现行主指标，
    口径见 rmse_bins）。log 条目可选带 nReviews/nLapses 计数器
    （scripts/eval_real.py 回放事件流时会带上），不带就退化成单箱。

    get_algo: 可选，注入算法实例（测试用；默认按名字从注册表取）。
    """
    from . import get as _get
    algo = get_algo() if get_algo else _get(algo_name)
    samples = []
    for r in log:
        p = predict(algo_name, r.get('prev'), r.get('t', 0))
        if p is None:
            continue
        samples.append((p, int(r['correct']), r.get('t', 0),
                        r.get('nReviews'), r.get('nLapses')))
    prob_samples = [(s[0], s[1]) for s in samples]
    return {
        'algo': algo_name,
        'predictsRetention': algo_name in _PREDICTORS,
        'n': len(log),
        'nScored': len(samples),
        'logLoss': log_loss(prob_samples),
        'brier': brier(prob_samples),
        'auc': auc(prob_samples),
        'rmseBins': rmse_bins(samples) if samples else None,
    }


def _metrics(algo, sim):
    """从一次仿真里汇总指标。"""
    reviews, cards = sim['reviews'], sim['cards']
    n_rev = len(reviews)
    lapse = sum(1 for r in reviews if r['correct'] == 0 and r['t'] > 0)
    ret = [c['retention'] for c in cards]
    avg_ret = sum(ret) / len(ret) if ret else 0.0
    mastered = sum(1 for x in ret if x >= MASTERED_AT)
    samples = [(r['predicted'], r['correct'], r['t'], r.get('nReviews'),
                r.get('nLapses'))
               for r in reviews if r['predicted'] is not None]
    prob_samples = [(s[0], s[1]) for s in samples]
    return {
        'algo': algo.name,
        'totalReviews': n_rev,
        'reviewsPerCard': round(n_rev / len(cards), 2) if cards else 0,
        'lapses': lapse,
        'lapseRate': round(lapse / n_rev, 4) if n_rev else 0.0,
        # 核心公平指标：同样复习一次，换来多少留存
        'efficiency': round(avg_ret / (n_rev / len(cards)), 4) if cards and n_rev else 0.0,
        'finalRetention': round(avg_ret, 4),
        'mastered': mastered,
        'masteredRate': round(mastered / len(cards), 4) if cards else 0.0,
        'predictsRetention': algo.name in _PREDICTORS,
        'logLoss': log_loss(prob_samples),
        'auc': auc(prob_samples),
        'rmseBins': rmse_bins(samples),
    }


def compare(algos=None, n_cards=300, horizon=365, seed=7):
    """多算法对拍：同一条遗忘曲线、同一批卡、同一个随机种子。

    seed 相同 = 抽到的真实半衰期分布和答题结果完全一致，
    算法之间唯一的差别就是**怎么排间隔** —— 这才是公平对比。

    默认比全部注册的算法。
    """
    from . import get as _get, names as _names
    algos = algos or _names()
    out = {}
    for name in algos:
        a = _get(name)
        if name == 'bkt':
            # BKT 不排期（它答「掌握没」，不答「何时复习」）。
            # 让它排期等于把它硬塞进不属于它的角色，评测就没意义了。
            continue
        out[name] = _metrics(a, simulate(a, n_cards=n_cards, horizon=horizon, seed=seed))
    return out


def report(algos=None, n_cards=300, horizon=365, seed=7):
    """把 compare() 渲染成一张能直接贴进文档/简历的表（纯文本）。"""
    data = compare(algos, n_cards, horizon, seed)
    if not data:
        return '（没有可评测的算法 —— bkt 不排期，已跳过）'
    head = ('算法', '复习次数', '次/卡', '遗忘次数', '期末留存', '掌握卡数',
            '效率', 'AUC', 'RMSE(bins)')
    rows = [head]
    for name, m in data.items():
        auc_s = '%.3f' % m['auc'] if m['auc'] is not None else '—'
        rm_s = '%.4f' % m['rmseBins'] if m.get('rmseBins') is not None else '—'
        rows.append((name, str(m['totalReviews']), str(m['reviewsPerCard']),
                     str(m['lapses']), '%.1f%%' % (m['finalRetention'] * 100),
                     str(m['mastered']), '%.3f' % m['efficiency'], auc_s, rm_s))
    w = [max(len(str(r[i])) for r in rows) for i in range(len(head))]
    line = '  '.join('-' * x for x in w)
    out = ['  '.join(str(rows[0][i]).ljust(w[i]) for i in range(len(head))), line]
    for r in rows[1:]:
        out.append('  '.join(str(r[i]).ljust(w[i]) for i in range(len(head))))
    out.append('')
    out.append('（— = 该算法不做留存概率预测：SM-2 无概率模型，'
               'BKT 的 p 是掌握度非留存率。这是算法能力边界，不是缺数据。）')
    out.append('（RMSE(bins) 为 srs-benchmark 现行主指标口径，越低越好。）')
    return '\n'.join(out)
