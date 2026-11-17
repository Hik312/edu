# -*- coding: utf-8 -*-
"""算法库工厂 —— 决定事件流 / 掌握度 / 参数存哪儿。

和 `store/` 工厂同一个套路：**切换只改配置，降级必须看得见**。

- 配置项 `ALGO_STORE`（env 优先，其次 `config.local.json`）：`json`（默认）| `pg`
- 选了 pg 但装不了 psycopg / 连不上 / 表没建 → **回退 json 照常服务**，
  但 `degraded()` 会写明原因，启动横幅要打出来。
  悄悄回退是最坏的结果：你以为事件在往 PG 写、其实在写文件，
  等要拿 PG 做分析时才发现库是空的。
"""

import json
import os
import threading

from .base import AlgoStore                     # 对外契约，新后端继承它
from .jsonfile import JsonAlgoStore             # 默认后端 + 降级目标

__all__ = ['AlgoStore', 'JsonAlgoStore', 'get', 'reset', 'status',
           'degraded', 'configured_name', 'pg_config', 'DEFAULT_NAME']

DEFAULT_NAME = 'json'

_current = None
#: 降级原因。None = 没降级。
_degraded = None
_init_lock = threading.Lock()     # 保护 get() 的单例构建（见下面的双检锁）

_BACK_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_LOCAL_CFG = os.path.join(_BACK_DIR, 'config.local.json')


def _load_local():
    try:
        with open(_LOCAL_CFG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def configured_name():
    return (os.environ.get('ALGO_STORE')
            or _load_local().get('ALGO_STORE')
            or DEFAULT_NAME)


def pg_config():
    """PG 连接参数。密码走环境变量 `PGPASSWORD` 或 config.local.json，
    **不要写在代码里**。"""
    cfg = _load_local().get('Postgres', {})
    return {
        'host': os.environ.get('PGHOST') or cfg.get('host', '127.0.0.1'),
        'port': int(os.environ.get('PGPORT') or cfg.get('port', 5432)),
        'user': os.environ.get('PGUSER') or cfg.get('user', 'postgres'),
        'password': os.environ.get('PGPASSWORD') or cfg.get('password', ''),
        'dbname': os.environ.get('PGDATABASE') or cfg.get('database', 'study_algo'),
    }


def _build():
    """造后端。只在这里选一次，之后不复探（换库要重启进程）。"""
    global _degraded
    name = str(configured_name()).strip().lower()

    if name in ('pg', 'postgres', 'postgresql'):
        try:
            from .pg import PgAlgoStore          # 延迟 import：没装 psycopg 也不影响默认路径
            s = PgAlgoStore(**pg_config())
            if s.ping():
                _degraded = None
                return s
            _degraded = 'ALGO_STORE=pg 但连不上 PostgreSQL（%s）→ 回退 json' % s.last_error
        except Exception as e:
            _degraded = 'ALGO_STORE=pg 但初始化失败（%s: %s）→ 回退 json' % (
                type(e).__name__, e)
    elif name != DEFAULT_NAME:
        # 配置写错了要吵出来，别悄悄当 json 用
        _degraded = 'ALGO_STORE=%r 不是已知后端（可用 json / pg）→ 回退 json' % name

    _degraded = _degraded if name != DEFAULT_NAME else None
    return JsonAlgoStore()


def get():
    global _current
    if _current is None:
        _current = _build()
    return _current


def degraded():
    """降级原因，None 表示没降级。挂到 /api/storage.degraded 那类地方给人看。"""
    if _current is None:
        get()
    return _degraded


def reset():
    """清掉单例，下次 `get()` 重新连。改了配置又不想重启时用。"""
    global _current, _degraded
    _current = None
    _degraded = None


def status():
    s = get()
    return {'backend': s.name, 'degraded': degraded()}
