# -*- coding: utf-8 -*-
"""预置管理员账号 —— 公开部署（ADMIN_FIRST=0）下 admin 的唯一入口。

用法（在项目根 study/ 下跑）：

    python back_study/scripts/make_admin.py <用户名> <密码> [昵称]
    python back_study/scripts/make_admin.py <用户名> -          # 密码交互输入，不进 shell 历史

账号不存在就建（密码走和注册同一套 check_password 规则），存在就只提权，
**不改已有账号的密码**。提权直接写存储层：users 域没有改角色接口
（角色不在改资料接口里是刻意的防越权设计），运维脚本是唯一例外。
"""
import getpass
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))            # back_study/scripts
CORE = os.path.join(os.path.dirname(HERE), 'core')
if CORE not in sys.path:
    sys.path.insert(0, CORE)

import db                                                     # noqa: E402


def main(argv):
    # Windows 控制台默认 GBK，中文 docstring 会打成乱码（同 run.py 的处理）
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if len(argv) < 2:
        print(__doc__)
        return 1
    name, pw = argv[0], argv[1]
    display = argv[2] if len(argv) > 2 else ''
    if pw == '-':
        pw = getpass.getpass('密码: ')
    u = db.user_by_name(name)
    if u is None:
        u, err = db.create_user(name, pw, display)
        if err:
            print('建号失败：%s' % err)
            return 1
    raw = db.backend().user_get(u['id'])
    if raw.get('role') != 'admin':
        raw['role'] = 'admin'
        db.backend().user_put(raw)
    print('admin 就绪：%s (id=%s)' % (name, u['id']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))