# -*- coding: utf-8 -*-
"""FSRS-6 —— 用「记忆稳定性」而不是「倍数」来排间隔。

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

## 2026-11-15：FSRS-4.5 → FSRS-6

权重与公式逐字对照 py-fsrs v6.3.3（open-spaced-repetition，MIT）同步，
关键差异四条：

1. **衰减指数可训练**：4.5 是固定 `DECAY=-0.5`、`FACTOR=19/81`；
   6 改成 `DECAY=-w20`（默认 -0.1542）、`FACTOR = 0.9^(1/DECAY)-1 ≈ 0.9807`。
   构造保证 R(S)=0.9，所以 retention=0.9 时「间隔 == 稳定性」的恒等式
   仍然成立 —— 存储兼容性没破（见下面第 3 条妥协）。
2. **难度更新加了线性阻尼**：`ΔD_damped = ΔD·(10-D)/9`，难度越大单次
   失误冲击越小；初始难度从线性式 `w4-(G-3)·w5` 改成指数式
   `w4-e^(w5·(G-1))+1`。均值回归锚点仍是 D0(4)。
3. **新增同日复习分支**（w17/w18/w19）：同一天重复刷一张卡，
   `S' = S·max(e^(w17·(G-3+w18))·S^(-w19), 1)` —— 因子 <1 时取 1，
   即**同日复习最多不变、绝不降级**；Again 的同日降级走遗忘公式自带的
   同日上界 `min(·, S/e^(w17·w18))`。4.5 对同日复习没有任何特殊处理
   （R 算出来恒为 1，S 涨幅为 0），6 会给小幅增长 —— 这是行为差异，
   对旧进度无迁移成本：复几次自然收敛。
4. **参数 17 → 21**：+w17/w18（同日系数）、+w19（同日饱和幂）、+w20（衰减）。
   全部 21 个都在 LOWER/UPPER_BOUNDS 里有合法区间 —— fit-fsrs
   （algo/fsrs_fit.py）拟合时用它夹住搜索范围。

**老实说三件事**，别把它当成银弹：

1. 权重 `W` 用的是 FSRS-6 **论文默认值**（公开数据集拟合的），
   没有在本项目数据上重新拟合。想真正适配你的卡片，用 `fit-fsrs`
   端点（数据够 400 条后，照 fsrs-optimizer 的思路用 SPSA+Adam 微调）。
2. 项目只有三档评级（不会/模糊/会），FSRS 原生是四档
   （Again/Hard/Good/Easy）。这里把「会」映射到 Good(3)，**Easy 那档
   用不上**，所以 easy bonus（w16）恒为 1。想用满四档要先改前端评级。
3. 存储上复用了现有字段：`ef` 存难度 D（1–10）、`interval` 存间隔天数，
   下次再从 interval 反解 S。**这是妥协**：`progress` 表没有 S 和 D 的列，
   加列要动存储层三处（DDL / 探测 / import-json）。反解只在
   `retention != 0.9` 时有舍入误差（0.9 时 I 恰好等于 S，两种版本一致）。
   另：从 SM-2 或 FSRS-4.5 切过来时旧值会被拉回合法区间，
   复习几次就会回归正常，不用特意重置进度。

**fuzz（间隔抖动）刻意不实现**：py-fsrs 会给 ≥2.5 天的间隔加 ±5%/10%/15%
的随机抖动来摊平负载，但本项目 check.js 要拿 json / mysql 两种存储
**逐位比对**到期队列 —— 随机性会毁掉这份对照。负载均衡交给
algo/loadbalance.py（确定性版 Load Balance）去做。
"""

import math

from .base import Algo, LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD, _num, today_str, diff_days


def _clamp(v, lo, hi):
    return min(hi, max(lo, v))


class FSRS(Algo):
    name = 'fsrs'
    label = 'FSRS-6（记忆稳定性模型）'
    needs = ('每卡几十条复习记录才能体现优势。默认权重来自 FSRS-6 论文；'
             '复习记录攒够 400 条后可用 fit-fsrs 拟合个性化权重。')
    #: 见 sm2.py 同名常量的说明：文档说三个算法都声明了 ef_note，
    #: 实际只有 BKT 有。FSRS 的 ef 存的是难度 D（1~10），
    #: 与 SM-2 的难度因子（1.3~2.6）**不是一个东西**，必须写清楚。
    ef_note = 'ef = 难度 D（1~10），不是 SM-2 的难度因子'

    #: FSRS-6 默认权重（21 个，py-fsrs v6.3.3 逐字对照）。改之前先想清楚在干什么：
    #: w0-w3 初始稳定性、w4-w5 初始难度、w6-w7 难度更新与均值回归、
    #: w8-w10 稳定后增长、w11-w14 遗忘后重算、w15 hard 惩罚、w16 easy 加成、
    #: w17-w19 同日复习、w20 衰减指数。
    W = (0.212, 1.2931, 2.3065, 8.2956,
         6.4133, 0.8334, 3.0194, 0.001,
         1.8722, 0.1666, 0.796,
         1.4835, 0.0614, 0.2629, 1.6483,
         0.6014, 1.8729,
         0.5425, 0.0912, 0.0658,
         0.1542)

    #: 拟合时允许的权重区间（py-fsrs 原版边界，fsrs_fit 拿它夹搜索范围）
    LOWER_BOUNDS = (0.001, 0.001, 0.001, 0.001, 1.0, 0.001, 0.001, 0.001,
                    0.0, 0.0, 0.001, 0.001, 0.001, 0.001, 0.0, 0.0, 1.0,
                    0.0, 0.0, 0.0, 0.1)
    UPPER_BOUNDS = (100, 100, 100, 100, 10, 4, 4, 0.75,
                    4.5, 0.8, 3.5, 5, 0.25, 0.9, 4, 1, 6,
                    2, 2, 0.8, 0.8)
    STABILITY_MIN = 0.001

    #: 稳定性下限。4.5 时代是 0.1，FSRS-6 收紧到 0.001（py-fsrs 原值）——
    #: 「同一天内刚学就忘」的极短稳定性现在是合法状态。
    #: 遗忘曲线的两个形状常量不再写死（见 _refresh）：DECAY 由 w20 驱动，
    #: FACTOR 由「R(S)=0.9」这个构造性要求反解出来。
    DECAY = -0.1542
    FACTOR = 0.9 ** (1.0 / DECAY) - 1

    def __init__(self, retention=0.9, w=None):
        """retention：目标保持率。0.9 = 「希望复习时还有 90% 记得」。

        调低（如 0.85）= 允许忘得更多 → 间隔**更长**、复习更疏；
        调高（如 0.95）= 想记得更牢 → 间隔**更短**、复习更勤。
        （4.5 时代的注释把方向写反了，2026-11-15 由 pytest 抓出来改正：
        I = S·(r^(1/DECAY)−1)/FACTOR，r 越小分子越大 → I 越长。）
        w：替换默认 21 权重（fit-fsrs 的产物）。传进来后 DECAY/FACTOR
        会按新权重的 w20 重算 —— 这两个常量是权重的函数，不是独立旋钮。
        """
        self.retention = _clamp(float(retention), 0.7, 0.99)
        self.W = tuple(self.W)
        if w:
            self.set_weights(w)

    def set_weights(self, w):
        """替换实例权重（fit-fsrs 接线用）。长度/区间不合法直接抛 ValueError ——
        配置错了装没装过比装错了好，跟 ALGO 配错就抛是同一条原则。"""
        w = tuple(float(x) for x in w)
        if len(w) != len(self.W):
            raise ValueError('FSRS 权重必须是 %d 个，收到 %d 个'
                             % (len(self.W), len(w)))
        for i, x in enumerate(w):
            if not (self.LOWER_BOUNDS[i] <= x <= self.UPPER_BOUNDS[i]):
                raise ValueError('FSRS w%d=%g 超出合法区间 [%g, %g]'
                                 % (i, x, self.LOWER_BOUNDS[i], self.UPPER_BOUNDS[i]))
        self.W = w
        self._refresh()

    def _refresh(self):
        """由当前权重重算派生常量。DECAY=-w20；FACTOR 保证 R(S)=0.9。"""
        self.DECAY = -self.W[20]
        self.FACTOR = 0.9 ** (1.0 / self.DECAY) - 1

    # ---------- 三块的初值与递推 ----------
    def _init_stability(self, g, W=None):
        W = W or self.W
        return max(W[g - 1], self.STABILITY_MIN)

    def _init_difficulty(self, g, W=None):
        """FSRS-6 初始难度：指数式 D0(G)=w4-e^(w5(G-1))+1（4.5 是线性式）。"""
        W = W or self.W
        return _clamp(W[4] - math.exp(W[5] * (g - 1)) + 1, 1.0, 10.0)

    def _next_difficulty(self, d, g, W=None):
        # FSRS-5/6 的难度更新（4.5 没有阻尼项）：
        #   ΔD = -w6·(G-3)
        #   ΔD_damped = ΔD·(10-D)/9   ← 线性阻尼：已经很难的卡，单次失误冲击小
        #   D' = clamp(w7·D0(4) + (1-w7)·(D+ΔD_damped), 1, 10)
        # 均值回归的锚点是 **D0(Easy)**，不是「本次评级的初始难度」——
        # 4.5 时代就修过的坑：锚点随评级浮动会与论文不符（数值影响很小，
        # 但既然声明按论文实现就按论文来）。
        W = W or self.W
        d0_easy = self._init_difficulty(4, W)
        dd = -W[6] * (g - 3) * (10.0 - d) / 9.0
        return _clamp(W[7] * d0_easy + (1 - W[7]) * (d + dd), 1.0, 10.0)

    def retrievability(self, t, s):
        """经过 t 天，还记得的概率。R = (1 + F·t/S)^DECAY，DECAY=-w20。"""
        if s <= 0:
            return 0.0
        return (1.0 + self.FACTOR * max(0.0, t) / s) ** self.DECAY

    def _next_stability(self, d, s, r, g, t=1, W=None):
        """FSRS-6 稳定性递推。t = 距上次复习的天数（0 = 同日复习）。

        三条路径：
          同日 + 会/模糊   → S·max(e^(w17(G-3+w18))·S^(-w19), 1)（只涨不跌）
          遗忘（Again）    → 长期重算式 与 同日上界 S/e^(w17·w18) 取小
          长期 + 会/模糊   → S·(1+e^w8·(11-D)·S^(-w9)·(e^(w10(1-R))-1)·惩罚/加成)
        """
        W = W or self.W
        if t <= 0 and g != LEVEL_AGAIN:
            # 同日复习：增长因子不小于 1 —— 刷得再勤也不能把 S 刷小；
            # S 越大饱和幂 S^(-w19) 压得越狠，防止「同一天无限刷卡膨胀」。
            factor = math.exp(W[17] * (g - 3 + W[18])) * (s ** (-W[19]))
            return max(s * max(factor, 1.0), self.STABILITY_MIN)
        if g == LEVEL_AGAIN:
            # 忘了：稳定性掉到「重学一张这么难的卡」该有的水平；
            # 同日上界 min(·, S/e^(w17·w18)) 管住「刚复习完立刻又标不会」的场景。
            new = (W[11] * d ** (-W[12])
                   * ((s + 1) ** W[13] - 1)
                   * math.exp(W[14] * (1 - r)))
            return max(min(new, s / math.exp(W[17] * W[18])), self.STABILITY_MIN)
        # 想起来了：难度越低、忘得越透（R 越小），涨得越多。
        hard_penalty = W[15] if g == LEVEL_HARD else 1.0
        easy_bonus = 1.0          # 项目没有第四档（Easy），w16 用不上
        gain = (math.exp(W[8]) * (11.0 - d) * s ** (-W[9])
                * (math.exp(W[10] * (1.0 - r)) - 1.0)
                * hard_penalty * easy_bonus)
        return max(self.STABILITY_MIN, s * (1.0 + gain))

    # ---------- 间隔 <-> 稳定性 ----------
    def _k(self):
        """间隔↔稳定性的换算系数。r=0.9 时 k=1（I 恰好等于 S）。"""
        k = (self.retention ** (1.0 / self.DECAY) - 1.0) / self.FACTOR
        return k

    def interval_for(self, s):
        """由稳定性反解间隔：I = (S/FACTOR)·(r^(1/DECAY)−1)。r=0.9 时 I == S。"""
        return max(1, round(s * self._k()))

    def stability_of(self, interval):
        """由存下来的间隔天数反解稳定性（存不下浮点 S，只能这么绕）。"""
        k = self._k()
        return max(self.STABILITY_MIN, interval / k) if k > 0 else self.STABILITY_MIN

    # ---------- 契约实现 ----------
    def schedule(self, prev, level, today=None, w=None):
        """`w`：本次调用使用的个性化权重（fit-fsrs 产物），None 用默认。

        实现方式是临时造一个轻量实例（21 个 float 的拷贝，微秒级）——
        **绝不原地改 self.W**：注册表里的实例是全进程共享的单例，
        请求并发下改共享状态就是另一个 _LAST_META 串台。
        """
        day = today or today_str()
        g = level if level in (LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD) else LEVEL_AGAIN

        if w:
            inst = FSRS(retention=self.retention)
            inst.set_weights(w)
            return inst.schedule(prev, level, today=day)

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
            # t 传进去：t==0（同日）走 FSRS-6 的同日分支
            s = self._next_stability(d, s, r, g, t=t)
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
