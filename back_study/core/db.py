# -*- coding: utf-8 -*-
"""数据层：卡片读取 + 学习状态持久化 + SM-2 间隔调度。

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
"""
import copy
import json
import os
import re
import sys
from datetime import date, timedelta

import security                                            # core/security.py
import store as store_pkg                                  # core/store/
from store.base import read_json as _read_json             # 档案文件的读写（不走后端）
from store.base import write_json as _write_json

CORE_DIR = os.path.dirname(os.path.abspath(__file__))      # back_study/core
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
def schedule(prev, level):
    """算下一次复习时间。level: 1=不会 2=模糊 3=会。返回新的进度记录。

    **这里故意不写算法**：实现全在 `back_study/algo/`（SM-2 / FSRS …），
    本函数只负责转发到当前选定的那一个。换算法改配置就行（`ALGO=fsrs`
    或 config.local.json），数据层一行不用动。

    返回字段固定 6 个（level/interval/ef/reps/nextAt/updatedAt）——
    因为 MySQL 的 progress 表就是这 6 列，多一个字段会被静默丢掉。
    """
    return algo.get().schedule(prev, level)


# ---------- 内置卡（内容源：data/*.js） ----------
# 缓存：以前每来一个请求就把 data/*.js 整个重新解析一遍（/api/cards、/api/stats、
# 复习队列都各解析一次）。文件级 mtime+size 做键，改一个字节就失效。
_src_cache = {'key': None, 'cards': None}


def _src_key(files):
    try:
        return tuple((f, os.path.getmtime(os.path.join(DATA_DIR, f)),
                      os.path.getsize(os.path.join(DATA_DIR, f))) for f in files)
    except OSError:
        return None


def load_source_cards():
    """读 data/*.js。文件形如 `var CARDS_X = [...]`，
    数组部分是严格 JSON 字面量（由 back_study/scripts/normalize-data.js 保证），
    用 raw_decode 从 '[' 处直接解析，不跑 JS 引擎。

    返回的是**深拷贝**：调用方随手改一下返回值不会污染缓存。
    """
    if not os.path.isdir(DATA_DIR):
        return []
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.js'))
    key = _src_key(files)
    if key is not None and _src_cache['key'] == key and _src_cache['cards'] is not None:
        return [copy.deepcopy(c) for c in _src_cache['cards']]

    out = []
    for f in files:
        src = read_text(os.path.join(DATA_DIR, f))
        m = re.search(r'var\s+(CARDS_[A-Za-z0-9_]+)\s*=', src)
        if not m:
            continue                            # catalog.js 走的是这条分支，跳过
        idx = src.find('[', m.end())
        if idx < 0:
            continue
        try:
            arr, _ = json.JSONDecoder().raw_decode(src, idx)
        except ValueError as e:
            print('[db] 解析失败 %s: %s' % (f, e), file=sys.stderr)
            continue
        for c in arr:
            c['_src'] = f
            out.append(c)

    _src_cache['key'] = key
    _src_cache['cards'] = out
    return [copy.deepcopy(c) for c in out]


def builtin_stale():
    """MySQL 后端专用：库里的内置卡跟 data/*.js 对不对得上。

    True 的两种情况：表里一条都没有（还没跑 dbseed.py --sync）、
    或者指纹对不上（改了 data/*.js 没同步）。
    """
    st = backend()
    if not st.holds_builtin:
        return False
    try:
        if not st.builtin_all():
            return True
        return bool(st.builtin_stale(load_source_cards()))
    except Exception as e:
        print('[db] 内置卡指纹检查失败: %s' % e, file=sys.stderr)
        return True


def builtin_cards():
    """内置卡。JSON 后端读文件；MySQL 后端读表。

    **内容是文件说了算，数据库只是查询用的副本**：所以表空着、或指纹过期时
    一律回落到文件 —— 前者防止界面突然变成 0 张卡，后者防止端上一个
    已经被改掉、库里还是旧的版本（那比没有数据库更难查）。
    """
    st = backend()
    if st.holds_builtin:
        try:
            rows = st.builtin_all()
        except Exception as e:
            print('[db] 读内置卡失败，回落文件: %s' % e, file=sys.stderr)
            rows = None
        if rows and not builtin_stale():
            return rows
    return load_source_cards()


# ---------- 自定义卡 ----------
def load_custom():
    return backend().custom_all()


def save_custom(lst):
    backend().custom_replace(lst)


# ---------- 卡片汇总 ----------
def all_cards(category=None, subject=None):
    """内置卡 + 自定义卡；同 id 时自定义优先。可按领域/科目过滤。"""
    m = {}
    for c in builtin_cards():
        m[c['id']] = c
    for c in load_custom():
        c = dict(c)
        c['_custom'] = True
        m[c['id']] = c
    out = list(m.values())
    if category:
        out = [c for c in out if c.get('category') == category]
    if subject:
        out = [c for c in out if c.get('subject') == subject]
    return out


# ---------- 分类树（配置，留在文件里） ----------
def load_catalog():
    """读 data/catalog.js 的分类树（同样是严格 JSON 字面量）。

    刻意**不进数据库**：这是配置不是数据 —— 网页端靠 `<script src="data/catalog.js">`
    直接读它，后端只是拿来把 id 翻译成中文名。挪进库里，数据库一挂连导航都没了。
    """
    if not os.path.exists(FILE_CATALOG):
        return []
    src = read_text(FILE_CATALOG)
    m = re.search(r'var\s+(CATALOG)\s*=', src)
    if not m:
        return []
    idx = src.find('[', m.end())
    if idx < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
    except ValueError as e:
        print('[db] 分类树解析失败: %s' % e, file=sys.stderr)
        return []
    return arr


def cat_name(category_id):
    for cat in load_catalog():
        if cat.get('id') == category_id:
            return cat.get('name')
    return category_id


def subject_name(subject_id):
    for cat in load_catalog():
        for s in cat.get('subjects', []):
            if s.get('id') == subject_id:
                return s.get('name')
    return subject_id


# ---------- 目标岗位（配置，留在文件里） ----------
FILE_ROLES = os.path.join(DATA_DIR, 'roles.js')


def load_roles():
    """读 data/roles.js 的岗位定义（严格 JSON 字面量 `var ROLES = [...]`）。

    和 catalog 一样**不进数据库**：这是配置不是数据 —— 岗位是内容创作者写死的
    目录，改它应该走 git，而不是靠一个能被网页改写的运行时状态。
    """
    if not os.path.exists(FILE_ROLES):
        return []
    src = read_text(FILE_ROLES)
    m = re.search(r'var\s+ROLES\s*=', src)
    if not m:
        return []
    idx = src.find('[', m.end())
    if idx < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
    except ValueError as e:
        print('[db] 岗位定义解析失败: %s' % e, file=sys.stderr)
        return []
    return arr


def role_by_id(role_id):
    for r in load_roles():
        if r.get('id') == role_id:
            return r
    return None


# ---------- 学习方向（配置，留在文件里） ----------
FILE_DIRECTIONS = os.path.join(DATA_DIR, 'directions.js')


def load_directions():
    """读 data/directions.js 的学习方向（严格 JSON 字面量 `var DIRECTIONS = [...]`）。

    和 catalog / roles 一样**不进数据库**：这是配置不是数据 —— 方向是内容创作者
    写死的分组，改它应该走 git。复习队列按它筛卡，前端 chips 也从它来。
    """
    if not os.path.exists(FILE_DIRECTIONS):
        return []
    src = read_text(FILE_DIRECTIONS)
    m = re.search(r'var\s+DIRECTIONS\s*=', src)
    if not m:
        return []
    idx = src.find('[', m.end())
    if idx < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
    except ValueError as e:
        print('[db] 学习方向解析失败: %s' % e, file=sys.stderr)
        return []
    return arr


def direction_kws(dir_ids):
    """方向 id 列表 → 合并后的关键词（去重、保序）。查不到的方向静默跳过。

    多选方向时取**并集**：选了「Agent 开发」和「Python 基础」就推两边的卡。
    """
    ids = set(dir_ids or [])
    kws, seen = [], set()
    for d in load_directions():
        if d.get('id') not in ids:
            continue
        for k in (d.get('keywords') or []):
            k = str(k).strip()
            if k and k.lower() not in seen:
                seen.add(k.lower())
                kws.append(k)
    return kws


# ---------- 长期档案（L3 记忆）----------
# 刻意**不进 store 契约**：加进 base/mysql/jsonfile/schema 四处的代价，
# 换来的只是"档案跟着 MySQL 走"。而它是派生数据 —— 目标岗位、常问主题、
# 薄弱卡都能重新积累，丢了不影响任何核心功能。文件后端足够。
# 等 progress/notes 做 user_id 隔离（P0）时，它自然跟着一起搬进库。
FILE_PROFILES = os.path.join(STORE_DIR, 'profiles.json')


def load_profiles():
    return _read_json(FILE_PROFILES, {})


def profile_of(user_id):
    """取某个用户的长期档案。没有就返回空壳（前端据此判断"还没设过"）。

    `dailyTarget` / `directions` 是**学习设置**（每天学几张、学什么方向），
    和 role/topics/weak 一起存：它影响的是复习队列，但同样"跟着这个人走"，
    存 localStorage 换台设备就没了。
    `dailyTarget == 0` 表示从没设过 —— 前端按默认值显示，不要当 0 张来排。
    """
    if user_id is None:
        return {'role': '', 'topics': [], 'weak': [],
                'dailyTarget': 0, 'directions': []}
    p = load_profiles().get(str(user_id)) or {}
    return {'role': p.get('role') or '',
            'topics': list(p.get('topics') or []),
            'weak': list(p.get('weak') or []),
            'dailyTarget': int(p.get('dailyTarget') or 0),
            'directions': list(p.get('directions') or [])}


def save_profile(user_id, patch):
    """合并写入档案（只覆盖发上来的字段）。

    topics/weak 做**去重 + 上限截断**：这两条是自动积累的，
    不截断的话常问一年之后每次问答都往提示词里塞几百个主题。

    dailyTarget / directions 则是**覆盖写**，跟上面两条语义相反：
    它们是用户手选的设置，追加会让「取消勾选的方向」永远取消不掉。
    没发（None）就不动 —— 单改每日目标的请求不能顺手清空方向。
    """
    if user_id is None:
        return None
    all_p = load_profiles()
    cur = all_p.get(str(user_id)) or {'role': '', 'topics': [], 'weak': []}
    if isinstance(patch, dict):
        if 'role' in patch:
            cur['role'] = str(patch.get('role') or '')
        for k in ('topics', 'weak'):
            if k in patch and isinstance(patch[k], list):
                seen, out = set(), []
                for x in list(cur.get(k) or []) + [str(v) for v in patch[k]]:
                    if x and x not in seen:
                        seen.add(x)
                        out.append(x)
                cur[k] = out[-24:]                 # 每类最多留 24 条
        if patch.get('dailyTarget') is not None:
            try:
                cur['dailyTarget'] = max(0, min(200, int(patch['dailyTarget'])))
            except (TypeError, ValueError):
                cur['dailyTarget'] = 0
        if patch.get('directions') is not None and isinstance(patch['directions'], list):
            ids, seen = [], set()
            for x in patch['directions']:
                x = str(x).strip()
                if x and x not in seen:
                    seen.add(x)
                    ids.append(x)
            cur['directions'] = ids[:12]           # 方向一共才 12 个，够用了
    all_p[str(user_id)] = cur
    ensure_store()
    _write_json(FILE_PROFILES, all_p)
    return cur


def get_today_pick(user_id):
    """今日自选复习清单：用户自己点名「今天就刷这些」的卡 id。

    跨天自动作废（存的日期不是今天 → 空）：清单是「今日」语义，
    隔天还留着会让昨天的负担变成今天的，和 dueToday 一样越滚越大。
    上限 100 与 set_today_pick 一致，读侧再截一次是防手改文件撑爆队列。
    """
    if user_id is None:
        return []
    p = load_profiles().get(str(user_id)) or {}
    tp = p.get('todayPick') or {}
    if tp.get('date') != today_str():
        return []
    return [str(x) for x in (tp.get('ids') or [])][:100]


def set_today_pick(user_id, ids):
    """**整体覆盖**写今日清单：过滤不存在的卡、去重、截 100、盖当天日期。

    和 save_profile 分开写而不是往里加字段：清单是带日期的整体覆盖，
    塞进那个「只动发上来的字段」的合并函数里两边语义都不对 ——
    它会把「没发 date」当成不动日期，隔天的旧清单就清不掉了。
    """
    if user_id is None:
        return []
    valid = {c['id'] for c in all_cards()}
    out, seen = [], set()
    for x in (ids or []):
        x = str(x)
        if x in valid and x not in seen:
            seen.add(x)
            out.append(x)
        if len(out) >= 100:                   # 一天刷 100 张已经到顶了
            break
    all_p = load_profiles()
    cur = all_p.get(str(user_id)) or {'role': '', 'topics': [], 'weak': []}
    cur['todayPick'] = {'date': today_str(), 'ids': out}
    all_p[str(user_id)] = cur
    ensure_store()
    _write_json(FILE_PROFILES, all_p)
    return out


def _kw_hits(kw, cards):
    """技能词在不在这个科目的卡里：匹配 keywords / title / topicPath。

    用子串匹配而不是精确相等 —— 「B+树」这种词在卡里常写作「B+树索引原理」，
    精确相等会把明明有的卡报成缺。
    """
    k = (kw or '').strip().lower()
    if not k:
        return False
    for c in cards:
        hay = ' '.join((c.get('keywords') or []) +
                       [c.get('title') or ''] +
                       (c.get('topicPath') or [])).lower()
        if k in hay:
            return True
    return False


def card_hit(card, kws):
    """这张卡命中方向关键词吗（子串、大小写不敏感）。

    口径和 `_kw_hits` 是同一套 —— keywords / title / topicPath 任何一处包含即算。
    区别只在方向：`_kw_hits` 问「这个词在不在这一组卡里」（岗位对账用），
    这里问「这张卡在不在这个方向里」（复习队列筛选用）。所以必须逐卡算，
    不能借 `_kw_hits` —— 它短路返回的是组级结论。
    """
    hay = ' '.join((card.get('keywords') or []) +
                   [card.get('title') or ''] +
                   (card.get('topicPath') or [])).lower()
    for kw in kws:
        k = (kw or '').strip().lower()
        if k and k in hay:
            return True
    return False


def role_plan(role_id=None, subjects=None):
    """目标岗位 → 知识点地图。返回每个技能组的卡片、掌握情况与缺口。

    两条入口共用一个出口：
      role_id   预置岗位（data/roles.js）
      subjects   自定义科目组合（"java,ai,python"），不落库、用完即走

    为什么缺口按**技能词**算而不是按科目：科目「AI工程」有卡 ≠ 覆盖了这个岗位
    要的「向量检索」。技能词是岗位真正的考点，缺哪条说哪条才有用。
    """
    if role_id:
        role = role_by_id(role_id)
        if role is None:
            return None
        skills = role.get('skills') or []
        head = {'id': role.get('id'), 'name': role.get('name'),
                'desc': role.get('desc'), 'custom': False}
    else:
        subs = [s for s in (subjects or '').split(',') if s.strip()]
        if not subs:
            return None
        known = {s.get('id') for cat in load_catalog() for s in cat.get('subjects', [])}
        subs = [s.strip() for s in subs if s.strip() in known]
        if not subs:
            return None
        skills = [{'subject': s, 'weight': 2, 'keywords': []} for s in subs]
        head = {'id': 'custom', 'name': '自定义组合', 'desc': '自己勾的科目',
                'custom': True}

    prog = get_progress()
    groups, covered_n, total_kw = [], 0, 0
    for sk in sorted(skills, key=lambda x: -(x.get('weight') or 0)):
        sub = sk.get('subject')
        cards = all_cards(subject=sub)
        rows = []
        for c in sorted(cards, key=lambda x: x.get('id') or ''):
            p = prog.get(c.get('id')) or {}
            rows.append({
                'id': c.get('id'), 'title': c.get('title'),
                'oneLine': c.get('oneLine'), 'level': p.get('level', 0),
                'nextAt': p.get('nextAt'),
            })
        kws = sk.get('keywords') or []
        missing = [k for k in kws if not _kw_hits(k, cards)]
        covered = [k for k in kws if k not in missing]
        total_kw += len(kws)
        covered_n += len(covered)
        groups.append({
            'subject': sub, 'name': subject_name(sub),
            'weight': sk.get('weight') or 1,
            'count': len(rows),
            'learned': sum(1 for r in rows if r['level'] > 0),
            'mastered': sum(1 for r in rows if r['level'] == 3),
            'cards': rows,
            'covered': covered,
            'missing': missing,
        })

    return dict(head, skills=groups,
                summary={'keywords': total_kw, 'covered': covered_n,
                         'percent': int(round(100.0 * covered_n / total_kw))
                         if total_kw else 100,
                         'cards': sum(g['count'] for g in groups),
                         'mastered': sum(g['mastered'] for g in groups)})


# ---------- 知识框架（MOC 树） ----------
def build_outline(category=None, subject=None):
    """四层树：领域 → 科目 → 主题(topicPath) → 卡片。
    主题层从 topicPath 自动推导，不用另外维护一份目录。"""
    prog = get_progress()
    cards = all_cards(category=category, subject=subject)

    tree = []
    # ★ 这里曾经写成 `index[(cat, sub)] = 领域节点的 children`，于是同一个
    # category 的第二个 subject 因为 key 不同，又 append 了一个新的领域节点 ——
    # 67 张卡会长出 9 个顶层节点、其中 work 重复 5 次、kaoyan 重复 4 次，
    # 「领域 → 科目」第一层直接退化成「一科目一领域」。
    # 修法：按 cat 建索引，领域节点只在**首次见到这个 cat** 时进 tree。
    tree_index = {}                             # cat -> 领域节点
    for c in cards:
        cat = c.get('category') or 'other'
        sub = c.get('subject') or 'other'
        if cat not in tree_index:
            node = {'id': cat, 'name': cat_name(cat), 'type': 'category',
                    'count': 0, 'children': {}}
            tree.append(node)
            tree_index[cat] = node
        cat_node = tree_index[cat]
        sub_children = cat_node['children']
        if sub not in sub_children:
            sub_children[sub] = {'id': sub, 'name': subject_name(sub),
                                 'type': 'subject', 'count': 0, 'children': {}}
        sub_node = sub_children[sub]

        # 沿 topicPath 逐层下行（SpringBoot › 核心原理 › 自动装配），
        # 不只用 path[0]——否则所有卡都塌在同一层，看不出结构
        path = c.get('topicPath') or ['未归档']
        p = prog.get(c['id'])
        cur = sub_node['children']
        for i, seg in enumerate(path):
            if seg not in cur:
                cur[seg] = {'id': seg, 'name': seg, 'type': 'topic',
                            'count': 0, 'children': {}, 'cards': []}
            node = cur[seg]
            node['count'] += 1
            if i == len(path) - 1:
                node['cards'].append({
                    'id': c['id'],
                    'title': c.get('title'),
                    'oneLine': c.get('oneLine', ''),
                    'level': p.get('level') if p else 0,
                    'path': ' › '.join(path)
                })
            cur = node['children']
        sub_node['count'] += 1
        cat_node['count'] += 1

    def to_list(d):
        out = []
        for v in d.values():
            n = dict(v)
            n['children'] = to_list(v['children'])
            out.append(n)
        return out

    for node in tree:
        node['children'] = [
            dict(s, children=to_list(s['children']))
            for s in node['children'].values()
        ]
        node['count'] = sum(s['count'] for s in node['children'])
    return tree


# ---------- 知识图谱 ----------
def build_graph(category=None, subject=None):
    """节点：领域 / 科目 / 主题 / 卡片四层；边：层级归属 + 卡片间的语义关联。

    层级边是骨架（否则图会散成互不相连的孤岛）；
    语义边来自卡片的 related 字段，必须带 kind 与 note——不做关键词自动连，
    那样得到的只是毛线球，不是知识图谱。
    """
    prog = get_progress()
    cards = all_cards(category=category, subject=subject)
    ids = set(c['id'] for c in cards)

    nodes = {}
    edges = []

    def node(nid, label, ntype, **kw):
        if nid not in nodes:
            nodes[nid] = dict({'id': nid, 'label': label, 'type': ntype,
                               'degree': 0}, **kw)
        return nodes[nid]

    def link(a, b, kind, **kw):
        if a not in nodes or b not in nodes:
            return
        edges.append(dict({'source': a, 'target': b, 'kind': kind}, **kw))
        nodes[a]['degree'] += 1
        nodes[b]['degree'] += 1

    # --- 层级骨架 ---
    for c in cards:
        cat = c.get('category') or 'other'
        sub = c.get('subject') or 'other'
        path = c.get('topicPath') or ['未归档']

        node('cat:' + cat, cat_name(cat), 'category', cat=cat)
        node('sub:' + cat + '/' + sub, subject_name(sub), 'subject',
             cat=cat, sub=sub)

        # 主题按完整路径逐层建节点，相邻层相连（SpringBoot → 核心原理 → 自动装配）
        parent = 'sub:' + cat + '/' + sub
        for i, seg in enumerate(path):
            nid = 'topic:' + sub + '/' + '/'.join(path[:i + 1])
            node(nid, seg, 'topic', cat=cat, sub=sub, depth=i)
            link(parent, nid, 'belong')
            parent = nid

        node(c['id'], c.get('title'), 'card',
             cat=cat, sub=sub, topic=path[-1],
             oneLine=c.get('oneLine', ''),
             keywords=c.get('keywords', []),
             level=(prog.get(c['id']) or {}).get('level', 0))
        link(c['id'], parent, 'belong')

    # --- 语义关联（去重：无向，A-B 与 B-A 视为同一条） ---
    seen = set()
    for c in cards:
        for r in (c.get('related') or []):
            tid = r.get('id') if isinstance(r, dict) else r
            if tid not in ids or tid == c['id']:
                continue                        # 指向已删除的卡就静默跳过
            key = tuple(sorted([c['id'], tid]))
            if key in seen:
                continue
            seen.add(key)
            note = r.get('note', '') if isinstance(r, dict) else ''
            kind = r.get('kind', 'rel') if isinstance(r, dict) else 'rel'
            link(c['id'], tid, kind, note=note)

    return {'nodes': list(nodes.values()), 'edges': edges}


def neighbors(cid, depth=1):
    """局部图谱：给定卡片，返回它的 n 层邻居子图。
    Obsidian 的经验是——全局图谱到了几百节点就是毛线球，
    真正有用的是「这张卡周围有什么」。"""
    g = build_graph()
    nodes = {n['id']: n for n in g['nodes']}
    adj = {}
    for e in g['edges']:
        adj.setdefault(e['source'], []).append((e['target'], e))
        adj.setdefault(e['target'], []).append((e['source'], e))

    if cid not in nodes:
        return {'nodes': [], 'edges': [], 'center': None}

    visited = {cid}
    frontier = [cid]
    keep_edges = {}
    for _ in range(depth):
        nxt = []
        for cur in frontier:
            for nb, e in adj.get(cur, []):
                ek = tuple(sorted([e['source'], e['target']])) + (e['kind'],)
                if ek not in keep_edges:
                    keep_edges[ek] = e
                if nb not in visited:
                    visited.add(nb)
                    nxt.append(nb)
        frontier = nxt
        if not frontier:
            break

    return {
        'center': cid,
        'nodes': [dict(nodes[i], isCenter=(i == cid)) for i in visited],
        'edges': list(keep_edges.values())
    }


# ---------- 笔记 ----------
def load_notes():
    return backend().notes_all()


def _next_daily_id(prefix, existing, day=None):
    """按「日期 + 不重复序号」发号，序号取**已有最大值 + 1**。

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


def upsert_note(note):
    """有 id 就更新，没有就新建。返回保存后的笔记。"""
    lst = load_notes()
    nid = note.get('id')
    now = today_str()
    if nid:
        for n in lst:
            if n.get('id') == nid:
                merged = dict(n)
                merged.update(note)
                merged['updatedAt'] = now
                backend().note_put(merged)
                return merged
    nid = nid or _next_daily_id('note', lst, now)
    note = dict(note)
    note['id'] = nid
    note.setdefault('createdAt', now)
    note['updatedAt'] = now
    backend().note_put(note)
    return note


def delete_note(nid):
    st = backend()
    if any(n.get('id') == nid for n in st.notes_all()):
        st.note_del(nid)
        return True
    return False


# ---------- 文档（整份导入的章节化资料） ----------
def load_docs():
    return backend().docs_all()


def upsert_doc(doc):
    """有 id 就覆盖，没有就新建。chapters 一并存，不做增量合并
    （一份文档要么整存要么整删）。"""
    lst = load_docs()
    did = doc.get('id')
    now = today_str()
    if did:
        for d in lst:
            if d.get('id') == did:
                merged = dict(d)
                merged.update(doc)
                merged['updatedAt'] = now
                backend().doc_put(merged)
                return merged
    did = did or _next_daily_id('doc', lst, now)
    doc = dict(doc)
    doc['id'] = did
    doc.setdefault('createdAt', now)
    doc['updatedAt'] = now
    backend().doc_put(doc)
    return doc


def delete_doc(did):
    st = backend()
    if any(d.get('id') == did for d in st.docs_all()):
        st.doc_del(did)
        return True
    return False


def get_doc(did):
    for d in load_docs():
        if d.get('id') == did:
            return d
    return None


def set_doc_ai(did, items, meta=None):
    """把 LLM 精读结果写回章节。items: [{'index': 章节下标, 'ai': {...}}]

    逐章写、逐章存，所以「精读一章看一章」是安全的——中途打断也不会丢已完成的。
    顺带更新 aiDone/aiTotal，前端据此画进度。

    只 put 这一份文档（不是 load 全量再 save 全量）：一份几十章的 PDF
    正文加上 AI 结果能到几百 KB，章节级写操作要是每次都把整个 documents
    表重写一遍，精读十章的代价是重复落盘十倍数据。
    """
    d = get_doc(did)
    if d is None:
        return None
    chs = d.get('chapters') or []
    for it in items:
        k = it.get('index')
        if isinstance(k, int) and 0 <= k < len(chs):
            chs[k]['ai'] = it.get('ai')
    d['chapters'] = chs
    d['aiDone'] = sum(1 for c in chs if c.get('ai'))
    d['aiTotal'] = len(chs)
    if meta:
        d['aiModel'] = meta.get('model')
        d['aiProvider'] = meta.get('provider')
    d['updatedAt'] = today_str()
    backend().doc_put(d)
    return d


def rename_deck(did, title):
    """改卡片组（deck）的名字。

    组名的真相源是**文档标题**；卡和草稿里的 deck 是生成时抄的冗余字符串
    （没有独立的组表，MySQL 里连 deck 列都没有）。所以只改文档不行 ——
    已生成的卡还挂着旧名，下次从这份文档出卡又会按新标题抄一遍，
    同一组会分裂成两个 chips。三处必须一起改：

      1. documents.title（真相源，下次出卡按它抄）
      2. 自定义卡 payload 里的 deck
      3. 草稿里的 deck

    topicPath[1] 也是生成时按标题截的（title[:20]），对得上旧名才跟着改 ——
    手工改过目录路径的卡不动。返回 None 表示文档不存在；{'ok': False} 表示
    参数不合法（空名），由上层转成 HTTP 错误。"""
    doc = get_doc(did)
    if doc is None:
        return None
    new = (title or '').strip()[:60]
    if not new:
        return {'ok': False, 'msg': '组名不能为空'}
    old = str(doc.get('title') or '')
    if new == old:
        return {'ok': True, 'title': new, 'cards': 0, 'drafts': 0}
    upsert_doc({'id': did, 'title': new})

    def fix(c):
        if c.get('deckId') != did:
            return False
        c['deck'] = new
        tp = c.get('topicPath')
        if isinstance(tp, list) and len(tp) >= 2 and tp[1] == old[:20]:
            tp[1] = new[:20]
        return True

    n_cards = n_drafts = 0
    custom = load_custom()
    for c in custom:
        if fix(c):
            n_cards += 1
    if n_cards:
        save_custom(custom)
    drafts = load_drafts()
    for d in drafts:
        if fix(d):
            n_drafts += 1
    if n_drafts:
        save_drafts(drafts)
    return {'ok': True, 'title': new, 'cards': n_cards, 'drafts': n_drafts}


# ---------- 草稿（导入缓冲区） ----------
def load_drafts():
    return backend().drafts_all()


def save_drafts(lst):
    backend().draft_replace(lst)


# ---------- 进度 ----------
def get_progress():
    return backend().progress_all()


def set_level(cid, level, user_id=None):
    """标记掌握程度 + 追加一条复习事件。

    **为什么是双写**：`progress` 是**状态**（只留最新一条，覆盖式），
    而知识追踪模型（BKT/DKT/AKT）要的是**历史**。两者用途不同，不能互相替代 ——
    硬把历史塞进 progress 会把「查到期」这个最频繁的查询拖慢，
    而只留状态、不留历史，就永远训不出任何模型。

    `user_id` 传了才写事件（老调用方不传也能跑，只是没历史）。
    等所有端点都接上登录用户之后，这个参数就该改成必填。
    """
    rec = schedule(get_progress().get(cid), level)
    backend().progress_put(cid, rec)
    if user_id is not None:
        # ★ log_review 和 mastery_of 必须在**同一个 try** 里。
        # 它们打的是算法库（PG 或文件），和 progress 是两套存储；
        # 从前只包住了 mastery_of，而 log_review 裸在 try 外面 ——
        # pg 掉线 / 算法库文件只读时：进度已经改完、事件没写、请求返回 500。
        # 用户看到失败就会重试，而重试是从**已经推进过的**进度再算一次
        # （连续两次「会」本该 1→3 天，重试后直接跳到 3×ef≈8 天），
        # 状态和他的认知对不上，而且没有任何地方提示这件事。
        # 掌握度、事件流都是**派生数据**，丢了能重算；进度的正确性优先。
        try:
            log_review(user_id, cid, level)
            mastery_of(user_id, cid, refresh=True)
        except Exception as e:
            sys.stderr.write('[set_level] 派生数据写入失败（进度已保存）：%s\n' % e)
    return rec


# ---------- 复习事件流（知识追踪的数据地基） ----------
#: 「模糊」算答对还是答错？BKT 只吃二值，这里定 **模糊 = 没答对**。
#: 理由：模糊说明没真正掌握，按错处理的结果是「多复习一次」，按对处理的结果是
#: 「可能永远不再见面」。两种错误里，前者的代价小得多。
CORRECT_LEVEL = 3


def log_review(user_id, card_id, level, kc=None, at=None, elapsed_ms=None):
    """追加一条复习事件。

    kc（知识点）默认就是 card_id —— 一期没做知识点粒度，一张卡一个知识点。
    等 `topicPath` 末级能用之后，这里换成真正的 kc，事件流的其它部分不用动。
    """
    return algostore.get().events_append({
        'user_id': str(user_id),
        'card_id': card_id,
        'kc': kc or card_id,
        'level': int(level),
        'correct': 1 if int(level) >= CORRECT_LEVEL else 0,
        'at': at or today_str(),
        'elapsed_ms': elapsed_ms,
    })


#: 回放类调用（BKT 拟合 / 掌握度）要**全量**事件，不是默认的最近 500 条。
#: 0 = 不截断（见 algostore.base.events_of 的 limit 契约）。
#: 为什么必须显式写：默认 500 会在卡库×复习次数上去之后悄悄截断，
#: 表现为「掌握度算到一半就不动了」，而且换后端症状还不一样。
EVENTS_ALL = 0


def events_of(user_id, kc=None, card_id=None, limit=500):
    """某人的复习事件，按时间正序（BKT 要按序回放）。

    `limit` 语义：取**最近** limit 条再正序返回；`limit=0`/`None` 表示全量。
    回放路径请显式传 `EVENTS_ALL`，别用默认值。
    """
    return algostore.get().events_of(user_id, kc=kc, card_id=card_id,
                                     limit=limit)


def events_count(user_id=None):
    return algostore.get().events_count(user_id)


# ---------- BKT 掌握度 ----------
def _params_key(user_id=None):
    return 'bkt:params:' + (str(user_id) if user_id else 'global')


def bkt_params(user_id=None):
    """BKT 四参数。拟合过就用拟合值，没拟合过就用默认。

    缓存在 Redis：这个值只在你重新拟合时才变，但「算掌握度」每次都要读它，
    不缓存就是每次请求多打一次 PG/文件。
    """
    key = _params_key(user_id)
    c = cache.get()
    got = c.get(key)
    if got:
        return dict(got)
    params = algostore.get().params_get(key) or dict(algo.BKT_DEFAULT_PARAMS)
    c.set(key, params, ttl=3600)
    return dict(params)


def fit_bkt(user_id=None):
    """用自己的事件流拟合 BKT 四参数，拟合成功就存起来。

    返回 `(params, info)`。数据不够时**返回默认参数并说明原因**，不硬拟合——
    20 条记录拟合 4 个参数必然过拟合，那时候默认参数反而预测得更准。
    """
    evs = events_of(str(user_id), limit=EVENTS_ALL) if user_id else []
    by_kc = {}
    for e in evs:
        by_kc.setdefault(e.get('kc'), []).append(e)
    seqs = []
    for rows in by_kc.values():
        # 回放必须严格按时间序，同一天按写入序（id）—— BKT 是马尔可夫的，
        # 顺序错了算出来的 p 就是错的，而且错得很隐蔽。
        rows.sort(key=lambda r: (str(r.get('at') or ''), r.get('id') or 0))
        seqs.append(algo.bkt.from_events(rows))

    params, info = algo.bkt_fit(seqs)
    if info.get('fitted'):
        algostore.get().params_put(_params_key(user_id), params)
        cache.get().set(_params_key(user_id), params, ttl=3600)
        # ★ 参数一换，之前算出来的掌握度**全部作废**。
        #   漏掉这一步的症状非常阴：拟合完立刻查掌握度，拿到的是拟合之前
        #   用旧参数算的缓存值，于是「重新拟合了但结果没变」——
        #   你会以为是模型没生效，其实是缓存没失效。
        cache.get().clear('bkt:p:%s:' % user_id if user_id else 'bkt:p:')
        # mastery 表里那批同样是旧参数下的派生值，一起清掉，下次读时重算。
        algostore.get().mastery_clear(user_id)
    return params, info


def mastery_of(user_id, kc, refresh=False):
    """这个人在某个知识点上的掌握度 p ∈ [0,1]。

    为什么必须缓存：算一次要把这个人的整条事件流从头回放一遍，
    而到期队列、看板、AI 助手每次都要读。不缓存 = 每次都在扫表。

    refresh=True 表示「刚产生了新事件，缓存的那份已经过期」。
    """
    key = 'bkt:p:%s:%s' % (user_id, kc)
    c = cache.get()
    if not refresh:
        got = c.get(key)
        if got is not None:
            return float(got)

    p = algo.bkt.predict(
        algo.bkt.from_events(events_of(user_id, kc=kc, limit=EVENTS_ALL)),
        bkt_params(user_id))
    c.set(key, p, ttl=600)
    algostore.get().mastery_put(user_id, kc, p)
    return p


def mastery_all(user_id):
    """{kc: p}。只返回**已经算过**的；没算过的 kc 不在这里。

    要拿全量就先对每张卡调一次 `mastery_of()`，别在这里偷偷补算——
    那会让一个看起来是「读」的函数去做 N 次重放，慢得莫名其妙。
    """
    return algostore.get().mastery_all(user_id)


def reset_progress(cid):
    backend().progress_del(cid)


def clear_progress():
    backend().progress_clear()


# ---------- 到期队列 ----------
#: 「从没复习过」的哨兵值。前端/接口把它翻译成 null，别让 999 漏出去。
OVERDUE_NEVER = 999
_RANK = {1: 0, 2: 1, 0: 2, 3: 3}


def due_list(domain=None, include_all=False, category=None, subject=None):
    """到期队列。未标记过 = 待学（永远在队列里）。

    排序：不会(1) → 模糊(2) → 未标记(0) → 会(3)，同档里逾期久的优先。
    为什么未标记排在「会」前面、却在「不会」后面：先补漏，再学新，
    最后才是巩固 —— 「不会」的卡再不看就白背了，「没背过」的卡明天开始也不迟。
    顺带修掉一个老 bug：原来写成 `x['level'] or 9`，未标记(0) 会被算成 9，
    整批「从没背过」的新卡被排到「已经会了」的后面，队列里翻半天见不到新内容。

    MySQL 后端会走 SQL 快路径（LEFT JOIN + 索引排序）；内容副本过期或
    用的是文件后端时，回落到下面这段等价的 Python 实现。两条路径的排序
    规则必须一致 —— check.js 的冒烟就是拿同一批断言同时打两边的。
    """
    st = backend()
    if st.holds_builtin and not builtin_stale():
        try:
            rows = st.due_cards(category=category, subject=subject,
                                domain=domain, include_all=include_all)
        except Exception as e:
            print('[db] SQL 队列失败，回落 Python 路径: %s' % e, file=sys.stderr)
            rows = None
        if rows is not None:
            for x in rows:
                if x['overdue'] is None:
                    x['overdue'] = OVERDUE_NEVER
            return rows

    today = today_str()
    prog = get_progress()
    items = []
    for c in all_cards(category=category, subject=subject):
        if domain and c.get('domain') != domain:
            continue
        p = prog.get(c['id'])
        if p is None:
            overdue = OVERDUE_NEVER
            due = True
        else:
            overdue = diff_days(safe_next_at(p, today), today)
            due = overdue >= 0
        if not include_all and not due:
            continue
        items.append({
            'card': c,
            'progress': p,
            # p['level'] 会在记录缺 level 键时 KeyError 500；
            # 同一份数据在 build_outline / role_plan 里都用 p.get('level')，
            # 口径要一致。
            'level': p.get('level', 0) if p else 0,
            'overdue': overdue,
            'due': due
        })
    items.sort(key=lambda x: (_RANK.get(x['level'], 2), -x['overdue'], x['card']['id']))
    return items


def stats():
    prog = get_progress()
    cards = all_cards()
    today = today_str()
    s = {'total': len(cards), 'custom': 0, 'known': 0, 'fuzzy': 0,
         'weak': 0, 'unmarked': 0, 'dueToday': 0, 'notes': len(load_notes()),
         'drafts': len(load_drafts()), 'docs': len(load_docs()),
         'domains': {}, 'byCategory': {}, 'bySubject': {}}
    for c in cards:
        if c.get('_custom'):
            s['custom'] += 1
        d = c.get('domain', '未分类')
        s['domains'][d] = s['domains'].get(d, 0) + 1
        cat = c.get('category') or '未分类'
        sub = c.get('subject') or '未分类'
        s['byCategory'][cat] = s['byCategory'].get(cat, 0) + 1
        key = cat + '/' + sub
        s['bySubject'][key] = s['bySubject'].get(key, 0) + 1
        p = prog.get(c['id'])
        if p is None:
            s['unmarked'] += 1
            s['dueToday'] += 1
            continue
        lv = p.get('level')
        if lv == 3:
            s['known'] += 1
        elif lv == 2:
            s['fuzzy'] += 1
        else:
            s['weak'] += 1
        if diff_days(safe_next_at(p, today), today) >= 0:
            s['dueToday'] += 1
    return s


# ---------- 用户 ----------
# 用户是唯一一个不属于卡片域的实体：它是所有 per-user 数据（掌握度、答题记录、
# 笔记）的前置条件。存储层只管存取，这里补规则。
#
# 注意：**加登录只做到「有账号、能登录」**。progress / notes 目前还没有
# user_id，也就是「谁都能登，但数据还是大家共用一份」。这一步刻意留着，
# 因为它要配一次数据迁移 —— 顺手加列的下场是现有进度变成「找不到」，
# 比暂时不隔离糟糕得多。

def public_user(u):
    """对外暴露的用户对象。**任何**要返回给前端的用户都必须过这一道。

    直接把存储层的 dict 返回出去会把 passwordHash 漏出去。这类泄露多半
    不是有人故意，而是「顺手 return 了上游对象」。
    """
    if not u:
        return None
    return {
        'id': u.get('id'),
        'username': u.get('username') or '',
        'displayName': u.get('displayName') or u.get('username') or '',
        'role': u.get('role') or 'user',
        'createdAt': u.get('createdAt'),
    }


def user_all():
    return [public_user(u) for u in backend().user_all()]


def user_get(uid):
    return backend().user_get(uid)


def user_by_name(username):
    return backend().user_by_name(username)


def user_count():
    try:
        return backend().user_count()
    except Exception:
        return 0


def create_user(username, password, display_name=''):
    """建账号。返回 `(user 或 None, 错误话术)`。

    两条规则放在这里而不是端点里，因为这里是唯一的账号创建入口
    （注册端点 / 将来的 CLI 建号都要走它）：
      1. 用户名重复要拦 —— 存储层虽然有唯一索引，但得换成人话报错
      2. **第一个注册的人自动是管理员** —— 单机部署不用手工建号，
         自己一个人用也不会出现「大家都一样」的尴尬
    """
    ok, name_or_msg = security.check_username(username)
    if not ok:
        return None, name_or_msg
    name = name_or_msg

    ok, pw_or_msg = security.check_password(password)
    if not ok:
        return None, pw_or_msg

    if backend().user_by_name(name):
        return None, '用户名已被占用'

    rec = {
        'username': name,
        'passwordHash': security.hash_password(pw_or_msg),
        'displayName': (display_name or '').strip()[:32] or name,
        'role': 'admin' if user_count() == 0 else 'user',
        'openid': None,
    }
    uid = backend().user_put(rec)
    return public_user(backend().user_get(uid)), None


def verify_login(username, password):
    """校验账号密码。返回 `(user 或 None, 错误话术)`。

    「用户不存在」和「密码错」**故意返回同一句话** —— 分开写就等于白送
    一个用户名枚举接口，别人可以拿它筛出哪些账号真实存在。
    """
    bad = '用户名或密码不对'
    name = (username or '').strip()
    if not name or not password:
        return None, bad
    u = backend().user_by_name(name)
    if not u:
        return None, bad
    if not security.verify_password(password, u.get('passwordHash')):
        return None, bad
    return public_user(u), None


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
    return info
