# -*- coding: utf-8 -*-
"""认证原语：密码哈希 + JWT 签发/校验 + 用户名规则。

**JWT 用 PyJWT，不再手写**（2026-09-26 改）
原先这里手写了 base64url + hmac-sha256，理由只有一个：零依赖版 `server.py`
一个第三方包都不能装。项目已经决定不再维持「零依赖」这条线（后面还要接 Redis，
本来就要装依赖），所以这层妥协没有意义了 —— 手写 JWT 省下的依赖，
换来的是要自己维护签名/验签/过期逻辑，而**这段代码一旦写错就是鉴权绕过**，
是所有代码里最不该手写的一类。

换 PyJWT 的实际收益，按重要性排：
  1. `decode()` **强制要求显式传 `algorithms`**。手写版压根不看 header 里的 alg，
     这次侥幸没出事（它无条件按 HS256 验签，alg:none 的伪造 token 会验签失败），
     但那属于运气 —— 省略 alg 校验是 JWT 的经典漏洞，PyJWT 从接口上堵死了。
  2. `exp` / `nbf` / `iat` 的语义由库保证（含时钟偏移处理），不用自己比时间戳。
  3. 将来要换 RS256 或加 `iss`/`aud`，改一个参数的事。

**兼容性**：老 token 不受影响。PyJWT 的 HS256 就是 HMAC-SHA256，
签名算法和密钥都没变，升级前发出去的 token 照样能验过，不会被强制重新登录。

**密码哈希仍用标准库 pbkdf2_hmac**，没换成 bcrypt/argon2 ——
120k 轮 SHA256 对这个规模够用，而换它要引入带 C 扩展的依赖。
真要加固，先把 PBKDF2_ROUNDS 调上去，收益比换算法直接。
"""

import hashlib
import json
import hmac
import os
import re
import secrets
import sys
import threading
import time

try:
    import jwt
except ImportError as _e:  # pragma: no cover
    raise RuntimeError(
        '缺少 PyJWT。装一下：pip install PyJWT\n'
        '（或 pip install -r requirements.txt）。\n'
        '本项目已不再支持「零依赖」运行，鉴权改用 PyJWT 签发/校验 HS256。'
    ) from _e

BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY_DIR = os.path.dirname(BACK_DIR)
SECRET_FILE = os.path.join(STUDY_DIR, 'data', 'store', 'jwt-secret.txt')

#: PBKDF2 迭代次数。12 万次在现代机器上约 60~90ms。
#: 想加固就调这个数 —— 老用户不受影响，因为轮数写进了哈希串里（见 hash_password）。
PBKDF2_ROUNDS = 120_000

#: 一张卡背一天的场景下，7 天有效期比 1 小时舒服得多 ——
#: 学习工具动不动就要求重新登录，比不鉴权还烦。
TOKEN_TTL = 7 * 24 * 3600

#: **只允许 HS256**。这个列表是白名单，不放 RS256 / none ——
#: 攻击者把 header 的 alg 改成别的算法时，PyJWT 会直接拒掉。
ALLOWED_ALGS = ('HS256',)

USERNAME_RE = r'^[A-Za-z0-9_]{3,20}$'


# ---------------------------------------------------------------- 密码
def hash_password(password: str) -> str:
    """返回 `pbkdf2_sha256$轮数$盐$摘要`。

    把轮数写进字符串是刻意的：以后调高 PBKDF2_ROUNDS，老用户的密码
    仍然能用原轮数验证通过，不需要强制所有人改密码。
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ROUNDS)
    return 'pbkdf2_sha256$%d$%s$%s' % (PBKDF2_ROUNDS, salt.hex(), dk.hex())


def verify_password(password: str, stored: str) -> bool:
    """恒返回 bool，绝不抛异常 —— 调用方只需要知道「对还是不对」。

    用 hmac.compare_digest 而不是 `==`：字符串比较是短路的，
    理论上能从耗时差里把摘要一个字节一个字节猜出来。
    """
    try:
        algo, rounds, salt_hex, dk_hex = (stored or '').split('$')
        if algo != 'pbkdf2_sha256':
            return False
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                 bytes.fromhex(salt_hex), int(rounds))
    except Exception:
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


# ---------------------------------------------------------------- JWT
def make_token(user_id, secret: str, ttl: int = TOKEN_TTL, extra=None) -> str:
    """签发 token。`sub` 一律转成 str —— JWT 规范要求 sub 是字符串。"""
    now = int(time.time())
    body = {'sub': str(user_id), 'iat': now, 'exp': now + int(ttl)}
    if extra:
        body.update(extra)
    # PyJWT 2.x 返回 str（1.x 返回 bytes，那时到处要 .decode()，现在不用了）
    return jwt.encode(body, secret, algorithm='HS256')


def read_token(token: str, secret: str):
    """校验签名与有效期，通过返回 payload，任何一种失败都返回 None。

    返回值统一成 None 是刻意的：签名错、格式错、过期，对调用方来说
    处理方式完全一样（401），分成不同异常只会诱使人写出错误的分支。

    `algorithms=ALLOWED_ALGS` **不能省**：省了 PyJWT 会抛错，
    而如果哪天有人为了"让它跑起来"改成读 header 里的 alg，
    就等于把 alg:none 伪造 token 的路子打开了 —— 别改这里。
    """
    if not token:
        return None
    try:
        return jwt.decode(token, secret, algorithms=list(ALLOWED_ALGS))
    except Exception:
        # 过期、签名错、base64 坏、不是三段 —— 对调用方都是「无效」
        return None


# ---------------------------------------------------------------- 密钥
_cached_secret = None


def get_secret() -> str:
    """密钥来源，按优先级：环境变量 → config.local.json → 本地文件 → 新生成。

    **必须持久化**。如果每次启动随机生成，服务一重启所有人的 token 全失效，
    表现是「昨天还好好的，今天一打开就让我重新登录」，而且查不出原因。
    落盘位置在 data/store/ 下（已在 .gitignore 里），权限设 600。
    """
    global _cached_secret
    if _cached_secret:
        return _cached_secret

    s = (os.environ.get('JWT_SECRET') or '').strip()
    if not s:
        try:
            # 这里**故意**用函数内 import，不是漏了提到文件头：
            # core/security.py 要能被 scripts/test_security.py 单独 import
            # （不依赖 config.local.json、不依赖 store 包能导入成功）。
            # 提到顶部的话，测鉴权就得先有一个能用的 store 环境。
            import store as store_pkg
            s = str((store_pkg.load_config() or {}).get('JWT_SECRET') or '').strip()
        except Exception:
            s = ''
    if not s:
        try:
            with open(SECRET_FILE, 'r', encoding='utf-8') as f:
                s = f.read().strip()
        except Exception:
            s = ''
    if not s:
        s = secrets.token_urlsafe(48)
        try:
            os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
            with open(SECRET_FILE, 'w', encoding='utf-8') as f:
                f.write(s)
            os.chmod(SECRET_FILE, 0o600)
            print('[auth] 已生成 JWT 密钥并保存到 %s' % SECRET_FILE)
        except Exception as e:
            print('[auth] 密钥无法落盘（本次运行有效，重启后所有人要重新登录）: %s' % e,
                  file=sys.stderr)

    # HS256 要求密钥至少 32 字节（RFC 7518 §3.2），短了 PyJWT 会警告。
    # 走的都是上面那条 token_urlsafe(48)，只有手填环境变量才可能踩到。
    if len(s.encode('utf-8')) < 32:
        print('[auth] 警告：JWT 密钥短于 32 字节，HS256 强度不足（请改 JWT_SECRET）',
              file=sys.stderr)

    _cached_secret = s
    return s


# ---------------------------------------------------------------- 输入校验
def check_username(name: str):
    """返回 (ok, 规范化后的用户名 或 错误话术)。别在各处各写一份。"""
    name = (name or '').strip()
    if not name:
        return False, '用户名不能为空'
    if not re.match(USERNAME_RE, name):
        return False, '用户名只能是 3-20 位字母、数字或下划线'
    return True, name


def check_password(pw: str):
    pw = pw or ''
    if len(pw) < 6:
        return False, '密码至少 6 位'
    if len(pw) > 64:
        # 不设上限的话，有人塞 1MB 进来，每次登录都要跑一遍 PBKDF2，
        # 相当于白送一个 DoS 入口
        return False, '密码最多 64 位'
    return True, pw

# ---------------------------------------------------------------- 登录限速
# ★ 2026-11-15 加（评测遗留项）：此前登录接口可无限爆破 —— JWT 有效期 7 天，
#   拿到 token 就是长期凭据，而 PBKDF2 12 万轮反而让每次尝试的服务端成本
#   更高（爆破者并发打进来 = 白送 DoS）。限速策略：
#   - 双键计数：按用户名（防定向爆破单账号）+ 按客户端 IP（防换用户名扫库），
#     任一超限即拒；
#   - 窗口 10 分钟、上限 10 次失败；成功登录清零该用户名的失败记录；
#   - 计数存 Redis（cache.get()，多 worker 一致），Redis 不可用降级进程内
#     dict —— 单机部署下语义不变，只是跨进程不共享（可接受，见 cache.py）。
LOGIN_WINDOW = 600          # 秒
LOGIN_MAX_FAILS = 10

_fail_mem = {}              # 进程内降级桶 {key: [timestamps]}
_login_lock = threading.Lock()


def _login_key(kind, ident):
    return 'login:fail:%s:%s' % (kind, str(ident or '').strip().lower())


def _login_failures(key, now):
    """读某个 key 的失败时间戳列表（Redis 或进程内），顺手清掉窗口外的。"""
    try:
        import cache as _cache
        raw = _cache.get().get(key)
        if raw:
            return [t for t in json.loads(raw) if now - t < LOGIN_WINDOW]
    except Exception:
        pass
    return [t for t in _fail_mem.get(key, []) if now - t < LOGIN_WINDOW]


def _remember_fail(key, now):
    stamps = _login_failures(key, now)
    stamps.append(now)
    _fail_mem[key] = stamps               # 双写：Redis 挂了内存桶还能接住
    try:
        import cache as _cache
        _cache.get().set(key, json.dumps(stamps), ttl=LOGIN_WINDOW + 60)
    except Exception:
        pass


def login_blocked(username, ip=''):
    """这次登录尝试是否应被拒绝。返回 (blocked, 剩余秒数)。"""
    now = time.time()
    with _login_lock:
        for kind, ident in (('user', username), ('ip', ip)):
            key = _login_key(kind, ident)
            fails = _login_failures(key, now)
            if len(fails) >= LOGIN_MAX_FAILS:
                remain = int(LOGIN_WINDOW - (now - fails[0])) + 1
                return True, max(remain, 1)
    return False, 0


def record_login_failure(username, ip=''):
    now = time.time()
    with _login_lock:
        for kind, ident in (('user', username), ('ip', ip)):
            _remember_fail(_login_key(kind, ident), now)


def clear_login_failures(username):
    """登录成功后清用户名维度的计数（IP 维度保留 —— 防同一个 IP 上
    「试很多账号各试 9 次」绕过窗口）。"""
    with _login_lock:
        _fail_mem.pop(_login_key('user', username), None)
        try:
            import cache as _cache
            _cache.get().delete(_login_key('user', username))
        except Exception:
            pass
