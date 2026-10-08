# -*- coding: utf-8 -*-
"""HLR —— 半衰期回归（Half-Life Regression，Duolingo 在用）。

## 它想解决什么

SM-2 的间隔是 `iv = iv × ef`，**乘法反馈**：间隔自己乘自己，涨得快也炸得快。
连着标十次「会」，间隔就到几百天，跟你有没有真的记住没关系。

FSRS 有记忆模型，但需要大量数据拟合 19 个权重才准。

HLR 走中间路线：**只记一个「记忆半衰期 h」**（过了 h 天，记忆剩一半），
间隔由 h 反推。**零预训练权重、零数据就能用**，而且比 SM-2 稳。

## 核心只有两行

1. 留存率：`R(t) = 2^(-t/h)` —— 距上次复习 t 天后，还记得的概率。
   这就是「半衰期」这个名字的来源：t = h 时 R = 0.5。
2. 选间隔：解 `2^(-iv/h) = target` 得 `iv = h · log2(1/target)`。
   也就是说**间隔不是拍脑袋乘出来的，是从 h 算出来的**。

## ⚠️ 和论文原式的关系（别引用错）

Settles & Meeder(2014) 的 HLR 是**逻辑回归**（用特征预测答对概率，参数靠
数据拟合）。这里实现的是它的**核心思想 + 简化式**：

- 保留「用半衰期建模记忆衰减」这一核心
- 参数退化成 2 个（初始半衰期 H0、目标保留率 target），**不需要拟合**
- 换来的好处是**冷启动友好**：新用户 / 新卡立刻就有合理间隔，
  而 FSRS 在数据攒够之前只能拿论文默认权重硬撑

它是「可用的近似」，不是「论文的复现」。要严格复现得引入回归 + 特征工程，
那是另一件事（而且也得先有数据）。

## 三个档位怎么改 h

| 评级 | h 变化 | 直觉 |
|---|---|---|
| 会 (3) | `h × (1 + 1.2(1-R))` | 答对了就加长；**R 越低加得越多**（超期还答对 = 记忆比预期强） |
| 模糊 (2) | `h × 0.8` | 打折，但没否定 |
| 不会 (1) | `h × 0.4` | 大幅缩短 |

「R 越低加得越多」是 HLR 和 SM-2 最大的行为差异：SM-2 每次「会」都是
`×ef` 一视同仁地涨；HLR 会区分「刚过一天就答对」和「拖了很久才答对」。

## 切算法时的坑（和其他算法一样）

`ef` 在 SM-2 里是难度因子（1.3~2.6）、在 FSRS 里是难度 D（1~10）——
两者都落在合法的半衰期范围 `[1, 3650]` 内，**没法从数值上区分**。这里做了
兜底：用旧间隔反推一个 h 下限（`h ≥ interval / K`），保证切换后第一次的
间隔不短于旧算法给的间隔。否则从 SM-2 切过来，ef=2.6 会被当成「半衰期
2.6 天」，第一次间隔直接掉到 1 天。

FSRS / BKT 遇到同类问题时用的是「越界夹回 + 几次后回归正常」，这里是同一
条路上的另一种解法 —— 因为 HLR 的合法区间太宽，夹不住。
"""

import math

from .base import (Algo, LEVEL_AGAIN, LEVEL_GOOD, LEVEL_HARD, _num,
                   diff_days)

#: 初始半衰期（天）。量级取 Duolingo 公开的 15~25 天之上一点 ——
#: 实测（HLR vs SM-2/FSRS，300 卡 365 天仿真）取 20 天会保守到每 5 天复习一次，
#: 35 天 + 下面的 target 组合能把间隔推到 8→11→14→18→24→31 天这条合理曲线。
H0 = 35.0
#: 目标保留率：安排间隔时，希望「到下次复习时还记得」的概率是这个值。
#: 取 0.85 而不是 0.9：K=log2(1/target)，target 越高间隔越短。
#: 0.85 → K≈0.234，实测比 0.9 少一半复习次数而遗忘率只略升。
TARGET_R = 0.85
#: 「会」时半衰期的增长强度。见 schedule() 里的 (1 - R) 修正。
GROWTH = 2.0
#: 「模糊」打折、「不会」重罚。
HARD_SHRINK = 0.8
AGAIN_SHRINK = 0.4
#: 半衰期的合法区间（天）。夹在这里防手改数据 / 脏数据。
H_MIN, H_MAX = 1.0, 3650.0

#: iv = h · K，K = log2(1/target)。target=0.9 → K≈0.152。
#: 算成常量而不是每次 log2，纯粹是为了让 interval_for() 读起来是行话。
K = math.log2(1.0 / TARGET_R)


def _clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def retrievability(t_days, h):
    """t 天后还记得的概率：2^(-t/h)。

    给评测层用（algo/eval.py 量算法准不准就是量这个预测准不准）。
    """
    h = _clamp(float(h), H_MIN, H_MAX)
    return _clamp(2.0 ** (-max(0.0, float(t_days)) / h), 0.0, 1.0)


class HLR(Algo):
    """半衰期回归：用记忆半衰期反推复习间隔。"""

    name = 'hlr'
    label = 'HLR 半衰期回归（零数据可用）'
    needs = ('不需要预训练权重、不需要历史数据 —— 新用户/新卡立刻可用。'
             '代价是参数只有 2 个（初始半衰期、目标保留率），'
             '不如拟合过的 FSRS 精细。')
    ef_note = 'ef = 记忆半衰期 h（天），不是难度因子'

    def half_life(self, prev):
        """从旧记录里读半衰期，顺带处理「从别的算法切过来」的脏 ef。"""
        h = _clamp(_num(prev, 'ef', H0), H_MIN, H_MAX)
        # 兜底：旧 ef 是难度因子/难度 D 时数值偏小，用旧间隔反推一个下限，
        # 保证切换后第一次间隔不短于旧算法给的（详见模块文档「切算法时的坑」）。
        iv_prev = _num(prev, 'interval', 0, int)
        if iv_prev > 0:
            h = max(h, iv_prev / K)
        return _clamp(h, H_MIN, H_MAX)

    def interval_for(self, h):
        """半衰期 → 间隔：解 2^(-iv/h)=target。h=20 → 3 天。"""
        return max(1, int(round(_clamp(float(h), H_MIN, H_MAX) * K)))

    def schedule(self, prev, level, today=None):
        day = today or self._today()
        h_prev = self.half_life(prev)

        # 距上次复习过了多久。有 updatedAt 就用真实天数（跨天复习是常态），
        # 没有就用上次的间隔兜底（老数据可能没这个键）。
        last = (prev or {}).get('updatedAt')
        if last:
            try:
                t = max(0, diff_days(str(last), day))
            except (ValueError, TypeError):
                t = _num(prev, 'interval', 0, int)
        else:
            t = _num(prev, 'interval', 0, int)

        r = retrievability(t, h_prev)

        if level == LEVEL_GOOD:
            # (1 - r) 修正：超期才答对说明记忆比模型预期强，多涨一点
            h = h_prev * (1.0 + GROWTH * (1.0 - r))
        elif level == LEVEL_HARD:
            h = h_prev * HARD_SHRINK
        else:
            h = h_prev * AGAIN_SHRINK
        h = _clamp(h, H_MIN, H_MAX)

        # reps 沿用 SM-2 的语义（连续答对次数）：FSRS 和 BKT 也都保留它，
        # 前端的「连对 N 次」统计和 due_list 的档位排序就不因为换算法而变样。
        reps_prev = max(0, _num(prev, 'reps', 0, int))
        if level == LEVEL_GOOD:
            reps = reps_prev + 1
        elif level == LEVEL_AGAIN:
            reps = 0
        else:
            reps = reps_prev

        iv = self.interval_for(h)
        return self._rec(level, iv, h, reps, self.next_at(iv, day), day)

    def _today(self):
        from .base import today_str
        return today_str()
