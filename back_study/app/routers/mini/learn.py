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

#: 复习队列默认给几张。与 web 端的 `DAILY_DEFAULT`（stores/learning.js）=20
#: 兜底值：**只在档案里从没设过时**用（dailyTarget == 0）。
#: 与 web 端 `stores/learning.js: DAILY_DEFAULT` 是同一个默认值 ——
#: 两端各写一份必然漂移，所以这里显式注释对齐关系。
#: ★ 曾把它当「小程序的每日目标」直接用，于是用户在 web 端把目标设成 50、
#:   切到小程序首页仍写「今天要学 20 张」—— 同一套档案两个值。
#:   现在真值一律读档案（见下方 `_plan_limit`），这里只兜「从没设过」。
QUEUE_DEFAULT = 20

router = APIRouter(prefix='/api/mini', tags=['小程序'])


def _brief(c, level=0):
    """列表项：手机列表只展示这些字段，mechanism/scene 大字段一律不带。"""
    return {'id': c['id'], 'domain': c.get('domain'), 'topicPath': c.get('topicPath'),
            'title': c.get('title'), 'oneLine': c.get('oneLine'),
            'tags': c.get('tags'), 'level': level,
            'deck': c.get('deck'), 'deckId': c.get('deckId'),
            '_custom': bool(c.get('_custom'))}


def _plan_limit(user):
    """这个登录用户「今天实际要刷几张」。

    ★ 必须读档案，不能用 QUEUE_DEFAULT 写死 ——
    每日目标是**跟人走**的设置（web 端能改，存后端档案 dailyTarget），
    在小程序这边写死 20，等于用户在 web 端设的 50 在小程序完全无效，
    而且两个页面会显示不同的数字。
    档案里从没设过（dailyTarget == 0）才回落 QUEUE_DEFAULT。
    """
    try:
        t = int((db.profile_of(user.get('id')) or {}).get('dailyTarget') or 0)
    except Exception:
        t = 0
    return t if t > 0 else QUEUE_DEFAULT


def _filter_dirs(items, dirs):
    """按学习方向筛队列。口径与 web 端 /api/review/due?dirs= 逐字一致：
    筛在**截断之前**（先拿满 limit 再丢，方向卡会被后面的基本卡挤出队列）；
    传了查不到的方向 id → 当没筛（别返回空队列）。"""
    if not dirs:
        return items
    kws = db.direction_kws([d.strip() for d in dirs.split(',') if d.strip()])
    if not kws:
        return items
    return [x for x in items if db.card_hit(x['card'], kws)]


@router.get('/home', summary='首页聚合（统计 + 分类树 + 方向 + 今日清单）')
def home(user=Depends(current_user)):
    """小程序首页一个请求拿全部：数字、科目分类、学习方向入口、今日自选。

    directions 带 count（口径 = /api/directions，见那边注释）：卡包页的模块
    chips 要显示「12」，没卡的方向不该让人白点。
    """
    cards = db.all_cards()
    # 单遍统计：每个方向的 count 一次遍历算完（见 db.direction_counts），
    # 不再每方向重扫全库。口径与 /api/directions 完全一致。
    counts = db.direction_counts(cards)
    dirs_out = [dict(d, count=counts.get(d.get('id'), 0))
                for d in db.load_directions()]
    st = db.stats(user.get('id'))
    pick = db.get_today_pick(user.get('id'))
    # dueToday 是**全库到期数**，而复习队列端点默认只给 20 张（review_queue 的
    # limit=20）。首页大数字直接摆 400、点进去只有 20，是同一套系统两个口径。
    # 后端把「今天实际要刷几张」算好给前端，别让两端各算一遍（早晚会算出不同值）。
    # 挑了自选清单就以清单为准 —— 清单本身就是用户对「今天做多少」的显式表态。
    st['dueTodayPlan'] = len(pick) if pick else min(st['dueToday'], _plan_limit(user))
    return {'ok': True,
            'stats': st,
            'catalog': db.load_catalog(),
            'directions': dirs_out,
            # 首页 CTA 要区分「按到期刷」和「按自选清单刷」，给 count 就够，
            # 清单 id 明细队列端点自己回，首页不需要。
            'pick': pick}


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
    prog = db.get_progress(user.get('id'))
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
    c['level'] = (db.get_progress(user.get('id')).get(cid) or {}).get('level', 0)
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
def review_queue(limit: int = Query(0, ge=0, le=100,
                                    description='0 = 按用户的每日目标（档案里的 dailyTarget），不传就用它'),
                 domain: Optional[str] = Query(None),
                 dirs: Optional[str] = Query(
                     None, description='学习方向 id，逗号分隔。与 web 端 /review/due同口径，'
                                       '此前小程序**完全没有**这个筛选 → 在 web 设的方向切到小程序就失效'),
                 pick: str = Query('',
                                   description='=1 时只回今日自选清单里的卡（清单空回空队列，不当作退化成普通队列）'),
                 all: str = Query('',alias='all',
                                  description='=1 时忽略每日目标，把今天全部到期的都给了'
                                              '（首页那20 张刷完、库里还剩几百张时用；'
                                              '上限受 limit 约束，最高 100）'),
                 by: str = Query('level',
                                 description='level=按自评档位排（默认）| bkt=按 BKT 掌握度低的优先'),
                 user=Depends(current_user)):
    if pick == '1':
        # 口径和 /api/review/due?pick=1 一致：due_list 全量排序后按清单 id 收窄，
        # 字段/顺序与普通队列同一套渲染，前端不用分两套。
        ids = set(db.get_today_pick(user.get('id')))
        items = [x for x in db.due_list(include_all=True, user_id=user.get('id'))
                 if x['card']['id'] in ids]
    else:
        items = _filter_dirs(db.due_list(domain=domain or None,
                                         user_id=user.get('id')), dirs)
    # limit 不传（0）就用这个人的每日目标，而不是模块级常量 ——
    # 否则用户在 web 端设的目标在小程序不生效。
    # all=1 则忽略每日目标，把到期的全给（上限仍受 le=100 约束）。
    if all == '1':
        lim = limit or 100
    else:
        lim = limit or _plan_limit(user)
    # 和 web 端 /api/review/due?by=bkt 同一套：先按 BKT 掌握度重排再截断，
    # 默认 by=level 时整段跳过、顺序与以前完全一致。
    if by == 'bkt':
        items = db.sort_by_mastery(items, user.get('id'))
    items = items[:lim]
    queue = [{'id': x['card']['id'], 'title': x['card'].get('title'),
              'oneLine': x['card'].get('oneLine'),
              'domain': x['card'].get('domain'),
              'topicPath': x['card'].get('topicPath'),
              'level': x['level'],
              'nextAt': x['progress'].get('nextAt') if x['progress'] else None,
              'overdue': None if x['overdue'] == db.OVERDUE_NEVER else x['overdue']}
             for x in items]
    if by == 'bkt':
        for row, x in zip(queue, items):
            row['p'] = x.get('p')
    # ★ 「今天还有多少张没刷」——小程序原来只回 total=len(queue)（这一页给了几张），
    # 于是首页摆dueTodayPlan=20、学习页刷完 20 张就显示"今日复习完成"，
    # 而库里明明还剩 393 张到期 —— 用户在小程序里**没有任何入口能刷到它们**
    # （刷新队列也没用，那 20 张已经答过）。这是产品死结，不只是体验瑕疵。
    # 所以额外回dueTotal（全库到期数）：前端据此显示「今天已刷完，还有 N 张，
    # 继续刷」并给一个all=1 的入口。
    try:
        due_total = len(db.due_list(user_id=user.get('id')))
    except Exception:
        due_total = len(items)
    return {'ok': True, 'today': db.today_str(), 'total': len(queue),
            'dueTotal': due_total, 'queue': queue}


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
