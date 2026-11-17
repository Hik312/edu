# -*- coding: utf-8 -*-
"""评测层的单元测试 —— 指标数学 + srs-benchmark 口径对齐。"""
import math

import pytest

from algo import eval as ev


# ---------- 基础指标 ----------
def test_log_loss_known_values():
    # 全对全信 → 0（p=1.0 被 EPS 截断，残差 ~1e-6）；对半瞎猜 → ln2
    assert ev.log_loss([(0.5, 1), (0.5, 0)]) == pytest.approx(math.log(2), abs=1e-9)
    assert ev.log_loss([(1.0, 1)]) == pytest.approx(0.0, abs=1e-5)
    assert ev.log_loss([]) is None


def test_auc_extremes():
    assert ev.auc([(0.9, 1), (0.1, 0)]) == 1.0
    assert ev.auc([(0.1, 1), (0.9, 0)]) == 0.0
    assert ev.auc([(0.5, 1), (0.5, 0)]) == 0.5
    assert ev.auc([(0.5, 1)]) is None          # 只有一类 → 无法定义


def test_calibration_bins():
    out = ev.calibration([(0.9, 1), (0.1, 0), (0.85, 1)], bins=5)
    assert out and all({'bin', 'n', 'predicted', 'actual'} == set(x) for x in out)
    hi = out[-1]
    assert hi['n'] == 2 and hi['actual'] == 1.0


# ---------- srs-benchmark 口径 ----------
def test_bin_grid_log_lattice():
    # 对数网格取整公式（数值取自 srs-benchmark）：2.48·2.57^k
    assert ev._bin_grid(0, 2.48, 2.57) == 0
    assert ev._bin_grid(-3, 2.48, 2.57) == 0
    v1 = ev._bin_grid(1, 2.48, 2.57)           # k=0 → round(2.48)
    assert v1 == 2
    v2 = ev._bin_grid(3, 2.48, 2.57)           # k=1 → round(2.48·2.57)=round(6.37)
    assert v2 == 6


def test_rmse_bins_weighted():
    """同箱系统偏差按箱内样本数加权。"""
    # 两箱各 2 样本：pred 0.9/actual 1.0（差 0.1）、pred 0.2/actual 0.0（差 0.2）
    pairs = [(0.9, 1, 5, 3, 0), (0.9, 1, 5, 3, 0),
             (0.2, 0, 30, 3, 1), (0.2, 0, 30, 3, 1)]
    expected = math.sqrt((2 * 0.1 ** 2 + 2 * 0.2 ** 2) / 4)
    assert ev.rmse_bins(pairs) == pytest.approx(expected, abs=1e-9)
    # 大箱权重压过小箱：第三条样本自成一箱（特征不同）
    pairs2 = pairs + [(0.5, 0, 300, 10, 4)]
    # 大箱差 0.5 但只占 1/5 权重
    expected2 = math.sqrt((2 * 0.1 ** 2 + 2 * 0.2 ** 2 + 1 * 0.5 ** 2) / 5)
    assert ev.rmse_bins(pairs2) == pytest.approx(expected2, abs=1e-9)
    assert ev.rmse_bins([]) is None


def test_rmse_bins_missing_features():
    """计数器缺失（None）的轴全部并箱；提供了的特征轴照常分箱。

    dt=5 与 dt=30 落不同格（对数网格），两箱各自的偏差 0.1 / 0.2：
    RMSE = sqrt((0.1² + 0.2²)/2) ≈ 0.158。
    """
    pairs = [(0.9, 1, 5), (0.2, 0, 30)]
    got = ev.rmse_bins(pairs)
    assert got == pytest.approx(math.sqrt((0.1 ** 2 + 0.2 ** 2) / 2), abs=1e-9)
    # 完全不给特征（全 None）→ 全部落同一箱，量的是整体偏差
    pairs2 = [(0.9, 1), (0.2, 0)]
    got2 = ev.rmse_bins(pairs2)
    assert got2 == pytest.approx(math.sqrt(0.05 ** 2), abs=1e-9)


# ---------- evaluate / compare 全链路 ----------
def test_evaluate_synthetic_log():
    """evaluate() 接真实 log 的口径：带 prev/t/correct/计数的条目。

    prev 状态用 FSRS 自己回放出来（与 scripts/eval_real.py 的做法一致）。
    """
    import datetime

    from algo.fsrs import FSRS
    algo_inst = FSRS()
    log = []
    dates = ['2026-11-01', '2026-11-03', '2026-11-10', '2026-12-10', '2026-12-12']
    levels = [3, 3, 3, 1, 3]
    prev = None
    n_rev, lapses = 0, 0
    for i, level in enumerate(levels):
        at = dates[i]
        if i > 0:
            t = (datetime.date.fromisoformat(at)
                 - datetime.date.fromisoformat(dates[i - 1])).days
            p = ev.predict('fsrs', prev, t)
            assert p is not None
            log.append({'prev': prev, 't': t,
                        'correct': 0 if level == 1 else 1, 'level': level,
                        'nReviews': n_rev, 'nLapses': lapses})
            if level == 1:
                lapses += 1
        prev = algo_inst.schedule(prev, level, today=at)
        n_rev += 1
    out = ev.evaluate('fsrs', log)
    assert out['predictsRetention'] is True
    assert out['nScored'] == len(log)            # log 本身已不含首复习（构造时跳过）
    assert 0 <= out['rmseBins'] <= 1
    assert out['logLoss'] is not None
    # SM-2 不做概率预测 → nScored=0，各指标为 None（能力边界的如实呈现）
    out2 = ev.evaluate('sm2', log)
    assert out2['predictsRetention'] is False
    assert out2['logLoss'] is None


def test_compare_smoke():
    """对拍管线：同一 seed 下各算法都出全套指标。"""
    data = ev.compare(['sm2', 'fsrs'], n_cards=20, horizon=90, seed=1)
    assert set(data) == {'sm2', 'fsrs'}
    for m in data.values():
        for k in ('totalReviews', 'efficiency', 'finalRetention',
                  'logLoss', 'auc', 'rmseBins'):
            assert k in m
    assert data['sm2']['logLoss'] is None       # 能力边界


def test_report_table_render():
    text = ev.report(['sm2', 'fsrs'], n_cards=15, horizon=60, seed=2)
    assert '算法' in text and 'RMSE(bins)' in text
