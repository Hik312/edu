# -*- coding: utf-8 -*-
"""BKT —— 贝叶斯知识追踪（Bayesian Knowledge Tracing）。

**它和 SM-2 / FSRS 不是替换关系，是回答不同的问题**：

- SM-2 / FSRS 回答「下次什么时候看」→ 输出一个**间隔**
- BKT  回答「到底掌握没有」→ 输出一个**掌握度概率 p ∈ [0,1]**

所以正确答案是叠着用：BKT 定优先级（先学没掌握的），SM-2 定时间（掌握的少看）。
这里为了能塞进统一的 `schedule()` 契约，让 BKT 也输出间隔 —— 用 p 去驱动：
掌握度高就拉长，不会就明天再来。

## 模型本体（四行）

四个参数，每个都是人能解释的概率：

| 参数 | 含义 | 典型值 |
|---|---|---|
| `p_init`    | 没学过之前的先验掌握度 | 0.1 ~ 0.3 |
| `p_transit` | 练一次**从不会变会**的概率 | 0.05 ~ 0.2 |
| `p_slip`    | 会但答错（手滑） | 0.05 ~ 0.2 |
| `p_guess`   | 不会但蒙对 | 0.1 ~ 0.3 |

答对后：p' = p(1−slip) / [p(1−slip) + (1−p)·guess]
答错后：p' = p·slip   / [p·slip   + (1−p)(1−guess)]
然后  ：p ← p' + (1−p')·transit        # 练习本身也会让人学会

就这四行。**真正值钱的不是这四行，是 fit()** —— 用你自己的答题记录把这四个
数拟合出来。「我在自己学生的真实数据上拟合出 slip=0.07」这才叫自己的算法，
抄默认参数谁都会。

## 一个绕不开的前提

BKT 只吃**二值**（对 / 错）。而系统的评级是三档（不会 / 模糊 / 会）。
这里的取舍：**「模糊」按答错处理**。理由是宁可多复习、不要漏掉没掌握的 ——
把模糊当成学会，后果是这张卡被排到很久以后，而学生其实不会。

## 数据门槛

`needs` 里写了。低于门槛别拟合：20 条记录去拟合四个参数，拟合出来的数
能完美贴合这 20 条、但换一天预测就是瞎猜 —— 这是过拟合，不是模型。
"""

from .base import Algo, LEVEL_GOOD, _num

#: 默认参数。这是文献里常见的量级，不是从你的数据里算出来的 ——
#: 用 fit() 拿到自己的参数之前，它只是个能跑起来的占位。
DEFAULT_PARAMS = {
    'p_init': 0.25,
    'p_transit': 0.10,
    'p_slip': 0.10,
    'p_guess': 0.20,
}

#: 拟合下限。少于这个数就直接返回默认参数，并在返回值里说明原因。
#: 20 条记录拟合 4 个参数 ≈ 每条记录摊 0.2 个参数，必过拟合。
MIN_SEQS = 8        # 至少这么多个知识点序列
MIN_STEPS = 30      # 至少这么多条答题记录


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)


def to_correct(level):
    """三档评级 → 二值。只有「会」算对，模糊算错（理由见模块文档）。"""
    return 1 if int(level) == LEVEL_GOOD else 0


def step(p, correct, params=None):
    """一次练习后的掌握度。这是 BKT 的全部。"""
    q = params or DEFAULT_PARAMS
    slip = _clamp(float(q.get('p_slip', DEFAULT_PARAMS['p_slip'])))
    guess = _clamp(float(q.get('p_guess', DEFAULT_PARAMS['p_guess'])))
    transit = _clamp(float(q.get('p_transit', DEFAULT_PARAMS['p_transit'])))
    p = _clamp(float(p))

    # P(答对) —— 两条路：真会且没手滑，或者不会但蒙对了
    p_correct = p * (1.0 - slip) + (1.0 - p) * guess
    p_correct = min(max(p_correct, 1e-9), 1.0 - 1e-9)

    if correct:
        post = p * (1.0 - slip) / p_correct
    else:
        post = p * slip / (1.0 - p_correct)

    # 练一次本身也会让人学会 —— 这一项是 BKT 区别于「单纯计数」的地方
    return _clamp(post + (1.0 - post) * transit)


def replay(seq, params=None, p0=None):
    """把一串答题记录跑一遍，返回每一步之后的掌握度。

    seq: 由 0/1 组成的列表（1=答对）
    返回: 长度和 seq 相同的列表，第 i 项是做完第 i 次练习之后的 p
    """
    q = params or DEFAULT_PARAMS
    p = float(q.get('p_init', DEFAULT_PARAMS['p_init'])) if p0 is None else float(p0)
    out = []
    for c in seq:
        p = step(p, 1 if c else 0, q)
        out.append(p)
    return out


def predict(seq, params=None):
    """最终掌握度。空序列 = 先验。"""
    q = params or DEFAULT_PARAMS
    if not seq:
        return _clamp(float(q.get('p_init', DEFAULT_PARAMS['p_init'])))
    return replay(seq, q)[-1]


# ---------------- 拟合 ----------------
def log_likelihood(seq, params=None):
    """这串答题记录在给定参数下出现的对数似然。

    拟合的目标就是把它最大化。每一步用「这一步答对/答错的概率」取 log 累加，
    然后用**预测到的 p** 去更新状态（不是用真实答案反推）—— 这是标准的
    BKT 似然，别把「预测」和「事后更新」混着写，那样会高估模型的预测能力。
    """
    import math

    q = params or DEFAULT_PARAMS
    slip = _clamp(float(q.get('p_slip', DEFAULT_PARAMS['p_slip'])))
    guess = _clamp(float(q.get('p_guess', DEFAULT_PARAMS['p_guess'])))
    # transit 不在这里单独取：状态更新走 step()，它内部会带上 transit。
    # 只有「答对/答错的概率」这一项需要 slip 和 guess。
    p = _clamp(float(q.get('p_init', DEFAULT_PARAMS['p_init'])))

    ll = 0.0
    for c in seq:
        pc = p * (1.0 - slip) + (1.0 - p) * guess
        pc = min(max(pc, 1e-9), 1.0 - 1e-9)
        ll += math.log(pc) if c else math.log(1.0 - pc)
        p = step(p, 1 if c else 0, q)
    return ll


def _grid():
    """参数搜索网格。

    为什么用网格搜索而不是梯度下降：四个参数、都是 [0,1] 内的概率、
    量级已知，625 个组合在现代机器上不到一秒就跑完，而且**不会掉进局部最优**。
    梯度下降在这里是杀鸡用牛刀，还得引 numpy。
    """
    return {
        'p_init': (0.10, 0.20, 0.30, 0.40, 0.50),
        'p_transit': (0.05, 0.10, 0.15, 0.20, 0.30),
        'p_slip': (0.02, 0.05, 0.10, 0.15, 0.25),
        'p_guess': (0.05, 0.10, 0.20, 0.30, 0.40),
    }


def fit(seqs, grid=None):
    """从多条答题序列里拟合四个参数。

    seqs: `[[0,1,1,...], [1,0,...]]`，每个元素是一个知识点上的一串答题记录。
    返回: `(params, info)`。数据不够时返回默认参数，并在 info 里写明原因 ——
    **不要硬拟合**。给 5 条记录拟合出四个参数，得到的数能完美贴合这 5 条，
    但对第 6 条的预测是瞎猜。那时候「用默认参数」反而更准。
    """
    g = grid or _grid()
    seqs = [list(s) for s in (seqs or []) if s]
    n_seq, n_step = len(seqs), sum(len(s) for s in seqs)

    if n_seq < MIN_SEQS or n_step < MIN_STEPS:
        return dict(DEFAULT_PARAMS), {
            'fitted': False,
            'reason': '数据不够（需要至少 %d 个知识点 / %d 条记录，'
                      '现在 %d / %d）→ 用默认参数' % (MIN_SEQS, MIN_STEPS,
                                                      n_seq, n_step),
            'nSeq': n_seq, 'nStep': n_step,
        }

    best, best_ll = None, float('-inf')
    for pi in g['p_init']:
        for pt in g['p_transit']:
            for ps in g['p_slip']:
                for pg in g['p_guess']:
                    cand = {'p_init': pi, 'p_transit': pt,
                            'p_slip': ps, 'p_guess': pg}
                    ll = sum(log_likelihood(s, cand) for s in seqs)
                    if ll > best_ll:
                        best_ll, best = ll, cand

    return best, {'fitted': True, 'logLikelihood': round(best_ll, 4),
                  'nSeq': n_seq, 'nStep': n_step,
                  'gridSize': len(g['p_init']) * len(g['p_transit'])
                              * len(g['p_slip']) * len(g['p_guess'])}


def from_events(events):
    """事件流 → 答题序列。

    events: `[{'correct': 0/1, ...}, ...]`，按时间升序。
    这条转换放在这里而不是 core 里，是为了让 algo 包保持「拿 dict 就能跑」，
    不需要 import core —— 但代价是调用方得自己保证顺序。
    """
    return [1 if int(e.get('correct') or 0) else 0 for e in (events or [])]


class BKT(Algo):
    """把 BKT 塞进统一的调度契约：用掌握度 p 反推复习间隔。"""

    name = 'bkt'
    label = 'BKT 贝叶斯知识追踪'
    needs = '每人每知识点 5-10 次答题；拟合四参数需要 8 个知识点 / 30 条以上'
    ef_note = 'ef = 掌握度 p（0~1），不是难度因子'

    #: 掌握度到间隔的映射上限。p=1 时的间隔（天）。
    MAX_INTERVAL = 20

    def __init__(self, params=None):
        self.params = dict(DEFAULT_PARAMS)
        if params:
            self.params.update({k: v for k, v in params.items()
                                if k in DEFAULT_PARAMS})

    def interval_of(self, p):
        """掌握度 → 间隔（天）。

        p 高就拉长，但用平方压一下：p=0.5 时不是「一半的间隔」而是 5 天。
        直觉是「半会不会」最需要赶紧再看，而不是拖到中位间隔。
        p=0 → 1 天；p=0.5 → 6 天；p=0.8 → 13.8→14 天；p=1 → 21 天。
        """
        p = _clamp(float(p))
        return max(1, int(round(1 + self.MAX_INTERVAL * p * p)))

    def schedule(self, prev, level, today=None, w=None):  # w: 个性化权重参数，本算法不用，见 algo/base.py 契约
        # ★ ef 在 BKT 里是掌握度，但 prev 可能是 SM-2 留下来的（2.5 这种），
        #   也可能是 FSRS 的难度 D（1~10）。越界一律夹回 [0,1]，
        #   否则 p=2.5 会让后续所有计算失去意义，而且不报错。
        p_prev = _clamp(_num(prev, 'ef', self.params['p_init']))
        reps = max(0, int(_num(prev, 'reps', 0, int)))

        p = step(p_prev, to_correct(level), self.params)
        iv = self.interval_of(p)
        day = today or self._today()
        return self._rec(level, iv, p, reps + 1,
                         self.next_at(iv, day), day)

    def _today(self):
        from .base import today_str
        return today_str()
