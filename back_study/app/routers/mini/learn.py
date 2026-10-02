# -*- coding: utf-8 -*-
"""小程序端学习面：首页聚合 / 卡包分页 / 卡详情 / 复习队列与标记。

与 web 端对应接口的差异（为什么单独一组而不复用 /api/*）：
- /home 一次拿齐首页要的数字 + 分类树，手机弱网少跑几个来回；
- /cards 强制分页（web 是一次全量，手机列表装不下 400 张）；
- /cards/{id} 顺带返回 related 的标题（web 端图谱自己拉邻居），
  小程序详情页点「相关卡」不想多打一次请求。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import db
from ...deps import current_user
from ...schemas import PickIn, ProgressIn
from ..web.cards import _search_pool

router = APIRouter(prefix='/api/mini', tags=['小程序'])


def _brief(c, level=0):
    """列表项：手机列表只展示这些字段，mechanism/scene 大字段一律不带。"""
    return {'id': c['id'], 'domain': c.get('domain'), 'topicPath': c.get('topicPath'),
            'title': c.get('title'), 'oneLine': c.get('oneLine'),
            'tags': c.get('tags'), 'level': level,
            'deck': c.get('deck'), 'deckId': c.get('deckId'),
            '_custom': bool(c.get('_custom'))}


@router.get('/home', summary='首页聚合（统计 + 分类树 + 方向 + 今日清单）')
def home(user=Depends(current_user)):
    """小程序首页一个请求拿全部：数字、科目分类、学习方向入口、今日自选。

    directions 带 count（口径 = /api/directions，见那边注释）：卡包页的模块
    chips 要显示「12」，没卡的方向不该让人白点。
    """
    cards = db.all_cards()
    dirs_out = []
    for d in db.load_directions():
        kws = [str(k) for k in (d.get('keywords') or [])]
        dirs_out.append(dict(d, count=sum(1 for c in cards if db.card_hit(c, kws))))
    return {'ok': True,
            'stats': db.stats(),
            'catalog': db.load_catalog(),
            'directions': dirs_out,
            # 首页 CTA 要区分「按到期刷」和「按自选清单刷」，给 count 就够，
            # 清单 id 明细队列端点自己回，首页不需要。
            'pick': db.get_today_pick(user.get('id'))}


@router.get('/cards', summary='卡包列表（分页 + 搜索 + 方向）')
def list_cards(page: int = Query(1, ge=1),
               pageSize: int = Query(20, ge=1, le=50),
               subject: Optional[str] = Query(None),
               domain: Optional[str] = Query(None),
               dirs: str = Query('', description='学习方向 id，逗号分隔（模块筛，如 agent）'),
               q: str = Query('', description='关键词，空格分隔表示全都要命中'),
               idsOnly: str = Query('', description='=1 时只回 {ids: [...]}（详情页逐张浏览要一次拿全模块 id 列表，不吃分页）'),
               user=Depends(current_user)):
    cards = db.all_cards(subject=subject or None)
    if domain:
        cards = [c for c in cards if c.get('domain') == domain]
    if dirs:
        # 和 /api/review/due 同口径：筛在分页截断之前，否则第 2 页开始就串了。
        kws = db.direction_kws([d.strip() for d in dirs.split(',') if d.strip()])
        if kws:
            cards = [c for c in cards if db.card_hit(c, kws)]
    words = q.strip().lower().split()
    if words:
        cards = [c for c in cards if all(w in _search_pool(c) for w in words)]
    if idsOnly == '1':
        # 逐张浏览：detail 页要「上一张/下一张」，拿全量 id 一次定位，免得
        # 按页翻到边界还得回头补页。标题不带 —— 切卡时本来就逐张 /cards/{id} 拉。
        return {'ok': True, 'total': len(cards), 'ids': [c['id'] for c in cards]}
    prog = db.get_progress()
    total = len(cards)
    start = (page - 1) * pageSize
    page_items = cards[start:start + pageSize]
    items = [_brief(c, (prog.get(c['id']) or {}).get('level', 0)) for c in page_items]
    return {'ok': True, 'total': total, 'page': page, 'pageSize': pageSize,
            'hasMore': start + pageSize < total, 'cards': items}


@router.get('/cards/{cid}', summary='卡详情（含图示与相关卡标题）')
def get_card(cid: str, user=Depends(current_user)):
    c = next((x for x in db.all_cards() if x['id'] == cid), None)
    if not c:
        raise HTTPException(404, '卡片不存在')
    c = dict(c)
    c['level'] = (db.get_progress().get(cid) or {}).get('level', 0)
    # 相关卡直接带标题+理由：详情页底部「相关卡片」一屏点走，不再补请求。
    # related 元素是 {id,kind,note}（check.js 校验的契约），兼容纯 id 老数据。
    by_id = {x['id']: x for x in db.all_cards()}
    rel_brief = []
    for r in (c.get('related') or []):
        rid = r.get('id') if isinstance(r, dict) else r
        if rid in by_id:
            rel_brief.append({'id': rid, 'title': (by_id[rid] or {}).get('title', ''),
                              'kind': r.get('kind') if isinstance(r, dict) else None,
                              'note': r.get('note') if isinstance(r, dict) else None})
    c['relatedBrief'] = rel_brief
    return {'ok': True, 'card': c}


@router.get('/review/queue', summary='今日复习队列（学习页用）')
def review_queue(limit: int = Query(20, ge=1, le=100),
                 pick: str = Query('',
                                   description='=1 时只回今日自选清单里的卡（清单空回空队列，不当作退化成普通队列）'),
                 user=Depends(current_user)):
    if pick == '1':
        # 口径和 /api/review/due?pick=1 一致：due_list 全量排序后按清单 id 收窄，
        # 字段/顺序与普通队列同一套渲染，前端不用分两套。
        ids = set(db.get_today_pick(user.get('id')))
        items = [x for x in db.due_list(include_all=True) if x['card']['id'] in ids]
    else:
        items = db.due_list()
    items = items[:limit]
    queue = [{'id': x['card']['id'], 'title': x['card'].get('title'),
              'oneLine': x['card'].get('oneLine'),
              'domain': x['card'].get('domain'),
              'topicPath': x['card'].get('topicPath'),
              'level': x['level'],
              'nextAt': x['progress'].get('nextAt') if x['progress'] else None,
              'overdue': None if x['overdue'] == 999 else x['overdue']}
             for x in items]
    return {'ok': True, 'today': db.today_str(), 'total': len(queue),
            'queue': queue}


@router.get('/review/pick', summary='今日自选复习清单')
def get_pick(user=Depends(current_user)):
    ids = db.get_today_pick(user.get('id'))
    return {'ok': True, 'today': db.today_str(), 'ids': ids, 'total': len(ids)}


@router.put('/review/pick', summary='设置今日自选复习清单（整体覆盖）')
def put_pick(body: PickIn, user=Depends(current_user)):
    ids = db.set_today_pick(user.get('id'), body.ids)
    return {'ok': True, 'ids': ids, 'total': len(ids)}


# 静态段（/review/pick）注册在路径参数（/review/{cid}）之前：Starlette 按注册
# 顺序匹配，静态在前是路由的既定规矩 —— 方法不同本不会撞（PUT/GET vs POST），
# 但放前面保证将来若加 POST /review/pick 也不用回头查顺序。
@router.post('/review/{cid}', summary='标记掌握程度（翻卡后点会/模糊/不会）')
def review(cid: str, body: ProgressIn, user=Depends(current_user)):
    if body.level not in (1, 2, 3):
        raise HTTPException(400, 'level 必须是 1(不会) / 2(模糊) / 3(会)')
    if not any(x['id'] == cid for x in db.all_cards()):
        raise HTTPException(404, '卡片不存在')
    rec = db.set_level(cid, body.level, user_id=user.get('id'))
    return {'ok': True, 'id': cid, 'progress': rec}
