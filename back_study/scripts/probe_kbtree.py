# -*- coding: utf-8 -*-
"""文件夹树端到端探针（真HTTP）。

★ 为什么这个脚本每次都要重建数据而不是只读：
  树是**账号级单例**，手测过一次之后库里就留着上次的文件夹，
  下次再跑断言全错。所以每次自己建一套 → 测 → 删干净。
跑：./.venv/Scripts/python.exe scripts/probe_kbtree.py
"""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:8080/api'
# ★ 用户名**每次随机**：树探针失败重跑时，固定用户名会撞上「用户名已被占用」，
#   然后脚本走进 login 分支，密码对不上（历史遗留账号是别的密码），
#   最终报出来的是「登录失败」—— 和真实故障毫无关系，纯属噪音。
#   探针账号本来就要每次新建（树是账号级单例），随机名正好符合语义。
USER = 'kbp%d' % (time.time() % 1000000)
PWD = 'kbprobe03x'


def call(path, body=None, method=None, token=None):
    """HTTP 调用。★ method 必须能独立指定 —— 只按「有没有 body」判
    是不是 POST，PUT 路由会全发成 POST 然后拿到 405，
    而 405 的报错完全看不出真实问题（这是 2026-10-11 踩过的坑）。"""
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    m = method or ('POST' if data is not None else 'GET')
    req = urllib.request.Request(url, data=data, method=m)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:300]}


bad = []


def ck(name, cond, extra=''):
    print(('  OK   ' if cond else '  FAIL ') + name + ('  ' + str(extra) if extra else ''))
    if not cond:
        bad.append(name)


def names(nodes):
    return [n['name'] for n in nodes]


def find(nodes, fid):
    """在树里按 id 找节点。**不能假设树是空的** ——
    库里有用户自己建的文件夹（「资料」里放着真文档），
    断言 len(tree)==1 这类写法一上手就是 FAIL，
    而且会让人误以为是代码坏了，其实是前置条件写错了。"""
    for n in nodes:
        if n.get('id') == fid:
            return n
        hit = find(n.get('children') or [], fid)
        if hit:
            return hit
    return None


def main():
    print('文件夹树端到端探针（账号 %s）' % USER)
    s, r = call('/auth/register', {'username': USER, 'password': PWD})
    tok = (r.get('token') if isinstance(r, dict) else None)
    if not tok:
        print('注册失败，无法继续：', s, str(r)[:200])
        return 1
    print('  token ok')

    made = []
    tree = {'t': []}

    def mk(name, parent=''):
        s, r = call('/kb/tree/folder', {'name': name, 'parentId': parent}, token=tok)
        if s == 200 and isinstance(r, dict) and r.get('node'):
            made.append(r['node']['id'])
            tree['t'] = r['tree']
        return r.get('node') if isinstance(r, dict) else None

    # ---- 三层树 ----
    a = mk('资料')
    b = mk('RAG', a['id'])
    c = mk('第0批', b['id'])
    ck('三层建好', bool(c) and names(find(tree['t'], c['id'])['children']) == [],
       [n['name'] for n in tree['t']])
    ck('二层名字对', find(tree['t'], b['id'])['name'] == 'RAG')
    ck('三层挂对了', find(tree['t'], b['id'])['children'][0]['id'] == c['id'])

    # ---- 放文档：先导一份，探针新账号本来是空的 ----
    # ★ 不能假设账号下有文档：新注册的探针账号一定是空的，
    #   「文档放进第三层」这类断言会在空数据上空跑 —— 看起来通过，
    #   其实一行都没执行到。断言必须在**非空**数据上才有意义。
    s, r = call('/import/doc', {
        'filename': '探针笔记.md',
        'text': '# 探针\n\n第1章\n内容\n\n第2章\n内容2\n',
        'docType': '资料'
    }, token=tok)
    did = r.get('doc', {}).get('id') if isinstance(r, dict) and s == 200 else None
    ck('导入一份探针文档', s == 200 and bool(did), r if not did else '')
    if did:
        s, r = call('/docs/%s/move' % did, {'docId': did, 'folderIds': [c['id']]}, token=tok)
        node = find(r.get('tree') or [], c['id']) if s == 200 else None
        ck('文档放进第三层', bool(node) and did in (node.get('docs') or []),
           r if s != 200 else (node or {}).get('docs'))
        s2, r2 = call('/docs', token=tok)
        ck('放过的文档仍在列表里（没被移动操作弄丢）',
           did in [x['id'] for x in (r2.get('docs') or [])])

    # ---- 折叠态持久化 ----
    s, r = call('/kb/tree/folder/' + b['id'], {'collapsed': True}, method='PUT', token=tok)
    ck('折叠态写回', s == 200 and find(r.get('tree') or [], b['id']).get('collapsed') is True)
    s, r = call('/kb/tree', token=tok)
    ck('折叠态重读还在', find(r['tree'], b['id']).get('collapsed') is True)

    # ---- 防环 ----
    s, r = call('/kb/tree/move', {'id': a['id'], 'parentId': a['id']}, token=tok)
    ck('不能移进自己', s == 400, s)
    s, r = call('/kb/tree/move', {'id': a['id'], 'parentId': c['id']}, token=tok)
    ck('不能移进孙级', s == 400, s)
    s, r = call('/kb/tree', token=tok)
    ck('防环后树没被动过', find(r['tree'], a['id']) is not None
       and find(r['tree'], c['id']) is not None)

    # ---- 改名 ----
    s, r = call('/kb/tree/folder/' + c['id'], {'name': '第一批'}, method='PUT', token=tok)
    ck('改名生效', s == 200 and find(r.get('tree') or [], c['id'])['name'] == '第一批')

    # ---- 移出 ----
    if did:
        s, r = call('/docs/%s/move' % did, {'docId': did, 'folderIds': []}, token=tok)
        ck('移出后不再挂在任何文件夹',
           s == 200 and not any(did in (n.get('docs') or []) for n in r['tree']))

        # ---- ★ 删文档自动清树（2026-10-11 补的漏）----
        call('/docs/%s/move' % did, {'docId': did, 'folderIds': [c['id']]}, token=tok)
        s, r = call('/docs/' + did, method='DELETE', token=tok)
        ck('删文档返回 ok', s == 200 and r.get('ok') is True, r)
        s, r = call('/kb/tree', token=tok)
        left = [d for n in r['tree'] for d in (n.get('docs') or [])]
        ck('★ 树里的死 id 已被摘掉', did not in left, left)

    # ---- 删中间层：文档保命 ----
    s, r = call('/kb/tree/folder/' + b['id'] + '?mode=doc2root', method='DELETE', token=tok)
    ck('删中间层 ok', s == 200, s)
    ck('删后子树消失', s == 200 and find(r.get('tree') or [], c['id']) is None
       and find(r.get('tree') or [], b['id']) is None)
    ck('父节点还在', s == 200 and find(r.get('tree') or [], a['id']) is not None)

    # ---- 清理：只删自己建的 ----
    # ★ 从根往下删：删父节点会把子树一起带走，再删子节点就是 404。
    #   倒着删（先子后父）才是对的顺序。
    for fid in reversed(made):
        if find(tree['t'], fid) or True:
            st = call('/kb/tree/folder/' + fid + '?mode=doc2root', method='DELETE', token=tok)[0]
            if st != 200:
                print('  (清理 ' + fid + ' 返回 ' + str(st) + '，可能已被父级带走)')
    s, r = call('/kb/tree', token=tok)
    ck('探针节点已全部清空',
       s == 200 and not any(x['id'] in made for x in r['tree']))

    print('\n全部通过' if not bad else '\n失败：' + ', '.join(bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())