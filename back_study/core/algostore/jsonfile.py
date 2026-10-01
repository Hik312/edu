# -*- coding: utf-8 -*-
"""算法库 · JSON 文件实现 —— **默认后端**，也是 PG 连不上时的降级目标。

选它当默认值不是因为它好，是因为它**零依赖**：不装 psycopg、不连任何服务
也能把事件流跑起来。算法数据本来就是 append-only 的，二十张卡、单人使用，
文件完全扛得住。等真的要跨学生分析了再切 PG，接口一行都不用改。

三个文件落在 `data/store/`（和 progress.json 同目录，一样是**状态**不是内容）：

- `algo_events.json`  事件流，列表，append-only
- `algo_mastery.json` {user_id: {kc: p}}
- `algo_params.json`  {key: 拟合出来的参数}
"""

import json
import os
import threading
import time

from .base import AlgoStore

# ★ 这里必须退**三**层：本文件在 `back_study/core/algostore/jsonfile.py`，
# 退两层只到 `back_study/core`，于是 DATA_DIR 算成 `back_study/data` ——
# 事件流被写到项目里另一个目录，而 docstring 和 .gitignore 都指着
# `study/data/store/`。运维按文档去备份/排查时什么都找不到。
# 对照 store/jsonfile.py 的算法（它是 core/store/ 下的同名文件，退两层正好）。
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # core
ROOT = os.path.dirname(os.path.dirname(CORE_DIR))                        # 项目根
DATA_DIR = os.path.join(ROOT, 'data')
STORE_DIR = os.path.join(DATA_DIR, 'store')

_lock = threading.Lock()


def _next_id(rows):
    """事件 id 必须是**单调递增的整数**，不能用随机串。

    为什么：BKT 要按时间**严格回放**事件。同一天连着标三次，三条事件的 `at`
    完全相同，这时候排序只能靠 id —— 用 uuid 的话顺序是随机的，
    「先是会、然后忘了、又想起来」会被排成任意顺序，拟合出来的参数是错的。
    PG 那边 id 是 BIGSERIAL（自增整数），两边必须同序。
    """
    m = 0
    for r in rows:
        try:
            m = max(m, int(r.get('id') or 0))
        except (TypeError, ValueError):
            continue
    return m + 1


def _sort_key(r):
    try:
        i = int(r.get('id') or 0)
    except (TypeError, ValueError):
        i = 0
    return (str(r.get('at') or ''), i)


class JsonAlgoStore(AlgoStore):
    name = 'json'

    FILES = {
        'events': os.path.join(STORE_DIR, 'algo_events.json'),
        'mastery': os.path.join(STORE_DIR, 'algo_mastery.json'),
        'params': os.path.join(STORE_DIR, 'algo_params.json'),
    }

    def __init__(self):
        os.makedirs(STORE_DIR, exist_ok=True)

    # ---------------- 底层读写 ----------------
    def _read(self, kind, default):
        try:
            with open(self.FILES[kind], 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            # 文件不存在或内容坏了 → 返回默认值。
            # 事件流读不出来就是「没有历史」，不该让整个接口 500。
            return default

    def _write(self, kind, data):
        tmp = self.FILES[kind] + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.FILES[kind])          # 原子换，写一半断电不毁原文件

    # ---------------- 事件流 ----------------
    def events_append(self, ev):
        with _lock:
            rows = self._read('events', [])
            row = dict(ev)
            row['id'] = int(row.get('id') or 0) or _next_id(rows)
            rows.append(row)
            self._write('events', rows)
            return row

    def events_of(self, user_id, kc=None, card_id=None, limit=500):
        rows = self._read('events', [])
        out = [r for r in rows if str(r.get('user_id')) == str(user_id)]
        if kc:
            out = [r for r in out if r.get('kc') == kc]
        if card_id:
            out = [r for r in out if r.get('card_id') == card_id]
        out.sort(key=_sort_key)
        return out[-limit:] if limit and limit > 0 else out

    def events_count(self, user_id=None):
        rows = self._read('events', [])
        if user_id is None:
            return len(rows)
        return len([r for r in rows if str(r.get('user_id')) == str(user_id)])

    def events_clear(self, user_id=None):
        with _lock:
            if user_id is None:
                self._write('events', [])
                return
            rows = self._read('events', [])
            self._write('events', [r for r in rows
                                   if str(r.get('user_id')) != str(user_id)])

    # ---------------- 掌握度 ----------------
    def mastery_get(self, user_id, kc):
        v = self._read('mastery', {}).get(str(user_id), {}).get(kc)
        # 契约要求返回 float 或 None，而文件里存的是 {'p':…, 'at':…}
        return v.get('p') if isinstance(v, dict) else v

    def mastery_put(self, user_id, kc, p, extra=None):
        with _lock:
            m = self._read('mastery', {})
            slot = m.setdefault(str(user_id), {})
            slot[kc] = {'p': float(p), 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
            if extra:
                slot[kc].update(extra)
            self._write('mastery', m)

    def mastery_all(self, user_id):
        raw = self._read('mastery', {}).get(str(user_id), {})
        return {k: v.get('p') for k, v in raw.items()}

    def mastery_clear(self, user_id=None):
        with _lock:
            if user_id is None:
                self._write('mastery', {})
                return
            m = self._read('mastery', {})
            m.pop(str(user_id), None)
            self._write('mastery', m)

    # ---------------- 参数 ----------------
    def params_get(self, key, default=None):
        v = self._read('params', {}).get(key)
        return default if v is None else v

    def params_put(self, key, value):
        with _lock:
            p = self._read('params', {})
            p[key] = value
            self._write('params', p)

    def ping(self):
        return os.path.isdir(STORE_DIR)

    # 供 dbseed / 迁移脚本用
    def file_of(self, kind):
        return self.FILES.get(kind)
