# -*- coding: utf-8 -*-
"""卡片校验结果缓存（Redis）。

## 为什么缓存这个

校验一张卡要**联网搜索 + 调本地模型**，实测一次约 60 秒。而校验的
**结论对同一张卡、同一份内容是稳定的** —— 卡没改，答案就不该变。
问第二次同样的知识点时重跑一遍纯属浪费，而且把「后台核对」拖到一分钟，
用户等得很没道理。

## 失效策略：靠**内容指纹**，不靠时间

key 里带 `指纹 = md5(参与校验的字段内容)`。所以：
- 卡被改（内容变了）→ 指纹变 → 自动重新校验，**不会返回旧结论**
- 卡没改→ 指纹不变 → 命中缓存
- TTL 只是兜底（默认 7 天），真正的失效靠指纹

★ 这里刻意**不用「卡 id + 时间」当key**：那样改了卡之后，
  在 TTL 到期前会一直返回旧结论 —— 而"卡改了却给旧校验结果"
  比"慢"严重得多（前端会拿旧建议去改已经被改过的卡）。

## 降级策略

`core/cache.py` 已经保证 Redis 挂了自动回退进程内 MemoryCache、
且读失败返回 None 不抛异常。这里只用它做 get/set，
所以 Redis 不可用时功能照常（只是每次重算）。
"""
import hashlib
import json
import os

import cache as core_cache

# 参与指纹的字段：与 verify._SHOW_FIELDS 保持一致。
# ★ 必须一致：漏一个字段就意味着"改了那个字段但指纹没变"→ 拿到旧结论。
_FINGERPRINT_FIELDS = ['title', 'oneLine', 'mechanism', 'why', 'analogy',
                       'scene', 'keywords', 'interviewQ']

PREFIX = 'study:verify:'
# 7 天：靠指纹失效，TTL 只是防止「一批永远不失效的 key」堆满内存。
DEFAULT_TTL = 7 * 24 * 3600

# 允许为空的环境变量：设成 0 / false 就全局关掉缓存（排障用）
def _enabled():
    return os.environ.get('VERIFY_CACHE', '1').strip().lower() not in ('0', 'false', 'off')


def fingerprint(card):
    """卡片内容指纹。字段内容变了指纹就变 —— 这是缓存失效的唯一依据。"""
    parts = []
    for f in _FINGERPRINT_FIELDS:
        v = card.get(f)
        if isinstance(v, (list, tuple)):
            v = ','.join(str(x) for x in v)
        parts.append('%s=%s' % (f, v if v is not None else ''))
    raw = '|'.join(parts).encode('utf-8')
    return hashlib.md5(raw).hexdigest()[:12]


def _key(card):
    return '%s%s:%s' % (PREFIX, card.get('id') or 'unknown', fingerprint(card))


def get(card):
    """读缓存的校验结论。**读失败/未命中一律返回 None**，绝不抛异常。"""
    if not _enabled():
        return None
    try:
        raw = core_cache.get().get(_key(card))
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        # 坏数据当没缓存（可能是老版本写了别的结构）
        return None


def put(card, result):
    """写缓存。result 是 _judge_batch 里那张卡的原始判定（或 None）。"""
    if not _enabled():
        return
    try:
        core_cache.get().set(_key(card), json.dumps(result, ensure_ascii=False),
                             ttl=DEFAULT_TTL)
    except Exception:
        pass    # 缓存写失败绝不影响主流程


def drop(card):
    """手动失效一张卡（用户刚改过卡时调用，可选 —— 指纹本来就会变，
    这个留着给「强制重核」用，比如用户想再看一遍联网证据）。"""
    try:
        core_cache.get().delete(_key(card))
    except Exception:
        pass


def stats():
    """给 /api/health 或调试用：当前有没有启用、用的哪个后端。"""
    c = core_cache.get()
    return {
        'enabled': _enabled(),
        'backend': type(c).__name__,
        'degraded': core_cache.degraded(),
        'ttl_days': DEFAULT_TTL // 86400,
    }