# -*- coding: utf-8 -*-
"""笔记：独立笔记 + 卡片底部的「我的理解」（后者本质上就是挂了 cardId 的笔记）。

笔记没有「离线副本」这一层：前端一律走接口读写，所以换设备看到的是同一份。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import db
from ..schemas import NoteIn

router = APIRouter(prefix='/api', tags=['笔记'])


@router.get('/notes', summary='笔记列表')
def list_notes(category: Optional[str] = Query(None),
               subject: Optional[str] = Query(None),
               cardId: Optional[str] = Query(None, description='只看某张卡下面的理解'),
               q: str = Query('', description='搜标题 / 正文 / 标签')):
    notes = db.load_notes()
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
def upsert_note(body: NoteIn):
    n = body.model_dump(exclude_none=True)
    if not (n.get('title') or '').strip() and not (n.get('body') or '').strip():
        raise HTTPException(400, '标题和正文不能都为空')
    return {'ok': True, 'note': db.upsert_note(n)}


@router.get('/notes/{nid}', summary='单条笔记')
def get_note(nid: str):
    n = next((x for x in db.load_notes() if x.get('id') == nid), None)
    if not n:
        raise HTTPException(404, '笔记不存在')
    return {'ok': True, 'note': n}


@router.put('/notes/{nid}', summary='修改笔记')
def update_note(nid: str, body: NoteIn):
    patch = body.model_dump(exclude_none=True)
    patch['id'] = nid                       # 路径里的 id 说了算
    return {'ok': True, 'note': db.upsert_note(patch)}


@router.delete('/notes/{nid}', summary='删除笔记')
def delete_note(nid: str):
    # 返回值原本就是「删掉没有」，保持原样：前端拿它判断要不要提示
    return {'ok': db.delete_note(nid)}
