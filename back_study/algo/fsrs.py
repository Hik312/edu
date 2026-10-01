# -*- coding: utf-8 -*-
"""FSRS-4.5 —— 用「记忆稳定性」而不是「倍数」来排间隔。

**为什么要有它**：SM-2 的间隔是 `旧间隔 × ef` 硬乘出来的，第三档之后就是
1→3→9→27→81 一路指数爆炸，跟人实际的遗忘曲线没关系。FSRS 反过来，先建模
「这张卡的记忆稳定性 S（天）」，再由目标保持率反解出间隔，所以间隔增长会
随着复习次数自然放缓。

三个变量：

- **D 难度**（1–10）：这张卡有多难记。答对降、答错升，且带均值回归，
  不会因为一次失误就永久变难。
- **S 稳定性**（天）：记忆能撑多久。答对涨、答错跌，涨幅取决于当前
  难度、上次提取时的掌握程度 R —— **忘得越干净才想起来，记得越牢**，
  这是 FSRS 比 SM-2 最本质的差别（间隔学习效应）。
- **R 可提取性**（0–1）：此刻还记得的概率，按幂函数随时间衰减。

**老实说三件事**，别把它当成银弹：

1. 权重 `W` 用的是 FSRS-4.5 **论文默认值**（在公开数据集上拟合的），
   没有在本项目数据上重新拟合。想真正适配你的卡片，得攒够记录后自己
   跑一遍优化 —— 那是 `fit()`，还没实现。
2. 项目只有三档评级（不会/模糊/会），FSRS 原生是四档
   （Again/Hard/Good/Easy）。这里把「会」映射到 Good(3)，**Easy 那档
   用不上**，所以 easy bonus（w16）恒为 1。想用满四档要先改前端评级。
3. 存储上复用了现有字段：`ef` 存难度 D（1–10）、`interval` 存间隔天数，
   下次再从 interval 反解 S。**这是妥协**：`progress` 表没有 S 和 D 的列，
   加列要动存储层三处（DDL / 探测 / import-json）。反解只在
   `retention != 0.9` 时有不到一天的舍入误差（0.9 时 I 恰好等于 S）。
   另：从 SM-2 切过来时旧的 ef（1.3–2.6）会被当成难度 D 读进去，
   复习几次就会回归正常，不用特意重置进度。
"""

import math

from .base import Algo, LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD, _num, today_str, diff_days


def _clamp(v, lo, hi):
    return min(hi, max(lo, v))


class FSRS(Algo):
    name = 'fsrs'
    label = 'FSRS-4.5（记忆稳定性模型）'
    needs = ('每卡几十条复习记录才能体现优势。权重是论文默认值，'
             '未在本项目数据上拟合 —— 拟合需要事件流，还没建。')
    #: 见 sm2.py 同名常量的说明：文档说三个算法都声明了 ef_note，
    #: 实际只有 BKT 有。FSRS 的 ef 存的是难度 D（1~10），
    #: 与 SM-2 的难度因子（1.3~2.6）**不是一个东西**，必须写清楚。
    ef_note = 'ef = 难度 D（1~10），不是 SM-2 的难度因子'

    #: 遗忘曲线的两个形状常量。19/81 这个数不是瞎取的：它让「目标保持率
    #: 0.9」时 I 恰好等于 S，公式两边刚好约掉。
    FACTOR = 19.0 / 81.0
    DECAY = -0.5

    #: FSRS-4.5 默认权重（17 个）。改之前先想清楚在干什么 ——
    #: w0-w2 初始稳定性、w4-w7 难度、w8-w10 稳定后增长、w11-w14 遗忘后重算、
    #: w15 hard 惩罚、w16 easy 加成。
    W = (0.4872, 1.4003, 3.7145, 13.8206,
         5.1618, 1.2298, 0.8975, 0.031,
         1.6474, 0.1367, 1.0461, 2.1072,
         0.0793, 0.3246, 1.587, 0.2272, 2.8755)

    def __init__(self, retention=0.9):
        """retention：目标保持率。0.9 = 「希望复习时还有 90% 记得」。

        调低 → 间隔更短、复习更勤；调高 → 间隔更长、但更容易忘。
        """
        self.retention = _clamp(float(retention), 0.7, 0.99)

    # ---------- 三块的初值与递推 ----------
    def _init_stability(self, g):
        return max(self.W[g - 1], 0.1)

    def _init_difficulty(self, g):
        return _clamp(self.W[4] - (g - 3) * self.W[5], 1.0, 10.0)

    def _mean_reversion(self, init, cur):
        """难度向「这张卡本来的难度」回归，避免单次失误把卡永久判死刑。"""
        return self.W[7] * init + (1 - self.W[7]) * cur

    def _next_difficulty(self, d, g):
        # ★ 均值回归的锚点是 **D0(Easy)**，不是「本次评级的初始难度」。
        # FSRS-4.5（py-fsrs）里这一步是
        #     D' = w7 · D0(4) + (1 - w7) · (D - w6 · (g - 3))
        # 其中 D0(4) = w4 - w5，正好是 g=4 时的 _init_difficulty。
        # 写成 self._init_difficulty(g) 会让锚点随评级浮动，与论文不符。
        # 数值影响很小（w7=0.031，1-10 量纲上 ≤0.04），但文档写的就是
        # 「FSRS-4.5 论文默认权重/公式」，那就按论文来。
        d0_easy = self._init_difficulty(4)
        return _clamp(self._mean_reversion(d0_easy, d)
                      - self.W[6] * (g - 3), 1.0, 10.0)

    def retrievability(self, t, s):
        """经过 t 天，还记得的概率。R = (1 + F·t/S)^(-0.5)。"""
        if s <= 0:
            return 0.0
        return (1.0 + self.FACTOR * max(0.0, t) / s) ** self.DECAY

    def _next_stability(self, d, s, r, g):
        if g == LEVEL_AGAIN:
            # 忘了：稳定性掉到「重学一张这么难的卡」该有的水平。
            new = (self.W[11] * d ** (-self.W[12])
                   * ((s + 1) ** self.W[13] - 1)
                   * math.exp(self.W[14] * (1 - r)))
            return _clamp(new, 0.1, s)
        # 想起来了：难度越低、忘得越透（R 越小），涨得越多。
        hard_penalty = self.W[15] if g == LEVEL_HARD else 1.0
        easy_bonus = 1.0          # 项目没有第四档（Easy），w16 用不上
        gain = (math.exp(self.W[8]) * (11.0 - d) * s ** (-self.W[9])
                * (math.exp(self.W[10] * (1.0 - r)) - 1.0)
                * hard_penalty * easy_bonus)
        return max(0.1, s * (1.0 + gain))

    # ---------- 间隔 <-> 稳定性 ----------
    def interval_for(self, s):
        """由稳定性反解间隔：I = S·(r^(1/DECAY) − 1)/F。r=0.9 时 I == S。"""
        k = (self.retention ** (1.0 / self.DECAY) - 1.0) / self.FACTOR
        return max(1, round(s * k))

    def stability_of(self, interval):
        """由存下来的间隔天数反解稳定性（存不下浮点 S，只能这么绕）。"""
        k = (self.retention ** (1.0 / self.DECAY) - 1.0) / self.FACTOR
        return max(0.1, interval / k) if k > 0 else 0.1

    # ---------- 契约实现 ----------
    def schedule(self, prev, level, today=None):
        day = today or today_str()
        g = level if level in (LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD) else LEVEL_AGAIN

        prev_iv = _num(prev, 'interval', 0, int)
        # 距上次复习过了多久：有 updatedAt 就算真实天数，没有就用上次的间隔。
        # （老数据可能没有 updatedAt，别让它把 R 算成 0。）
        last = (prev or {}).get('updatedAt')
        if last:
            try:
                t = max(0, diff_days(str(last), day))
            except (ValueError, TypeError):
                t = prev_iv
        else:
            t = prev_iv

        if prev_iv <= 0 and not last:
            # 第一次复习：难度和稳定性都取评级对应的初值。
            d = self._init_difficulty(g)
            s = self._init_stability(g)
            reps = 1 if g == LEVEL_GOOD else 0
        else:
            # 旧记录里的 ef 就是难度 D（SM-2 切过来时是 1.3–2.6，会被拉回 1–10）。
            d = _clamp(_num(prev, 'ef', self._init_difficulty(g)), 1.0, 10.0)
            s = self.stability_of(prev_iv) if prev_iv > 0 else self._init_stability(g)
            r = self.retrievability(t, s)

            d = self._next_difficulty(d, g)
            s = self._next_stability(d, s, r, g)
            # reps 的语义沿用 SM-2（连续答对次数），FSRS 本身不用它，
            # 纯粹是为了前端统计和到期排序不因为换了算法就变样。
            if g == LEVEL_GOOD:
                reps = _num(prev, 'reps', 0, int) + 1
            elif g == LEVEL_AGAIN:
                reps = 0
            else:
                reps = _num(prev, 'reps', 0, int)

        iv = self.interval_for(s)
        return self._rec(level, iv, d, reps, self.next_at(iv, day), day)
