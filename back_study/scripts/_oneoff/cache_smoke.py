# -*- coding: utf-8 -*-
"""一次性验证：缓存层到底用的是 Redis 还是内存，两者行为是否一致。

为什么单独验一次：`cache.get()` 连不上 Redis 时会**静默退回内存**，
业务照跑不报错。所以"没报错"不等于"用了 Redis"——必须把后端名字打出来看。
"""
import os
import sys

_BACK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _BACK not in sys.path:
    sys.path.insert(0, _BACK)
sys.path.insert(0, os.path.join(_BACK, 'core'))

import cache                                               # noqa: E402

KEY = 'probe:cache'


def main():
    c = cache.get()
    print('后端：%s   降级：%s' % (c.name, cache.degraded()))

    ok = True
    c.delete(KEY)
    ok &= c.get(KEY) is None
    print('空读：%s' % c.get(KEY))

    # dict 能不能存（走 JSON 序列化）
    c.set(KEY, {'p': 0.83, 'kc': 'ai-agent'}, ttl=60)
    got = c.get(KEY)
    ok &= isinstance(got, dict) and abs(got['p'] - 0.83) < 1e-9
    print('存 dict 再读：%s' % got)

    # 前缀清理
    c.set('probe:other', 1, ttl=60)
    cache.get().clear('probe:')
    ok &= c.get(KEY) is None
    print('前缀清理后：%s' % c.get(KEY))

    print('\n结果：%s' % ('全部通过' if ok else '**有失败项**'))
    if c.name == 'memory':
        print('注意：当前是内存降级。想用 Redis 就启动 E:\\Redis\\start.bat '
              '再重跑这个脚本。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
