# -*- coding: utf-8 -*-
"""数据层 · 地基 —— 路径常量、存储工厂入口、日期工具、调度转发。

**这一层只负责「怎么算」，不负责「存哪儿」**——存哪儿交给 core/store/
（JSON 文件 / MySQL 两个后端，见 store/base.py 的契约）。
这样换存储不用动业务逻辑。

对外函数名与签名**保持与接入数据库之前完全一致**：routers 都按老名字调，
改的是它们脚下的实现。这条是硬约束 —— 签名一改，调用方就得跟着改一遍，
而这种改动不会有任何编译错误提醒你。

规则与前端 index.html 里的 schedule() 必须保持一致，否则会出现
「网页说明天复习、后端说后天」的不一致。

除第三方驱动外只用标准库：pymysql 只在真的选了 MySQL 后端时才被导入
（在 core/store/mysql.py 里，由工厂按需 import），所以不连数据库时不装它也能跑。

★ 2026-11-15 拆包：本文件原是 2119 行的 core/db.py，按域拆成了 db/ 包。
  拆分原则与依赖方向见包 `__init__.py` 的说明。
"""
import os
import sys
from datetime import date, timedelta

import store as store_pkg                                  # core/store/
from store.base import read_json as _read_json             # 档案/覆盖层的读写（不走后端）
from store.base import write_json as _write_json

CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # back_study/core
BACK_DIR = os.path.dirname(CORE_DIR)                       # back_study
ROOT = os.path.dirname(BACK_DIR)                           # study（项目根）

# algo/ 和 core/ 是平级目录，不在同一条搜索路径上，得自己挂进来。
# （不能让 algo 反过来 import core —— 那是循环依赖，而且算法层会被拖着
#  必须起服务才能测。它的依赖方向是单向的：db 用 algo。）
if BACK_DIR not in sys.path:
    sys.path.insert(0, BACK_DIR)
import algo                                                # back_study/algo/
import algostore                                           # core/algostore/（算法库）
import cache                                               # core/cache.py（Redis 优先）
DATA_DIR = os.path.join(ROOT, 'data')                      # 共用卡片数据
STORE_DIR = os.path.join(DATA_DIR, 'store')
# 唯一保留的文件常量：catalog.js 是**内容**不是状态，本就不走 store 层。
# 这里以前还摆着 FILE_PROGRESS / FILE_CUSTOM / FILE_DRAFTS / FILE_NOTES /
# FILE_DOCS 和 STORE_DIR_JSON 六个「兼容旧名」常量，2026-09-26 全删 ——
# 真正生效的路径在 store/jsonfile.py 的 self.file 字典里，那六个全仓无人引用，
# 留着反而像存在第二个真相源：改了它们以为生效、实际一点用没有。
FILE_CATALOG = os.path.join(DATA_DIR, 'catalog.js')

# 档案/覆盖层等「不走 store 契约的散文件」统一用这两个别名读写
# （cards.py / profiles.py 从这里 import，别再各自 from store.base import）。
__all_base__ = []


def backend():
    return store_pkg.get()


# ---------- 通用读写 ----------
def ensure_store():
    if not os.path.isdir(STORE_DIR):
        os.makedirs(STORE_DIR, exist_ok=True)


def read_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ---------- 日期 ----------
def today_str(d=None):
    t = d or date.today()
    return t.strftime('%Y-%m-%d')


def add_days(s, n):
    y, m, d = [int(x) for x in s.split('-')]
    return today_str(date(y, m, d) + timedelta(days=n))


def diff_days(a, b):
    ya, ma, da = [int(x) for x in a.split('-')]
    yb, mb, db_ = [int(x) for x in b.split('-')]
    return (date(yb, mb, db_) - date(ya, ma, da)).days


def safe_next_at(p, today):
    """取一条进度记录的 nextAt，**把 None / 空串也当「今天」**。

    ★ 为什么不能写 `p.get('nextAt', today)`：那是「键不存在才用默认值」，
    兜不住「键存在但值是 None 或 ''」。而这两种值真的会出现 ——
    `progress` 表（MySQL）的 `next_at` 是 **DATE NULL**，写入侧是
    `rec.get('nextAt') or None`，`dbseed.py --import-json` 又会把源 JSON
    里的 rec 原样搬进库；`store/mysql.py` 的到期队列里甚至专门为
    `next_at IS NULL` 写了一支分支，说明作者本来就预期存在这种行。

    不兜住的后果：`None.split` → AttributeError、`''.split('-')` 解包
    失败 → `/api/review/due` 和 `/api/stats` 直接 500。整张卡库有一个
    坏行就全站看不了队列，代价与「一行判空」完全不成比例。
    """
    v = (p or {}).get('nextAt')
    return v if isinstance(v, str) and v.strip() else today


# ---------- 间隔调度 ----------
def schedule(prev, level, today=None, w=None):
    """算下一次复习时间。level: 1=不会 2=模糊 3=会。返回新的进度记录。

    **这里故意不写算法**：实现全在 `back_study/algo/`（SM-2 / FSRS …），
    本函数只负责转发到当前选定的那一个。换算法改配置就行（`ALGO=fsrs`
    或 config.local.json），数据层一行不用动。

    返回字段固定 6 个（level/interval/ef/reps/nextAt/updatedAt）——
    因为 MySQL 的 progress 表就是这 6 列，多一个字段会被静默丢掉。

    ★ `today` 是给「按历史事件重放」用的（2026-10-03 加）。算法层的
    schedule(prev, level, today) 本来就有这个参数（各 algo 实现都支持，
    注释里写明"仅测试用"），但**转发层从前没往上带**——
    结果重放历史事件时，每一条都被当成"今天"，
    9月 29 号和今天的学习压成同一天，nextAt 全落在今天，
    之后所有"逾期天数"排序都是错的。转发层漏一个参数，
    下游就静默给出错误结果，比直接报错更难查。

    ★ `w`（2026-11-15 加）：个性化 FSRS 权重（fit-fsrs 的产物）。
    传了就覆盖默认权重算这一次；None = 用算法自己的默认值。
    只对 FSRS 生效，其它算法忽略 —— 见 algo/base.py 契约。
    """
    return algo.get().schedule(prev, level, today=today, w=w)


# ---------- 发号 ----------
def _next_daily_id(prefix, existing, day=None):
    """按「日期 + 不重复序号」发号，序号取**已有最大值 + 1**。

    笔记域和文档域共用（note-<日期>-N / doc-<日期>-N），所以放在 base。
    调用方也可以直接 `db._next_daily_id(...)`（web/docs.py 就是这么干的）。

    ★ 为什么不能用 `len(existing) + 1`：删掉中间任意一条后计数会回退，
    新号就会撞上仍然存在的那条记录，而两个存储后端都是 upsert 语义
    （jsonfile 按 id 覆盖、mysql 是 ON DUPLICATE KEY UPDATE）→
    **新建一条笔记会把别人那条笔记的标题正文覆盖掉**，接口还回 ok:true。

    真实现象：今天建了 3 条（尾号 1/2/3）→ 删掉第 1 条 → 再新建 →
    新号 3 → 第 3 条被覆盖。文档同理（doc-<日期>-N）。

    序号只增不复用，所以被删掉的号不会回来 —— 这跟 store/jsonfile.py
    给用户发号时的取舍一致：历史数据（progress.user_id、attempt.user_id）
    将来会指回来，号一旦复用就会指到另一个对象身上。
    """
    stamp = (day or today_str()).replace('-', '')
    head = '%s-%s-' % (prefix, stamp)
    used = set()
    for x in existing:
        xid = str(x.get('id') or '')
        if xid.startswith(head):
            tail = xid[len(head):]
            if tail.isdigit():
                used.add(int(tail))
    return head + str(max(used) + 1 if used else 1)


# ---------- 存储状态 ----------
def storage_info():
    """给 /api/storage 用。退化原因、内容副本是否过期都折叠进来。

    ★ 除了业务存储，还要把**算法库（PG）与缓存（Redis）的降级**一起报出来。
    从前这两个模块的 `degraded()` 全仓只有一次性脚本在用，服务端一处都没消费：
    横幅不打、`/api/storage` 不吐。而两个模块的 docstring 都写着
    「降级原因会写进 degraded() 让启动横幅打出来」，项目的硬要求也是
    「降级必须看得见」。结果就是 `ALGO_STORE=pg` 连不上时事件静默落到
    JSON 文件、Redis 连不上时掌握度缓存退化成进程内存，都没有任何提示 ——
    正是这条硬要求要防的那种情况。
    """
    # 惰性 import：base 是包的地基，builtin 在它之上；在函数体内取
    # 就不必让「import db」这一下把整条链都拉起来。
    from .builtin import builtin_stale, load_source_cards
    info = store_pkg.info()
    st = backend()
    if st.holds_builtin:
        file_cards = load_source_cards()
        db_cards = None
        try:
            db_cards = st.builtin_all()
        except Exception:
            pass
        info['builtin'] = {
            'inDb': len(db_cards) if db_cards is not None else None,
            'inFile': len(file_cards),
            'stale': builtin_stale(),
            # 说清楚「谁说了算」：内容是 data/*.js 说了算，DB 只是查询副本
            'authority': 'data/*.js',
            'syncCmd': 'python back_study/scripts/dbseed.py --sync',
        }
    else:
        info['builtin'] = {
            'inDb': None,
            'inFile': len(load_source_cards()),
            'stale': False,
            'authority': 'data/*.js',
        }
    # 算法库：事件流 / 掌握度 / 拟合参数存哪儿
    try:
        info['algo'] = {'backend': type(algostore.get()).__name__,
                        'degraded': algostore.degraded()}
    except Exception as e:
        info['algo'] = {'backend': '?', 'degraded': str(e)[:160]}
    # 缓存：只用来缓存 BKT 掌握度
    try:
        info['cache'] = {'backend': type(cache.get()).__name__,
                         'degraded': cache.degraded()}
    except Exception as e:
        info['cache'] = {'backend': '?', 'degraded': str(e)[:160]}
    # 业务缓存（答题/校验）：与上面同一个 Redis 实例，只是 key 前缀不同。
    # 单独报出来是因为**它们可以被关掉**（环境变量），出问题时得看得到。
    try:
        from agent.qa import ans_cache
        from agent.qa import retr_cache
        from agent.verify import cache as vcache
        info['cache']['biz'] = {'qa': ans_cache.stats(),
                                'retr': retr_cache.stats(),
                                'verify': vcache.stats()}
    except Exception as e:
        info['cache']['biz'] = {'error': str(e)[:160]}
    return info
