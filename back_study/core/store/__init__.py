# -*- coding: utf-8 -*-
"""存储后端工厂：决定这次进程用 JSON 文件还是 MySQL。

**配置优先级**：环境变量 > back_study/config.local.json > 内置默认值。
    STORE=json|mysql            （默认 json）
    MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB

**降级是硬要求**，不是「顺手加的保护」：
    - 没装 pymysql        → 回退 JSON，服务照常起
    - MySQL 没起来        → 回退 JSON，服务照常起
    - 库/表还没建          → 回退 JSON，并明确提示去跑 dbseed.py
理由：这是个背卡工具，最要紧的是「打开就有卡」。为了数据库挂了而整站打不开，
是把手段当成了目的。

但降级必须**看得见**：`info()['degraded']` 会带上原因，
`/api/health` 和 `/api/storage` 都吐出来。悄悄降级 = 用户以为在用 MySQL，
实际写进 JSON，等哪天发现数据「不见了」才懵。
"""
import json
import os
import sys
import threading

# 只导真正用得上的那个名字。这里以前还有三行「供外部转引」的 re-export
# （Store / json_loads / json_dumps / jsonfile / JsonFileStore），2026-09-26 删掉：
# 全仓没有任何地方写 `store.JsonFileStore` 这种带包名的取法，全是各自
# `from .jsonfile import ...`。re-export 的代价不是多两行，是**没人知道它是死的**。
from .jsonfile import JsonFileStore                 # 工厂回退用（见 _fallback）

BACK_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(BACK_DIR, 'config.local.json')

_lock = threading.Lock()
_current = None
_degraded = None            # None = 正常；str = 降级原因


# ---------------------------------------------------------------- 配置
def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f) or {}
        except Exception as e:
            print('[store] 配置读取失败 %s: %s' % (CONFIG_FILE, e), file=sys.stderr)
    # 环境变量覆盖（部署时不想写文件就用这个）
    env_store = os.environ.get('STORE')
    if env_store:
        cfg['STORE'] = env_store
    my = dict(cfg.get('MySQL') or {})
    for key, env in (('host', 'MYSQL_HOST'), ('port', 'MYSQL_PORT'),
                     ('user', 'MYSQL_USER'), ('password', 'MYSQL_PASSWORD'),
                     ('database', 'MYSQL_DB')):
        v = os.environ.get(env)
        if v:
            my[key] = v
    cfg['MySQL'] = my
    return cfg


def wanted_backend():
    return (os.environ.get('STORE')
            or (load_config().get('STORE'))
            or 'json').strip().lower()


# ---------------------------------------------------------------- 工厂
def get():
    """拿当前后端（进程内只建一次）。"""
    global _current
    with _lock:
        if _current is None:
            _current = _build()
        return _current


def reload():
    """丢掉缓存重建。改了 config.local.json 后不想重启服务时用。"""
    global _current, _degraded
    with _lock:
        if _current is not None:
            try:
                _current.close()
            except Exception:
                pass
        _current = None
        _degraded = None
        return _build()


def _fallback(reason):
    global _degraded
    _degraded = reason
    print('[store] MySQL 不可用，已回退到 JSON 文件后端：%s' % reason, file=sys.stderr)
    return JsonFileStore()


def _table_missing(st, name):
    """表不存在返回 True。空表返回 False（`SELECT 1 ... LIMIT 1` 无行不抛异常）。"""
    try:
        st._one('SELECT 1 FROM `%s` LIMIT 1' % name)
        return False
    except Exception:
        return True


def _build():
    global _degraded
    _degraded = None
    if wanted_backend() != 'mysql':
        return JsonFileStore()

    cfg = (load_config().get('MySQL') or {})
    try:
        from .mysql import MySQLStore
    except ImportError as e:
        return _fallback('没装 pymysql（pip install pymysql）: %s' % e)

    st = MySQLStore(host=cfg.get('host') or '127.0.0.1',
                    port=cfg.get('port') or 3306,
                    user=cfg.get('user') or 'root',
                    password=cfg.get('password') or '',
                    db=cfg.get('database') or 'study_cards')
    try:
        st.ping()
    except Exception as e:
        return _fallback('%s:%s 连不上（%s: %s）'
                         % (cfg.get('host') or '127.0.0.1',
                            cfg.get('port') or 3306,
                            type(e).__name__, str(e)[:100]))

    # ---- 表结构兜底：每次启动补一次缺的表 ----
    #
    # 为什么不只靠 `dbseed.py --sync`：**给 DDL 加一张新表时，旧库不会自己长出来**。
    # 上一版就吃了这个亏 —— users 表写进了 DDL，但库是更早建的，
    # 没人想起来再跑一次初始化，于是服务正常启动、数据也读得到，
    # 一直到有人点「登录」才 500，报错点离原因隔了十万八千里。
    # DDL 全是 `CREATE TABLE IF NOT EXISTS`，幂等、只补缺的、不碰已有的，
    # 放在启动路径上比放在一个"要记得跑"的脚本里可靠得多。
    # 失败基本都是账号没有 CREATE 权限，提示一句就够，不该拦着服务起。
    try:
        st.init_schema()
    except Exception as e:
        print('[store] 启动时自动建表跳过（%s）：%s'
              % (type(e).__name__, str(e)[:120]), file=sys.stderr)

    # ---- 探测必须覆盖**所有必需的表**，不能只看 cards ----
    # 只查一张表的后果：别的表缺了查不出来，服务照常起来，
    # 直到某个具体功能被点到才炸 —— 就是上面 users 那个坑。
    need = ('cards', 'users', 'progress', 'notes', 'documents', 'drafts', 'meta')
    missing = [t for t in need if _table_missing(st, t)]
    if missing:
        return _fallback('库 %s 缺表 %s，跑一下：'
                         'python back_study/scripts/dbseed.py --sync'
                         % (cfg.get('database') or 'study_cards',
                            '、'.join(missing)))
    return st


# ---------------------------------------------------------------- 状态
def info():
    """后端运行时状态，直接喂给 /api/health 与 /api/storage。

    前端不用自己判断后端的可用性 —— 这里已经把它折叠成一个 ok 字段，
    并且**永远不返回敏感信息**（password 一律不出现在这里）。
    """
    st = get()
    try:
        out = st.info()
    except Exception as e:
        out = {'store': st.name, 'ok': False, 'error': str(e)[:160]}
    out['want'] = wanted_backend()
    out['degraded'] = _degraded
    out['configFile'] = CONFIG_FILE if os.path.exists(CONFIG_FILE) else None
    return out


def banner_lines():
    """启动横幅里那几行存储信息。

    **降级必须打在这里** —— 横幅是唯一一个「不看日志也一定会看到」的地方。
    悄悄回退成 JSON 的代价是：你以为在写数据库，其实写进了文件，
    等哪天换机器才发现数据没跟过来。
    """
    # 变量名别叫 info —— 会把上面那个同名函数遮蔽掉，
    # 于是 `info = info()` 变成 UnboundLocalError。
    # 这类错误 py_compile 查不出来，只有真起一次服务才会炸。
    st_info = info()
    out = []
    if st_info.get('store') == 'mysql':
        out.append('存储    MySQL %s:%s/%s · 卡 %s · 进度 %s · 笔记 %s · 文档 %s'
                   % (st_info.get('host'), st_info.get('port'), st_info.get('db'),
                      st_info.get('cards'), st_info.get('progress'),
                      st_info.get('notes'), st_info.get('documents')))
    else:
        out.append('存储    JSON 文件 data/store/（单机够用，多端同步要上 MySQL）')
    if st_info.get('degraded'):
        out.append('        !! 配置想用 %s，实际回退成 %s：%s'
                   % (st_info.get('want'), st_info.get('store'), st_info['degraded']))
    return out


def make_mysql():
    """按配置**直接**建一个 MySQL 后端，不做任何可用性探测。

    专门给 dbseed.py 用。这是个先有鸡还是先有蛋的问题：库还没建的时候
    get() 会判定「不可用」并回退到 JSON，但初始化脚本恰恰需要连上去
    把库建出来。所以这里绕开探测 —— 连不上就让 pymysql 自己抛，
    由脚本打印真实的错误（"Unknown database" / "Access denied"），
    比工厂那句笼统的「已回退」有用得多。
    """
    from .mysql import MySQLStore
    cfg = (load_config().get('MySQL') or {})
    return MySQLStore(host=cfg.get('host') or '127.0.0.1',
                      port=cfg.get('port') or 3306,
                      user=cfg.get('user') or 'root',
                      password=cfg.get('password') or '',
                      db=cfg.get('database') or 'study_cards')
