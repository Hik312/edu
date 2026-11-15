# -*- coding: utf-8 -*-
"""登录限速的单元测试 —— security.login_blocked / record / clear 三件套。

双键口径（用户名 + IP）与 10 次窗口在 security.py 有完整注释，这里锁行为。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))

import security



# ---------- 登录限速（2026-11-15 加） ----------
def test_login_rate_limit_blocks_after_max_failures():
    """同一用户名连续失败 10 次 → 第 11 次被拒；别的用户名（换 IP）不受影响。"""
    sec = security
    ip = 'rl-ip-user-test'
    # 清干净测试账号的计数（用户名 + IP 双键都清，测试间互不污染）
    sec.clear_login_failures('rl_test_user')
    sec._fail_mem.pop(sec._login_key('ip', ip), None)
    for _ in range(sec.LOGIN_MAX_FAILS):
        sec.record_login_failure('rl_test_user', ip)
    blocked, remain = sec.login_blocked('rl_test_user', ip)
    assert blocked is True
    assert remain >= 1
    # 其它用户名不受该用户的失败计数牵连（换 IP，避开留下的 IP 计数）
    assert sec.login_blocked('rl_other_user', 'rl-ip-other')[0] is False
    # 成功登录清零用户名维度（换 IP 查，避开本测试留下的 IP 计数）
    sec.clear_login_failures('rl_test_user')
    assert sec.login_blocked('rl_test_user', 'rl-ip-clear')[0] is False


def test_login_rate_limit_ip_dimension():
    """IP 维度独立计数：换用户名扫库也会被 IP 键拦住。"""
    sec = security
    ip = 'rl-test-ip-2'
    try:
        for _ in range(sec.LOGIN_MAX_FAILS):
            sec.record_login_failure('rl_user_a_%d' % _, ip)
        blocked, _ = sec.login_blocked('rl_fresh_user', ip)
        assert blocked is True          # 换了用户名，IP 键超限照样拦
    finally:
        # 清掉该 IP 的计数（直接清进程内桶；Redis 键 10 分钟自然过期）
        sec._fail_mem.pop(sec._login_key('ip', ip), None)
