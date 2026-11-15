# -*- coding: utf-8 -*-
"""数据层 · 卡片域 —— 自定义卡、修正覆盖层、三源合并。

合并管线：builtin（data/*.js 或 cards 表）+ custom（用户自建）+ override
（内置卡的 AI 修正），同 id 时后者赢。合并结果缓存在 `_all_cache`，
失效键 = data/*.js 文件键 + `_cards_ver` 写代数。
"""
import os
import time as _time

from store.base import read_json as _read_json
from store.base import write_json as _write_json

from .base import STORE_DIR, backend, ensure_store
from .builtin import _STALE_TTL, _src_files_key, builtin_cards

# ---------- 自定义卡 ----------
#: 自定义卡 / 覆盖层的**写代数**。all_cards() 的合并缓存拿它当失效键的一半
#: （另一半是 data/*.js 的文件键）。进程内任何写都要经 save_custom /
#: save_overrides 这两个口（apply_card_patch / revert_override / web/cards.py /
#: importer.py 全走它们），在口上集中失效，比让每个调用点记得失效可靠。
_cards_ver = 0


def _bump_cards_ver():
    """让 all_cards() 的合并缓存作废。只在 save_custom / save_overrides 里调。"""
    global _cards_ver
    _cards_ver += 1


def load_custom():
    return backend().custom_all()


def save_custom(lst):
    _bump_cards_ver()          # 先失效再写：宁可多重建一次，也不能写完忘了失效
    backend().custom_replace(lst)


# ---------- 卡片修正覆盖层 ----------
# 内置卡（agent 生成的，在 data/*.js / cards 表里是只读的）不能直接改。
# 曾经试过「复制成同 id 自定义卡」覆盖，但 MySQL 的 cards 表主键只有 id、
# 没有 (id, origin)，custom_put 的 ON DUPLICATE KEY 会命中 id 主键把那条
# 内置卡行静默覆盖掉（见 _upsert_card）—— 内置卡凭空消失。
# 所以改走**覆盖层**：修正字段单独存一份（cards.override.json，id→patch），
# all_cards() 读取时叠加。不动原始卡、不进 cards 表、可一键回退。
_OVERRIDE_PATH = os.path.join(STORE_DIR, 'cards.override.json')


def load_overrides():
    return _read_json(_OVERRIDE_PATH, {})


def save_overrides(d):
    _bump_cards_ver()          # 同 save_custom：先失效再写
    ensure_store()
    _write_json(_OVERRIDE_PATH, d)


def apply_card_patch(card_id, patch):
    """修正一张卡片的若干字段，返回修正后的卡片 dict；卡片不存在返回 None。

    自定义卡：原地改（custom store 里，id 唯一、不冲突）。
    内置卡：写进覆盖层（不碰原始卡、不进 cards 表），检索/问答经 all_cards() 自动吃到。
    """
    patch = {k: v for k, v in (patch or {}).items()
             if k not in ('id', '_custom', '_override')}
    if not patch:
        return None
    card = next((c for c in all_cards() if c.get('id') == card_id), None)
    if not card:
        return None
    if card.get('_custom'):
        # 自定义卡：就地改
        custom = load_custom()
        for i, x in enumerate(custom):
            if x.get('id') == card_id:
                custom[i].update(patch)
                custom[i]['_override'] = True
                save_custom(custom)
                return custom[i]
    # 内置卡：写入覆盖层
    ov = load_overrides()
    base = dict(ov.get(card_id) or {})
    base.update(patch)
    base['_override'] = True
    ov[card_id] = base
    save_overrides(ov)
    merged = dict(card)
    merged.update(patch)
    merged['_override'] = True
    return merged


def revert_override(card_id):
    """撤销一张卡的覆盖层修正，恢复原始内容。返回是否真的撤销了。"""
    ov = load_overrides()
    if card_id in ov:
        del ov[card_id]
        save_overrides(ov)
        return True
    return False


# ---------- 卡片汇总 ----------
#: 合并结果缓存。合并本身 0.3ms 不贵，贵的是每次重走 builtin_cards()
#: （SQL 全量读 + 指纹检查，2026-10-13 实测合计 70ms+）—— 而合并结果只在
#: 内置文件 / 自定义卡 / 覆盖层变化时才需要重算，所以按
#: 「data/*.js 文件键 + _cards_ver 写代数」缓存。
#: dbseed / fix 脚本是别的进程、本进程看不见它写库，60s TTL 兜底
#: （与 _stale_cache 同一套论证，见那边注释）。
_all_cache = {'key': None, 'cards': None, 'at': 0.0}


def _merged_cards():
    """builtin + custom + override 的合并结果。只在数据变化时重算。"""
    key = (_src_files_key(), _cards_ver)
    now = _time.time()
    if (_all_cache['key'] == key and _all_cache['cards'] is not None
            and now - _all_cache['at'] < _STALE_TTL):
        return _all_cache['cards']
    m = {}
    for c in builtin_cards():
        m[c['id']] = c
    for c in load_custom():
        c = dict(c)
        c['_custom'] = True
        m[c['id']] = c
    # 覆盖层：内置卡的修正（同 id 不进 cards 表，避开 MySQL 主键冲突）
    ov = load_overrides()
    if ov:
        for cid, patch in ov.items():
            if cid in m:
                merged = dict(m[cid])
                for k, v in patch.items():
                    if k == '_override':
                        continue
                    merged[k] = v
                merged['_override'] = True
                m[cid] = merged
    out = list(m.values())
    _all_cache['key'] = key
    _all_cache['cards'] = out
    _all_cache['at'] = now
    return out


def all_cards(category=None, subject=None):
    """内置卡 + 自定义卡；同 id 时自定义优先；覆盖层(override)叠加在内置卡上。
    可按领域/科目过滤。

    返回的是**每张卡一层的浅拷贝**：顶层字段可随手改，改不到缓存；
    但嵌套容器（related/keywords/mechanism…）与缓存**共享** —— 要动嵌套先
    自己拷贝。2026-10-13 把「每次合并」改成「合并结果缓存」时定的契约：
    全仓调用方都只读或只改顶层（apply_card_patch 改的是 load_custom() 新读
    的对象，离线脚本各改各的文件/新读列表），而逐张 deepcopy 是 17ms/次，
    正是这次要杀的瓶颈。
    """
    out = _merged_cards()
    if category:
        out = [c for c in out if c.get('category') == category]
    if subject:
        out = [c for c in out if c.get('subject') == subject]
    return [dict(c) for c in out]
