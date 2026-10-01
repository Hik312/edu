# -*- coding: utf-8 -*-
"""一次性端到端：同一张卡、同一串评级，分别用 ALGO=sm2 和 ALGO=fsrs 起服务，
看 HTTP 接口返回的进度是否真的按配置切换了算法。

验证的是「配置 → algo 注册表 → db.schedule → 接口」这条链路，
不是算法本身（算法对拍看 algo/demo.py）。
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
PY = os.path.join(ROOT, 'back_study', '.venv', 'Scripts', 'python.exe')
RUN = os.path.join(ROOT, 'back_study', 'run.py')
PORT = 8099
BASE = 'http://127.0.0.1:%d' % PORT
USER, PASS = 'zz_check_probe', 'zz_check_123456'


def req(method, path, body=None, token=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def wait_up(proc, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError('服务提前退出')
        try:
            s, _ = req('GET', '/api/health')
            if s == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError('服务没起来')


def run_case(algo_name, cid):
    env = dict(os.environ)
    env['ALGO'] = algo_name
    env['STORE'] = 'json'                 # 用文件后端，别动 MySQL 里的数据
    proc = subprocess.Popen([PY, RUN, str(PORT)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        wait_up(proc)
        s, body = req('POST', '/api/auth/login',
                      {'username': USER, 'password': PASS})
        if s != 200:
            print('登录失败 %s %s' % (s, body))
            return None
        token = body.get('token')

        req('DELETE', '/api/progress/' + cid, token=token)   # 从零开始
        rows = []
        for lv in (3, 3, 3, 2, 3):
            s, body = req('PUT', '/api/progress/' + cid,
                          {'level': lv}, token=token)
            if s != 200:
                print('标记失败 %s %s' % (s, body))
                return None
            rec = body.get('progress') or body
            rows.append((lv, rec.get('interval'), rec.get('ef'),
                         rec.get('reps'), rec.get('nextAt')))
        req('DELETE', '/api/progress/' + cid, token=token)   # 收尾清干净
        return rows
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    try:                                  # 端口可能本来就是空的，正常
        s, _ = req('GET', '/api/health')
        print('端口初始状态：HTTP %s（有服务在跑，本脚本会另起端口冲突）' % s)
    except Exception:
        print('端口初始状态：空闲（正常）')

    # 先随便拿一张卡
    proc = subprocess.Popen([PY, RUN, str(PORT)], env=dict(os.environ, STORE='json'),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        wait_up(proc)
        _, body = req('GET', '/api/cards?limit=1')
        cid = (body.get('cards') or body.get('items') or [{}])[0].get('id')
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    if not cid:
        print('拿不到卡 id：%s' % body)
        return 1
    print('测试卡：%s\n' % cid)

    out = {}
    for name in ('sm2', 'fsrs'):
        rows = run_case(name, cid)
        out[name] = rows
        print('=== ALGO=%s ===' % name)
        if not rows:
            print('  （失败）')
            continue
        print('  评级  间隔  ef/D    reps  下次到期')
        for lv, iv, ef, reps, nxt in rows:
            print('  %-4s  %-4s %-6s %-4s %s'
                  % ({1: '不会', 2: '模糊', 3: '会'}.get(lv, lv), iv, ef, reps, nxt))
        print()

    if out.get('sm2') and out.get('fsrs'):
        same = out['sm2'] == out['fsrs']
        print('两个算法结果相同？%s —— %s'
              % (same, '**异常：配置没生效**' if same else '正常，切换生效'))
        return 1 if same else 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
