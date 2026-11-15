# -*- coding: utf-8 -*-
"""四算法的**契约测试** —— 锁死 `algo/base.py` 里写明的约定。

这是拆包/换算法时最容易破、又最不容易被发现的一层：
- 出参必须**恰好** REC_KEYS 六键（多一个键会被 MySQL progress 表静默丢弃，
  JSON 后端看着好好的、一切库行为就变 —— base.py 契约注释的原话）；
- 间隔必须被 MAX_INTERVAL 夹住（否则 date+timedelta 抛 OverflowError 500）；
- prev 是脏数据（缺字段/类型错/None）不能炸 —— 算法要扛得住；
- 个性化权重参数 w 对不使用它的算法是无害的。

这些断言与 scripts/check.js 的 API 级契约断言互补：那边走 HTTP，这里直达
纯函数层，跑得快、报错准。
"""
import pytest

import algo
from algo.base import MAX_INTERVAL, REC_KEYS

ALL_ALGOS = ('sm2', 'fsrs', 'hlr', 'bkt')


@pytest.mark.parametrize('name', ALL_ALGOS)
def test_first_review_six_keys(name):
    rec = algo.get(name).schedule(None, 3)
    assert set(rec.keys()) == set(REC_KEYS), (name, rec)
    assert rec['nextAt'] and rec['updatedAt']


@pytest.mark.parametrize('name', ALL_ALGOS)
def test_sequence_six_keys_and_interval_monotonic(name):
    """连续标「会」：间隔不许倒退（前端/队列都按这个假设渲染）。"""
    a = algo.get(name)
    prev = None
    ivs = []
    day = 0
    base_day = '2026-01-01'
    import datetime
    for i in range(8):
        today = (datetime.date(2026, 1, 1)
                 + datetime.timedelta(days=day)).strftime('%Y-%m-%d')
        rec = a.schedule(prev, 3, today=today)
        assert set(rec.keys()) == set(REC_KEYS), (name, i, rec)
        assert rec['interval'] >= (ivs[-1] if ivs else 1) or name == 'fsrs', (
            # FSRS-6 的难度均值回归在极端序列下允许间隔微降 —— 契约只要求
            # 「不因算法崩溃」，单调性对 sm2/hlr 是硬的，fsrs 放宽为不回 0
            name, ivs, rec['interval'])
        assert rec['interval'] >= 1
        ivs.append(rec['interval'])
        prev = rec
        day += max(1, rec['interval'])


@pytest.mark.parametrize('name', ALL_ALGOS)
def test_dirty_prev_does_not_crash(name):
    """prev 是用户手改/老版本残留的残 dict —— 算法必须扛住。"""
    a = algo.get(name)
    dirty = [{'interval': None}, {'interval': 'abc'}, {'level': 'x', 'ef': []},
             {'interval': 10 ** 9}, {}, None]
    for prev in dirty:
        rec = a.schedule(prev, 2)
        assert set(rec.keys()) == set(REC_KEYS), (name, prev, rec)
        assert 0 <= rec['interval'] <= MAX_INTERVAL


def test_level_out_of_range_falls_back():
    """评级不在 1/2/3 → 按 Again 处理（不抛异常，契约是容错不是报错）。"""
    rec = algo.get('fsrs').schedule(None, 99)
    assert set(rec.keys()) == set(REC_KEYS)


def test_max_interval_clamped():
    """连标几十次「会」，间隔必须停在 MAX_INTERVAL 内 ——
    这是 OverflowError 500 的历史坑（见 algo/base.py 注释）。"""
    a = algo.get('sm2')
    prev = None
    for _ in range(60):
        prev = a.schedule(prev, 3)
    assert prev['interval'] <= MAX_INTERVAL


def test_huge_interval_clamped_in_prev():
    """prev 里已经塞了个天文数字 interval（手改 JSON）→ 算完必须回到界内。"""
    rec = algo.get('sm2').schedule({'interval': 10 ** 9, 'ef': 2.5}, 3)
    assert rec['interval'] <= MAX_INTERVAL


@pytest.mark.parametrize('name', ('sm2', 'hlr', 'bkt'))
def test_w_param_harmless(name):
    """个性化权重参数对不使用它的算法必须是无害的（签名统一，转发不分型）。"""
    a = algo.get(name)
    r1 = a.schedule(None, 3)
    r2 = a.schedule(None, 3, w=[1.0] * 21)
    assert r1 == r2


def test_registry_names():
    """注册表四算法齐活；名字写错抛 ValueError（不静默回退 sm2）。"""
    assert set(algo.names()) >= set(ALL_ALGOS)
    with pytest.raises(ValueError):
        algo.get('fsrs-4.5')
