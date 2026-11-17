# -*- coding: utf-8 -*-
"""缓存层 —— Redis 优先，没装就退回进程内存。

**为什么要有这一层**：BKT 算掌握度要把这个人的整条事件流重放一遍，而到期队列、
看板、AI 助手每次都要读。每次都重放 = 每次都扫全表。缓存住 `p_mastered` 之后，
只有真的产生了新事件才需要重算。

**为什么必须能降级**：这是**缓存**，不是存储。Redis 没装 / 没起 / 密码不对时，
服务的正确行为是「照常干活，只是慢一点」，而不是「起不来」。
所以这里和 `store/` / `algostore/` 一样：切不成功就退回内存，但要把原因
写进 `degraded()` 让启动横幅打出来 —— 悄悄降级会导致你以为缓存住了，
其实每次都在重算，而日志上一片安静。

内存降级的边界要清楚：**只在当前进程内有效，重启即失效，多进程之间不共享**。
所以它不是 Redis 的等价替代，只是「让你在没有 Redis 时也能开发和跑测试」。

配置（`back_study/config.local.json`）：
```json
"Redis": { "host": "127.0.0.1", "port": 6379, "password": "123456", "db": 0 }
```
env 也可以用：`REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` / `REDIS_DB`。
想彻底关掉 Redis：`"Redis": { "enabled": false }`。

用法：
```python
import cache
cache.get().set('bkt:p:u1:ai-agent', 0.83, ttl=600)
cache.get().get('bkt:p:u1:ai-agent')
```
"""

import json
import os
import threading
import time

__all__ = ['get', 'reset', 'status', 'degraded', 'enabled', 'PREFIX']

#: 所有 key 都带这个前缀。本机 Redis 只有一个实例，别的练手项目也在往里写，
#: 不加前缀迟早撞车（而且撞了以后症状是「数据莫名其妙变了」，很难查）。
PREFIX = 'study:'

_BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_CFG = os.path.join(_BACK_DIR, 'config.local.json')

_current = None
_degraded = None
_init_lock = threading.Lock()     # 保护 get() 的单例构建（见下面的双检锁）


def _load_local():
    try:
        with open(_LOCAL_CFG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _cfg():
    c = _load_local().get('Redis', {})
    return {
        'host': os.environ.get('REDIS_HOST') or c.get('host', '127.0.0.1'),
        'port': int(os.environ.get('REDIS_PORT') or c.get('port', 6379)),
        'password': os.environ.get('REDIS_PASSWORD') or c.get('password', ''),
        'db': int(os.environ.get('REDIS_DB') or c.get('db', 0)),
        'enabled': c.get('enabled', True),
    }


def enabled():
    """配置里 Redis 是不是开着。关了就直接走内存，连一次都不试着连。"""
    return bool(_cfg().get('enabled', True))


class MemoryCache(object):
    """进程内缓存。Redis 不可用时的兜底，也是单测里的默认后端。"""

    name = 'memory'

    def __init__(self):
        self._d = {}
        self._exp = {}
        self._lock = threading.Lock()

    def _alive(self, k):
        e = self._exp.get(k)
        return e is None or e > time.time()

    def get(self, key):
        with self._lock:
            if key in self._d and self._alive(key):
                return self._d[key]
            self._d.pop(key, None)
            self._exp.pop(key, None)
            return None

    def set(self, key, value, ttl=None):
        with self._lock:
            self._d[key] = value
            if ttl:
                self._exp[key] = time.time() + ttl
            else:
                self._exp.pop(key, None)
        return True

    def delete(self, key):
        with self._lock:
            self._d.pop(key, None)
            self._exp.pop(key, None)
        return True

    def clear(self, prefix=''):
        with self._lock:
            for k in list(self._d):
                if k.startswith(prefix):
                    self._d.pop(k, None)
                    self._exp.pop(k, None)
        return True

    def ping(self):
        return True


class RedisCache(object):
    """Redis 后端。value 走 JSON，所以能放 dict / list，不只是字符串。"""

    name = 'redis'

    def __init__(self, host='127.0.0.1', port=6379, password='', db=0, **_kw):
        # ★ protocol=2 必须显式给。redis-py 5+ 默认走 RESP3，连接时先发
        #   `HELLO 3`；而 E:\Redis 装的是 5.0.14，HELLO 是 Redis 6.0 才有的命令，
        #   于是报 `unknown command HELLO` —— 而且是在 ping() 里才炸，
        #   表现为「Redis 明明在跑，却降级成内存」，很容易误判成密码错了。
        self.cfg = dict(host=host, port=int(port), password=password or None,
                        db=int(db), decode_responses=True, protocol=2,
                        socket_connect_timeout=2, socket_timeout=2)
        self.last_error = ''
        self._cli = None
        self._lock = threading.Lock()

    def _c(self):
        if self._cli is None:
            # 延迟 import：没装 redis 包也不影响 import 本模块
            import redis
            # ★ redis-py 的连接池本身是线程安全的，不用像 psycopg/pymysql 那样
            #   做 thread-local —— 它内部按需借还连接。
            self._cli = redis.Redis(**self.cfg)
        return self._cli

    def _k(self, key):
        return PREFIX + str(key)

    def ping(self):
        try:
            self._c().ping()
            self.last_error = ''
            return True
        except Exception as e:
            self.last_error = '%s: %s' % (type(e).__name__, e)
            return False

    def get(self, key):
        try:
            raw = self._c().get(self._k(key))
        except Exception:
            return None                       # 缓存读失败不能让业务挂掉
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return raw

    def set(self, key, value, ttl=None):
        try:
            return self._c().set(self._k(key),
                                 json.dumps(value, ensure_ascii=False),
                                 ex=int(ttl) if ttl else None)
        except Exception:
            return False

    def delete(self, key):
        try:
            return bool(self._c().delete(self._k(key)))
        except Exception:
            return False

    def clear(self, prefix=''):
        """按前缀清。用 scan_iter 而不是 keys —— 生产库上 KEYS 会卡住整个实例，
        这里数据少无所谓，但习惯要养对。"""
        try:
            cli = self._c()
            pat = self._k(prefix) + '*'
            n = 0
            for k in cli.scan_iter(match=pat, count=200):
                cli.delete(k)
                n += 1
            return True
        except Exception:
            return False


def _build():
    global _degraded
    if not enabled():
        _degraded = None                       # 主动关掉不算降级
        return MemoryCache()

    # 探一下装没装。用 find_spec 而不是 import：import 进来不用会留一个
    # 「imported but unused」，而 pyflakes 不认 noqa（那是 flake8 的功能）。
    import importlib.util
    if importlib.util.find_spec('redis') is None:
        _degraded = '没装 redis 包（pip install redis）→ 用进程内存缓存'
        return MemoryCache()

    try:
        c = RedisCache(**_cfg())
        if c.ping():
            _degraded = None
            return c
        _degraded = '连不上 Redis（%s）→ 用进程内存缓存' % c.last_error
    except Exception as e:
        _degraded = 'Redis 初始化失败（%s: %s）→ 用进程内存缓存' % (
            type(e).__name__, e)
    return MemoryCache()


def get():
    # 双检锁：冷启动瞬间的并发请求会各自 _build() 一次，Redis 那边就多建
    # 一个连接池（旧的被丢弃且不关闭），_degraded 也可能被后完成的构建覆盖。
    # store/__init__.py 本来就有这把锁，这里漏了。
    global _current
    if _current is None:
        with _init_lock:
            if _current is None:          # 等锁期间别人可能已经建好
                _current = _build()
    return _current


def reset():
    """清掉单例。改了 Redis 配置又不想重启进程时用。"""
    global _current, _degraded
    _current = None
    _degraded = None


def degraded():
    if _current is None:
        get()
    return _degraded


def status():
    c = get()
    return {'backend': c.name, 'degraded': degraded()}
