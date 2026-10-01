# -*- coding: utf-8 -*-
"""MySQL 初始化 / 内容同步 / JSON 存量数据迁移。

用法（都在项目根 study/ 下跑）：

    python back_study/scripts/dbseed.py --status        # 看现在连的是哪个库、库里有什么
    python back_study/scripts/dbseed.py --sync          # 建库建表 + 把 data/*.js 灌进去
    python back_study/scripts/dbseed.py --sync --force  # 无视指纹，强制重灌内置卡
    python back_study/scripts/dbseed.py --import-json   # 把 data/store/*.json 的存量数据搬进 MySQL
    python back_study/scripts/dbseed.py --drop --yes    # 删库（真的会删，别手滑）

**--sync 与 --import-json 的区别，别搞混**：
    --sync       管的是**内容**（卡片），源头是 data/*.js，文件说了算，
                 库里的数据随时可以被覆盖，重跑无副作用。
    --import-json 管的是**状态**（复习进度、笔记、文档、草稿、自定义卡），
                 源头是 data/store/*.json，这是**单向**的：
                 搬进 MySQL 之后那份 JSON 就不再被读了。
                 所以它会先备份一份 .bak，且默认**跳过已存在的行**，
                 免得第二次跑把库里的新状态覆盖回老的。

零依赖以外的东西（pymysql）只有这一个脚本需要，且只在真用 MySQL 时。
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))            # back_study/scripts
BACK_DIR = os.path.dirname(HERE)                             # back_study
CORE_DIR = os.path.join(BACK_DIR, 'core')
ROOT = os.path.dirname(BACK_DIR)                             # study
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

import store as store_pkg                                     # noqa: E402
import db                                                     # noqa: E402

JSON_DIR = os.path.join(ROOT, 'data', 'store')


def hr(t):
    print('\n' + '=' * 66)
    print(t)
    print('=' * 66)


def need_mysql():
    """强制要一个 MySQL 后端。

    这里**不用** store_pkg.get()：工厂在「库还不存在」时会判定不可用
    并回退到 JSON，而本脚本的 --sync 恰恰就是要把库建出来 —— 用工厂的话
    第一次跑永远建不了库（先有鸡先有蛋）。
    """
    if store_pkg.wanted_backend() != 'mysql':
        hr('配置里没开 MySQL')
        print('  当前 STORE=%s' % store_pkg.wanted_backend())
        print('\n把 back_study/config.local.json 里的 STORE 改成 mysql，')
        print('或者启动时设一下环境变量：STORE=mysql python back_study/scripts/dbseed.py --sync')
        sys.exit(2)
    try:
        st = store_pkg.make_mysql()
        # 用 ping_server 而不是 ping：库还没建的时候带 database 的连接会
        # 直接报 1049，而我们现在就是要连上去把库建出来
        ver = st.ping_server()
        print('MySQL 服务可用，版本 %s' % ver)
    except ImportError as e:
        hr('没装 pymysql')
        print('  %s' % e)
        print('\n装一下：back_study/.venv/Scripts/python.exe -m pip install pymysql')
        print('（或者用系统 Python：python -m pip install pymysql）')
        sys.exit(2)
    except Exception as e:
        hr('连不上 MySQL')
        print('  %s: %s' % (type(e).__name__, str(e)[:200]))
        print('\n挨个查：① 服务起来了吗（net start | grep -i mysql）'
              '② config.local.json 里的端口/账号/密码对不对')
        sys.exit(2)
    return st


def cmd_status(st):
    hr('当前后端')
    info = store_pkg.info()
    for k in ('store', 'want', 'db', 'host', 'port', 'user', 'version',
              'cards', 'progress', 'notes', 'documents', 'drafts',
              'builtinDigest', 'degraded'):
        if info.get(k) is not None:
            print('  %-16s %s' % (k, info[k]))
    if info.get('configFile'):
        print('  %-16s %s' % ('configFile', info['configFile']))

    hr('内置卡：库 vs 文件')
    si = db.storage_info().get('builtin') or {}
    print('  data/*.js 里   %s 张' % si.get('inFile'))
    print('  库里            %s 张' % si.get('inDb'))
    print('  是否过期        %s' % ('是 —— 跑 --sync' if si.get('stale') else '否'))
    print('  内容权威来源    %s' % si.get('authority'))


def cmd_sync(st, force=False):
    hr('建库建表')
    r = st.init_schema()
    print('  DDL 执行完毕，中文全文索引: %s' % ('已建' if r.get('fulltext') else '未建'))
    if not r.get('fulltext'):
        print('  （%s —— 不影响功能，关键词搜索会退化成 LIKE）'
              % r.get('fulltextError', '原因未知'))

    hr('灌内置卡（data/*.js → cards 表）')
    cards = db.load_source_cards()
    if not cards:
        print('  data/*.js 里一张卡都没读到，检查一下文件格式')
        return 1
    res = st.seed_builtin(cards, force=force)
    if res.get('skipped'):
        print('  内容指纹一致，跳过（库里已是最新）。要强制重灌加 --force')
    else:
        print('  写入 %s 张，清掉 %s 张（源码里已删除的）' % (res['seeded'], res['removed']))
    print('  新指纹 %s' % res['digest'])

    hr('自定义卡')
    custom = db.load_custom()
    for c in custom:
        st.custom_put(c)
    print('  同步 %s 张自定义卡' % len(custom))
    return 0


def _backup(path):
    if not os.path.exists(path):
        return None
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    dst = path + '.bak-' + stamp
    shutil.copy2(path, dst)
    return dst


def cmd_import_json(st, overwrite=False):
    hr('把 data/store/*.json 的存量数据搬进 MySQL')
    print('  这是**单向**操作：搬完之后 JSON 那份就不再被读了。')
    print('  会先备份成 .bak-时间戳，默认跳过库里已有的行（不覆盖新状态）。\n')

    files = {'progress': 'progress.json', 'custom': 'cards.custom.json',
             'notes': 'notes.json', 'docs': 'documents.json',
             'drafts': 'drafts.json', 'users': 'users.json'}
    raw = {}
    for k, fn in files.items():
        p = os.path.join(JSON_DIR, fn)
        if not os.path.exists(p):
            raw[k] = None
            print('  %-18s 不存在，跳过' % fn)
            continue
        try:
            with open(p, 'r', encoding='utf-8') as f:
                raw[k] = json.load(f)
        except Exception as e:
            raw[k] = None
            print('  %-18s 读失败: %s' % (fn, e))
            continue
        n = len(raw[k]) if raw[k] is not None else 0
        print('  %-18s %s 条' % (fn, n))

    if not any(v for v in raw.values()):
        print('\n  JSON 里没有数据，不用搬 —— 直接 --sync 开始用 MySQL 就行。')
        return 0

    hr('开始搬运')

    # --- 进度 ---
    prog = raw.get('progress') or {}
    have = st.progress_all()
    n = 0
    for cid, rec in prog.items():
        if cid in have and not overwrite:
            continue
        st.progress_put(cid, rec)
        n += 1
    print('  进度        %s 条（库里原有 %s 条，跳过 %s 条）'
          % (n, len(have), len(prog) - n))

    # --- 自定义卡 ---
    cs = raw.get('custom') or []
    have = set(c.get('id') for c in st.custom_all())
    n = 0
    for c in cs:
        if c.get('id') in have and not overwrite:
            continue
        st.custom_put(c)
        n += 1
    print('  自定义卡    %s 张' % n)

    # --- 笔记 ---
    ns = raw.get('notes') or []
    have = set(x.get('id') for x in st.notes_all())
    n = 0
    for x in ns:
        if x.get('id') in have and not overwrite:
            continue
        st.note_put(x)
        n += 1
    print('  笔记        %s 条' % n)

    # --- 文档 ---
    ds = raw.get('docs') or []
    have = set(x.get('id') for x in st.docs_all())
    n = 0
    for x in ds:
        if x.get('id') in have and not overwrite:
            continue
        st.doc_put(x)
        n += 1
    print('  文档        %s 份（含全部章节）' % n)

    # --- 草稿 ---
    drafts = raw.get('drafts') or []
    if drafts:
        have = set(x.get('id') for x in st.drafts_all())
        merged = [x for x in st.drafts_all()] + \
                 [x for x in drafts if x.get('id') not in have or overwrite]
        st.draft_replace(merged)
    print('  草稿        %s 条' % len(drafts))

    # --- 账号 ---
    #
    # 这一段以前是漏的：files 里没有 users.json，于是切到 MySQL 之后
    # 账号一个都不过去，表现是「服务能起、卡片能看，就是登录 500 / 登不进」。
    #
    # ⚠️ 不能图省事直接 `st.user_put(u)` —— user_put 见到 id 就走 UPDATE，
    # 往一张空表上 UPDATE 是**静默影响 0 行**，一条也进不去，还不报错。
    # 所以这里按用户名逐个对齐：库里没有就**剥掉 id** 让它走 INSERT
    # （由 AUTO_INCREMENT 重新发号），库里已有才带上库里的真实 id 去 UPDATE。
    users = raw.get('users') or []
    existing = {}
    for u in st.user_all(with_secret=True):
        existing[(u.get('username') or '').lower()] = u
    added = updated = skipped = 0
    for u in users:
        name = (u.get('username') or '').strip()
        if not name:
            continue
        row = dict(u)
        cur = existing.get(name.lower())
        if cur:
            if not overwrite:
                skipped += 1
                continue
            row['id'] = cur.get('id')      # 带真实 id 才是有效 UPDATE
            updated += 1
        else:
            row.pop('id', None)            # 不带 id 才会 INSERT
            added += 1
        st.user_put(row)
    print('  账号        新增 %s 个，更新 %s 个，跳过 %s 个（库里原有 %s 个）'
          % (added, updated, skipped, len(existing)))

    hr('备份 JSON（搬完之后它们不再被读）')
    for fn in files.values():
        b = _backup(os.path.join(JSON_DIR, fn))
        if b:
            print('  %s → %s' % (fn, os.path.basename(b)))
    return 0


def cmd_drop(st, yes=False):
    if not yes:
        hr('拒绝执行')
        print('  --drop 会删掉整个库，必须再加 --yes 才动手。')
        return 1
    cfg = st.cfg
    name = cfg['database']
    hr('删库 %s' % name)
    boot = dict(cfg)
    boot.pop('database')
    boot.pop('cursorclass')
    conn = st._pymysql.connect(**boot)
    try:
        with conn.cursor() as cur:
            cur.execute('DROP DATABASE IF EXISTS `%s`' % name)
    finally:
        conn.close()
    print('  已删除。重建：python back_study/scripts/dbseed.py --sync')
    return 0


def main():
    ap = argparse.ArgumentParser(
        description='初始化 / 同步原理卡片平台的 MySQL 后端',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument('--status', action='store_true', help='只看状态，不改任何东西')
    ap.add_argument('--sync', action='store_true', help='建库建表 + 灌 data/*.js（幂等）')
    ap.add_argument('--force', action='store_true', help='配合 --sync：无视指纹强制重灌')
    ap.add_argument('--import-json', dest='import_json', action='store_true',
                    help='把 data/store/*.json 的存量数据单向搬进 MySQL')
    ap.add_argument('--overwrite', action='store_true',
                    help='配合 --import-json：库里已有的行也用 JSON 覆盖')
    ap.add_argument('--drop', action='store_true', help='删库（需再加 --yes）')
    ap.add_argument('--yes', action='store_true', help='确认危险操作')
    a = ap.parse_args()

    if not any([a.status, a.sync, a.import_json, a.drop]):
        a.status = True                      # 不带参数就叫它看一眼状态

    st = need_mysql()

    if a.status:
        cmd_status(st)
    if a.sync:
        cmd_sync(st, force=a.force)
    if a.import_json:
        cmd_import_json(st, overwrite=a.overwrite)
    if a.drop:
        return cmd_drop(st, yes=a.yes)

    if a.sync and not a.status:
        print()
        cmd_status(st)
    return 0


if __name__ == '__main__':
    sys.exit(main())
