# -*- coding: utf-8 -*-
"""数据层 · 目录配置域 —— 分类树 / 目标岗位 / 学习方向 / 方向关键词命中。

这批数据（catalog.js / roles.js / directions.js）**刻意不进数据库**：
它们是内容创作者写死的配置，改它应该走 git，而不是靠一个能被网页改写的
运行时状态。后端只负责把 id 翻译成中文名、把方向翻译成关键词命中。
"""
import json
import os
import re
import sys

from .base import DATA_DIR, FILE_CATALOG, read_text
from .cards import all_cards


def load_catalog():
    """读 data/catalog.js 的分类树（同样是严格 JSON 字面量）。

    刻意**不进数据库**：这是配置不是数据 —— 网页端靠 `<script src="data/catalog.js">`
    直接读它，后端只是拿来把 id 翻译成中文名。挪进库里，数据库一挂连导航都没了。
    """
    if not os.path.exists(FILE_CATALOG):
        return []
    src = read_text(FILE_CATALOG)
    m = re.search(r'var\s+(CATALOG)\s*=', src)
    if not m:
        return []
    idx = src.find('[', m.end())
    if idx < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
    except ValueError as e:
        print('[db] 分类树解析失败: %s' % e, file=sys.stderr)
        return []
    return arr


def cat_name(category_id):
    for cat in load_catalog():
        if cat.get('id') == category_id:
            return cat.get('name')
    return category_id


def subject_name(subject_id):
    for cat in load_catalog():
        for s in cat.get('subjects', []):
            if s.get('id') == subject_id:
                return s.get('name')
    return subject_id


# ---------- 目标岗位（配置，留在文件里） ----------
FILE_ROLES = os.path.join(DATA_DIR, 'roles.js')


def load_roles():
    """读 data/roles.js 的岗位定义（严格 JSON 字面量 `var ROLES = [...]`）。

    和 catalog 一样**不进数据库**：这是配置不是数据 —— 岗位是内容创作者写死的
    目录，改它应该走 git，而不是靠一个能被网页改写的运行时状态。
    """
    if not os.path.exists(FILE_ROLES):
        return []
    src = read_text(FILE_ROLES)
    m = re.search(r'var\s+ROLES\s*=', src)
    if not m:
        return []
    idx = src.find('[', m.end())
    if idx < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
    except ValueError as e:
        print('[db] 岗位定义解析失败: %s' % e, file=sys.stderr)
        return []
    return arr


def role_by_id(role_id):
    for r in load_roles():
        if r.get('id') == role_id:
            return r
    return None


# ---------- 学习方向（配置，留在文件里） ----------
FILE_DIRECTIONS = os.path.join(DATA_DIR, 'directions.js')


def load_directions():
    """读 data/directions.js 的学习方向（严格 JSON 字面量 `var DIRECTIONS = [...]`）。

    和 catalog / roles 一样**不进数据库**：这是配置不是数据 —— 方向是内容创作者
    写死的分组，改它应该走 git。复习队列按它筛卡，前端 chips 也从它来。
    """
    if not os.path.exists(FILE_DIRECTIONS):
        return []
    src = read_text(FILE_DIRECTIONS)
    m = re.search(r'var\s+DIRECTIONS\s*=', src)
    if not m:
        return []
    idx = src.find('[', m.end())
    if idx < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
    except ValueError as e:
        print('[db] 学习方向解析失败: %s' % e, file=sys.stderr)
        return []
    return arr


def direction_kws(dir_ids):
    """方向 id 列表 → 合并后的关键词（去重、保序）。查不到的方向静默跳过。

    多选方向时取**并集**：选了「Agent 开发」和「Python 基础」就推两边的卡。
    """
    ids = set(dir_ids or [])
    kws, seen = [], set()
    for d in load_directions():
        if d.get('id') not in ids:
            continue
        for k in (d.get('keywords') or []):
            k = str(k).strip()
            if k and k.lower() not in seen:
                seen.add(k.lower())
                kws.append(k)
    return kws


def _kw_hits(kw, cards):
    """技能词在不在这个科目的卡里：匹配 keywords / title / topicPath。

    用子串匹配而不是精确相等 —— 「B+树」这种词在卡里常写作「B+树索引原理」，
    精确相等会把明明有的卡报成缺。
    """
    k = (kw or '').strip().lower()
    if not k:
        return False
    for c in cards:
        hay = ' '.join((c.get('keywords') or []) +
                       [c.get('title') or ''] +
                       (c.get('topicPath') or [])).lower()
        if k in hay:
            return True
    return False


def card_hit(card, kws):
    """这张卡命中方向关键词吗（子串、大小写不敏感）。

    口径和 `_kw_hits` 是同一套 —— keywords / title / topicPath 任何一处包含即算。
    区别只在方向：`_kw_hits` 问「这个词在不在这一组卡里」（岗位对账用），
    这里问「这张卡在不在这个方向里」（复习队列筛选用）。所以必须逐卡算，
    不能借 `_kw_hits` —— 它短路返回的是组级结论。
    """
    hay = ' '.join((card.get('keywords') or []) +
                   [card.get('title') or ''] +
                   (card.get('topicPath') or [])).lower()
    for kw in kws:
        k = (kw or '').strip().lower()
        if k and k in hay:
            return True
    return False


def direction_counts(cards=None):
    """单遍统计每个方向能推出多少张卡（替代原来每方向重扫全库的 N×M 写法）。

    原来在 /api/directions 和 /api/mini/home 里都是：for d in 方向:
    sum(1 for c in cards if card_hit(c, kws)) —— 每张卡的 haystack 被重复拼了
    N 次（N=方向数）。这里每张卡只拼一次，再对每个方向累计命中；all_cards()
    也只调一次。复杂度仍是「卡×方向」的子串判定（不建倒排就没有更优解），
    但省掉了 N 倍重复的字符串拼接，卡数到几百、方向十几个时差别明显。
    返回 {dir_id: count}，与 card_hit 同口径（任一关键词子串命中即算）。
    """
    if cards is None:
        cards = all_cards()
    dirs = load_directions()
    if not dirs:
        return {}
    # 每张卡拼一次 haystack（card_hit 原本每张卡每次都拼，N×M 次白拼）
    pools = {}
    for c in cards:
        pools[c['id']] = ' '.join(
            (c.get('keywords') or []) + [c.get('title') or ''] +
            (c.get('topicPath') or [])
        ).lower()
    counts = {}
    for d in dirs:
        did = d.get('id')
        kws = [str(k).strip().lower() for k in (d.get('keywords') or [])
               if str(k).strip()]
        if not kws:
            counts[did] = 0
            continue
        n = 0
        for cid, hay in pools.items():
            if any(k in hay for k in kws):
                n += 1
        counts[did] = n
    return counts
