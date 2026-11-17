# -*- coding: utf-8 -*-
"""算法层 —— 间隔重复 / 知识追踪算法都放这儿，要用就 `import algo`。

**这一层不依赖 core**（不 import db / store）：拿一个 dict 就能跑，不起服务、
不连库也能单测和调参。依赖方向是单向的 —— `core/db.py` 用 `algo`，反过来不行。

怎么用：

```python
import algo

algo.get().schedule(prev, level)      # 用当前默认算法算下一次复习
algo.get('fsrs').schedule(prev, level)  # 临时指定
algo.names()                            # 有哪些算法
```

换算法改配置，不用动代码（优先级和 `STORE` 一样）：

1. 环境变量 `ALGO=fsrs`
2. `back_study/config.local.json` 里的 `"ALGO": "fsrs"`
3. 都没有 → `sm2`

**写错的算法名会直接抛 ValueError，不会悄悄退回 sm2。** 配置拼错却假装成功，
比启动失败糟糕得多 —— 你以为在评估 FSRS，其实跑了三个月 SM-2。
"""

import json
import os

from .base import (Algo, LEVEL_AGAIN, LEVEL_HARD, LEVEL_GOOD,
                   REC_KEYS, today_str, add_days, diff_days)
from .sm2 import SM2
from .fsrs import FSRS
from .hlr import HLR
from .bkt import BKT, DEFAULT_PARAMS as BKT_DEFAULT_PARAMS, fit as bkt_fit

DEFAULT_NAME = 'sm2'

#: 名字 → 实例。实例是有状态的（FSRS 带 retention），注册时就造好，
#: 之后 `get()` 一直返回同一个对象，不要在请求路径上反复 new。
_REGISTRY = {
    'sm2': SM2(),
    'fsrs': FSRS(),
    'hlr': HLR(),
    'bkt': BKT(),
}

#: None = 还没解析过默认算法（惰性，避免在 import 阶段就去读文件）
_current = None

_BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_CFG = os.path.join(_BACK_DIR, 'config.local.json')


def register(algo, overwrite=False):
    """把新算法挂进注册表。自己写了算法就在包里 import 它、调这个函数。

    algo: Algo 的子类实例（不是类本身 —— 实例才能带 retention 这类参数）
    """
    if not isinstance(algo, Algo):
        raise TypeError('要注册 Algo 的实例，收到了 %r' % (algo,))
    if algo.name in _REGISTRY and not overwrite:
        raise ValueError('算法名 %r 已被占用' % algo.name)
    _REGISTRY[algo.name] = algo
    return algo


def names():
    """所有已注册算法的名字。"""
    return sorted(_REGISTRY.keys())


def describe_all():
    """给接口/文档用：每个算法一句话自我介绍。"""
    return [_REGISTRY[n].describe() for n in names()]


def _local_algo():
    """读 config.local.json 的 ALGO；文件不存在或没这个键就返回 None。"""
    try:
        with open(_LOCAL_CFG, 'r', encoding='utf-8') as f:
            return json.load(f).get('ALGO')
    except (OSError, ValueError):
        return None


def _resolve():
    """算出默认算法名。env > config.local.json > DEFAULT_NAME。"""
    name = os.environ.get('ALGO') or _local_algo() or DEFAULT_NAME
    name = str(name).strip().lower()
    if name not in _REGISTRY:
        raise ValueError(
            '算法 %r 没注册。可用的：%s' % (name, ', '.join(names())))
    return name


def get(name=None):
    """取算法实例。不传 name 就用默认算法（只解析一次，之后走缓存）。"""
    global _current
    if name is None:
        if _current is None:
            _current = _resolve()
        name = _current
    name = str(name).strip().lower()
    if name not in _REGISTRY:
        raise ValueError(
            '算法 %r 没注册。可用的：%s' % (name, ', '.join(names())))
    return _REGISTRY[name]


def set_default(name):
    """运行时切换默认算法（测试、A/B 实验用）。不影响配置文件。"""
    global _current
    if str(name).strip().lower() not in _REGISTRY:
        raise ValueError(
            '算法 %r 没注册。可用的：%s' % (name, ', '.join(names())))
    _current = str(name).strip().lower()
    return _REGISTRY[_current]


def reset():
    """清掉默认算法缓存，下次 `get()` 重新读配置。改了配置又不想重启时用。"""
    global _current
    _current = None


__all__ = ['Algo', 'SM2', 'FSRS', 'HLR', 'BKT', 'bkt_fit', 'BKT_DEFAULT_PARAMS',
           'get', 'set_default', 'register', 'names',
           'describe_all', 'reset', 'DEFAULT_NAME', 'REC_KEYS',
           'LEVEL_AGAIN', 'LEVEL_HARD', 'LEVEL_GOOD',
           'today_str', 'add_days', 'diff_days']
