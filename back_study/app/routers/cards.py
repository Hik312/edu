# -*- coding: utf-8 -*-
"""卡片读写。

只读卡片来自 data/*.js（可被人手改），能被接口改的只有 `data/store/cards.custom.json`
里那份自定义卡 —— 这条边界保留着：内置卡是「源码」，自定义卡是「数据」，
混在一起以后就没法用 git 管理内容了。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import db
import importer
from ..deps import current_user
from ..schemas import CardIn

router = APIRouter(prefix='/api', tags=['卡片'])

# ★ 读写卡片全部要求登录：内置卡是源码（改不了），但自定义卡的增删改
# 曾经匿名可用 —— 任何网页/局域网设备都能删掉你的卡。


def _search_pool(c):
    """把一张卡能被打中的字段拼成一坨，供关键词匹配。"""
    return ' '.join([
        c.get('title', ''), c.get('oneLine', ''), c.get('analogy', ''),
        ' '.join(c.get('keywords') or []), ' '.join(c.get('mechanism') or []),
        ' '.join(c.get('scene') or []),
    ]).lower()


@router.get('/cards', summary='卡片列表 / 搜索')
def list_cards(category: Optional[str] = Query(None, description='按一级分类过滤'),
               subject: Optional[str] = Query(None, description='按科目过滤'),
               domain: Optional[str] = Query(None, description='按领域过滤，如 工作 / 考研'),
               deck_id: Optional[str] = Query(None, alias='deckId',
                                              description='按卡片组过滤（文档导出的卡）'),
               q: str = Query('', description='关键词，空格分隔表示「全都要命中」'),
               brief: str = Query('', description='=1 只回 id/title 等轻字段，列表页用'),
               user=Depends(current_user)):
    cards = db.all_cards(category=category or None, subject=subject or None)

    if domain:
        cards = [c for c in cards if c.get('domain') == domain]
    if deck_id:
        # 按 deckId 精确匹配而不是按组名：同名文档可能传两份，组名会撞
        cards = [c for c in cards if c.get('deckId') == deck_id]

    words = (q or '').strip().lower().split()
    if words:
        cards = [c for c in cards if all(w in _search_pool(c) for w in words)]

    # 带上复习档位：卡片墙和详情页的「未标记/模糊/会」徽标要真值，
    # 以前接口不返回 level，前端 `card.level ?? 0` 恒为未标记 —— 标过的也显示没标。
    prog = db.get_progress()
    for c in cards:
        c['level'] = (prog.get(c['id']) or {}).get('level', 0)

    if brief == '1':                      # 列表页用：省掉 mechanism/scene 那些大字段
        cards = [{'id': c['id'], 'domain': c.get('domain'), 'topicPath': c.get('topicPath'),
                  'title': c.get('title'), 'oneLine': c.get('oneLine'), 'tags': c.get('tags'),
                  'level': c.get('level', 0),
                  # 组名 / 组 id 要带上：卡片墙按组筛和显示「来自哪份文档」都靠它
                  'deck': c.get('deck'), 'deckId': c.get('deckId'),
                  '_custom': bool(c.get('_custom'))} for c in cards]

    return {'ok': True, 'total': len(cards), 'cards': cards}


@router.post('/cards', summary='新建自定义卡', status_code=200)
def create_card(body: CardIn, user=Depends(current_user)):
    # exclude_none：没发的字段就别落盘成 null，否则卡片详情里会多出一堆空行
    c = body.model_dump(exclude_none=True)
    miss = importer.validate(dict(c, scene=c.get('scene') or ['（待补充）', '（待补充）']))
    if miss:
        raise HTTPException(400, '缺少字段: ' + ' / '.join(miss))
    custom = db.load_custom()
    if any(x.get('id') == c.get('id') for x in custom):
        raise HTTPException(409, 'id 已存在')
    custom.append(c)
    db.save_custom(custom)
    return {'ok': True, 'card': c}


@router.get('/cards/{cid}', summary='单张卡详情')
def get_card(cid: str, user=Depends(current_user)):
    c = next((x for x in db.all_cards() if x['id'] == cid), None)
    if not c:
        raise HTTPException(404, '卡片不存在')
    c = dict(c)
    c['level'] = (db.get_progress().get(cid) or {}).get('level', 0)
    return {'ok': True, 'card': c}


@router.put('/cards/{cid}', summary='修改自定义卡')
def update_card(cid: str, body: CardIn, user=Depends(current_user)):
    # exclude_unset：这是 PATCH 语义，只动发过来的键。
    # 用 exclude_none 会把手滑发成 null 的字段一起写进去。
    patch = body.model_dump(exclude_unset=True)
    custom = db.load_custom()
    for i, x in enumerate(custom):
        if x.get('id') == cid:
            custom[i].update(patch)
            custom[i]['id'] = cid            # id 不许被 patch 改掉
            db.save_custom(custom)
            return {'ok': True, 'card': custom[i]}
    raise HTTPException(404, '只能修改自定义卡（内置卡在 data/*.js 里改）')


@router.delete('/cards/{cid}', summary='删除自定义卡')
def delete_card(cid: str, user=Depends(current_user)):
    # 返回值保持 {ok:True}：删一张不存在的卡不算错（幂等），前端不区分。
    # 但要把「到底删掉了没有」暴露出去 —— 否则「我明明点了删除，卡片还在」
    # （内置卡在 data/*.js 里，接口删不掉）会变成一个查不出原因的现象。
    before = len(db.load_custom())
    db.save_custom([x for x in db.load_custom() if x.get('id') != cid])
    return {'ok': True, 'removed': before - len(db.load_custom())}
