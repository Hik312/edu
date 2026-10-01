# -*- coding: utf-8 -*-
"""算法库契约 —— 事件流 / 掌握度 / 模型参数的存放处。

**为什么单独开这一层，不塞进 `core/store/`**：

`store/` 装的是**业务数据**（用户、卡片、进度、笔记），按用户选的是 MySQL。
而这里装的是**算法和 AI 的数据**：复习事件流、BKT 掌握度、拟合出来的参数，
后期还有 LangGraph 的 checkpoint 和向量。用户定的分工是
「算法一类放 PG，用户一类放 MySQL」—— 两个库各管一摊，不是三选一。

塞进 `store/` 会让「换后端」这件事变成全量的：切一次就要把业务数据也迁一遍，
而算法数据是 append-only 的、丢了可以重放（只要卡片还在），两者的运维性质不同。

**契约要点**：

1. 全同步（和 store/ 一致，别在这里引入 async）。
2. 事件是 **append-only**，只增不改不删。这是知识追踪模型的命根子 ——
   事件流一旦能被改写，"拟合出来的参数"就没有意义了。
3. 所有方法都带 `user_id`。掌握度是 per-user 的，没有 user_id 的掌握度
   等于所有人共用一个大脑（这正是现在 `progress` 表的问题）。
4. 读不到一律返回空 / None，不抛异常 —— 算法层要能在"没数据"时照常工作。
"""

EVENT_KEYS = ('id', 'user_id', 'card_id', 'kc', 'level', 'correct',
              'at', 'elapsed_ms')


class AlgoStore(object):
    """算法库后端基类。方法没实现就抛，避免「以为接了其实没接」。"""

    name = 'base'

    # ---------------- 事件流（append-only）----------------
    def events_append(self, ev):
        """追加一条复习事件，返回写进去的那条（带 id）。"""
        raise NotImplementedError

    def events_of(self, user_id, kc=None, card_id=None, limit=500):
        """取某人的事件，按时间正序（BKT 要按序回放）。"""
        raise NotImplementedError

    def events_count(self, user_id=None):
        raise NotImplementedError

    def events_clear(self, user_id=None):
        """只给测试和「重置学习数据」用，正常流程不许调。"""
        raise NotImplementedError

    # ---------------- 掌握度（BKT 产出）----------------
    def mastery_get(self, user_id, kc):
        """返回 float 或 None（还没算过）。"""
        raise NotImplementedError

    def mastery_put(self, user_id, kc, p, extra=None):
        raise NotImplementedError

    def mastery_all(self, user_id):
        """{kc: p}，给看板和到期排序用。"""
        raise NotImplementedError

    def mastery_clear(self, user_id=None):
        raise NotImplementedError

    # ---------------- 模型参数（拟合产出）----------------
    def params_get(self, key, default=None):
        raise NotImplementedError

    def params_put(self, key, value):
        """value 必须是可 JSON 化的（dict / list / 数字）。"""
        raise NotImplementedError

    # ---------------- 自检 ----------------
    def ping(self):
        """能不能正常读写。False 就说明该降级了。"""
        raise NotImplementedError
