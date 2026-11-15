# -*- coding: utf-8 -*-
"""数据层 · 用户域 —— 账号创建、登录校验、公开视图。

用户是唯一一个不属于卡片域的实体：它是所有 per-user 数据（掌握度、答题记录、
笔记）的前置条件。存储层只管存取，这里补规则。

注意：**加登录只做到「有账号、能登录」**。progress / notes 目前还没有
user_id，也就是「谁都能登，但数据还是大家共用一份」。这一步刻意留着，
因为它要配一次数据迁移 —— 顺手加列的下场是现有进度变成「找不到」，
比暂时不隔离糟糕得多。
（此注释已成历史：progress / notes 现已按 user_id 隔离，2026-10-03。）
"""
import time

import security                                            # core/security.py

from .base import backend

# ---------- user_get 微缓存（2026-11-15，评测遗留项） ----------
# deps.current_user 每个请求都 user_get 一次 —— MySQL 后端下就是每请求
# 一条 SELECT。用户数据几乎不变（改昵称是月级操作），30s TTL 的进程内
# 缓存能把这条查询从热路径上拿掉。**所有用户写路径（user_put）都会
# 失效缓存** —— 昵称改完最迟下一请求就生效，不会有 30s 的旧值窗口。
_USER_CACHE = {}                        # uid -> (ts, user 或 None)
_USER_TTL = 30.0


def _user_cache_invalidate(uid=None):
    if uid is None:
        _USER_CACHE.clear()
    else:
        _USER_CACHE.pop(str(uid), None)


def public_user(u):
    """对外暴露的用户对象。**任何**要返回给前端的用户都必须过这一道。

    直接把存储层的 dict 返回出去会把 passwordHash 漏出去。这类泄露多半
    不是有人故意，而是「顺手 return 了上游对象」。
    """
    if not u:
        return None
    return {
        'id': u.get('id'),
        'username': u.get('username') or '',
        'displayName': u.get('displayName') or u.get('username') or '',
        'role': u.get('role') or 'user',
        'createdAt': u.get('createdAt'),
    }


def user_all():
    return [public_user(u) for u in backend().user_all()]


def user_get(uid):
    key = str(uid)
    now = time.time()
    hit = _USER_CACHE.get(key)
    if hit and now - hit[0] < _USER_TTL:
        return hit[1]
    u = backend().user_get(uid)
    _USER_CACHE[key] = (now, u)
    return u


def user_by_name(username):
    return backend().user_by_name(username)


def user_count():
    try:
        return backend().user_count()
    except Exception:
        return 0


def create_user(username, password, display_name=''):
    """建账号。返回 `(user 或 None, 错误话术)`。

    两条规则放在这里而不是端点里，因为这里是唯一的账号创建入口
    （注册端点 / 将来的 CLI 建号都要走它）：
      1. 用户名重复要拦 —— 存储层虽然有唯一索引，但得换成人话报错
      2. **第一个注册的人自动是管理员** —— 单机部署不用手工建号，
         自己一个人用也不会出现「大家都一样」的尴尬
    """
    ok, name_or_msg = security.check_username(username)
    if not ok:
        return None, name_or_msg
    name = name_or_msg

    ok, pw_or_msg = security.check_password(password)
    if not ok:
        return None, pw_or_msg

    if backend().user_by_name(name):
        return None, '用户名已被占用'

    rec = {
        'username': name,
        'passwordHash': security.hash_password(pw_or_msg),
        'displayName': (display_name or '').strip()[:32] or name,
        'role': 'admin' if user_count() == 0 else 'user',
        'openid': None,
    }
    uid = backend().user_put(rec)
    _user_cache_invalidate(uid)
    return public_user(backend().user_get(uid)), None


def update_user_profile(uid, display_name=''):
    """改个人信息（目前只有昵称一项可改）。返回 `(user 或 None, 错误话术)`。

    用户名 / 密码 / 角色**不在这里改**：用户名是登录凭据（还有唯一索引），
    密码要走单独的改密流程（要验旧密码），混在一个「改资料」接口里
    迟早出越权问题。

    昵称口径与 create_user 一致：strip、截 32 字、留空回退用户名 ——
    同一个字段在两处各写一套校验，改一处忘一处就是 bug。
    """
    u = backend().user_get(uid)
    if not u:
        return None, '用户不存在'
    rec = dict(u)   # 含 passwordHash，原样写回（user_put 是整条替换）
    rec['displayName'] = (display_name or '').strip()[:32] or rec.get('username') or ''
    nid = backend().user_put(rec)
    _user_cache_invalidate(nid)
    return public_user(backend().user_get(nid)), None


def verify_login(username, password):
    """校验账号密码。返回 `(user 或 None, 错误话术)`。

    「用户不存在」和「密码错」**故意返回同一句话** —— 分开写就等于白送
    一个用户名枚举接口，别人可以拿它筛出哪些账号真实存在。
    """
    bad = '用户名或密码不对'
    name = (username or '').strip()
    if not name or not password:
        return None, bad
    u = backend().user_by_name(name)
    if not u:
        return None, bad
    if not security.verify_password(password, u.get('passwordHash')):
        return None, bad
    return public_user(u), None
