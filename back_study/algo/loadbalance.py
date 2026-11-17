# -*- coding: utf-8 -*-
"""Load Balance —— 把到期卡分散到相邻的闲日，避免「今天 300 张、明天 0 张」。

创意来源：fsrs4anki-helper 的 Load Balance（把同日到期卡摊到前后几天）。
那个插件本身对 Anki 用户价值极大，但几乎没有平台抄 —— 因为标准实现给
≥2.5 天的间隔加 ±5%/10%/15% 的**随机**抖动，而本项目的 check.js 要拿
json / mysql 两种存储**逐位比对**到期队列，随机性会毁掉这份对照。

所以这里是**确定性版**：

- 只**推迟**（nextAt → nextAt+1..window），绝不提前 —— 提前等于偷偷缩短
  间隔，违背主调度算法的稳定性结论。排多远是算法的职责，具体排哪天是
  本模块的职责，两者不许互相越界。
- 候选日里挑**负载最小**的；平局按日期先后（不引入任何随机源，
  同一份数据两次调用结果完全一致）。
- 只在「原计划日已过载」时才动，不动的比例越大越好 —— 这是摊平
  尖峰的边角工具，不是重排序器。

配置（env > config.local.json > 默认，与 ALGO/STORE 同一套优先级）：

    "LoadBalance": {"enabled": true, "window": 2, "cap": 40}
    # enabled  默认 false —— 改变了排期行为，必须显式打开
    # window   允许推迟的天数范围（±0 = 关闭，无意义）
    # cap      单日上限；null = 自动（当前负载 + window 内日均，向上取整）
"""

import json
import os
import time

#: 默认配置。enabled=false：改变排期行为的事必须显式打开，跟 ALGO 配错
#: 宁可抛错不静默回退是同一条哲学的两面。
_DEFAULTS = {'enabled': False, 'window': 2, 'cap': None}

_BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_CFG = os.path.join(_BACK_DIR, 'config.local.json')

#: 配置缓存。改 config.local.json 要等 60s 才生效 —— 对一个排期开关足够了。
_cfg_cache = {'at': 0.0, 'cfg': None}
_CFG_TTL = 60.0


def _num(v, default, lo, hi):
    try:
        x = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


def config():
    """读 Load Balance 配置（带 60s 缓存）。永远返回一份完整 dict。"""
    now = time.time()
    if _cfg_cache['cfg'] is not None and now - _cfg_cache['at'] < _CFG_TTL:
        return dict(_cfg_cache['cfg'])
    cfg = dict(_DEFAULTS)
    # 1) config.local.json 的 "LoadBalance" 段
    try:
        with open(_LOCAL_CFG, 'r', encoding='utf-8') as f:
            local = json.load(f).get('LoadBalance') or {}
        if isinstance(local, dict):
            cfg['enabled'] = bool(local.get('enabled', cfg['enabled']))
            if local.get('window') is not None:
                cfg['window'] = _num(local.get('window'), cfg['window'], 0, 14)
            if local.get('cap') is not None:
                cfg['cap'] = _num(local.get('cap'), None, 1, 100000) \
                    if str(local.get('cap')).strip() else None
    except (OSError, ValueError):
        pass                                    # 没配 / 坏 JSON → 纯默认
    # 2) 环境变量覆盖（LB_ENABLED=1 / LB_WINDOW=3 / LB_CAP=40）
    env = os.environ.get('LB_ENABLED')
    if env is not None:
        cfg['enabled'] = env.strip().lower() in ('1', 'true', 'yes', 'on')
    if os.environ.get('LB_WINDOW') is not None:
        cfg['window'] = _num(os.environ.get('LB_WINDOW'), cfg['window'], 0, 14)
    if os.environ.get('LB_CAP'):
        cfg['cap'] = _num(os.environ.get('LB_CAP'), cfg['cap'], 1, 100000)
    _cfg_cache['at'] = now
    _cfg_cache['cfg'] = cfg
    return dict(cfg)


def _shift(day, n):
    """"YYYY-MM-DD" + n 天 → "YYYY-MM-DD"。stdlib 日期，不 import db。"""
    from datetime import date, timedelta
    y, m, d = [int(x) for x in day.split('-')]
    return (date(y, m, d) + timedelta(days=n)).strftime('%Y-%m-%d')


def balance_next_at(rec, day_load, window=2, cap=None, max_interval=None):
    """把过载日的 nextAt 推到 window 内最闲的一天。

    rec      : 主调度算法的 6 键输出（会读 nextAt / interval；**不改 interval**
               —— 隔多少天是算法的结论，这里只改「具体哪天」）。
    day_load : {date_str: count}，该用户**其它卡**的 nextAt 分布
               （待标记的这张自己不在里面 —— 它马上会占一天）。
    cap      : 单日上限。None = 自动：window+1 个候选日（含原日）的
               现有负载 + 本次 +1，向上取整 —— 即「这批里最挤的一天
               也不过载」。 显式给数（如 40）则用它。
    max_interval : 若传入，推迟不会把 nextAt 推过「原间隔+window」对应的
               排期语义（目前仅用于防推过 MAX_INTERVAL 边界，一般不触发）。

    返回新的 rec dict（六键不变，nextAt 可能被推迟；输入不被修改）。
    """
    if not rec or window <= 0:
        return rec
    nxt = rec.get('nextAt')
    if not isinstance(nxt, str) or len(nxt) != 10:
        return rec
    load = dict(day_load or {})
    # cap 自动值：候选窗（原日 + window 个推迟日）的现有负载均值向上取整
    if cap is None:
        window_days = [_shift(nxt, i) for i in range(window + 1)]
        cur = sum(load.get(d, 0) for d in window_days) / max(1, len(window_days))
        cap = max(1, int(cur) + 1)
    if load.get(nxt, 0) + 1 <= cap:
        return rec                              # 原日本来就不挤，一个字不动
    # 找 window 内最闲的一天（推迟方向）；平局取最早 —— 确定性优先
    best_day, best_load = None, None
    for i in range(1, window + 1):
        d = _shift(nxt, i)
        if max_interval is not None and _diff_days(nxt, d) > max_interval:
            break
        l = load.get(d, 0) + 1                  # 这张卡落进去之后该日的负载
        if best_load is None or l < best_load:
            best_day, best_load = d, l
    if best_day is None or best_load >= load.get(nxt, 0) + 1:
        return rec                              # 推了也不比留原地松，别动
    out = dict(rec)
    out['nextAt'] = best_day
    return out


def _diff_days(a, b):
    from datetime import date
    ya, ma, da = [int(x) for x in a.split('-')]
    yb, mb, db_ = [int(x) for x in b.split('-')]
    return (date(yb, mb, db_) - date(ya, ma, da)).days
