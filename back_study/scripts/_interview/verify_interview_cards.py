# -*- coding: utf-8 -*-
"""data/gen_interview_*.js 出库前校验：
    1) 数组能按 db.load_source_cards 的口径解析（var X = [ ... ]）
    2) 必填字段齐全、类型对（与 check.js 的卡片校验同口径）
    3) 正文合计分布（警告线 700，红线 500）
    4) id 在本文件内、以及 data/ 全部卡片文件间唯一
    5) 类比无技术词（llm._bad_analogy，仅警告）
    6) 有 diagram 的卡按 add_diagrams.validate_diagram 校验（前端播放器口径）
    python verify_interview_cards.py            # 全部三份
"""
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

try:
    from add_diagrams import validate_diagram
except Exception:
    validate_diagram = lambda d: 'validate_diagram 导入失败'  # noqa: E731

try:
    import llm
    bad_analogy = llm._bad_analogy
except Exception:
    def bad_analogy(a):
        return False

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(ROOT, 'data')

REQ_LIST = ('topicPath', 'tags', 'mechanism', 'keywords', 'scene', 'interviewQ')
REQ_STR = ('id', 'domain', 'category', 'subject', 'title', 'oneLine', 'analogy', 'why')


def parse_js(path):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'var\s+(CARDS_[A-Za-z0-9_]+)\s*=', src)
    if not m:
        raise ValueError('没有 var CARDS_X = 定义')
    idx = src.find('[', m.end())
    arr, _ = json.JSONDecoder().raw_decode(src, idx)
    return arr


def all_data_ids(exclude_files=()):
    ids = {}
    for f in glob.glob(os.path.join(DATA, '*.js')):
        if os.path.basename(f) in exclude_files:
            continue
        try:
            arr = parse_js(f)
        except Exception:
            continue
        for c in arr:
            cid = c.get('id')
            if cid:
                ids.setdefault(cid, []).append(os.path.basename(f))
    return ids


def body_total(c):
    return (len(c.get('oneLine') or '') + len(c.get('why') or '')
            + sum(len(x) for x in (c.get('mechanism') or []))
            + sum(len(x) for x in (c.get('scene') or []))
            + sum(len(x) for x in (c.get('interviewQ') or [])))


def check(path):
    name = os.path.basename(path)
    errs, warns = [], []
    try:
        arr = parse_js(path)
    except Exception as e:
        return ['解析失败: %s' % e], [], 0
    if not arr:
        errs.append('空数组')
    others = all_data_ids(exclude_files=(name,))
    seen = {}
    totals = []
    dg_kinds = {}
    for i, c in enumerate(arr):
        cid = c.get('id') or '#%d' % i
        d = c.get('diagram')
        if d is not None:
            if not isinstance(d, dict):
                errs.append('%s: diagram 不是对象' % cid)
            else:
                r = validate_diagram(d)
                if r:
                    errs.append('%s: diagram 非法：%s' % (cid, r))
                else:
                    dg_kinds[d['kind']] = dg_kinds.get(d['kind'], 0) + 1
    for i, c in enumerate(arr):
        cid = c.get('id') or '#%d' % i
        for k in REQ_STR:
            if not isinstance(c.get(k), str) or not c.get(k):
                errs.append('%s: 缺字段 %s' % (cid, k))
        for k in REQ_LIST:
            if not isinstance(c.get(k), list) or not c.get(k):
                errs.append('%s: 缺字段 %s' % (cid, k))
        if c.get('category') != 'work':
            errs.append('%s: category=%r 应为 work' % (cid, c.get('category')))
        if c.get('subject') not in ('ai', 'java', 'python', 'cs', 'fe'):
            errs.append('%s: subject=%r 不在目录里' % (cid, c.get('subject')))
        if isinstance(c.get('mechanism'), list) and len(c['mechanism']) < 6:
            errs.append('%s: mechanism 只有 %d 条（应>=6）' % (cid, len(c['mechanism'])))
        if isinstance(c.get('scene'), list) and len(c['scene']) < 2:
            errs.append('%s: scene <2' % cid)
        if isinstance(c.get('interviewQ'), list):
            if len(c['interviewQ']) < 3:
                warns.append('%s: interviewQ 只有 %d 条' % (cid, len(c['interviewQ'])))
            no_ans = [q for q in c['interviewQ'] if '（答：' not in q]
            if len(no_ans) == len(c['interviewQ']):
                warns.append('%s: interviewQ 都没有（答：…）' % cid)
        t = body_total(c)
        totals.append(t)
        if t < 500:
            errs.append('%s: 正文合计 %d < 500' % (cid, t))
        elif t < 700:
            warns.append('%s: 正文合计 %d 偏短' % (cid, t))
        if bad_analogy(c.get('analogy') or ''):
            warns.append('%s: 类比疑似含技术词: %s' % (cid, (c.get('analogy') or '')[:40]))
        seen.setdefault(cid, 0)
        seen[cid] += 1
        if cid in others:
            errs.append('%s: id 与 %s 撞车' % (cid, others[cid][0]))
    for cid, n in seen.items():
        if n > 1:
            errs.append('%s: 文件内重复 %d 次' % (cid, n))
    totals.sort()
    if totals:
        print('%s: %d 张，正文 min=%d p50=%d max=%d，图 %d 张 %s'
              % (name, len(arr), totals[0], totals[len(totals) // 2], totals[-1],
                 sum(dg_kinds.values()), dg_kinds or ''))
    return errs, warns, len(arr)


def main():
    files = [os.path.join(DATA, 'gen_interview_%s.js' % g)
             for g in ('redis', 'java', 'agent', 'cs')]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print('没有已发射的 gen_interview_*.js')
        return 1
    bad = 0
    for f in files:
        errs, warns, n = check(f)
        for w in warns:
            print('  WARN %s' % w)
        for e in errs:
            print('  FAIL %s' % e)
            bad += 1
        print('%s: %s' % (os.path.basename(f), 'OK' if not errs else '%d 个 FAIL' % len(errs)))
    print('==== %s ====' % ('ALL PASS' if not bad else '%d FAILURES' % bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
