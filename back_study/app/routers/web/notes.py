# -*- coding: utf-8 -*-
"""笔记：独立笔记 + 卡片底部的「我的理解」（后者本质上就是挂了 cardId 的笔记）。

笔记没有「离线副本」这一层：前端一律走接口读写，所以换设备看到的是同一份。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import db
from ...deps import current_user
from ...schemas import NoteIn

router = APIRouter(prefix='/api', tags=['笔记'])

# ★ 笔记是**个人数据**：5 个端点全部要求登录。
# 曾经它们不需要登录，而 main.py 的 CORS 又是 allow_origins=['*'] ——
# 于是用户浏览任意网页时，那个页面的 JS 就能 fetch 走全部笔记正文并删掉它们。
# 注意 GET 也算：简单请求不触发预检，跨源也能读到响应体。


@router.get('/notes', summary='笔记列表')
def list_notes(category: Optional[str] = Query(None),
               subject: Optional[str] = Query(None),
               cardId: Optional[str] = Query(None, description='只看某张卡下面的理解'),
               q: str = Query('', description='搜标题 / 正文 / 标签'),
               user=Depends(current_user)):
    notes = db.load_notes(user.get('id'))
    if category:
        notes = [n for n in notes if n.get('category') == category]
    if subject:
        notes = [n for n in notes if n.get('subject') == subject]
    if cardId:
        notes = [n for n in notes if n.get('cardId') == cardId]
    kw = (q or '').strip().lower()
    if kw:
        notes = [n for n in notes if kw in ((n.get('title') or '') + ' ' + (n.get('body') or '')
                                            + ' ' + ' '.join(n.get('tags') or [])).lower()]
    notes.sort(key=lambda n: n.get('updatedAt') or '', reverse=True)   # 最近改的排前面
    return {'ok': True, 'total': len(notes), 'notes': notes}


@router.post('/notes', summary='新建或更新笔记')
def upsert_note(body: NoteIn, user=Depends(current_user)):
    n = body.model_dump(exclude_none=True)
    if not (n.get('title') or '').strip() and not (n.get('body') or '').strip():
        raise HTTPException(400, '标题和正文不能都为空')
    return {'ok': True, 'note': db.upsert_note(n, user_id=user.get('id'))}


@router.get('/notes/{nid}', summary='单条笔记')
def get_note(nid: str, user=Depends(current_user)):
    n = next((x for x in db.load_notes(user.get('id')) if x.get('id') == nid), None)
    if not n:
        raise HTTPException(404, '笔记不存在')
    return {'ok': True, 'note': n}


@router.put('/notes/{nid}', summary='修改笔记')
def update_note(nid: str, body: NoteIn, user=Depends(current_user)):
    patch = body.model_dump(exclude_none=True)
    patch['id'] = nid                       # 路径里的 id 说了算
    # ★ must_exist=True：这是**更新**入口，id 不存在必须 404。
    #   前一个版本让它掉进新建分支 —— 沿用路径里的 id 凭空建出一条笔记，
    #   回 200 一切正常，前端以为改成功了。笔记路由里 GET 已经是 404 语义，
    #   PUT 却会静默新建，两条路径对同一种情况给两种答案。
    try:
        note = db.upsert_note(patch, must_exist=True, user_id=user.get('id'))
    except KeyError:
        raise HTTPException(404, '笔记不存在')
    return {'ok': True, 'note': note}


@router.delete('/notes/{nid}', summary='删除笔记')
def delete_note(nid: str, user=Depends(current_user)):
    # ★ 从前是 `return {'ok': db.delete_note(nid)}` —— 删不存在的笔记会得到
    #   HTTP 200 + ok:false，而 api/client.js 只对 HTTP 错误 reject、
    #   ok:false 是直接 resolve的 → 前端无条件当删除成功，还会把列表长度减一。
    #   「删一条不存在的笔记」不是成功，是 404（和GET/PUT 同一条路径上一致）。
    #   幂等性靠前端做（乐观更新失败后重拉列表），不该靠后端回200 含糊过去。
    if not db.delete_note(nid, user_id=user.get('id')):
        raise HTTPException(404, '笔记不存在')
    return {'ok': True}
