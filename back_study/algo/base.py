# -*- coding: utf-8 -*-
"""算法层契约 —— 所有间隔重复算法都长同一个样子。

**为什么要有这一层**：调度逻辑原本写在 `core/db.py:schedule()` 里，和
「读卡片 / 存进度」搅在一起。想换个算法（比如把 SM-2 换成 FSRS）就得进
数据层改业务逻辑，改完还没法证明新算法更好 —— 因为没有一个地方能同时
跑两个算法、拿同一批数据对拍。

现在算法全部搬到这里，`db.schedule()` 只剩一行转发。好处有三条：

1. **可互换**：任何算法都实现同一个 `schedule(prev, level)`，换算法改一个
   配置项，数据层一行不用动。
2. **可对拍**：`algo/demo.py` 能把两个算法喂同一串评级序列，直接比出
   「谁安排的复习次数更少、谁的间隔增长更稳」。这是能写进简历的那种结论，
   光说「我用了 XX 算法」谁都会。
3. **可独立测**：这个包**不反向依赖 core**（不 import db / store），
   拿一个 dict 就能跑，不需要起服务、不需要连数据库。

**契约（改之前想清楚）**：

- 入参 `prev` 是「这张卡上一次的进度记录」，可能是 `None`（从没复习过）
  或者是**用户手改过 / 老版本留下来的残 dict**，字段缺失、类型不对都得扛住。
- 出参必须是这 6 个键：`level / interval / ef / reps / nextAt / updatedAt`。
  **不要加键** —— MySQL 的 `progress` 表就是这 6 列（`interval`→`interval_d`），
  多出来的字段会被 `progress_put()` 静默丢弃，在 JSON 后端看着好好的、
  一切到 MySQL 行为就变了。需要新字段就得先改存储层（三处，见 docs/技术架构.md）。
"""

from datetime import date, timedelta

#: 评级。和前端、db.due_list 的排序档位保持一致，别另起一套数字。
LEVEL_AGAIN = 1   # 不会
LEVEL_HARD = 2    # 模糊
LEVEL_GOOD = 3    # 会

#: 进度记录的合法字段。出参只允许有这些键（原因见上面第 2 条）。
REC_KEYS = ('level', 'interval', 'ef', 'reps', 'nextAt', 'updatedAt')

#: 间隔上限（天）。
#: SM-2 的间隔是**指数增长**的（iv = iv × ef），一张卡连着标几十次「会」，
#: interval 就会涨到几千年 —— 然后 `date + timedelta` 直接抛
#: `OverflowError: date value out of range`，整个请求 500。
#: 这不是理论问题：批造数据的脚本跑两遍就会撞上。
#: 五年足够长了，超过五年的复习计划没有实际意义。
MAX_INTERVAL = 365 * 5


def clamp_interval(days):
    """把间隔夹到 [0, MAX_INTERVAL]。所有算法算完间隔都要过这一道。"""
    try:
        return max(0, min(int(days), MAX_INTERVAL))
    except (TypeError, ValueError):
        return 0


# ---------- 日期 ----------
# 这里刻意不复用 core/db.py 的同名函数：algo 是叶子层，一旦反向 import
# core 就成了循环依赖（db 要用 algo），而且这个包就得拖着整个数据层才能跑。
# 三个函数十几行，重复的成本远低于循环依赖的成本。
def today_str(d=None):
    """今天，格式 YYYY-MM-DD。"""
    return (d or date.today()).strftime('%Y-%m-%d')


def add_days(s, n):
    """'2026-09-29' + 3 → '2026-10-02'。"""
    y, m, d = [int(x) for x in s.split('-')]
    return today_str(date(y, m, d) + timedelta(days=n))


def diff_days(a, b):
    """两个 YYYY-MM-DD 相差几天（b - a）。"""
    ya, ma, da = [int(x) for x in a.split('-')]
    yb, mb, db_ = [int(x) for x in b.split('-')]
    return (date(yb, mb, db_) - date(ya, ma, da)).days


# ---------- 取值防御 ----------
def _num(prev, key, default, cast=float):
    """从旧记录里取一个数；缺字段 / 类型不对 / 为 None 一律回落默认值。

    为什么要这么啰嗦：`prev` 可能来自老版本数据、手改的 JSON，或者 MySQL
    取回来的 `Decimal`（DECIMAL 列不转 float 会直接把整个请求打 500）。
    """
    v = (prev or {}).get(key)
    try:
        if v is None:
            return default
        return cast(v)
    except (TypeError, ValueError):
        return default


class Algo(object):
    """算法基类。新算法继承它、实现 `schedule()`，再在 `__init__.py` 注册。"""

    #: 注册表里的名字（配置里写的就是这个）
    name = 'base'
    #: 给人看的名字
    label = '抽象算法（不要直接用）'
    #: 数据需求说明。写清楚「要攒多少数据才敢用」，别让人拿 20 条记录训 DKT。
    needs = '无'
    #: ef 这一列被本算法当成什么用。六个字段是死的、含义是活的 ——
    #: SM-2 拿它当难度因子、FSRS 当难度 D、BKT 当掌握度 p，所以必须声明，
    #: 否则看 progress.json 的人根本不知道 2.6 是难度还是概率。
    ef_note = 'ef 字段的含义（子类覆盖）'

    def schedule(self, prev, level, today=None):
        """算这张卡下一次什么时候复习。

        prev   : 上一次的进度记录 dict，可能是 None
        level  : 本次评级，见 LEVEL_* 三个常量
        today  : 仅测试用，注入「今天」；不传就用系统日期
        返回   : 只含 REC_KEYS 六个键的 dict
        """
        raise NotImplementedError

    # ---------- 造返回值 ----------
    def _rec(self, level, interval, ef, reps, next_at, updated_at):
        """统一组装返回值，顺手把类型收拾干净。

        interval / reps 必须是 int（MySQL 是 INT 列，前端也当整数显示）；
        ef 保留两位小数 —— 它同时被 SM-2 当难度因子、被 FSRS 当难度 D 用，
        是个通用的数值槽。
        """
        return {
            'level': int(level),
            'interval': clamp_interval(interval),
            'ef': round(float(ef), 2),
            'reps': max(0, int(reps)),
            'nextAt': next_at,
            'updatedAt': updated_at,
        }

    def next_at(self, interval, today=None):
        """下次到期日 = 今天 + 间隔。间隔在这里也要夹一次 ——
        `_rec()` 夹的是存进库里的值，`next_at()` 可能在别处被单独调用。"""
        base = today or today_str()
        return add_days(base, clamp_interval(interval))

    def describe(self):
        """给 `/api/...` 或 demo 用的一行自我介绍。"""
        return {'name': self.name, 'label': self.label, 'needs': self.needs}
