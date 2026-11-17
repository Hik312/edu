# -*- coding: utf-8 -*-
"""Web 端（浏览器 SPA）接口。

URL 前缀保持 /api/* 不变 —— 既有前端契约不动；「哪个端用哪组接口」靠
包路径 + OpenAPI tag 区分：小程序端接口在 ../mini/ 包，前缀 /api/mini/*。
"""
from . import (agent, ai, auth, cards, docs, imports, learning, notes,
               profile, system)

# main.py 按这个顺序注册。没有前后依赖，但保持与 Swagger 分组一致更顺眼。
# auth 放第一个：它是所有带 user_id 的域的前置条件，排在最前面读起来顺。
# profile 放最后：它只读事件流/会话流 + 调 core/report，不被任何域依赖。
ALL = (auth.router, system.router, cards.router, learning.router,
       notes.router, imports.router, docs.router, ai.router, agent.router,
       profile.router)

__all__ = ['ALL', 'agent', 'ai', 'auth', 'cards', 'docs', 'imports', 'learning',
           'notes', 'profile', 'system']
