# -*- coding: utf-8 -*-
"""探针：就「ReAct 论文」打一条真实 HTTP 问答，验证 SSE 端点全链路。

跑法（在 back_study 下，用 .venv）：
    ./.venv/Scripts/python.exe scripts/probe_docqa.py
会自己注册一个临时账号、问一句、打印收到的帧，最后清场。
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8099'
USER = 'pqa%d' % (int(time.time()) % 1000000)
PASS = 'Probe12345!'


def call(path, body=None, tok=None, raw=False, timeout=600):
    d = json.dumps(body).encode() if body is not None else None
    h = {'Content-Type': 'application/json'}
    if tok:
        h['Authorization'] = 'Bearer ' + tok
    req = urllib.request.Request(BASE + path, data=d, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8') if raw else json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'__err': e.code, 'body': e.read().decode('utf-8', 'replace')[:400]}


def main():
    reg = call('/api/auth/register', {'username': USER, 'password': PASS})
    if '__err' in reg:
        print('注册失败', reg)
        return 1
    tok = reg.get('token')
    print('账号', USER)

    docs = call('/api/docs', tok=tok).get('docs') or []
    paper = next((d for d in docs if d.get('isPaper')), None)
    if not paper:
        print('没有论文可测')
        return 1
    print('目标文档:', paper['title'])

    # 流式读，边读边打印帧类型
    req = urllib.request.Request(
        BASE + '/api/docs/%s/ask' % paper['id'],
        data=json.dumps({'question': 'What problem does ReAct solve and how does it '
                                     'interleave reasoning with acting?'}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok})
    t0 = time.time()
    frames = []
    answer = []
    try:
        r = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        print('HTTP %s: %s' % (e.code, e.read().decode('utf-8', 'replace')[:400]))
        return 1
    with r:
        buf = ''
        for chunk in r:
            buf += chunk.decode('utf-8', 'replace')
            while '\n\n' in buf:
                frame, buf = buf.split('\n\n', 1)
                ev = 'message'
                data = []
                for ln in frame.split('\n'):
                    if ln.startswith('event:'):
                        ev = ln[6:].strip()
                    elif ln.startswith('data:'):
                        data.append(ln[5:].lstrip(' '))
                payload = '\n'.join(data)
                frames.append(ev)
                if ev == 'message':
                    answer.append(payload.replace('\\n', '\n'))
                elif ev == 'error':
                    print('ERROR 帧:', payload)
    text = ''.join(answer)
    print('耗时 %.1fs' % (time.time() - t0))
    print('帧序列:', frames[:6], '... 共', len(frames))
    print('答案长度:', len(text))
    print('--- 答案前 400 字 ---')
    print(text[:400])
    ok = bool(text.strip()) and 'done' in frames
    print('结果:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())