# -*- coding: utf-8 -*-
"""个人中心：错题本 / 复盘 / 遗忘曲线 / 学习时长。

**这一层只做三件事**：取参数 → 调 `core/report.py` 里的聚合函数 → 返响应。
所有算法都在 core 层（纯函数、可不起服务单测），这里不写业务逻辑。

**对应前端** `web/src/api/profile.js` —— 字段形状按那边的 JSDoc 约定，
前端 `ProfileCenterView.vue` 直接渲染，后端不做二次包装。

★ 全部端点都要求登录：这些报表 100% 是个人数据
（错题本 = 你不会的卡、时长 = 你学了多久）。
按项目铁律，鉴权看的是「响应里有没有个人数据」，不是方法名 —— 这里全是 GET，
但一个都不能匿名。
"""
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field

import db
import report as R          # core/report.py —— core 是顶层包（同 deps.py 里 import db）
from ...deps import current_user

router = APIRouter(prefix='/api/profile', tags=['个人中心'])

_PERIODS = ('week', 'month', 'all')


def _today():
    return db.today_str()


def _cards_by_id():
    """{card_id: card}。报表里要把 cardId 翻成标题/科目，前端才好显示。"""
    return {c['id']: c for c in db.all_cards() if c.get('id')}


def _sessions_of(uid):
    """取学习会话。返回 `(rows, available)`。

    ★ 为什么必须容错：`algostore` 的 sessions 只有 jsonfile 后端实现了，
    PG 后端（`ALGO_STORE=pg`）还是 `NotImplementedError`。
    而这些报表全是**只读增强** —— 学习时长统计挂掉，不该让「个人中心」整页 500，
    不该让用户看到空白页以为功能坏了。取不到就当「还没有学习记录」，
    报表其余部分（错题本、曲线）照常工作。

    ★★ 但**必须把「不可用」这个事实报上去**（第二个返回值）：
    「降级必须看得见」是项目铁律。如果前端只拿到 `totalMinutes: 0`，
    界面上会显示「总学习时长 0h / 还没有学习记录」——
    **用户分不清是「我没学」还是「功能坏了」**。
    实测踩过：PG 后端下时长恒为 0，而界面上完全看不出原因。
    """
    try:
        return db.algostore.get().sessions_of(uid, limit=db.EVENTS_ALL) or [], True
    except NotImplementedError:
        # 存储层还没实现 sessions（如 PG 后端）——降级成空，不抛
        return [], False
    except Exception as e:
        import sys
        sys.stderr.write('[profile] 读学习会话失败（按空处理）：%s\n' % e)
        return [], False


def _append_session(uid, card_id, seconds, level, ts='', session_id=''):
    """写一条学习会话。**永远不抛异常**。

    埋点是「锦上添花」的数据，丢了不该让用户的复习操作失败 ——
    前端上报失败只影响专注度报表，不影响他刚标记的进度。
    """
    try:
        sec = R._clean_seconds(seconds)
        if sec < R.MIN_SESSION_SECONDS:
            return False
        db.algostore.get().sessions_append({
            'user_id': str(uid),
            'card_id': card_id,
            'duration_seconds': int(sec),
            'level': int(level or 0),
            'ts': ts or db.today_str(),
            'session_id': session_id or '',
        })
        return True
    except Exception:
        # 派生数据，丢了能接受；写 stderr 是为了「上报一直没进来」时能查
        import sys
        sys.stderr.write('[profile] 学习时长写入失败（已忽略）：%s\n' % card_id)
        return False


def _norm_period(p):
    """非法 period 一律回 'week'，不抛 400。

    为什么宽容：period 是前端下拉框的值，值不对时返回空数据比抛异常好排查。
    但**响应里会把归一化后的值回传**（`period` 字段），一眼能看出实际用的哪个。
    """
    return p if p in _PERIODS else 'week'


# ---------- 1. 概览 ----------

@router.get('/overview', summary='个人中心概览')
def profile_overview(user=Depends(current_user)):
    """顶部那排数字：复习次数 / 掌握卡数 / 薄弱卡数 / 平均掌握度 / 连续天数。

数字全部**后端算好后端给**，不让前端各算一遍 ——
两端各算一次必然出现「前端说 12、后端说 13」这种对不上的情况。

**★ 三个容易搞错的口径（改之前先读）**：

1. **`weakCards` / `fuzzyCards` 数的是「**曾经**错过」，不是「**现在**不会」**。
   数据来自**事件流**（历史），不是 `progress`（当前状态）。
   区别很实际：你把一张卡从「不会」改标成「会」之后，
   `progress` 里它就不算薄弱了，但「你曾经错过它」这个事实还在事件流里。
   **错题本用的是同一个口径**，两边必须一致 ——
   否则会出现「概览说薄弱 0 张、错题本列出 2 张」，用户会以为数据坏了。

2. **`avgMastery` 只对练过的卡求平均**。
   `mastery_map` 覆盖全库（416 张），没练过的都给先验 `p_init=0.25`；
   拿全库求平均会把结果死死拉到 25%，哪怕练过的卡全答对也永远显示 25%。
   配套返回 `practicedCards` 告诉前端分母是多少 ——
   「练过 7 张的平均 25%」和「练过 400 张的平均 25%」是两回事。

3. **`totalCards`（掌握卡片）用的是 `progress` 当前状态**，
   它和上面两个「历史」口径故意不同：这个数字的意义就是
   「**此刻**我能答对几张」，按当前状态算才对。
    """
    uid = user.get('id')
    events = db.events_of(uid, limit=db.EVENTS_ALL)
    cards = _cards_by_id()
    prog = db.get_progress(uid)

    total_reviews = len(events)

    # 掌握卡数：有进度且当前评级是「会」
    total_cards = sum(1 for r in prog.values() if int(r.get('level') or 0) == 3)

    # ★★ 薄弱卡：这里刻意用**事件流**而不是 progress，原因见下面的口径说明。
    #   progress 数的是「**当前**标着不会的卡」——你后来标成「会」它就消失了，
    #   但「你曾经错过它」这个事实还在事件流里。错题本用的是事件流口径，
    #   两边必须一致，否则概览显示 0、错题本显示 2，用户会以为数据坏了。
    weak_count = len({e.get('card_id') for e in events
                      if e.get('level') == R.LEVEL_AGAIN and e.get('card_id')})
    fuzzy_count = len({e.get('card_id') for e in events
                       if e.get('level') == R.LEVEL_HARD and e.get('card_id')})

    # ★★ 平均掌握度：**只对练过的卡求平均**，不是全库平均。
    #   `mastery_map` 覆盖全库 416 张，没练过的都给先验 p_init=0.25。
    #   如果拿全库求平均，409 张没练过的会把结果死死拉到 25% ——
    #   哪怕你把练过的卡全答对，界面也永远显示 25%（实测：练了 7 张、p 到 0.47，
    #   概览仍显示 25%）。这个数字要能反映真实掌握情况，就必须只算练过的。
    practiced = {e.get('card_id') for e in events if e.get('card_id')}
    mastery = db.mastery_map(uid, list(cards.keys()))
    if practiced:
        vals = [mastery.get(c, 0.0) for c in practiced]
        avg_mastery = round(sum(vals) / len(vals), 4) if vals else 0.0
    else:
        avg_mastery = 0.0

    # 学习天数 / 连续天数：从事件日期集合算
    days = sorted({R._day(e.get('at')) for e in events if e.get('at')})
    streak = _streak(days, _today())

    # 总学习分钟：所有会话累加。
    # 后端不支持 sessions 时自动是 0，并把 available=False 报上去让前端能提示降级
    sessions, s_ok = _sessions_of(uid)
    total_minutes = round(sum(R._clean_seconds(s.get('duration_seconds'))
                              for s in sessions) / 60.0, 2)

    wk = R.review_summary(events, 'week', _today())
    mo = R.review_summary(events, 'month', _today())

    return {'ok': True, 'data': {
        'totalReviews': total_reviews,
        'totalCards': total_cards,
        'weakCards': weak_count,
        'fuzzyCards': fuzzy_count,
        # ★ 新增：分母。不给这个数字，前端展示 avgMastery 时没法说清
        #   「25% 是练过 400 张的平均，还是练过 7 张的平均」——
        #   而这两个数含义完全不同（前者会被没练过的卡拉到先验值）。
        'practicedCards': len(practiced),
        'avgMastery': avg_mastery,
        'studyDays': len(days),
        'totalMinutes': total_minutes,
        # ★ 降级可见性：存储层不支持 sessions 时为 false，
        #   前端据此提示「该功能暂不可用」而不是显示成「你还没学过」。
        'sessionsAvailable': s_ok,
        'streakDays': streak,
        'lastSession': _last_session(uid),
        'weeklyReport': wk,
        'monthlyReport': mo,
    }}


def _streak(days, today):
    """连续学习天数：从今天（或昨天）往回数连续的复习日。

    ★ 今天还没学不算断：从昨天开始往回数。
    否则「每天晚上学习」的人每天早上打开都看到 streak=0，很泄气。
    """
    if not days:
        return 0
    import datetime
    try:
        t = datetime.date.fromisoformat(today)
    except (ValueError, TypeError):
        return len(set(days))
    ds = set(days)
    # 今天没学就从昨天开始数
    if today not in ds:
        t = t - datetime.timedelta(days=1)
    n = 0
    while t.isoformat() in ds:
        n += 1
        t = t - datetime.timedelta(days=1)
    return n


def _last_session(uid):
    """最近一条学习会话（概览卡片上显示「上次学到哪」）。"""
    rows, _ok = _sessions_of(uid)
    if not rows:
        return None
    s = rows[-1]
    return {'cardId': s.get('card_id', ''),
            'minutes': round(R._clean_seconds(s.get('duration_seconds')) / 60.0, 1),
            'ts': s.get('ts', ''), 'level': s.get('level')}


# ---------- 2. 错题本 / 复盘 ----------

@router.get('/mistakes', summary='错题本与复盘')
def profile_mistakes(period: str = Query('week'),
                     start: Optional[str] = Query(None),
                     end: Optional[str] = Query(None),
                     user=Depends(current_user)):
    """错题本：把「不会」和「模糊」的卡按被标记次数降序排出来。

    period: 'week' | 'month' | 'all'，只影响 reviewSessions 的时间窗，
    weakCards/fuzzyCards 始终是全量历史（错题本不该因为换周期就忘掉旧账）。
    """
    uid = user.get('id')
    events = db.events_of(uid, limit=db.EVENTS_ALL)
    data = R.mistake_book(events, _cards_by_id(), _norm_period(period), _today())
    return {'ok': True, 'data': data}


# ---------- 3. 遗忘曲线 ----------

@router.get('/forgetting-curve', summary='遗忘曲线')
def profile_forgetting_curve(
        card_id: Optional[str] = Query(None, alias='cardId'),
        days: int = Query(30, ge=1, le=365),
        user=Depends(current_user)):
    """掌握度 / 排期随时间的变化。

    cardId 不传 → 全库聚合（平均掌握度 + 三档分布按天）。
    cardId 传了 → 单卡明细。

    ★ 注意读法：这不是一条「平滑衰减曲线」。
    BKT 的 p 不会自己随时间下降 —— 遗忘是靠调度算法把 nextAt 一路往后推表达的。
    所以这里画的是「每次真实复习事件驱动的掌握度变化」，没复习的那天就没有点。

    ★★ 别把参数名改回 card_id：
      FastAPI 默认把 `card_id` 直接当查询参数名，而前端 `api/profile.js`
      的JSDoc 约定是 camelCase、实际传的也是 `cardId`
      （`getForgettingCurve({ cardId })`）。两者不一致的后果是**静默失效**：
      请求照样返200，但cardId 没进不来 → 走全库聚合分支，
      用户点某张卡想看明细，看到的却是整个库的平均曲线。
      这种 bug 没有任何报错，只有对照返回体里的 cardId 字段才发现。
    """
    uid = user.get('id')
    events = db.events_of(uid, limit=db.EVENTS_ALL)
    cards = _cards_by_id()
    if card_id:
        mastery = {card_id: db.mastery_of(uid, card_id)}
        prog = {card_id: db.get_progress(uid).get(card_id, {})}
    else:
        mastery = db.mastery_map(uid, list(cards.keys()))
        prog = db.get_progress(uid)
    data = R.forgetting_curve(events, prog, mastery, card_id, days, _today())
    return {'ok': True, 'data': data}


# ---------- 4. 学习时长 ----------

@router.get('/study-time', summary='学习时长与专注度')
def profile_study_time(period: str = Query('week'),
                       start: Optional[str] = Query(None),
                       end: Optional[str] = Query(None),
                       user=Depends(current_user)):
    """学习时长聚合：总计 / 按天 / 热力图 / 按科目 / 停留最久的卡。"""
    uid = user.get('id')
    sessions, s_ok = _sessions_of(uid)
    data = R.study_time(sessions, _cards_by_id(),
                        _norm_period(period) if period != 'all' else 'all', _today())
    # sessionsAvailable 透传给前端：false 时它显示「暂不可用」而不是「还没有记录」
    data['sessionsAvailable'] = s_ok
    return {'ok': True, 'data': data}


# ---------- 4.5 记忆保持率 / 复习热力图（2026-11-15 加，与 study-time 同模式） ----------

@router.get('/true-retention', summary='True Retention（Anki 口径记忆保持率）')
def profile_true_retention(user=Depends(current_user)):
    """young / mature（间隔 ≥21 天）分开算「记得率」，四档时间窗。

    和「正确率」的区别：正确率把「刚学完就测」和「隔三周再看」混在一起，
    新卡拉高数字。这一页是复习系统真正的成绩单。
    成熟度按卡**当前** interval 近似（局限见 R.true_retention 的 docstring）。
    """
    uid = user.get('id')
    events = db.events_of(uid, limit=db.EVENTS_ALL)
    prog = db.get_progress(uid)
    data = R.true_retention(events, prog, _today())
    return {'ok': True, 'data': data}


@router.get('/review-heatmap', summary='复习热力图（一年里每天刷了几张）')
def profile_review_heatmap(year: Optional[int] = Query(
        None, ge=2000, le=2100, description='不传 = 今天所在年份'),
        user=Depends(current_user)):
    """每日复习**张数**（study-time 的热力图是**分钟数**，两个口径互补）。

    事件流挂掉不该让个人中心 500：照 _sessions_of 的降级模式，按空处理。
    """
    uid = user.get('id')
    try:
        events = db.events_of(uid, limit=db.EVENTS_ALL)
    except Exception as e:
        import sys
        sys.stderr.write('[profile] 读复习事件失败（热力图按空处理）：%s\n' % e)
        events = []
    data = R.review_heatmap(events, year=year, today=_today())
    return {'ok': True, 'data': data}


# ---------- 5/6. 埋点上报 ----------

class SessionIn(BaseModel):
    cardId: str
    durationSeconds: int = 0
    level: int = 0
    ts: Optional[str] = None
    sessionId: Optional[str] = None


class BatchSessionsIn(BaseModel):
    sessions: List[SessionIn] = Field(default_factory=list)


@router.post('/review-session', summary='上报一次复习会话（单条）')
def report_session(body: SessionIn, user=Depends(current_user)):
    saved = _append_session(user.get('id'), body.cardId,
                            body.durationSeconds, body.level, body.ts, body.sessionId)
    return {'ok': True, 'saved': 1 if saved else 0}


@router.post('/review-sessions/batch', summary='批量上报复习会话')
def report_sessions_batch(body: BatchSessionsIn, user=Depends(current_user)):
    """页面关闭时批量上报。

    ★ 上限 500 条：前端可能攒了一整个学习期的会话，
    不设上限的话一个请求能塞爆 body（请求体上限 16MB）。
    """
    uid = user.get('id')
    saved = sum(1 for it in (body.sessions or [])[:500]
                if _append_session(uid, it.cardId, it.durationSeconds,
                                   it.level, it.ts, it.sessionId))
    return {'ok': True, 'saved': saved}