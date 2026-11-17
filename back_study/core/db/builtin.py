# -*- coding: utf-8 -*-
"""数据层 · 内置卡 —— 内容源 data/*.js 的解析与缓存。

缓存：以前每来一个请求就把 data/*.js 整个重新解析一遍（/api/cards、/api/stats、
复习队列都各解析一次）。文件级 mtime+size 做键，改一个字节就失效。
"""
import copy
import json
import os
import re
import sys
import time as _time

from .base import DATA_DIR, backend, read_text

# 缓存句柄：`_src_cache` / `_stale_cache` / `_all_cache`（后者在 cards.py）
# 三处失效判断共用同一把文件键 —— 「源文件变没变」只有一个答案。
_src_cache = {'key': None, 'cards': None}


def _src_files_key():
    """data/*.js 的文件指纹键（文件名 + mtime + size 元组）。

    `_src_cache` / `_stale_cache` / `_all_cache` 三处失效判断共用这一把键 ——
    「源文件变没变」只有一个答案，各写各的迟早口径分裂。
    ★ 用 os.scandir 而不是 listdir + getmtime/getsize：后者一个文件两次系统
      调用，11 个文件实测 3.9ms —— 这笔钱每次 all_cards() 都要付，把「命中
      不到 1ms」直接磨成 4ms。scandir 的 DirEntry.stat() 复用目录枚举带回来
      的文件属性，零额外系统调用，实测 0.11ms，键值与旧口径逐字段一致。
    """
    try:
        out = []
        with os.scandir(DATA_DIR) as it:
            for e in it:
                if e.name.endswith('.js'):
                    s = e.stat()
                    out.append((e.name, s.st_mtime, s.st_size))
        return tuple(sorted(out))
    except OSError:
        return None


def _source_cards_ref():
    """内置卡解析结果的**共享引用**（不拷贝）。**只读！要改先自己拷贝。**

    指纹比对、合并建缓存这类只读场景用它 —— 每次 deepcopy 是 17ms，
    正是 2026-10-13 性能排查里要杀的那块。对外的 load_source_cards()
    契约不变（仍返回深拷贝），怕调用方污染的场景照旧走它。
    """
    if not os.path.isdir(DATA_DIR):
        return []
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.js'))
    key = _src_files_key()
    if key is not None and _src_cache['key'] == key and _src_cache['cards'] is not None:
        return _src_cache['cards']

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
    return out


def load_source_cards():
    """读 data/*.js。文件形如 `var CARDS_X = [...]`，
    数组部分是严格 JSON 字面量（由 back_study/scripts/normalize-data.js 保证），
    用 raw_decode 从 '[' 处直接解析，不跑 JS 引擎。

    返回的是**深拷贝**：调用方随手改一下返回值不会污染缓存。
    （解析缓存本身在 _source_cards_ref 里，这里只负责拷贝那一层。）
    """
    return [copy.deepcopy(c) for c in _source_cards_ref()]


#: builtin_stale() 的判定缓存。一次指纹比对约 55ms，不该每个请求都付 ——
#: all_cards() / due_list() 每次都会问它一遍（2026-10-13 实测就是它把
#: 74ms 的 all_cards() 拖垮的）。失效论证（改这里先读完）：
#:   · 危险方向「False→True」（库里副本不再匹配文件）只会因 data/*.js
#:     变化触发 → 文件键变 → 必重算，不会漏；
#:   · 「True→False」只发生在 dbseed.py --sync 重灌之后，晚一点知道**只是
#:     多走文件回落，内容照旧正确**（内容是文件说了算）；
#:   · dbseed / fix 脚本是**别的进程**，本进程看不见它写库，所以再加 60s
#:     时效兜底 —— 同步完最多 1 分钟就切回 SQL 快路径。
_stale_cache = {'key': None, 'val': None, 'at': 0.0}
_STALE_TTL = 60


def builtin_stale():
    """MySQL 后端专用：库里的内置卡跟 data/*.js 对不对得上。

    True 的两种情况：表里一条都没有（还没跑 dbseed.py --sync）、
    或者指纹对不上（改了 data/*.js 没同步）。判定结果按文件键缓存 60s，
    失效论证见 `_stale_cache` 的注释。
    """
    st = backend()
    if not st.holds_builtin:
        return False
    key = _src_files_key()
    now = _time.time()
    if (_stale_cache['key'] == key and _stale_cache['val'] is not None
            and now - _stale_cache['at'] < _STALE_TTL):
        return _stale_cache['val']
    try:
        if not st.builtin_all():
            val = True
        else:
            # 传共享引用即可：mysql.builtin_stale 只读（算指纹 + 比 id 集合），
            # 不必付 load_source_cards() 的 17ms deepcopy
            val = bool(st.builtin_stale(_source_cards_ref()))
    except Exception as e:
        print('[db] 内置卡指纹检查失败: %s' % e, file=sys.stderr)
        val = True
    _stale_cache['key'] = key
    _stale_cache['val'] = val
    _stale_cache['at'] = now
    return val


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
