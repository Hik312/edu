# -*- coding: utf-8 -*-
"""FastAPI 依赖：从 Authorization 头解出「当前用户」。

单独成文件的理由：路由里要到处写 `user = Depends(current_user)`，
如果把它放在某个 router 里，其它 router 就得 import 那个 router，
几个域一交叉就成了网。
"""
from fastapi import Header, HTTPException

import db
import security


def token_from_header(authorization):
    """解析 `Bearer xxx`。格式不对一律返回 None，不抛异常。"""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1].strip() or None


def current_user(authorization: str = Header(None)):
    """必须登录。没登录 / token 过期一律 **401**。

    用 401 不用 403 是有原因的：前端 api/client.js 只对 401 做
    「清 token + 跳登录页」，403 会被当成普通错误弹个 toast ——
    用户会卡在当前页面反复点，不知道自己其实已经掉线了。
    """
    token = token_from_header(authorization)
    payload = security.read_token(token, security.get_secret()) if token else None
    if not payload:
        raise HTTPException(401, '未登录或登录已过期')

    u = db.user_get(payload.get('sub'))
    if not u:
        # 签名有效但账号已被删。当未登录处理，别放进去
        raise HTTPException(401, '账号不存在')
    return db.public_user(u)


# 这里以前还有个 optional_user()（匿名可过、返回 user 或 None），2026-09-26 删掉：
# 全仓没有任何端点用它，是「以后可能会用到」的占位。真要写
# 「登录了看自己的、没登录看公共的」端点时再补 —— 到时候大概是
# `def optional_user(authorization: str = Header(None))` 里 try/except 401，
# 五行就能加回来，比留一个没人调的函数更容易被记住。
