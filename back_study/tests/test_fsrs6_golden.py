# -*- coding: utf-8 -*-
"""FSRS-6 的**黄金值快照** —— 锁死与 py-fsrs v6.3.3 对照过的公式行为。

golden 值的来源：按 FSRS-6 公式手算 + 升级当天（2026-11-15）的数值冒烟
（见 git 历史里本轮的验证脚本）。改权重或改公式时这些测试会红 ——
**红是提醒你去对拍 py-fsrs，不是让你顺手改 golden**。

锁的五个点：
1. retention=0.9 时 k 恒等于 1（I == S 的存储兼容性恒等式，见 fsrs.py docstring）
2. 首次复习的 D0/S0 数值（指数式初始难度，FSRS-5/6 的新公式）
3. 同日复习「只涨不跌」（w17/w18/w19 分支）
4. Again 的同日上界 min(·, S/e^(w17·w18))
5. 个性化权重 w 的注入与区间校验（fit-fsrs 的接线契约）
"""
import pytest

from algo.fsrs import FSRS

# py-fsrs v6.3.3 的默认 21 权重（algo/fsrs.py 同源，这里再抄一份做交叉锁：
# 若有人误改了 fsrs.py 的 W 而没对照上游，这里会红）
EXPECTED_W = (0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
              1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483,
              0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542)


def test_default_weights_match_pyfsrs():
    assert FSRS.W == EXPECTED_W


def test_k_identity_at_r09():
    """r=0.9 → interval_for(S) == S 且 stability_of(I) == I（浮点容差内）。

    这是「ef/interval 列复用」这套存储妥协的根基：反解不对，
    FSRS-4.5 时代的旧进度一切库就会整体漂移。
    """
    f = FSRS()
    assert abs(f._k() - 1.0) < 1e-9
    for s in (0.5, 2.3065, 10.0, 365.0):
        assert abs(f.interval_for(s) - s) <= 1          # round 的 ±0.5
        assert abs(f.stability_of(s) - s) < 1e-6


def test_retrievability_shape():
    """R(0)=1；R(S)=0.9（构造性保证）；R 随 t 单调下降。"""
    f = FSRS()
    s = 10.0
    assert f.retrievability(0, s) == 1.0
    assert abs(f.retrievability(s, s) - 0.9) < 1e-9
    assert f.retrievability(1, s) > f.retrievability(5, s) > f.retrievability(30, s)


def test_first_review_golden():
    """首复习 Good：D0(3)=w4-e^(2·w5)+1≈2.119，S0(3)=w2=2.3065 → iv=2。"""
    f = FSRS()
    rec = f.schedule(None, 3, today='2026-11-15')
    assert rec['interval'] == 2
    assert rec['ef'] == pytest.approx(2.119, abs=0.01)
    assert rec['nextAt'] == '2026-11-17'
    assert rec['reps'] == 1


def test_first_review_again_gives_min_interval():
    rec = FSRS().schedule(None, 1, today='2026-11-15')
    assert rec['interval'] == 1
    assert rec['reps'] == 0


def test_same_day_recall_no_shrink():
    """同日复习（t=0）：记忆稳定性**绝不下降**（增长因子 max(·,1)）。

    FSRS-4.5 没有这个分支；FSRS-6 的 w17/w18/w19 专门管它。
    """
    f = FSRS()
    rec0 = f.schedule(None, 3, today='2026-11-15')       # S≈2.3065, iv=2
    # 同一天再标一次「会」：updatedAt 相同 → t=0
    rec1 = f.schedule(rec0, 3, today='2026-11-15')
    assert rec1['interval'] >= rec0['interval'], (rec0, rec1)


def test_same_day_again_drops_to_short():
    """同日 Again：走遗忘公式的同日上界，间隔回到 1 天。"""
    f = FSRS()
    rec0 = f.schedule(None, 3, today='2026-11-15')
    rec1 = f.schedule(rec0, 1, today='2026-11-15')
    assert rec1['interval'] == 1
    assert rec1['reps'] == 0


def test_lapse_then_relearn():
    """隔了很多天标「不会」→ 稳定性掉到低位但不为 0；再答对会涨回来。"""
    f = FSRS()
    rec = f.schedule(None, 3, today='2026-11-01')
    rec = f.schedule(rec, 3, today='2026-11-08')
    s_before = f.stability_of(rec['interval'])
    rec_fail = f.schedule(rec, 1, today='2026-12-08')    # 一个月后忘了
    assert rec_fail['interval'] < rec['interval']
    assert rec_fail['interval'] >= 1
    rec_back = f.schedule(rec_fail, 3, today='2026-12-09')
    assert rec_back['interval'] >= 1


def test_custom_weights_injection_and_bounds():
    """fit-fsrs 的接线契约：w 生效、区间校验抛 ValueError、单例不被污染。"""
    f = FSRS()
    w = list(EXPECTED_W)
    w[2] = 4.0                                # S0(Good) 调大
    rec = f.schedule(None, 3, w=w)
    assert rec['interval'] == 4               # round(4.0)
    assert f.W == EXPECTED_W                  # 共享单例没被改（线程安全底线）
    bad = list(EXPECTED_W)
    bad[4] = 50.0                             # D0 基准越界（合法上界 10）
    with pytest.raises(ValueError):
        f.schedule(None, 3, w=bad)
    wrong_len = list(EXPECTED_W)[:-1]
    with pytest.raises(ValueError):
        f.schedule(None, 3, w=wrong_len)


def test_retention_change_flips_interval_direction():
    """目标保持率调低（容忍更多遗忘）→ 间隔**更长**（同一个 S 下）。

    方向曾写反（4.5 时代注释说「调低→更短」），pytest 数学断言抓出来改正。
    """
    s = 10.0
    loose = FSRS(retention=0.85).interval_for(s)
    strict = FSRS(retention=0.95).interval_for(s)
    assert loose > strict


# ---------- fsrs_fit（SPSA+Adam 拟合） ----------
def test_fit_gated_when_data_insufficient():
    """数据不足 400 条 → 拒绝拟合并如实说明（宁缺毋滥）。"""
    import algo.fsrs_fit as fitmod
    seqs = [[(-1, 3, 1.0), (1, 3, 1.0), (3, 3, 1.0)]] * 5     # 10 条非首复习
    w, info = fitmod.fit(seqs)
    assert info['fitted'] is False
    assert '不足' in info['reason']
    assert list(w) == list(FSRS.W)                            # 回默认权重


def test_fit_single_class_rejected():
    """全对一个答案 → 拟合无意义，拒绝。"""
    import algo.fsrs_fit as fitmod
    seqs = [[(-1, 3, 1.0)] + [(2, 3, 1.0)] * 30] * 20        # 600 条全「记得」
    w, info = fitmod.fit(seqs, iters=5)
    assert info['fitted'] is False


def test_fit_recovers_direction_on_synthetic():
    """用「偏移真值」的合成学生造数据，拟合出的权重应朝真值方向移动。

    这是对 fsrs-optimizer 思路的端到端验证：损失（BCE+正则）下降、
    参数被数据拉向真值（保守但有方向 —— 正则存在的意义就是数据少时
    别乱动）。
    """
    import random

    import algo.fsrs_fit as fitmod
    tw = list(FSRS.W)
    for i in (0, 1, 2):
        tw[i] *= 0.65                                        # 初始稳定性偏低的学生
    proto = FSRS()
    proto.set_weights(tw)
    rng = random.Random(11)
    seqs = []
    for _card in range(150):
        seq = []
        s = d = None
        for rev in range(rng.randint(4, 12)):
            if rev == 0:
                g = rng.choice([3, 3, 3, 2, 1])
                d = proto._init_difficulty(g)
                s = proto._init_stability(g)
                seq.append((-1, g, 1.0 if g > 1 else 0.0))
                continue
            t = max(0, round(s * rng.uniform(0.2, 1.4)))
            r = proto.retrievability(t, s)
            y = 1.0 if rng.random() < r else 0.0
            g = 3 if y == 1.0 else 1
            seq.append((t, g, y))
            d = proto._next_difficulty(d, g)
            s = proto._next_stability(d, s, r, g, t=t)
        seqs.append(seq)
    w, info = fitmod.fit(seqs, iters=120)
    assert info['fitted'] is True
    assert info['bceAfter'] <= info['bceBefore'] + 1e-3      # 损失至少不恶化
    # w2 应朝真值（1.499）方向移动，而不是留在默认值（2.3065）
    dist_before = abs(FSRS.W[2] - tw[2])
    dist_after = abs(w[2] - tw[2])
    assert dist_after < dist_before, (FSRS.W[2], w[2], tw[2])
