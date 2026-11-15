# -*- coding: utf-8 -*-
"""FSRS-6 个性化权重拟合 —— 用你自己的复习记录微调 21 个权重。

## 为什么要有它

FSRS 默认权重是在公开数据集（上万个 Anki 用户的复习日志）上拟合的，
对你个人的记忆规律只是「平均意义上的准」。fsrs-optimizer 证明：
用个人日志重新拟合 21 个权重，log-loss 还能再降一截。本项目到
2026-11-15 才补上这一块 —— 之前 `fit()` 一直空着，不是忘了，是
事件流（algostore）攒够了才有拟合的原料。

## 和 fsrs-optimizer（官方实现）的差别，以及为什么

官方优化器用 PyTorch：Adam + autograd 求 21 维梯度 + scipy 预训练 S0。
本文件**刻意只用标准库**（algo 层零依赖的规矩不能为拟合破掉），
代价是拿不到解析梯度，于是用 **SPSA**（同步扰动随机逼近）估梯度：

    每轮只在正负两个方向上各评一次损失，21 维梯度一次估完
    g_i ≈ (L(w+cΔ) − L(w−cΔ)) / (2·c·Δ_i)，Δ_i ∈ {−1,+1} 随机

    SPSA 对维度不敏感（每轮固定 2 次损失评估），噪声由 Adam 的动量
    平滑；配合同步进行的 L2 正则（把权重往默认值拉），数据不多时
    也不会拟合出发散的参数。这是「官方思路（BCE 损失 + 权重正则 +
    Adam）+ 标准库能实现的梯度估计」的组合。

损失 = BCE(预测保留率, 实际记得与否) + γ·mean((w−w₀)/σ)²
      y 的口径与 srs-benchmark 一致：Again=0，Hard/Good/Easy=1
      （本项目的「模糊」是 Hard，算记得 —— 和 BKT 把「模糊」算错
      是两套刻意不同的口径：BKT 答的是「掌握没」，FSRS 答的是「记不记得」）。

## 数据门槛（照 bkt.fit 的模式）

MIN_EVENTS = 400（Anki 24.04 起的官方门槛；fsrs-optimizer 本身没有硬门槛，
但研究结论是 16 条能拟合、100 条起才算可靠）。不够就返回默认权重并
如实说原因 —— **宁可不用个性化，也不用 30 条记录拟合出的垃圾参数**。

## 与调度器的衔接

拟合出的权重经 algostore params_put 存为 `fsrs:params:<uid>`，
`db.set_level` 调 `schedule(prev, level, w=...)` 时带上 —— FSRS.schedule
用临时实例吃这组权重，注册表单例不受污染。看这个文件时配合读
algo/fsrs.py 的 `set_weights / schedule(w=)`。
"""

import math
import random
import time

from .fsrs import FSRS

#: 数据门槛。低于它拟合必然过拟合，返回默认权重 + fitted:false。
MIN_EVENTS = 400
#: BCE 里 p 的截断，防 log(0)
EPS = 1e-6
#: 正则强度。fsrs-optimizer 的 γ 默认偏小；这里 1.0 配 σ=(上界−下界)/2
#: 的归一，效果是「数据多时几乎不拉扯、数据少时温和地靠回默认值」。
REG_GAMMA = 1.0
#: SPSA/Adam 超参。lr 取 fsrs-optimizer 的 4e-2；SPSA 的 a/c 指数取
#: 文献推荐值（alpha=0.602, gamma_spsa=0.101）。
ITERS = 200
LR0 = 4e-2
SPSA_ALPHA = 0.602
SPSA_GAMMA = 0.101
C0 = 0.05


def _sigma(i, fsrs):
    """第 i 个权重的正则尺度：取合法区间宽度的一半。"""
    return max((fsrs.UPPER_BOUNDS[i] - fsrs.LOWER_BOUNDS[i]) / 2.0, 1e-3)


def _bce_loss(w, seqs, proto):
    """候选权重 w 下的平均 BCE（不含正则）。seqs 为空 / 无评分点返回 None。"""
    proto.set_weights(w)
    total, n = 0.0, 0
    for seq in seqs:
        d = s = None
        first = True
        for (t, g, y) in seq:
            if first:
                # 首次复习只用来初始化 D/S（它的评级就是「初见记没记住」，
                # 没有可预测的 R）—— 不进损失，与 srs-benchmark 的口径一致。
                d = proto._init_difficulty(g)
                s = proto._init_stability(g)
                first = False
                continue
            r = proto.retrievability(t, s)
            p = min(max(r, EPS), 1.0 - EPS)
            total -= y * math.log(p) + (1.0 - y) * math.log(1.0 - p)
            n += 1
            # 状态递推与 FSRS.schedule 同一套公式 —— 拟合和推理必须
            # 用同一个模型，否则拟合出的权重在推理时对不上号。
            d = proto._next_difficulty(d, g)
            s = proto._next_stability(d, s, r, g, t=t)
    if n == 0:
        return None
    return total / n


def fit(seqs, iters=ITERS, gamma=REG_GAMMA, seed=7):
    """拟合 FSRS-6 的 21 个权重。

    seqs : [[(t, g, y), ...], ...]
        每张卡一条按时间正序的序列。t = 距上次复习的天数（首次复习记 -1，
        只做初始化）；g = 评级 1/2/3；y = 1.0 记得 / 0.0 忘了（Again=0）。
    返回 (weights, info)。数据不够 / 全对一个答案时 fitted:false + reason，
    weights 为默认值 —— **调用方照常工作，只是没个性化**。

    info 键：fitted / reason / iterations / events（进了损失的复习数）/
    cards / bceBefore / bceAfter / seconds。bceBefore 用默认权重算，
    bceAfter 用拟合结果算 —— 两者一比就知道个性化有没有用，
    这个数字值得展示给用户。
    """
    t0 = time.time()
    proto = FSRS()                       # 只借用它的公式，不改注册表单例
    w0 = list(proto.W)

    n_ev = sum(max(0, len(s) - 1) for s in seqs)   # 首复习不计入
    if n_ev < MIN_EVENTS:
        return w0, {'fitted': False, 'reason': '复习记录不足（%d/%d 条）。'
                    '继续正常复习，攒够后再来拟合。' % (n_ev, MIN_EVENTS),
                    'events': n_ev, 'cards': len(seqs)}
    n_one = sum(1 for s in seqs for (_t, _g, y) in s[1:] if y >= 0.5)
    if n_one == 0 or n_one == n_ev:
        return w0, {'fitted': False, 'reason': '全部复习结果一样（全记得/全忘了），'
                    '拟合不出来的。', 'events': n_ev, 'cards': len(seqs)}

    def loss(w):
        bce = _bce_loss(w, seqs, proto)
        if bce is None:
            return float('inf')
        pen = sum(((w[i] - w0[i]) / _sigma(i, proto)) ** 2
                  for i in range(len(w))) / len(w)
        return bce + gamma * pen

    bce_before = _bce_loss(w0, seqs, proto)

    # ---- SPSA + Adam（标准库实现）----
    rng = random.Random(seed)
    w = list(w0)
    m = [0.0] * len(w)
    v = [0.0] * len(w)
    A = iters // 10
    b1, b2, eps = 0.9, 0.999, 1e-8
    for k in range(1, iters + 1):
        c_k = C0 / (k ** SPSA_GAMMA)
        a_k = LR0 / ((k + A) ** SPSA_ALPHA)
        delta = [1.0 if rng.random() < 0.5 else -1.0 for _ in w]
        wp = [min(max(w[i] + c_k * delta[i], proto.LOWER_BOUNDS[i]),
                  proto.UPPER_BOUNDS[i]) for i in range(len(w))]
        wm = [min(max(w[i] - c_k * delta[i], proto.LOWER_BOUNDS[i]),
                  proto.UPPER_BOUNDS[i]) for i in range(len(w))]
        lp, lm = loss(wp), loss(wm)
        if not math.isfinite(lp) or not math.isfinite(lm):
            continue                     # 这一轮的扰动飞出了可计算区，跳过
        for i in range(len(w)):
            g_i = (lp - lm) / (2.0 * c_k * delta[i])
            m[i] = b1 * m[i] + (1 - b1) * g_i
            v[i] = b2 * v[i] + (1 - b2) * g_i * g_i
            mh = m[i] / (1 - b1 ** k)
            vh = v[i] / (1 - b2 ** k)
            w[i] = min(max(w[i] - a_k * mh / (math.sqrt(vh) + eps),
                           proto.LOWER_BOUNDS[i]), proto.UPPER_BOUNDS[i])

    bce_after = _bce_loss(w, seqs, proto)
    info = {'fitted': True, 'iterations': iters, 'events': n_ev,
            'cards': len(seqs), 'bceBefore': round(bce_before, 6),
            'bceAfter': round(bce_after, 6),
            'seconds': round(time.time() - t0, 2),
            'note': 'BCE 越低预测越准；bceAfter 若没比 bceBefore 低，'
                    '说明默认权重已经够准，不必启用拟合结果。'}
    return [round(x, 6) for x in w], info
