# -*- coding: utf-8 -*-
"""鉴权单元测试。项目里第一份自动化测试 —— 放在鉴权上，因为它是
「一旦写错就是任意用户登录」的那类代码，且改动后没有任何页面会报错提醒你。

跑法（不用起服务、不碰数据库）：
    back_study/.venv/Scripts/python.exe back_study/scripts/test_security.py

退出码 0 = 全过，1 = 有失败。

**换 JWT 库 / 调 PBKDF2_ROUNDS / 改密钥来源之后，先跑这个。**
覆盖四件事：
  1. 签发→验签能拿回 sub
  2. **老 token 兼容**：迁移前手写 HS256 发出的 token 照样能验过
     （HS256 就是 HMAC-SHA256，算法和密钥都没变 → 不会被强制重新登录）
  3. 各种无效输入一律返回 None，绝不抛异常（调用方只判空）
  4. **alg 混淆攻击**：alg=none 空签名、alg=RS256 拿 HMAC 签名冒充，都必须被拒
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

# 用固定环境变量喂密钥，免得脚本去读 config.local.json 或往 data/store/ 落盘。
# 必须在 import security 之前设好 —— 它在 import 时不读，但 get_secret() 会缓存。
os.environ['JWT_SECRET'] = 'test-secret-0123456789-abcdefghijklmnop'

HERE = os.path.dirname(os.path.abspath(__file__))          # back_study/scripts
BACK = os.path.dirname(HERE)                               # back_study
sys.path.insert(0, os.path.join(BACK, 'core'))

import security  # noqa: E402

SEC = security.get_secret()
_failed = []


def chk(name, cond, extra=''):
    print(('  OK    ' if cond else '  FAIL  ') + name
          + (('   | %s' % (extra,)) if extra != '' else ''))
    if not cond:
        _failed.append(name)


def _b64e(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _jb(obj):
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _handmade(header, body, secret):
    """按 JWT 规范手搓一个 token（不经过 PyJWT），用来造老 token 和伪造品。"""
    seg = '%s.%s' % (_b64e(_jb(header)), _b64e(_jb(body)))
    sig = hmac.new(secret.encode('utf-8'), seg.encode('ascii'), hashlib.sha256).digest()
    return '%s.%s' % (seg, _b64e(sig))


def main():
    now = int(time.time())

    print('-- 1. 签发 / 验签 --')
    t = security.make_token(42, SEC)
    p = security.read_token(t, SEC)
    chk('round trip 拿回 sub', p is not None and p.get('sub') == '42', p)
    chk('payload 带 exp', p is not None and p.get('exp') > now)

    print('-- 2. 老 token 兼容（迁移前的手写 HS256）--')
    old = _handmade({'alg': 'HS256', 'typ': 'JWT'},
                    {'sub': '7', 'iat': now, 'exp': now + 3600}, SEC)
    p2 = security.read_token(old, SEC)
    chk('老 token 仍能验过，不会被强制重新登录',
        p2 is not None and p2.get('sub') == '7', p2)

    print('-- 3. 无效输入一律 None（不抛异常）--')
    chk('空串', security.read_token('', SEC) is None)
    chk('None', security.read_token(None, SEC) is None)
    chk('垃圾串', security.read_token('not-a-token', SEC) is None)
    chk('只有两段', security.read_token('a.b', SEC) is None)
    chk('错密钥', security.read_token(t, 'wrong-secret-0000000000000000000000') is None)
    chk('已过期', security.read_token(security.make_token(1, SEC, ttl=-10), SEC) is None)

    print('-- 4. alg 混淆必须被拒 --')
    none_tok = '%s.%s.' % (
        _b64e(_jb({'alg': 'none', 'typ': 'JWT'})),
        _b64e(_jb({'sub': '1', 'iat': now, 'exp': now + 3600})))
    chk('alg=none 空签名', security.read_token(none_tok, SEC) is None)
    chk('alg=RS256 拿 HMAC 签名冒充',
        security.read_token(_handmade({'alg': 'RS256', 'typ': 'JWT'},
                                      {'sub': '1', 'iat': now, 'exp': now + 3600},
                                      SEC), SEC) is None)

    print('-- 5. 口令哈希 --')
    h = security.hash_password('abc123456')
    chk('正确口令通过', security.verify_password('abc123456', h) is True)
    chk('错误口令拒绝', security.verify_password('wrong', h) is False)
    chk('坏格式不抛异常', security.verify_password('x', 'not-a-hash') is False)
    chk('空存储不抛异常', security.verify_password('x', '') is False)
    chk('盐随机（两次哈希不同）', security.hash_password('abc123456') != h)
    chk('哈希串里带轮数（将来调高不影响老用户）', h.startswith('pbkdf2_sha256$'))

    print()
    if _failed:
        print('FAILED: %d 项 -> %s' % (len(_failed), ', '.join(_failed)))
        return 1
    print('ALL OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
