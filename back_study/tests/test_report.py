# -*- coding: utf-8 -*-
"""报表聚合层的单元测试 —— core/report.py 的纯函数，造事件就能测。

「不会=1 / 模糊=2 / 会=3」这条全文件口径（模块注释里的 ★ 决策）在这里锁死。
"""
import pytest

import report as R                      # core/report.py（conftest 已挂 core 路径）

TODAY = '2026-11-15'                    # 调入的周（周一 11-09 ~ 周日 11-15）


_ev_counter = {'n': 0}


def _ev(cid, level, at, uid='1'):
    _ev_counter['n'] += 1
    return {'id': _ev_counter['n'], 'user_id': uid, 'card_id': cid,
            'kc': cid, 'level': level, 'correct': 1 if level >= 3 else 0,
            'at': at, 'elapsed_ms': None}


def _events():
    _ev_counter['n'] = 0
    evs = [
        _ev('c1', 1, '2026-11-10'),      # 周内：不会
        _ev('c1', 1, '2026-11-11'),      # 周内：又不会
        _ev('c2', 2, '2026-11-12'),      # 周内：模糊
        _ev('c3', 3, '2026-11-12'),      # 周内：会
        _ev('c1', 2, '2026-10-01'),      # 上周：模糊（不进 week 窗口）
        _ev('c9', 3, '2026-11-10'),      # 周内：会
    ]
    return evs


def test_mistake_book_buckets():
    out = R.mistake_book(_events(), period='week', today=TODAY)
    assert out['period'] == 'week'
    assert out['totalReviews'] == 6
    weak = {x['cardId']: x for x in out['weakCards']}
    fuzzy = {x['cardId']: x for x in out['fuzzyCards']}
    assert set(weak) == {'c1'} and weak['c1']['count'] == 2
    # ★ 口径（docstring 明说）：period 只影响 reviewSessions 的时间窗，
    #   错题本本身是**全量**口径 —— 上周 c1 的模糊也在这里。
    assert set(fuzzy) == {'c1', 'c2'}
    assert fuzzy['c1']['count'] == 1 and fuzzy['c2']['count'] == 1
    # 「会」不算错题本 —— 把「会」也算进来等于没筛选
    assert 'c3' not in weak and 'c3' not in fuzzy and 'c9' not in weak


def test_mistake_book_sort_by_count_then_recency():
    out = R.mistake_book(_events(), period='all', today=TODAY)
    fuzzy = out['fuzzyCards']
    # c2（本周 1 次）与 c1 的模糊（上周 1 次）同次数 → 最近复习的排前面
    assert fuzzy[0]['cardId'] == 'c2'
    assert fuzzy[0]['lastReviewed'] == '2026-11-12'


def test_review_summary_counts():
    out = R.review_summary(_events(), period='week', today=TODAY)
    assert out['totalReviews'] == 5       # 4 条本周 + c9（c1 上周那条不计）
    assert out['weakCount'] == 2
    assert out['goodCount'] == 2
    assert out['activeDays'] >= 3
    days = {d['date']: d['count'] for d in out['dailyCounts']}
    assert days.get('2026-11-10') == 2
    assert days.get('2026-10-01') is None


def test_period_passthrough_and_all():
    """report.py 对 period 透传（非法值回落 week 的防线在 profile.py 路由层，
    由 check.js 的 API 断言覆盖）；'all' 时窗口为空 = 全量。"""
    out_all = R.review_summary(_events(), period='all', today=TODAY)
    assert out_all['totalReviews'] == 6
    assert out_all['from'] == ''
    out_bad = R.review_summary(_events(), period='nonsense', today=TODAY)
    assert out_bad['period'] == 'nonsense'   # 透传，不在此层改写


def test_min_session_seconds_gate():
    """低于 2 秒的会话不计入专注度（误触/切页面噪声）。"""
    sessions = [
        {'card_id': 'c1', 'duration_seconds': 1, 'ts': '2026-11-10T08:00:00'},
        {'card_id': 'c1', 'duration_seconds': 30, 'ts': '2026-11-10T08:01:00'},
    ]
    out = R.study_time(sessions, period='week', today=TODAY)
    # 1 秒的会话被 MIN_SESSION_SECONDS 滤掉，只算 30 秒那一条 → 0.5 分钟
    assert out['totalSessions'] == 1
    assert out['totalMinutes'] == pytest.approx(0.5)


# ---------- True Retention / 复习热力图（2026-11-15 加） ----------

def _evs_ret():
    return [
        {'card_id': 'c1', 'level': 3, 'at': '2026-11-15'},   # 成熟卡答对
        {'card_id': 'c2', 'level': 1, 'at': '2026-11-15'},   # 新卡忘了
        {'card_id': 'c1', 'level': 3, 'at': '2026-11-10'},
        {'card_id': 'c3', 'level': 2, 'at': '2026-10-05'},   # 新卡「模糊」→ 算记得
        {'card_id': 'c1', 'level': 3, 'at': '2026-05-20'},
    ]


_PROG = {'c1': {'interval': 30}, 'c2': {'interval': 1}, 'c3': {'interval': 4}}


def test_true_retention_mature_vs_young():
    tr = R.true_retention(_evs_ret(), _PROG, today='2026-11-15')
    # c1 间隔 30 → mature：3 次全对；c2/c3 新卡：忘 1 记 1
    assert tr['all']['mature']['total'] == 3
    assert tr['all']['mature']['rate'] == 1.0
    assert tr['all']['young']['total'] == 2
    assert tr['all']['young']['rate'] == 0.5
    # 合计口径 = 两者之和
    assert tr['all']['total']['total'] == 5
    # 今天窗：只算 11-15 的两条
    assert tr['today']['total']['total'] == 2
    assert tr['today']['young']['rate'] == 0.0
    assert tr['today']['mature']['rate'] == 1.0
    # month 窗按日历月：11 月只有 11-10/11-15 三条（10 月、5 月的都不进）
    assert tr['month']['total']['total'] == 3
    assert tr['year']['total']['total'] == 5             # 5 月那条进今年


def test_true_retention_no_samples_rate_null():
    """窗口里没样本时 rate 是 null（不是 0%）—— 「没数据」和「全忘」是两回事。"""
    tr = R.true_retention([], {}, today='2026-11-15')
    assert tr['today']['young']['rate'] is None
    assert tr['all']['mature']['total'] == 0


def test_review_heatmap_counts_and_streak():
    hm = R.review_heatmap(_evs_ret(), year=2026, today='2026-11-15')
    assert hm['total'] == 5
    assert hm['activeDays'] == 4
    d15 = [d for d in hm['days'] if d['date'] == '2026-11-15'][0]
    assert d15['count'] == 2 and d15['weak'] == 1 and d15['good'] == 1
    assert hm['streak']['current'] == 1                  # 今天有、昨天没有
    assert hm['streak']['max'] >= 1


def test_review_heatmap_year_filter():
    """只统计请求年份的事件（2025 的事件不混进 2026）。"""
    evs = _evs_ret() + [{'card_id': 'cX', 'level': 3, 'at': '2025-12-31'}]
    hm = R.review_heatmap(evs, year=2026, today='2026-11-15')
    assert hm['total'] == 5
    hm25 = R.review_heatmap(evs, year=2025, today='2026-11-15')
    assert hm25['total'] == 1
