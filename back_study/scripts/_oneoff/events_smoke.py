# -*- coding: utf-8 -*-
"""一次性验证：事件流能不能真的写进去、读出来、按人隔离。

不起服务，直接在数据层打。用 STORE=json 避免动 MySQL 里的真实数据。
"""
import os
import sys

_BACK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_CORE = os.path.join(_BACK, 'core')
for p in (_BACK, _CORE):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.path.insert(0, _CORE)

# setdefault 而不是直接赋值：外面传 ALGO_STORE=pg 时要能盖住这里的默认值，
# 否则「想验 PG 却默默验了 json」，还打印一句全部通过 —— 假绿。
os.environ.setdefault('STORE', 'json')
os.environ.setdefault('ALGO_STORE', 'json')

import db                                                  # noqa: E402
import algostore                                           # noqa: E402

ALICE, BOB = 'u_alice', 'u_bob'
CARD = 'ai-agent'


def main():
    print('算法库后端：%s（降级=%s）' % (algostore.get().name,
                                        algostore.degraded()))
    # 从零开始
    db.algostore.get().events_clear()
    db.algostore.get().mastery_clear()

    for lv in (3, 2, 1, 3):
        db.set_level(CARD, lv, user_id=ALICE)
    db.set_level(CARD, 3, user_id=BOB)

    a = db.events_of(ALICE)
    b = db.events_of(BOB)
    print('\nAlice 事件 %d 条：' % len(a))
    for e in a:
        print('   level=%s correct=%s at=%s kc=%s'
              % (e['level'], e['correct'], e['at'], e['kc']))
    print('Bob 事件 %d 条' % len(b))
    print('总数（不分人）%d 条' % db.events_count())

    ok = True
    ok &= len(a) == 4 and len(b) == 1
    ok &= [e['correct'] for e in a] == [1, 0, 0, 1]
    ok &= db.events_count(ALICE) == 4

    # 不传 user_id 的老调用方式：状态照写，但不产生事件
    before = db.events_count()
    db.set_level(CARD, 3)
    ok &= db.events_count() == before
    print('\n不传 user_id 时事件数不变：%s' % (db.events_count() == before))

    # 掌握度槽位（BKT 还没落地，先验证读写通路）
    algostore.get().mastery_put(ALICE, CARD, 0.62)
    got = algostore.get().mastery_get(ALICE, CARD)
    ok &= abs((got or 0) - 0.62) < 1e-9
    print('掌握度写入再读出：%s' % got)

    # 参数槽位
    algostore.get().params_put('bkt:default', {'p_transit': 0.1, 'p_slip': 0.1})
    print('参数槽位：%s' % algostore.get().params_get('bkt:default'))

    # 收尾：清掉测试数据，别留脏事件在库里。
    # progress 也要清 —— set_level 会顺手写进度，只在 json 库里留一条
    # ai-agent 的假进度，会让 check.js 的「json vs mysql 队列对照」
    # 报数据不同步（json=3 mysql=0），看起来像排序逻辑坏了。
    db.algostore.get().events_clear()
    db.algostore.get().mastery_clear()
    db.reset_progress(CARD)
    print('\n清理后事件数：%d' % db.events_count())
    print('\n结果：%s' % ('全部通过' if ok else '**有失败项**'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
