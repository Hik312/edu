# -*- coding: utf-8 -*-
"""JSON 文件后端 —— 默认后端，也是「MySQL 连不上」时的降级目标。

行为与接入数据库之前**逐字节一致**：还是那五个文件，还是原子替换写入。
这么做是为了让关掉数据库时系统完全回到老样子，而不是变成另一个系统。
"""
import datetime
import os
import threading

from .base import Store, read_json, write_json

CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # back_study/core
BACK_DIR = os.path.dirname(CORE_DIR)                                     # back_study
ROOT = os.path.dirname(BACK_DIR)                                         # study
DATA_DIR = os.path.join(ROOT, 'data')
STORE_DIR = os.path.join(DATA_DIR, 'store')

# ★ 一把全局锁，保护「读全量 → 改 → 写全量」这一个整体。
#
# 为什么必须有：端点是同步 `def`，FastAPI 会把它们丢进 40 槽线程池，
# 所以并发是常态而不是例外。而这里每个写方法都是读全量、改一处、再写回全量；
# `write_json` 只保证「文件不会写一半」（原子替换），**不保证互斥** ——
# 两个线程同时改同一份 JSON 时，后写的那个会把前一个的修改整份覆盖掉。
#
# 真实现象：同一秒内标记两张不同的卡（或开两个标签页各标一张）→
# 先标的那张进度凭空消失。json 后端是默认后端，也是 MySQL 不可用时的
# 降级目标，命中概率不低。
#
# 对照：algostore/jsonfile.py 和 store/mysql.py 本来就有锁，只有这里漏了。
# 用 RLock 而不是 Lock：user_put 内部会调 self.user_all()（也走锁），
# 普通 Lock 在这里会自死锁。
_lock = threading.RLock()

#: 匿名桶的键。真实 uid 都得转成 str 存（MySQL 那边id 是 int，
#: JSON 这边是字符串，不统一就会出现 '1' 和 1 两份进度）。
ANON = ''


def _uid(user_id):
    return ANON if user_id is None else str(user_id)


# 这里以前还有 FILE_PROGRESS / FILE_CUSTOM / FILE_DRAFTS / FILE_NOTES / FILE_DOCS
# 五个模块级常量，2026-09-26 删掉：真正生效的是下面 self.file 那个字典，
# 五个常量一个字都没被引用过。**文件清单只留一个真相源。**
# 注意 self.file 比它多一项 users —— 旧常量那份漏了 users，
# 正好说明「两份并列的清单」迟早会分叉。


class JsonFileStore(Store):

    name = 'json'
    holds_builtin = False

    def __init__(self, store_dir=None):
        self.dir = store_dir or STORE_DIR
        self.file = {
            'progress': os.path.join(self.dir, 'progress.json'),
            'cards.custom': os.path.join(self.dir, 'cards.custom.json'),
            'drafts': os.path.join(self.dir, 'drafts.json'),
            'notes': os.path.join(self.dir, 'notes.json'),
            'documents': os.path.join(self.dir, 'documents.json'),
            'users': os.path.join(self.dir, 'users.json'),
        }

    # ---------------- 读 ----------------
    def _read(self, kind, fallback):
        return read_json(self.file[kind], fallback)

    def _write(self, kind, obj):
        write_json(self.file[kind], obj, ensure_dir=self.dir)

    def custom_all(self):
        return self._read('cards.custom', [])

    def progress_all(self, user_id=None):
        return self._user_bucket('progress', user_id, {})

    def notes_all(self, user_id=None):
        return self._user_bucket('notes', user_id, [])

    def _user_bucket(self, kind, user_id, fallback):
        """读某个人的那一格。

        ★ 2026-10-03 起progress.json / notes.json **多了一层 user_id**：
        `{uid: {cid: rec}}` / `{uid: [note, ...]}`。以前是扁平的
        `{cid: rec}` / `[note, ...]`，等于全系统共用一份 —— 两个用户复习
        同一张卡就互相覆盖（不是"看见别人的数据"，是后写的把先写的静默顶掉）。

        兼容老格式：读出来若不像带 uid 的结构（旧版 progress 顶层全是
        card_id，notes 顶层是 list 而非 dict），就整体当成**匿名桶**
        （uid=''）返回。降级路径也必须能读老库 —— 不然关掉 MySQL 就不是
        "回到老样子"，而是数据凭空消失。
        """
        raw = self._read(kind, None)
        if raw is None:
            return fallback
        if kind == 'notes':
            if isinstance(raw, list):                 # 老格式：顶层就是列表
                return raw if not user_id else []
            return (raw.get(_uid(user_id)) or []) if isinstance(raw, dict) else list(raw)
        if not isinstance(raw, dict):
            return fallback
        # 老 progress 格式 = {card_id: {...}}；新 = {uid: {card_id: {...}}}
        if raw and all(isinstance(v, dict) and any(
                k in v for k in ('level', 'interval', 'reps', 'nextAt'))
                for v in raw.values()):
            return raw if not user_id else {}          # 老格式且要个人视图 → 没有个人数据
        return raw.get(_uid(user_id)) or {}

    def docs_all(self):
        return self._read('documents', [])

    def drafts_all(self):
        return self._read('drafts', [])

    # ---------------- 写：卡片 ----------------
    # 所有写方法都把「读-改-写」整体圈进 _lock，别只锁 _write：
    # 那样两个线程仍会各自读到同一份旧数据，后写的整份覆盖前一个。
    def custom_put(self, card):
        with _lock:
            lst = self.custom_all()
            for i, c in enumerate(lst):
                if c.get('id') == card.get('id'):
                    lst[i] = card
                    break
            else:
                lst.append(card)
            self._write('cards.custom', lst)

    def custom_del(self, cid):
        with _lock:
            self._write('cards.custom',
                        [c for c in self.custom_all() if c.get('id') != cid])

    def custom_replace(self, lst):
        with _lock:
            self._write('cards.custom', list(lst))

    # ---------------- 写：进度 ----------------
    def progress_put(self, cid, rec, user_id=None):
        with _lock:
            raw = self._read('progress', {})
            if not isinstance(raw, dict) or (raw and not all(
                    isinstance(v, dict) for v in raw.values())):
                raw = {}
            # 老格式是 {cid: rec}，会被误当成 {uid: ...} 的一层 ——
            # 先按新格式判断，认不出就包一层。这是唯一能原地升级的地方，
            # 因为只有写路径知道"这个文件以后都要按新格式存"。
            if raw and all(isinstance(v, dict) and any(
                    k in v for k in ('level', 'interval', 'reps', 'nextAt'))
                    for v in raw.values()):
                raw = {ANON: raw}
            raw.setdefault(_uid(user_id), {})[cid] = rec
            self._write('progress', raw)

    def progress_del(self, cid, user_id=None):
        with _lock:
            raw = self._read('progress', {})
            if not isinstance(raw, dict):
                return
            uid = _uid(user_id)
            if uid in raw and isinstance(raw[uid], dict):
                raw[uid].pop(cid, None)
                self._write('progress', raw)

    def progress_clear(self, user_id=None):
        with _lock:
            uid = _uid(user_id)
            if uid == '*':                             # 显式要清所有人
                self._write('progress', {})
                return
            raw = self._read('progress', {})
            if not isinstance(raw, dict):
                return
            if uid in raw:
                raw[uid] = {}
                self._write('progress', raw)

    # ---------------- 写：笔记 ----------------
    def note_put(self, note, user_id=None):
        with _lock:
            raw = self._read('notes', {})
            if isinstance(raw, list):# 老格式 → 包一层
                raw = {ANON: raw}
            elif not isinstance(raw, dict):
                raw = {}
            lst = raw.setdefault(_uid(user_id), [])
            for i, n in enumerate(lst):
                if n.get('id') == note.get('id'):
                    lst[i] = note
                    break
            else:
                lst.append(note)
            self._write('notes', raw)

    def note_del(self, nid, user_id=None):
        with _lock:
            raw = self._read('notes', {})
            if not isinstance(raw, dict):
                return
            uid = _uid(user_id)
            if uid in raw:
                raw[uid] = [n for n in raw[uid] if n.get('id') != nid]
                self._write('notes', raw)

    # ---------------- 写：文档 ----------------
    def doc_put(self, doc):
        with _lock:
            lst = self.docs_all()
            for i, d in enumerate(lst):
                if d.get('id') == doc.get('id'):
                    lst[i] = doc
                    break
            else:
                lst.append(doc)
            self._write('documents', lst)

    def doc_del(self, did):
        with _lock:
            self._write('documents',
                        [d for d in self.docs_all() if d.get('id') != did])

    # ---------------- 写：草稿 ----------------
    def draft_replace(self, lst):
        with _lock:
            self._write('drafts', list(lst))

    # ---------------- 用户 ----------------
    def user_all(self, with_secret=False):
        """★ 默认**剔除**口令哈希，`with_secret=True` 才原样给。

        这个参数以前被完全忽略（注释还写着「JSON 端用不上」），于是同一个
        `backend().user_all()` 在两个后端返回不同的东西：mysql 默认剔除
        password_hash，json 原样吐出来。目前唯一的调用方 db.user_all 外面
        套了 public_user，所以还没漏；但任何将来「顺手 return 上游对象」
        的代码在 JSON 后端下就会直接把口令哈希交出去（db.py 里那段注释
        正是在警告这件事）。签名一样、行为也得一样 —— 这正是这个项目
        对两个后端的硬要求。
        """
        rows = self._read('users', [])
        if with_secret:
            return rows
        return [{k: v for k, v in u.items() if k != 'passwordHash'} for u in rows]

    def user_by_name(self, username):
        # 大小写不敏感：用户在手机上手打，把 Wangtong 打成 wangtong 是常事，
        # 报「用户不存在」比让他登录成功糟糕得多。
        # ★ 这里必须 with_secret=True：登录要拿口令哈希去比对。
        # user_all() 默认剔除哈希（与 mysql 后端一致），所以不能调它。
        key = (username or '').strip().lower()
        if not key:
            return None
        for u in self.user_all(with_secret=True):
            if (u.get('username') or '').lower() == key:
                return u
        return None

    def user_get(self, uid):
        # 用 str 比较：id 在 JSON 里可能是数字、也可能被前端传成字符串，
        # 类型不一致会让「明明有这个用户却查不到」。
        # 同样要 with_secret=True：db.user_get 的调用方里既有只读出口
        # （外面套 public_user），也有鉴权链路。
        for u in self.user_all(with_secret=True):
            if str(u.get('id')) == str(uid):
                return u
        return None

    def user_put(self, user):
        """新建或更新，**返回 id**。

        返回值是必须的：JSON 后端没有 AUTO_INCREMENT，id 得自己发。
        如果这里不返回，db.create_user 拿到 None，token 里的 sub 就变成
        字符串 "None" —— 表现是「注册看着成功、一刷新就掉登录」，
        而且日志里一点错都没有。
        """
        with _lock:
            lst = self.user_all(with_secret=True)

            if user.get('id'):
                for i, u in enumerate(lst):
                    if str(u.get('id')) == str(user['id']):
                        lst[i] = user
                        break
                else:
                    lst.append(user)
                self._write('users', lst)
                return int(user['id'])

            # 自增 = 现有最大 id + 1。**不复用被删掉的 id**：id 一旦复用，
            # 历史数据（progress.user_id、attempt.user_id）会指到另一个人身上
            nid = max([int(u.get('id') or 0) for u in lst] or [0]) + 1

            rec = dict(user)
            rec['id'] = nid
            # MySQL 那边有 DEFAULT CURRENT_TIMESTAMP，这里得自己补，
            # 不然同一个字段两个后端一个有值一个没有
            rec.setdefault('createdAt',
                           datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            lst.append(rec)
            self._write('users', lst)
            return nid

    def user_count(self):
        return len(self.user_all())

    # ---------------- 状态 ----------------
    def info(self):
        files = {}
        for k, p in self.file.items():
            files[k] = os.path.getsize(p) if os.path.exists(p) else 0
        return {'store': self.name, 'dir': self.dir, 'bytes': files,
                'users': self.user_count()}
