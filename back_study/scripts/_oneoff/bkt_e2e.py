# -*- coding: utf-8 -*-
"""一次性验证：BKT 在**真实调用路径**上跑得通。

和 bkt_smoke.py 的区别：那个直接调 algo 包（纯函数），这个走
`db.set_level()` → 事件流 → `db.fit_bkt()` → `db.mastery_of()` 的完整链路，
中间穿过了 algostore（PG / json）和 cache（Redis / 内存）两层。

跑法（默认走 PG + Redis，全链路最真实）：
    python back_study/scripts/_oneoff/bkt_e2e.py
只验算法不吃中间件：
    ALGO_STORE=json python back_study/scripts/_oneoff/bkt_e2e.py
"""
import os
import random
import sys

_BACK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _BACK not in sys.path:
    sys.path.insert(0, _BACK)
sys.path.insert(0, os.path.join(_BACK, 'core'))

os.environ.setdefault('STORE', 'json')      # 别动 MySQL 里的真实进度

import algo                                                # noqa: E402
import cache                                               # noqa: E402
import db                                                  # noqa: E402

U = 'zz-bkt-e2e'
TRUTH = {'p_init': 0.20, 'p_transit': 0.15, 'p_slip': 0.10, 'p_guess': 0.25}
ok = True


def check(name, cond, extra=''):
    global ok
    ok &= bool(cond)
    print('%-44s %s %s' % (name, 'OK' if cond else '**FAIL**', extra))


def level_of(correct):
    """二值 → 三档评级（走 BKT 的「模糊算错」约定）。"""
    return 3 if correct else 1


def main():
    store = db.algostore.get()
    print('算法库：%s（降级=%s）   缓存：%s（降级=%s）'
          % (store.name, db.algostore.degraded(),
             cache.get().name, cache.degraded()))
    print('调度算法：%s\n' % algo.get().name)

    kcs = ['zz-kc-%02d' % i for i in range(12)]
    # 从零开始，别让上次的残留影响拟合。
    # ★ progress 也要清：SM-2 的间隔会跨次累积，跑第二遍时 prev.interval
    #   已经很大，再乘 ef 就溢出了 date 的范围（现在 algo 层有上限兜底，
    #   但测试脚本自己留着脏状态，拟合出来的数也没意义）。
    store.events_clear(U)
    store.mastery_clear(U)
    for k in kcs:
        db.reset_progress(k)

    # ---- 造数据：12 个知识点，每个练 12 次，答案按真值参数生成 ----
    rnd = random.Random(20260929)
    # 前 8 个知识点练 12 次，后 4 个只练 3 次。
    # 为什么故意不均：**每个 kc 都练到饱和的话，所有掌握度都会收敛到 1.0**，
    #   区分度断言就变成在测随机数而不是测模型（第一版就是这么写的，
    #   结果 min=max=1.00 直接 FAIL）。用练习量制造差异，
    #   顺便验证一件真正有意义的事：BKT 是否反映了「练得多 → 掌握度高」。
    trained, fresh = kcs[:8], kcs[8:]
    for kc in kcs:
        n_rep = 12 if kc in trained else 3
        p = TRUTH['p_init']
        for _ in range(n_rep):
            pc = p * (1 - TRUTH['p_slip']) + (1 - p) * TRUTH['p_guess']
            c = 1 if rnd.random() < pc else 0
            # ★ 走真实路径：set_level 才是真正会产生事件的地方
            db.set_level(kc, level_of(c), user_id=U)
            p = algo.bkt.step(p, c, TRUTH)

    n = db.events_count(U)
    check('事件写入', n == 8 * 12 + 4 * 3, '%d 条' % n)

    # ---- 拟合 ----
    params, info = db.fit_bkt(U)
    print('真值  %s' % TRUTH)
    print('拟合  %s' % params)
    print('info  %s' % info)
    check('数据量够，真的拟合了', info.get('fitted') is True)
    check('拟合参数落库', db.algostore.get().params_get(
        db._params_key(U)) is not None)

    # ---- 掌握度 + 缓存 ----
    kc0 = kcs[0]
    p1 = db.mastery_of(U, kc0)
    check('掌握度在 [0,1]', 0.0 <= p1 <= 1.0, '%.4f' % p1)

    cached = cache.get().get('bkt:p:%s:%s' % (U, kc0))
    check('掌握度进了缓存', cached is not None and abs(cached - p1) < 1e-9,
          'cache=%s' % cached)

    p2 = db.mastery_of(U, kc0)               # 第二次应该直接命中缓存
    check('两次读取一致（缓存没写歪）', abs(p1 - p2) < 1e-9)

    p3 = db.mastery_of(U, kc0, refresh=True)
    check('refresh 后重算且一致', abs(p1 - p3) < 1e-9)

    check('掌握度写进了 mastery 表',
          abs((store.mastery_get(U, kc0) or -1) - p1) < 1e-9,
          '%.4f' % (store.mastery_get(U, kc0) or -1))

    # ---- 练得多的知识点掌握度更高 ----
    p_trained = [db.mastery_of(U, k, refresh=True) for k in trained]
    p_fresh = [db.mastery_of(U, k, refresh=True) for k in fresh]
    avg_t = sum(p_trained) / len(p_trained)
    avg_f = sum(p_fresh) / len(p_fresh)
    check('练 12 次的掌握度 > 练 3 次的', avg_t > avg_f,
          '练12次均值=%.3f  练3次均值=%.3f' % (avg_t, avg_f))

    # ---- 清理 ----
    # progress 也要清：set_level 顺手写了进度，只在 STORE=json 下留着一堆
    # zz-kc-* 的假卡。不清的话 check.js 的「json vs mysql 队列对照」会看到
    # 一堆 json 有、mysql 没有的卡，直接报数据不同步。
    store.events_clear(U)
    store.mastery_clear(U)
    cache.get().clear('bkt:p:%s:' % U)
    for k in kcs:
        db.reset_progress(k)
    check('清理干净', db.events_count(U) == 0
          and not db.get_progress().get(kcs[0]))

    print('\n结果：%s' % ('全部通过' if ok else '**有失败项**'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
