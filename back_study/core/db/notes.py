# -*- coding: utf-8 -*-
"""数据层 · 笔记域 —— 用户笔记与「卡片底部我的理解」同体系，全 per-user 隔离。"""
from .base import _next_daily_id, backend, today_str


def load_notes(user_id=None):
    return backend().notes_all(user_id)


def upsert_note(note, must_exist=False, user_id=None):
    """有 id 就更新，没有就新建。返回保存后的笔记。

    ★ `must_exist=True` 给**更新入口**（PUT /api/notes/{nid}）用：
    带 id 却在库里找不到，说明 id 拼错了或那条已被删掉 ——
    正确反应是 404。从前这里直接掉进新建分支，**沿用调用方传的 id**
    建出一条新笔记，接口回 200 一切正常，前端以为更新成功了，
    实际笔记越攒越多、且丢了一条。
    `must_exist=False`（默认）保持老行为不变，给新建入口用。

    ★ `user_id`：笔记是个人数据。查/写/删都限定在自己的桶里 ——
    别人笔记的 id 即使猜到也既查不到也删不掉（2026-10-03 加 user_id 隔离）。
    """
    lst = load_notes(user_id)
    nid = note.get('id')
    now = today_str()
    if nid:
        for n in lst:
            if n.get('id') == nid:
                merged = dict(n)
                merged.update(note)
                merged['updatedAt'] = now
                backend().note_put(merged, user_id)
                return merged
        if must_exist:
            raise KeyError(nid)
    nid = nid or _next_daily_id('note', lst, now)
    note = dict(note)
    note['id'] = nid
    note.setdefault('createdAt', now)
    note['updatedAt'] = now
    backend().note_put(note, user_id)
    return note


def delete_note(nid, user_id=None):
    st = backend()
    if any(n.get('id') == nid for n in st.notes_all(user_id)):
        st.note_del(nid, user_id)
        return True
    return False
