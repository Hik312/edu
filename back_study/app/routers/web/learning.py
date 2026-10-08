# -*- coding: utf-8 -*-
"""复习进度与统计。间隔调度（SM-2）本身在 db.schedule()，这里只做搬运。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import db
from ...deps import current_user
from ...schemas import PickIn, ProgressIn

router = APIRouter(prefix='/api', tags=['学习'])

_LEVEL_HINT = 'level 必须是 1(不会) / 2(模糊) / 3(会)'

# ★ 复习进度 / 队列 / 统计都是**个人数据**，全部要求登录。
# 曾经只有 PUT 挂了鉴权，而隔壁的 DELETE /api/progress（清空全部进度）
# 是匿名的 —— 加上 CORS 通配，任意网页一句 fetch 就能把你的进度清零。
# 保护一个端点不等于保护这条链，这几个必须一起看。


@router.get('/progress', summary='全部进度')
def get_progress(user=Depends(current_user)):
    return {'ok': True, 'progress': db.get_progress(user.get('id'))}


@router.delete('/progress', summary='清空全部进度')
def clear_progress(user=Depends(current_user)):
    db.clear_progress(user.get('id'))
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
    """复习历史，按时间正序。这是给知识追踪模型（BKT）喂的数据。

    BKT 已经落地了：掌握度就是从这条事件流回放出来的 —— 见
    `GET /api/mastery`（读掌握度）和 `POST /api/review/fit-bkt`（拿自己的
    事件流拟合四参数）。
    """
    return {'ok': True,
            'count': db.events_count(user.get('id')),
            'events': db.events_of(user.get('id'), card_id=card_id,
                                   limit=limit)}


@router.delete('/progress/{cid}', summary='重置某张卡的进度')
def reset_progress(cid: str, user=Depends(current_user)):
    db.reset_progress(cid, user.get('id'))
    return {'ok': True}


@router.get('/review/pick', summary='今日自选复习清单')
def get_pick(user=Depends(current_user)):
    """一天 311 张到期卡刷不完 —— 用户自己点名「今天就刷这些」。

    清单跨天自动作废（db 层按日期判），所以这里永远是今天的口径。
    """
    ids = db.get_today_pick(user.get('id'))
    return {'ok': True, 'today': db.today_str(), 'ids': ids, 'total': len(ids)}


@router.put('/review/pick', summary='设置今日自选复习清单（整体覆盖）')
def put_pick(body: PickIn, user=Depends(current_user)):
    ids = db.set_today_pick(user.get('id'), body.ids)
    return {'ok': True, 'ids': ids, 'total': len(ids)}


@router.get('/review/due', summary='今日复习队列')
def review_due(limit: int = Query(50, ge=1, le=500),
               domain: Optional[str] = Query(None),
               dirs: Optional[str] = Query(
                   None, description='学习方向 id，逗号分隔（data/directions.js）。只推这些方向的卡'),
               include_all: str = Query('', alias='all',
                                        description='=1 时把没到期的也带上（「全部过一遍」用）'),
               pick: str = Query('',
                                 description='=1 时只回今日自选清单里的卡（清单空就回空队列，不当作退化成普通队列）'),
               by: str = Query('level',
                               description='level=按自评档位排（默认，老行为）| '
                                           'bkt=按 BKT 掌握度低的优先排'),
               user=Depends(current_user)):
    # 形参叫 include_all、查询串仍叫 ?all=1：alias 保住了对外契约，
    # 又不至于在函数体里盖掉内置的 all()
    if pick == '1':
        # 自选模式：清单就是队列。仍走 due_list(include_all=True) 拿全量再按 id 收窄，
        # 这样 level/nextAt/overdue 字段口径和普通队列完全一致，前端不用分两套渲染。
        # 清单为空 → 回空 total=0，让前端能区分「没挑」和「挑了但都刷完了」。
        ids = set(db.get_today_pick(user.get('id')))
        items = [x for x in db.due_list(include_all=True, user_id=user.get('id'))
                 if x['card']['id'] in ids]
        # 顺序交给 due_list 的排序（先 level1/2 再 level0，同级按 overdue），
        # 不按清单写入顺序 —— 用户挑卡时是按页面顺序点的，没有轻重语义。
    else:
        items = db.due_list(domain=domain or None, include_all=(include_all == '1'),
                           user_id=user.get('id'))
        if dirs:
            # 方向筛必须在截断**之前**：先按方向过滤全量到期卡，再取 limit。
            # 顺序反了就是先拿满 limit 再丢，方向卡会被排在后面的基本卡挤出队列。
            kws = db.direction_kws([d.strip() for d in dirs.split(',') if d.strip()])
            if kws:                    # 传了查不到的方向 id → 当没筛，别返回空队列
                items = [x for x in items if db.card_hit(x['card'], kws)]
    # BKT 优先级排序必须在截断**之前**：否则只对「已经取到的前 limit 张」排序，
    # 等于没排 —— 真正掌握度低的卡已经被 limit 截掉了。默认 by=level 时这段不执行，
    # 返回顺序和以前逐字一致（check.js 拿旧顺序做断言）。
    if by == 'bkt':
        items = db.sort_by_mastery(items, user.get('id'))
    items = items[:limit]
    queue = [{'id': x['card']['id'], 'title': x['card'].get('title'),
              'domain': x['card'].get('domain'), 'oneLine': x['card'].get('oneLine'),
              'level': x['level'],
              'nextAt': x['progress'].get('nextAt') if x['progress'] else None,
              # overdue == OVERDUE_NEVER 是 db 层表示「从没复习过」的哨兵值，
              # 不该漏给前端。用常量而不是写 999（该值在 db.py 里改过一次，
              # planner 也已经改用常量，router 写死会漏）。
              'overdue': None if x['overdue'] == db.OVERDUE_NEVER else x['overdue']}
             for x in items]
    if by == 'bkt':
        # 只在按 BKT 排时附上 p：默认队列不该出现「p: null」这种半截数据，
        # 免得前端把 null 当成「掌握度 0」。
        for row, x in zip(queue, items):
            row['p'] = x.get('p')
    return {'ok': True, 'today': db.today_str(), 'total': len(items), 'queue': queue}


@router.get('/stats', summary='统计')
def stats(user=Depends(current_user)):
    """总卡数、今日待复习、掌握分布 —— 首页那几个数字。"""
    return {'ok': True, 'stats': db.stats(user.get('id'))}


@router.get('/mastery', summary='BKT 掌握度（每张卡 + 汇总）')
def mastery(brief: str = Query('', description='=1 时只回汇总，不回每张卡（首页/看板用，省流量）'),
            user=Depends(current_user)):
    """BKT 掌握度 p ∈ [0,1]：练得越多越接近 1，没练过的卡是先验 p_init。

    这就是「BKT 和 SM-2/FSRS 共存」里 BKT 那一半的可见面 —— 复习**时间**由
    主调度算法算（/api/review/due 的 nextAt），**掌握度**由这里单独给。

    刻意**不**在这里对每张卡跑回放（那是 N 次全量事件扫描，慢得莫名其妙）：
    直接读 mastery 表 + Redis 缓存，没算过的卡补先验。口径见 db.mastery_map。

    `computed=false` 的卡表示「还没算过它的掌握度」（没练过，或参数刚重拟合
    把 mastery 表清空了）—— 它的 p 是先验，不代表真的不会。
    """
    uid = user.get('id')
    cards = db.all_cards()
    pm = db.mastery_map(uid, cards)
    stored = db.mastery_all(uid) or {}
    rows = []
    buckets = {'weak': 0, 'mid': 0, 'strong': 0, 'untouched': 0}
    for c in cards:
        p = float(pm.get(c['id'], 0.25))
        computed = c['id'] in stored
        if not computed:
            buckets['untouched'] += 1
        elif p < 0.4:
            buckets['weak'] += 1
        elif p < 0.8:
            buckets['mid'] += 1
        else:
            buckets['strong'] += 1
        rows.append({'id': c['id'], 'title': c.get('title'),
                     'domain': c.get('domain'), 'p': round(p, 4),
                     'computed': computed})
    avg = (sum(r['p'] for r in rows) / len(rows)) if rows else 0.0
    summary = {'total': len(rows), 'avgP': round(avg, 4),
               'events': db.events_count(uid),
               'computed': len(stored), **buckets}
    if brief == '1':
        # 汇总 + 参数，不带 cards。首页/看板只要那条分布条，
        # 拉 400 张卡的明细纯属浪费流量（手机端尤其明显）。
        return {'ok': True, 'params': db.bkt_params(uid), 'summary': summary}
    return {'ok': True,
            'params': db.bkt_params(uid),
            'summary': summary,
            'cards': rows}


@router.post('/review/fit-bkt', summary='用我的事件流拟合 BKT 四参数')
def fit_bkt_ep(user=Depends(current_user)):
    """用自己的复习记录拟合 BKT 的四个概率参数（p_init/transit/slip/guess）。

    数据不够时**如实返回 `fitted:false` + 原因**并继续用默认参数 —— 不硬凑
    一个「看起来拟合过了」的参数。硬拟合比不拟合更差：它会完美贴合手上这
    几条记录，换一天预测就是瞎猜（过拟合）。

    拟合成功会顺带清掉这个人的掌握度缓存和 mastery 表（参数一换，旧的
    派生值全部作废），所以 fit 之后重新读 /api/mastery 才是新参数下的结果。
    """
    params, info = db.fit_bkt(user.get('id'))
    return {'ok': True, 'params': params, 'info': info}
