# -*- coding: utf-8 -*-
"""数据层 · 长期档案（L3 记忆）+ 今日自选清单。

刻意**不进 store 契约**：加进 base/mysql/jsonfile/schema 四处的代价，
换来的只是"档案跟着 MySQL 走"。而它是派生数据 —— 目标岗位、常问主题、
薄弱卡都能重新积累，丢了不影响任何核心功能。文件后端足够。
等 progress/notes 做 user_id 隔离（P0）时，它自然跟着一起搬进库。
"""
import os

from store.base import read_json as _read_json
from store.base import write_json as _write_json

from .base import STORE_DIR, ensure_store, today_str
from .cards import all_cards

FILE_PROFILES = os.path.join(STORE_DIR, 'profiles.json')


def load_profiles():
    return _read_json(FILE_PROFILES, {})


def profile_of(user_id):
    """取某个用户的长期档案。没有就返回空壳（前端据此判断"还没设过"）。

    `dailyTarget` / `directions` 是**学习设置**（每天学几张、学什么方向），
    和 role/topics/weak 一起存：它影响的是复习队列，但同样"跟着这个人走"，
    存 localStorage 换台设备就没了。
    `dailyTarget == 0` 表示从没设过 —— 前端按默认值显示，不要当 0 张来排。
    """
    if user_id is None:
        return {'role': '', 'topics': [], 'weak': [],
                'dailyTarget': 0, 'directions': []}
    p = load_profiles().get(str(user_id)) or {}
    return {'role': p.get('role') or '',
            'topics': list(p.get('topics') or []),
            'weak': list(p.get('weak') or []),
            'dailyTarget': int(p.get('dailyTarget') or 0),
            'directions': list(p.get('directions') or [])}


def save_profile(user_id, patch):
    """合并写入档案（只覆盖发上来的字段）。

    topics/weak 做**去重 + 上限截断**：这两条是自动积累的，
    不截断的话常问一年之后每次问答都往提示词里塞几百个主题。

    dailyTarget / directions 则是**覆盖写**，跟上面两条语义相反：
    它们是用户手选的设置，追加会让「取消勾选的方向」永远取消不掉。
    没发（None）就不动 —— 单改每日目标的请求不能顺手清空方向。
    """
    if user_id is None:
        return None
    all_p = load_profiles()
    cur = all_p.get(str(user_id)) or {'role': '', 'topics': [], 'weak': []}
    if isinstance(patch, dict):
        if 'role' in patch:
            cur['role'] = str(patch.get('role') or '')
        for k in ('topics', 'weak'):
            if k in patch and isinstance(patch[k], list):
                seen, out = set(), []
                for x in list(cur.get(k) or []) + [str(v) for v in patch[k]]:
                    if x and x not in seen:
                        seen.add(x)
                        out.append(x)
                cur[k] = out[-24:]                 # 每类最多留 24 条
        if patch.get('dailyTarget') is not None:
            try:
                cur['dailyTarget'] = max(0, min(200, int(patch['dailyTarget'])))
            except (TypeError, ValueError):
                # ★ 解析失败**保留原值**，不要兜底成 0。
                #   0 在这个模块里的语义是「从没设过」（见profile_of 的注释），
                #   兜底成 0 = 静默清掉用户设的目标：用户设 50，传了个非法值，
                #   下次拉档案看到 0、按默认值 20 显示，于是「我设的 50 丢了」——
                #   而接口回 200，没有任何报错线索。
                #   非法输入要么被 schema挡住（Pydantic 类型），
                #   要么这里静默忽略原值，都不该改用户的设置。
                pass
        if patch.get('directions') is not None and isinstance(patch['directions'], list):
            ids, seen = [], set()
            for x in patch['directions']:
                x = str(x).strip()
                if x and x not in seen:
                    seen.add(x)
                    ids.append(x)
            cur['directions'] = ids[:12]           # 方向一共才 12 个，够用了
    all_p[str(user_id)] = cur
    ensure_store()
    _write_json(FILE_PROFILES, all_p)
    return cur


def get_today_pick(user_id):
    """今日自选复习清单：用户自己点名「今天就刷这些」的卡 id。

    跨天自动作废（存的日期不是今天 → 空）：清单是「今日」语义，
    隔天还留着会让昨天的负担变成今天的，和 dueToday 一样越滚越大。
    上限 100 与 set_today_pick 一致，读侧再截一次是防手改文件撑爆队列。
    """
    if user_id is None:
        return []
    p = load_profiles().get(str(user_id)) or {}
    tp = p.get('todayPick') or {}
    if tp.get('date') != today_str():
        return []
    return [str(x) for x in (tp.get('ids') or [])][:100]


def set_today_pick(user_id, ids):
    """**整体覆盖**写今日清单：过滤不存在的卡、去重、截 100、盖当天日期。

    和 save_profile 分开写而不是往里加字段：清单是带日期的整体覆盖，
    塞进那个「只动发上来的字段」的合并函数里两边语义都不对 ——
    它会把「没发 date」当成不动日期，隔天的旧清单就清不掉了。
    """
    if user_id is None:
        return []
    valid = {c['id'] for c in all_cards()}
    out, seen = [], set()
    for x in (ids or []):
        x = str(x)
        if x in valid and x not in seen:
            seen.add(x)
            out.append(x)
        if len(out) >= 100:                   # 一天刷 100 张已经到顶了
            break
    all_p = load_profiles()
    cur = all_p.get(str(user_id)) or {'role': '', 'topics': [], 'weak': []}
    cur['todayPick'] = {'date': today_str(), 'ids': out}
    all_p[str(user_id)] = cur
    ensure_store()
    _write_json(FILE_PROFILES, all_p)
    return out
