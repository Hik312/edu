# -*- coding: utf-8 -*-
"""小程序端接口（前缀 /api/mini/*）。

设计取向和 web 包不同：手机上一次只看一张卡、列表必须分页、首页要一次
拿到聚合数据（少发请求）。所以这里的端点按「移动场景的页面」组织，
而不是按后端域拆 —— 登录、首页、卡包、详情、复习，五个面各管各的。
"""
from . import auth, learn

ALL = (auth.router, learn.router)

__all__ = ['ALL', 'auth', 'learn']
