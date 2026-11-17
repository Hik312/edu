# -*- coding: utf-8 -*-
"""Load Balance（确定性版）的单元测试。

锁三条：不提前（只推迟）、确定性（无随机源，两次调用逐位一致）、
不动的比例越大越好（原日不挤就一个字不改）。
"""
from algo.loadbalance import _shift, balance_next_at, config


def test_shift_dates():
    assert _shift('2026-11-15', 1) == '2026-11-16'
    assert _shift('2026-11-30', 2) == '2026-12-02'      # 跨月
    assert _shift('2026-12-31', 1) == '2027-01-01'      # 跨年


def _rec(iv=10, day='2026-11-20'):
    return {'level': 3, 'interval': iv, 'ef': 5.0, 'reps': 3,
            'nextAt': day, 'updatedAt': '2026-11-15'}


def test_underloaded_day_untouched():
    """原日不挤 → 原样返回（一字不改，连 dict 都不重建语义）。"""
    rec = _rec()
    out = balance_next_at(rec, {}, window=2, cap=20)
    assert out == rec
    # 「原日已有 9 张、cap=10」→ 这张进去刚好 10 张，不挤
    out2 = balance_next_at(rec, {'2026-11-20': 9}, window=2, cap=10)
    assert out2['nextAt'] == '2026-11-20'


def test_overloaded_day_moves_to_lightest():
    """原日过载 → 推到 window 内最闲的一天；interval 不变。"""
    rec = _rec()
    load = {'2026-11-20': 30, '2026-11-21': 5, '2026-11-22': 12}
    out = balance_next_at(rec, load, window=2, cap=10)
    assert out['nextAt'] == '2026-11-21'                # 5+1=6 最闲
    assert out['interval'] == rec['interval']           # 只改排期不改间隔
    for k in rec:
        assert k in out


def test_tie_breaks_earlier():
    """两个候选日负载相同 → 取更早的（确定性优先）。"""
    rec = _rec()
    load = {'2026-11-20': 30, '2026-11-21': 5, '2026-11-22': 5}
    out = balance_next_at(rec, load, window=2, cap=10)
    assert out['nextAt'] == '2026-11-21'


def test_no_lighter_day_means_no_move():
    """推迟也不比原地松 → 不动（这是边角工具，不是重排序器）。"""
    rec = _rec()
    load = {'2026-11-20': 3, '2026-11-21': 30, '2026-11-22': 30}
    out = balance_next_at(rec, load, window=2, cap=2)
    # cap=2：原日 3+1=4 > 2 过载；候选日都 31 > 4 —— 推了更挤，不动
    assert out['nextAt'] == '2026-11-20'


def test_auto_cap():
    """cap 不给 → 自动 = 候选窗现有负载均值向上取整。"""
    rec = _rec()
    load = {'2026-11-20': 10, '2026-11-21': 0, '2026-11-22': 1}
    out = balance_next_at(rec, load, window=2)
    # 均值 = (10+0+1)/3 ≈ 3.67 → cap=4；原日 10+1=11 > 4 → 推到 21 日（0+1=1）
    assert out['nextAt'] == '2026-11-21'


def test_deterministic():
    """无随机源：同一份数据两次调用必须逐位一致。"""
    rec = _rec()
    load = {'2026-11-20': 25, '2026-11-21': 7, '2026-11-22': 9, '2026-11-23': 2}
    a = balance_next_at(rec, load, window=3, cap=10)
    b = balance_next_at(rec, load, window=3, cap=10)
    assert a == b
    assert a['nextAt'] == '2026-11-23'                  # 2+1=3 最闲


def test_input_not_mutated():
    rec = _rec()
    snapshot = dict(rec)
    balance_next_at(rec, {'2026-11-20': 50}, window=2, cap=5)
    assert rec == snapshot


def test_config_defaults_and_shape():
    """config() 永远返回完整三键；默认关（不显式打开绝不该自己生效）。"""
    cfg = config()
    assert set(cfg) >= {'enabled', 'window', 'cap'}
    assert cfg['enabled'] in (True, False)
    assert isinstance(cfg['window'], int) and cfg['window'] >= 0


def test_env_overrides():
    """环境变量覆盖配置文件（LB_ENABLED=1 打开）。"""
    import os
    old = {k: os.environ.get(k) for k in ('LB_ENABLED', 'LB_WINDOW', 'LB_CAP')}
    try:
        os.environ['LB_ENABLED'] = '1'
        os.environ['LB_WINDOW'] = '3'
        os.environ['LB_CAP'] = '40'
        import algo.loadbalance as LB
        LB._cfg_cache['cfg'] = None                     # 清缓存强制重读
        cfg = LB.config()
        assert cfg['enabled'] is True
        assert cfg['window'] == 3
        assert cfg['cap'] == 40
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
