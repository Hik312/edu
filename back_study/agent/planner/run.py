# -*- coding: utf-8 -*-
"""命令行入口。

    .venv/Scripts/python.exe back_study/agent_lab/run.py --status   # 环境探活
    .venv/Scripts/python.exe back_study/agent_lab/run.py --dump     # 只看取数，不调模型
    .venv/Scripts/python.exe back_study/agent_lab/run.py --top 5    # 跑全图

★ 第一步先跑 --dump：它只用 collect + score，几秒内出结果。
  确认候选卡、掌握度、前置关系都对了，再去填 write 节点 ——
  数据错了的话，模型写得再漂亮也是错的。
"""
import argparse
import json
import os
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))              # .../agent/planner
_BACK = os.path.dirname(os.path.dirname(_HERE))                 # .../back_study
for _p in (os.path.join(_BACK, 'core'), _BACK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent import model as M            # noqa: E402  公共模型工厂
from agent.planner import planner       # noqa: E402  本 Agent（按包导入，别当顶层模块）


def show_status():
    st = M.status()
    print('AI 状态：%s' % ('可用' if st.get('ok') else '不可用'))
    print('  通道    %s' % st.get('provider'))
    print('  模型    %s' % (st.get('model') or '-'))
    print('  说明    %s' % (st.get('msg') or ''))
    return bool(st.get('ok'))


def dump(user_id, limit):
    """只跑取数 + 排序，不碰模型。用来验证地基。"""
    cands = planner.load_candidates(user_id)
    print('用户 %s 的候选：%d 张（下面按优先级从高到低）' % (user_id, len(cands)))
    print('%-30s %-8s %-7s %-8s %s' % ('id', '掌握度', '逾期', '前置', '优先分'))
    print('-' * 78)
    for c in planner.score_candidates(cands, user_id)[:limit]:
        print('%-30s %-8.2f %-7s %-8s %.3f' % (
            c['id'][:30], c['p'],
            '没学过' if c['never'] else '%d天' % (c['overdue'] or 0),
            (','.join(c['prereq'])[:8] or '-'), c['score']))
    print()
    print('★ 逐列核对：掌握度在 0~1、没学过的掌握度应该接近 p_init、')
    print('  前置那一列有值说明 related 里写了 prereq 且方向没接反。')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', action='store_true', help='环境探活')
    ap.add_argument('--dump', action='store_true', help='只看取数，不调模型')
    ap.add_argument('--user', default='u1', help='用户 id（默认 u1）')
    ap.add_argument('--top', type=int, default=5, help='出几张（默认 5）')
    ap.add_argument('--limit', type=int, default=15, help='--dump 打印几行（默认 15）')
    a = ap.parse_args()

    if a.status:
        return 0 if show_status() else 1

    if a.dump:
        dump(a.user, a.limit)
        return 0

    if not show_status():
        print('\n模型不可用，先修上面的问题再跑。')
        return 1

    print('规划中（用户 %s，出 %d 张）…' % (a.user, a.top))
    try:
        st = planner.plan(a.user, a.top)
    except NotImplementedError as e:
        print('\n─────────────────────────────────────')
        print('%s' % e)
        print('─────────────────────────────────────')
        print('这是留给你的作业：打开 planner.py 的 write()，填那 3 处 TODO。')
        print('提示：先跑 --dump 确认取数没问题，再动 write。')
        return 2

    print('\n候选 %d 张 → 选出 %d 张（重试 %d 次，%s）' % (
        len(st['candidates']), len(st['plan']), st['tries'],
        '过检' if st['ok'] else '没过检：' + (st['msg'] or '未知')))
    if st['plan']:
        print()
        for i, it in enumerate(st['plan'], 1):
            print('%d. %s' % (i, it.get('id')))
            print('   %s' % it.get('reason'))
    print('\n原始 state：')
    print(json.dumps(st, ensure_ascii=False, indent=2)[:1500])
    return 0


if __name__ == '__main__':
    sys.exit(main())
