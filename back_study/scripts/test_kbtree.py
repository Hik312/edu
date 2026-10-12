# -*- coding: utf-8 -*-
"""文件夹树 kbtree 的单元测试。

★ 为什么必须有**二级**用例：kbtree 第一版的 `_find` 把外层列表当成
  「子列表」用（`for lst in nodes: for i,n in enumerate(lst)`），
  于是一级文件夹（不走_find）全部正常，二级起必炸。
  只测一层的测试**永远发现不了这个 bug**，直到前端做二级目录才暴露。
  所以这里的每条用例都至少到三层，且移动/防环/删除都跑深层。

跑：cd back_study &&./.venv/Scripts/python.exe scripts/test_kbtree.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import kbtree as K  # noqa: E402

_bad = []


def ck(name, cond):
    print(('  OK   ' if cond else '  FAIL ') + name)
    if not cond:
        _bad.append(name)


def tree():
    """资料 → RAG → 0 ；另有顶层「论文」。深度 3 层，够测递归。"""
    t = []
    a = K.add_folder(t, '', '资料')['node']
    b = K.add_folder(t, a['id'], 'RAG')['node']
    c = K.add_folder(t, b['id'], '0')['node']
    d = K.add_folder(t, '', '论文')['node']
    return t, a, b, c, d


def main():
    print('kbtree 单元测试')

    # ---- id 唯一性：同毫秒连建三次也必须唯一（2026-10-11 的真 bug）----
    ids = {K._new_id() for _ in range(200)}
    ck('连建 200 个 id 不重复', len(ids) == 200)

    # ---- 建树 + 深层查找 ----
    t, a, b, c, d = tree()
    ck('顶层 2 个', len(t) == 2)
    ck('二层挂在一层下', len(a['children']) == 1 and a['children'][0]['id'] == b['id'])
    ck('三层挂在二层下', b['children'][0]['id'] == c['id'])
    ck('_find 找得到深层节点', K._find(t, c['id'])[1] == 0)
    ck('_find 找不到返回 None', K._find(t, 'f_nope')[0] is None)
    ck('二级下不存在时报「父不存在」', not K.add_folder(t, 'f_nope', 'x')['ok'])

    # ---- 放文档：集合语义（先摘后插，不重复）----
    K.put_docs(t, 'doc-1', [a['id']])
    K.put_docs(t, 'doc-2', [c['id']])
    ck('文档放进深层', c['docs'] == ['doc-2'])
    K.put_docs(t, 'doc-1', [a['id']])
    K.put_docs(t, 'doc-1', [a['id']])
    ck('重复放同一文件夹不出现两份', a['docs'] == ['doc-1'])
    K.put_docs(t, 'doc-1', [b['id']])
    ck('移动后旧文件夹里不再有它', 'doc-1' not in a['docs'] and b['docs'] == ['doc-1'])
    n = sum(1 for x, _ in K._walk(t, None) if 'doc-1' in x['docs'])
    ck('一份文档只出现在一个文件夹', n == 1)
    K.put_docs(t, 'doc-1', [])
    ck('传空列表=移出所有文件夹',
       not any('doc-1' in x['docs'] for x, _ in K._walk(t, None)))

    # ---- 移动 + 防环 ----
    t, a, b, c, d = tree()
    ck('把三层的 0 移到顶层', K.move_folder(t, c['id'], '')['ok'] and len(t) == 3)
    ck('顶层 0 与原节点同 id', any(x['id'] == c['id'] for x in t))
    ck('不能移进自己', not K.move_folder(t, a['id'], a['id'])['ok'])
    # ★ 必须用**一棵新的树**：上面刚把 c 移到了顶层，
    #   此时 c 已经不是 a 的后代，拿它测防环当然「不环」——
    #   这就是「用例之间共用可变状态」的典型假失败：
    #   测的是上一条用例留下的数据，断言与被测行为无关。
    t2, a2, b2, c2, d2 = tree()
    ck('不能移进自己的子文件夹', not K.move_folder(t2, a2['id'], c2['id'])['ok'])
    ck('不能移进自己的孙文件夹', not K.move_folder(t2, a2['id'],
                                       K.add_folder(t2, c2['id'], 'x')['node']['id'])['ok'])
    ck('防环后树仍可遍历', len(list(K._walk(t2, None))) == 5)
    ck('不能把不存在的节点当父', not K.move_folder(t, d['id'], 'f_nope')['ok'])

    # ---- 改名 / 折叠 ----
    t, a, b, c, d = tree()
    ck('改二级名', K.rename_folder(t, b['id'], '新名')['ok']
       and t[0]['children'][0]['name'] == '新名')
    ck('改名不存在→失败', not K.rename_folder(t, 'f_nope', 'x')['ok'])
    ck('空名拒绝', not K.rename_folder(t, b['id'], '  ')['ok'])
    K.set_collapsed(t, b['id'], True)
    ck('折叠态被持久化', t[0]['children'][0]['collapsed'] is True)

    # ---- 删除默认保文档 ----
    t, a, b, c, d = tree()
    K.put_docs(t, 'keep-1', [c['id']])
    r = K.delete_folder(t, b['id'])
    ck('删中间层：子树文档被上报而不是丢掉',
       r['ok'] and 'keep-1' in r['moved'])
    ck('删后二级消失', not any(x['id'] == b['id'] for x, _ in K._walk(t, None)))
    ck('兄弟节点不受影响', len(t) == 2)

    # ---- 删文档时清树（drop_doc）----
    # ★ 这条是补 2026-10-11 的漏：树在 meta、文档在 documents，是两个存储。
    #   删文档不摘树引用 → 文件夹里挂着永远打不开的死 id，界面上还看不出来。
    t, a, b, c, d = tree()
    # ★ 注意 put_docs 是**集合语义**（先摘后插），所以两次 put_docs
    #   不会让文档同时属于两个文件夹。想造「一份文档挂两级」的脏数据
    #   得直接改树 —— 而这正是线上可能出现的形态（比如树是手工改过的、
    #   或者以后加了别的写入路径），所以 drop_doc 必须按多级清理来测。
    a['docs'] = ['gone-1']
    c['docs'] = ['gone-1', 'stays']
    r = K.drop_doc(t, 'gone-1')
    ck('删文档：多层级引用一次摘干净',
       r['removed'] == 2
       and not any('gone-1' in (x.get('docs') or []) for x, _ in K._walk(t, None)))
    ck('删文档：别的文档不受影响',
       any('stays' in (x.get('docs') or []) for x, _ in K._walk(t, None)))
    ck('删不存在的文档不报错且 removed=0', K.drop_doc(t, 'nope')['removed'] == 0)
    ck('drop_doc 不动文件夹本身', len(t) == 2 and len(c['children']) == 0)

    # ---- 脏数据不炸树 ----
    dirty = K._norm([{'name': 'ok'}, {'noname': 1}, 'garbage', None,
                     {'name': 'x', 'children': 'notalist', 'docs': 'notalist'}])
    ck('脏树被规整成 2 个合法节点', len(dirty) == 2)
    ck('非list children 被修成空列表', dirty[1]['children'] == []
       and dirty[1]['docs'] == [])
    ck('缺 name 的节点被丢掉', all(x['name'] for x in dirty))
    ck('顶层不是 list 时返回空树', K._norm('notalist') == [])
    ck('对非 list 调用不会 500',
       isinstance(K.add_folder('notalist', '', 'x'), dict))

    # ---- 深度 200 层不爆栈 ----
    deep = []
    parent = ''
    for i in range(200):
        parent = K.add_folder(deep, parent, 'n%d' % i)['node']['id']
    ok, _ = K._find(deep, parent)
    ck('200 层深树能查到最底层', ok is not None)

    print('\n%s（%d 项失败）' % ('全部通过' if not _bad else '失败：' + ', '.join(_bad),
                                len(_bad)))
    return 1 if _bad else 0


if __name__ == '__main__':
    sys.exit(main())