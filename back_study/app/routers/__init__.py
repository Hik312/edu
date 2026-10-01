# -*- coding: utf-8 -*-
"""路由集合。

按「改一处只动一个文件」切分：认证 / 结构 / 卡片 / 学习 / 笔记 / 导入 / 文档 / AI 精读 / AI Agent。
（更早的实现是一个 390 行的 if-elif 长梯子，加接口要横着读一遍才能确认没写重路径。）
这里是文件级的隔离，Swagger 也自动按 tags 分组。

agent.py 是唯一「依赖可选」的路由 —— 它在函数内部 import agent 包，
没装 langchain 也能正常起服务，调它的接口时才返 503 并提示怎么装。
"""
from . import agent, ai, auth, cards, docs, imports, learning, notes, system

# main.py 按这个顺序注册。没有前后依赖，但保持与 Swagger 分组一致更顺眼。
# auth 放第一个：它是所有带 user_id 的域的前置条件，排在最前面读起来顺。
ALL = (auth.router, system.router, cards.router, learning.router,
       notes.router, imports.router, docs.router, ai.router, agent.router)

__all__ = ['ALL', 'agent', 'ai', 'auth', 'cards', 'docs', 'imports', 'learning',
           'notes', 'system']
