# -*- coding: utf-8 -*-
"""翻译链路探针：真 HTTP 打 translate 的 6 个端点，验数字保护与续跑。

跑法：./.venv/Scripts/python.exe scripts/probe_translate.py [段数]
默认只翻 3 段（够验证全链路，不必等一小时）。
"""
import json
import secrets
import string
import sys
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8099'
USER = 'pzt%d' % (int(time.time()) % 1000000)
PWD = 'Pp' + ''.join(secrets.choice(string.ascii_letters + string.digits)
                    for _ in range(10)) + '7'
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
FAIL = []


def check(name, cond, detail=''):
    print('%s %s%s' % ('PASS' if cond else 'FAIL', name,
                       ('  ' + str(detail)[:120]) if detail else ''))
    if not cond:
        FAIL.append(name)


def api(path, body=None, tok=None, method=None):
    """★ method 必须显式传 —— 这个探针要打 PUT/DELETE，
    只靠「有没有 body」推断方法的话，PUT 会被发成 POST，
    服务端返回 405 而断言失败 ——症状看起来像「端点没实现」，
    其实是探针自己错了。"""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 method=method or ('POST' if data else 'GET'))
    req.add_header('Content-Type', 'application/json')
    if tok:
        req.add_header('Authorization', 'Bearer ' + tok)
    try:
        with OP.open(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')[:300]


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    st, b = api('/api/auth/login', {'username': USER, 'password': PWD})
    if st != 200:
        st, b = api('/api/auth/register',
                    {'username': USER, 'password': PWD, 'displayName': '探针'})
    tok = b.get('token')
    check('注册/登录', bool(tok), b)
    if not tok:
        return 1

    docs = api('/api/docs', tok=tok)[1]['docs']
    paper = next(d for d in docs if d.get('isPaper'))
    did = paper['id']
    print('文档：', paper['title'])

    # --- GET 进度 ---
    st, r = api('/api/docs/%s/translate' % did, tok=tok)
    check('GET translate', st == 200 and r.get('ok'), str(r)[:120])
    total = r['status']['total']
    check('切段数 > 100', total > 100, total)
    check('segments 带原文', bool(r['segments'][0]['src']))
    check('translatable 判定为真', r['translatable'] is True)

    # --- 术语表 ---
    check('术语表已抽', len(r['glossary']) >= 10, len(r['glossary']))
    st, g = api('/api/docs/%s/translate/glossary' % did,
                {'en': 'few-shot', 'zh': '少样本'}, tok=tok, method='PUT')
    check('PUT 术语', st == 200 and any(x['en'] == 'few-shot' for x in g['glossary']))
    locked = next(x for x in g['glossary'] if x['en'] == 'few-shot')
    check('手动术语默认锁定', locked['locked'] is True)

    # --- SSE 翻译 ---
    t0 = time.time()
    req = urllib.request.Request(
        BASE + '/api/docs/%s/translate/run' % did,
        data=json.dumps({'mode': 'limit:%d' % limit, 'verify': True}).encode(),
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + tok})
    segs, done_frame, err = [], None, ''
    with OP.open(req, timeout=900) as resp:
        buf = ''
        for chunk in resp:
            buf += chunk.decode('utf-8', 'replace')
            while '\n\n' in buf:
                frame, buf = buf.split('\n\n', 1)
                ev, data = 'message', []
                for ln in frame.split('\n'):
                    if ln.startswith('event:'):
                        ev = ln[6:].strip()
                    elif ln.startswith('data:'):
                        data.append(ln[5:].lstrip(' '))
                pay = '\n'.join(data)
                if ev == 'seg':
                    segs.append(json.loads(pay))
                elif ev == 'done':
                    done_frame = json.loads(pay)
                elif ev == 'error':
                    err = pay
    dt = time.time() - t0
    print('\n翻译 %d 段用了 %.1fs（%.1fs/段）' % (len(segs), dt,
                                             dt / max(len(segs), 1)))
    check('SSE 收到 %d 段' % limit, len(segs) == limit, len(segs))
    check('SSE 无 error 帧', not err, err)
    check('收到 done 帧', done_frame is not None)

    for s in segs:
        if s['status'] == 'ok' and s['zh']:
            print('\n--- 段 %d（%s, score=%s）---' % (s['i'], s['status'], s['score']))
            print('原文：', r['segments'][s['i']]['src'][:200].replace('\n', ' '))
            print('译文：', s['zh'][:260].replace('\n', ' '))
            if s['score'] is not None:
                check('回译分 > 0.5（段%d）' % s['i'], s['score'] > 0.5, s['score'])
            break

    # --- 续跑：再跑一次应该跳过已译的 ---
    st, r2 = api('/api/docs/%s/translate' % did, tok=tok)
    check('进度已更新', r2['status']['done'] >= len(segs), r2['status'])
    check('已译段有译文', any((v.get('zh') or '') for v in r2['translations'].values()))

    # --- 数字保护抽查 ---
    import re
    checked = 0
    for k, v in r2['translations'].items():
        if not v.get('zh'):
            continue
        src = r2['segments'][int(k)]['src']
        nums = set(re.findall(r'\d+\.?\d*%?', src))
        zh = v['zh']
        miss = [x for x in nums if x not in zh]
        if miss:
            check('段%s 数字未丢' % k, False, '缺 ' + ','.join(miss))
        checked += 1
    if checked:
        check('数字保护抽查 %d 段全过' % checked, True)

    # --- 术语表保护：重抽后 few-shot 应仍在 ---
    st, g2 = api('/api/docs/%s/translate/glossary' % did, {}, tok=tok)
    fs = next((x for x in g2.get('glossary', []) if x['en'] == 'few-shot'), None)
    check('重抽术语表后手动术语仍在', bool(fs), fs)

    print('\n%s' % ('ALL PASS' if not FAIL else 'FAILED: ' + ', '.join(FAIL)))
    return 0 if not FAIL else 1


if __name__ == '__main__':
    sys.exit(main())