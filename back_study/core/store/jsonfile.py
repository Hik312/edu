# -*- coding: utf-8 -*-
"""JSON 文件后端 —— 默认后端，也是「MySQL 连不上」时的降级目标。

行为与接入数据库之前**逐字节一致**：还是那五个文件，还是原子替换写入。
这么做是为了让关掉数据库时系统完全回到老样子，而不是变成另一个系统。
"""
import datetime
import os

from .base import Store, read_json, write_json

CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # back_study/core
BACK_DIR = os.path.dirname(CORE_DIR)                                     # back_study
ROOT = os.path.dirname(BACK_DIR)                                         # study
DATA_DIR = os.path.join(ROOT, 'data')
STORE_DIR = os.path.join(DATA_DIR, 'store')

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

    def progress_all(self):
        return self._read('progress', {})

    def notes_all(self):
        return self._read('notes', [])

    def docs_all(self):
        return self._read('documents', [])

    def drafts_all(self):
        return self._read('drafts', [])

    # ---------------- 写：卡片 ----------------
    def custom_put(self, card):
        lst = self.custom_all()
        for i, c in enumerate(lst):
            if c.get('id') == card.get('id'):
                lst[i] = card
                break
        else:
            lst.append(card)
        self._write('cards.custom', lst)

    def custom_del(self, cid):
        self._write('cards.custom', [c for c in self.custom_all() if c.get('id') != cid])

    def custom_replace(self, lst):
        self._write('cards.custom', list(lst))

    # ---------------- 写：进度 ----------------
    def progress_put(self, cid, rec):
        m = self.progress_all()
        m[cid] = rec
        self._write('progress', m)

    def progress_del(self, cid):
        m = self.progress_all()
        m.pop(cid, None)
        self._write('progress', m)

    def progress_clear(self):
        self._write('progress', {})

    # ---------------- 写：笔记 ----------------
    def note_put(self, note):
        lst = self.notes_all()
        for i, n in enumerate(lst):
            if n.get('id') == note.get('id'):
                lst[i] = note
                break
        else:
            lst.append(note)
        self._write('notes', lst)

    def note_del(self, nid):
        self._write('notes', [n for n in self.notes_all() if n.get('id') != nid])

    # ---------------- 写：文档 ----------------
    def doc_put(self, doc):
        lst = self.docs_all()
        for i, d in enumerate(lst):
            if d.get('id') == doc.get('id'):
                lst[i] = doc
                break
        else:
            lst.append(doc)
        self._write('documents', lst)

    def doc_del(self, did):
        self._write('documents', [d for d in self.docs_all() if d.get('id') != did])

    # ---------------- 写：草稿 ----------------
    def draft_replace(self, lst):
        self._write('drafts', list(lst))

    # ---------------- 用户 ----------------
    def user_all(self, with_secret=False):
        # with_secret 这个参数 JSON 端用不上（本来就是原样读文件），
        # 但**签名必须和 MySQL 后端一致** —— 否则换个后端就 TypeError，
        # 而这类错误只有在真的切库那一刻才暴露
        return self._read('users', [])

    def user_by_name(self, username):
        # 大小写不敏感：用户在手机上手打，把 Wangtong 打成 wangtong 是常事，
        # 报「用户不存在」比让他登录成功糟糕得多
        key = (username or '').strip().lower()
        if not key:
            return None
        for u in self.user_all():
            if (u.get('username') or '').lower() == key:
                return u
        return None

    def user_get(self, uid):
        # 用 str 比较：id 在 JSON 里可能是数字、也可能被前端传成字符串，
        # 类型不一致会让「明明有这个用户却查不到」
        for u in self.user_all():
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
        lst = self.user_all()

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
        # 历史数据（将来 progress.user_id、attempt.user_id）会指到另一个人身上
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
