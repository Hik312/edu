# -*- coding: utf-8 -*-
"""统一卡片的 `domain` 字段（一次性清洗脚本）。

**为什么需要它**：`domain` 是**旧字段**，只被首页「领域分布」这一个地方消费，
但它现在的状态是乱的 —— 表现为四种口径分裂：

1. **同名不同写**：`Java后端`(170) 和 `求职·Java`(10) 是同一个领域两种写法，
   于是首页把一个领域显示成两行。
2. **迁移不同步**：`middleware` 76 张卡只改了 `subject`，
   `domain` 还留着 `Java后端` → 中间件在首页被显示成「Java后端」。
3. **粒度不一**：有的值是科目（`Java后端`）、有的是主题（`操作系统`）、
   还有 `待归类` 这种脏值。
4. **与 subject 矛盾**：同一张卡的 `subject=java` 但 `domain=Java后端`，
   两个字段各说各话。

★ **根治方式是让 domain 由 subject 派生**，而不是各自独立维护 ——
两个字段能对不上，根因就是它们都存了「分类信息」却各写各的。
`subject` 是有 catalog 约束的（check.js 会校验），`domain` 没有，
所以 `domain` 只能是派生值，不该是独立数据。

**幂等**：可重复执行。

用法（必须用项目 venv）：
    back_study/.venv/Scripts/python.exe back_study/scripts/fix_domain.py
    back_study/.venv/Scripts/python.exe back_study/scripts/fix_domain.py --dry-run
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # back_study/scripts
_ROOT = os.path.dirname(os.path.dirname(_HERE))             # study/
DATA = os.path.join(_ROOT, 'data')
if not os.path.isdir(DATA):
    raise SystemExit('找不到 data 目录：%s（路径计算错了？）' % DATA)

TARGET_TOPIC = '中间件'
SKIP = ('catalog.js', 'roles.js', 'directions.js')

#: subject id → 人类可读的领域名。**唯一真相是 catalog.js 的 name**，
#: 这里只做 id → name 的映射，别自己另起一套中文名。
SUBJECT_LABEL = {
    'java': 'Java后端',
    'python': 'Python基础',
    'ai': 'AI工程',
    'cs': '计算机基础',
    'fe': '前端',
    'algorithm': '算法',
    'middleware': '中间件',
    'politics': '政治',
    'english': '英语',
    'math': '数学',
    'major': '专业课',
}


def main():
    dry = '--dry-run' in sys.argv
    changed = 0
    detail = {}

    for name in sorted(os.listdir(DATA)):
        if not name.endswith('.js') or name in SKIP:
            continue
        path = os.path.join(DATA, name)
        src = open(path, encoding='utf-8').read()
        m = re.search(r'(\[.*\])\s*;', src, re.S)
        if not m:
            continue
        try:
            cards = json.loads(m.group(1))
        except ValueError:
            continue
        n = 0
        for c in cards:
            subj = c.get('subject')
            if not subj:
                continue
            want = SUBJECT_LABEL.get(subj)
            if want is None or c.get('domain') == want:
                continue
            detail.setdefault(c.get('domain'), {}).setdefault(want, 0)
            detail[c['domain']][want] += 1
            c['domain'] = want
            n += 1
        if n:
            changed += n
            if not dry:
                out = src[:m.start(1)] + json.dumps(cards, ensure_ascii=False, indent=2) \
                    + src[m.end(1):]
                open(path, 'w', encoding='utf-8').write(out)

    print('[fix_domain] %s' % ('DRY-RUN（未写盘）' if dry else '已写入'))
    print('  修正 %d 张卡的 domain 字段' % changed)
    if detail:
        print('\n  改写映射（旧 → 新）：')
        for old in sorted(detail):
            for new, cnt in sorted(detail[old].items()):
                print('    %-14s → %-10s %d 张' % (old, new, cnt))
    if dry:
        print('\n加 --dry-run 去掉即为真正执行。')
    else:
        print('\n下一步：python back_study/scripts/dbseed.py --sync')


if __name__ == '__main__':
    main()