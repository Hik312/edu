# -*- coding: utf-8 -*-
"""复习进度与统计。间隔调度（SM-2）本身在 db.schedule()，这里只做搬运。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import db
from ..deps import current_user
from ..schemas import ProgressIn

router = APIRouter(prefix='/api', tags=['学习'])

_LEVEL_HINT = 'level 必须是 1(不会) / 2(模糊) / 3(会)'


@router.get('/progress', summary='全部进度')
def get_progress():
    return {'ok': True, 'progress': db.get_progress()}


@router.delete('/progress', summary='清空全部进度')
def clear_progress():
    db.clear_progress()
    return {'ok': True}


@router.put('/progress/{cid}', summary='标记某张卡的掌握程度')
def set_progress(cid: str, body: ProgressIn, user=Depends(current_user)):
    """标记后返回算出来的下次复习时间。

    注意：`level` 的取值检查放在这里手动做，而不是用 `Field(ge=1, le=3)` ——
    那样 FastAPI 会回 422，老前端只认 400。校验方式换了但状态码不能换。

    ★ 这个端点**必须登录**：复习事件要记到具体的人头上，否则 BKT 算出来的
    掌握度是所有人的混合 —— 那是错的，而且错得看不出来。
    """
    if body.level not in (1, 2, 3):
        raise HTTPException(400, _LEVEL_HINT)
    rec = db.set_level(cid, body.level, user_id=user.get('id'))
    return {'ok': True, 'id': cid, 'progress': rec}


@router.get('/review/events', summary='我的复习事件流')
def my_events(limit: int = Query(200, ge=1, le=2000),
              card_id: Optional[str] = Query(None),
              user=Depends(current_user)):
    """复习历史，按时间正序。这是给知识追踪模型（BKT/DKT）喂的数据。

    现在只写不读 —— 等 `algo/bkt.py` 落地，掌握度就是从这里回放算出来的。
    """
    return {'ok': True,
            'count': db.events_count(user.get('id')),
            'events': db.events_of(user.get('id'), card_id=card_id,
                                   limit=limit)}


@router.delete('/progress/{cid}', summary='重置某张卡的进度')
def reset_progress(cid: str):
    db.reset_progress(cid)
    return {'ok': True}


@router.get('/review/due', summary='今日复习队列')
def review_due(limit: int = Query(50, ge=1, le=500),
               domain: Optional[str] = Query(None),
               dirs: Optional[str] = Query(
                   None, description='学习方向 id，逗号分隔（data/directions.js）。只推这些方向的卡'),
               include_all: str = Query('', alias='all',
                                        description='=1 时把没到期的也带上（「全部过一遍」用）')):
    # 形参叫 include_all、查询串仍叫 ?all=1：alias 保住了对外契约，
    # 又不至于在函数体里盖掉内置的 all()
    items = db.due_list(domain=domain or None, include_all=(include_all == '1'))
    if dirs:
        # 方向筛必须在截断**之前**：先按方向过滤全量到期卡，再取 limit。
        # 顺序反了就是先拿满 limit 再丢，方向卡会被排在后面的基本卡挤出队列。
        kws = db.direction_kws([d.strip() for d in dirs.split(',') if d.strip()])
        if kws:                        # 传了查不到的方向 id → 当没筛，别返回空队列
            items = [x for x in items if db.card_hit(x['card'], kws)]
    items = items[:limit]
    queue = [{'id': x['card']['id'], 'title': x['card'].get('title'),
              'domain': x['card'].get('domain'), 'oneLine': x['card'].get('oneLine'),
              'level': x['level'],
              'nextAt': x['progress'].get('nextAt') if x['progress'] else None,
              # overdue == 999 是 db 层表示「从没复习过」的哨兵值，不该漏给前端
              'overdue': None if x['overdue'] == 999 else x['overdue']}
             for x in items]
    return {'ok': True, 'today': db.today_str(), 'total': len(queue), 'queue': queue}


@router.get('/stats', summary='统计')
def stats():
    """总卡数、今日待复习、掌握分布 —— 首页那几个数字。"""
    return {'ok': True, 'stats': db.stats()}
