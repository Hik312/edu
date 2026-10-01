# -*- coding: utf-8 -*-
"""SM-2（SuperMemo 2）简化版 —— 系统当前在跑的那个。

这是 2026-09-29 从 `core/db.py:schedule()` **逐行搬过来**的，业务逻辑一个
数字都没改。搬的目的不是重写，是让它和 FSRS 站在同一条起跑线上，能被同一
个脚本对拍。

算法本身三句话：

- 记得住（会）：间隔按 ef 倍数拉长，ef 往上加一点（上限 2.6）
- 有点模糊：间隔砍半、ef 往下扣 0.15，但不清零连续次数
- 完全不会：一切归零，明天重来，ef 扣 0.2

**它的问题**：ef 只能靠 ±0.1/0.15/0.2 的硬编码步长蠕动，跟真实记忆曲线
没关系；间隔永远是整数乘法，第三档之后就开始指数爆炸（1→3→9→27→81…）。
这就是要有 FSRS 的原因。

**顺带修了一个老 bug**：原版判断 `isinstance(p.get('ef'), (int, float))` ——
MySQL 的 `ef` 列是 DECIMAL，pymysql 取回来是 `Decimal`，**不是** int/float，
于是每复习一次 ef 都被静默重置成 2.5，等于「用了数据库之后难度因子永远是
初始值」。现在统一走 `base._num()`，Decimal 会被正常转成 float。
"""

from .base import Algo, LEVEL_GOOD, LEVEL_HARD, _num, today_str


class SM2(Algo):
    name = 'sm2'
    label = 'SM-2 简化版（间隔重复经典算法）'
    needs = '零数据即可用。纯规则，不学习、不需要历史。'
    #: 文档写着「每个算法都在 ef_note 里声明了」，但从前只有 BKT 有，
    #: SM2/FSRS 继承的是基类那个占位符 —— 看 progress 表的人
    #: 根本不知道这个 2.6 是难度还是概率。补齐。
    ef_note = 'ef = 难度因子（1.3~2.6），越大表示这张卡越容易记住'

    #: ef 的上下界。原实现里写死在函数里，提到类上方便调参对比。
    EF_MIN = 1.3
    EF_MAX = 2.6

    def schedule(self, prev, level, today=None):
        p = prev or {}
        # 三个状态都从旧记录里恢复，缺了就用「从没复习过」的初值。
        ef = _num(p, 'ef', 2.5)
        reps = _num(p, 'reps', 0, int)
        iv = _num(p, 'interval', 0, int)

        if level == LEVEL_GOOD:
            reps += 1
            if reps == 1:
                iv = 1
            elif reps == 2:
                iv = 3
            else:
                iv = max(1, round(iv * ef))
            ef = min(self.EF_MAX, ef + 0.1)
        elif level == LEVEL_HARD:
            # 模糊：间隔砍半但连续次数不清零 —— 记得「大概会」不算断档。
            iv = max(1, round(iv / 2)) if iv > 1 else 1
            ef = max(self.EF_MIN, ef - 0.15)
        else:
            # 不会：连击断掉，明天重来。
            reps = 0
            iv = 1
            ef = max(self.EF_MIN, ef - 0.2)

        day = today or today_str()
        return self._rec(level, iv, ef, reps, self.next_at(iv, day), day)
