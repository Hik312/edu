# -*- coding: utf-8 -*-
"""截图验证临时探针。跑完即删。"""
import json
import os
import secrets
import string
import time
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:8080'
BACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(os.path.dirname(BACK), 'web', 'dist')
USER = 'zzshot%d' % (time.time() % 100000)
_a = string.ascii_letters + string.digits
PWD = 'Pp' + ''.join(secrets.choice(_a) for _ in range(10)) + '7'


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 method='POST' if data else 'GET')
    req.add_header('Content-Type', 'application/json')
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


st, body = call('/api/auth/login', {'username': USER, 'password': PWD})
if st != 200:
    st, body = call('/api/auth/register',
                    {'username': USER, 'password': PWD, 'displayName': '截图探针'})
if not (isinstance(body, dict) and body.get('token')):
    print('FAIL', st, str(body)[:200])
    raise SystemExit(1)
tok = body['token']
open(os.path.join(DIST, '_probe_token.txt'), 'w', encoding='utf-8').write(tok)


def hdr(path, payload=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 method=method or ('POST' if data else 'GET'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', 'Bearer ' + tok)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print('  !', path, e.code, e.read().decode()[:200])
        raise


hdr('/api/import/doc', {
    'filename': '待翻译论文.pdf',
    'dataB64': open(os.path.join(BACK, 'scripts', 'fixtures', 'sample.pdf'), 'rb').read()
        .hex() and __import__('base64').b64encode(
            open(os.path.join(BACK, 'scripts', 'fixtures', 'sample.pdf'), 'rb').read()).decode(),
    'docType': '论文'})
lst = hdr('/api/docs')
docs = lst.get('docs') or []
print('OK', USER, 'docs=', [d['title'] for d in docs][:3])