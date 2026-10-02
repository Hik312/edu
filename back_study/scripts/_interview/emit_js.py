# -*- coding: utf-8 -*-
"""把 out_{group}.jsonl 发射成 data/gen_interview_{group}.js（供 db 与 check.js 收录）。

    python emit_js.py redis|java|agent|all
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(ROOT, 'data')

NOTE = {
    'redis': 'Redis 面试题扩充（小林coding 40题页 + JavaGuide 单主题，8B 生成 + 对齐自检）',
    'java': 'Java 后端面试题扩充（JavaGuide 单主题/MySQL/分布式/MQ/高可用/Spring，8B 生成 + 对齐自检）',
    'agent': 'Agent 开发面试题扩充（Agent-Interview-100 题库，8B 生成 + 对齐自检）',
    'cs': '计算机基础面试题扩充（操作系统/网络/数据结构/算法，8B 生成 + 对齐自检）',
}


def emit(group):
    out_path = os.path.join(HERE, 'out_%s.jsonl' % group)
    if not os.path.exists(out_path):
        print('%s: 没有 %s，跳过' % (group, out_path))
        return 0
    cards, seen = [], set()
    with open(out_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            if c['id'] in seen:
                continue
            seen.add(c['id'])
            cards.append(c)
    var = 'CARDS_INTERVIEW_' + group.upper()
    path = os.path.join(DATA, 'gen_interview_%s.js' % group)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// %s：%d 张\n' % (NOTE[group], len(cards)))
        f.write('var %s = \n%s;\n' % (var, json.dumps(cards, ensure_ascii=False, indent=2)))
        f.write('module.exports = %s;\n' % var)
    print('%s: %d 张 → %s' % (group, len(cards), path))
    return len(cards)


def main():
    groups = ['redis', 'java', 'agent', 'cs'] if (sys.argv[1:] or ['all'])[0] == 'all' else sys.argv[1:]
    total = sum(emit(g) for g in groups)
    print('合计 %d 张' % total)


if __name__ == '__main__':
    main()
