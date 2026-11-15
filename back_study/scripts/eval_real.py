# -*- coding: utf-8 -*-
"""用**真实复习日志**对四算法做 srs-benchmark 口径的评测 —— 把「可对拍」变成数字。

    python scripts/eval_real.py                # 评所有有事件的用户（聚合到个人级）
    python scripts/eval_real.py --user 1      # 只评某个用户
    python scripts/eval_real.py --json out.json  # 顺带把结果落成 JSON

## 它在评什么（和 algo/eval.py 仿真的分工）

- `algo/eval.py compare()`：仿真世界里谁排期排得好（efficiency / 期末留存）。
- 本脚本：**真实日志**上谁的概率预测准（log-loss / RMSE(bins) / AUC）。
  ground truth 是「你那次复习到底记没记住」—— 事件流里就有，不用仿真。

## 关键实现：算法状态从事件流重建

事件流里没有「那次复习前的进度快照」，但**不需要**：调度是确定性的，
「第 i 次复习前的状态」= 从头把前 i-1 次事件喂给 `algo.schedule()` 回放出来。
这正是 fsrs-optimizer / srs-benchmark 处理真实日志的标准做法
（细节差异：我们不存浮点 S，状态经 interval 列反解 —— 见 algo/fsrs.py 的妥协说明）。

y 的口径与 srs-benchmark 一致：Again(1)=忘，Hard/Good(2/3)=记得。
注意与 BKT 的「correct = level≥3」是两套口径（问的问题不同），别混用。

## 结果解读

log-loss ~0.69 = 瞎猜；FSRS-6 在 srs-benchmark 万人数据集上是 0.346。
你自己的数字波动很大（几十条样本），看趋势别抠小数。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACK = os.path.dirname(_HERE)
for _p in (_BACK, os.path.join(_BACK, 'core')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import algo                       # noqa: E402
import db                         # noqa: E402  core/db/ 包（2026-11-15 拆包后同路径）
from algo import eval as ev       # noqa: E402


def user_cards_sequences(uid):
    """某用户的事件流 → 每张卡按时间正序的事件列表。

    返回 {card_id: [{'at','level','correct'}, ...]}。排序纪律与
    fit_bkt/fit_fsrs 相同：按 (at, id)，同一天的按写入序 ——
    BKT/FSRS 都是顺序敏感的，排错结果就错。
    """
    evs = db.events_of(str(uid), limit=db.EVENTS_ALL)
    by_card = {}
    for e in evs:
        by_card.setdefault(e.get('card_id'), []).append(e)
    out = {}
    for cid, rows in by_card.items():
        rows.sort(key=lambda r: (str(r.get('at') or ''), r.get('id') or 0))
        out[cid] = rows
    return out


def replay_card(algo_name, rows):
    """单卡回放：边重排状态边产出 (p, y, t, nReviews, nLapses) 评测样本。

    返回 (samples, n_reviews)。p 为 None 的算法（sm2/bkt）samples 为空 ——
    那是能力边界，不是缺数据（见 algo/eval.py 顶部说明）。
    """
    a = algo.get(algo_name)
    samples = []
    prev = None
    prev_at = None
    n_rev = 0
    lapses = 0
    for r in rows:
        at = str(r.get('at') or '')
        level = int(r.get('level') or 1)
        y = 0 if level == 1 else 1          # srs-benchmark 口径：Again=忘
        if prev_at is not None:
            t = max(0, db.diff_days(prev_at, at))
            p = ev.predict(algo_name, prev, t)
            if p is not None:
                samples.append((p, y, t, n_rev, lapses))
            if level == 1:
                lapses += 1
        # 回放推进算法自身状态（用事件里的评级，不掺任何预测）
        prev = a.schedule(prev, level, today=at)
        n_rev += 1
        prev_at = at
    return samples, n_rev


def main():
    ap = argparse.ArgumentParser(description='真实复习日志的四算法评测')
    ap.add_argument('--user', type=str, default=None,
                    help='只评这个用户（默认：聚合全部有事件的用户）')
    ap.add_argument('--json', dest='json_out', default=None,
                    help='把结果落成 JSON 文件（默认只打印）')
    args = ap.parse_args()

    if args.user:
        targets = [(args.user, user_cards_sequences(args.user))]
    else:
        # 全部用户各自评一遍（留存是个人属性，聚合跨人会稀释口径），
        # 再挑事件最多的当「主表」。用户列表来自进度档案里出现过的 uid。
        profiles = db.load_profiles()
        uids = sorted(profiles.keys(), key=lambda u: -len(
            db.events_of(u, limit=db.EVENTS_ALL)))
        targets = [(u, user_cards_sequences(u)) for u in uids
                   if db.events_count(u) > 0]
    if not targets:
        print('没有任何复习事件可评 —— 先正常背几天卡再回来跑这个。')
        return 1

    result = {'generatedAt': db.today_str(), 'benchmark': 'srs-benchmark 口径 '
              '（log-loss 自然对数 BCE / RMSE(bins) 对数网格三特征分箱 / AUC）',
              'users': {}}
    for uid, cards in targets:
        per_algo = {}
        n_events = 0
        for name in algo.names():
            samples = []
            n_reviews = 0
            for cid, rows in cards.items():
                s, n = replay_card(name, rows)
                samples.extend(s)
                n_reviews += n
            n_events += n_reviews
            prob = [(x[0], x[1]) for x in samples]
            per_algo[name] = {
                'predictsRetention': name in ev._PREDICTORS,
                'nReviews': n_reviews,
                'nScored': len(samples),
                'logLoss': ev.log_loss(prob),
                'brier': ev.brier(prob),
                'auc': ev.auc(prob),
                'rmseBins': ev.rmse_bins(samples) if samples else None,
                'calibration': ev.calibration(prob, bins=5),
            }
        result['users'][str(uid)] = {'cards': len(cards), 'reviews': n_events,
                                     'algos': per_algo}

    # ---- 渲染主表（取第一个用户；多用户时各自都在 JSON 里）----
    uid, block = next(iter(result['users'].items()))
    print('评测用户 %s（%d 张卡 / %d 次复习）  生成于 %s'
          % (uid, block['cards'], block['reviews'], result['generatedAt']))
    head = ('算法', '样本数', 'log-loss↓', 'RMSE(bins)↓', 'AUC↑', 'Brier↓')
    rows = [head]
    for name, m in block['algos'].items():
        def s(v, fmt='%.4f'):
            return fmt % v if v is not None else '—'
        rows.append((name, str(m['nScored']), s(m['logLoss']),
                     s(m['rmseBins']), s(m['auc']), s(m['brier'])))
    w = [max(len(str(r[i])) for r in rows) for i in range(len(head))]
    line = '  '.join('-' * x for x in w)
    print('  '.join(str(rows[0][i]).ljust(w[i]) for i in range(len(head))))
    print(line)
    for r in rows[1:]:
        print('  '.join(str(r[i]).ljust(w[i]) for i in range(len(head))))
    print('')
    print('（— = 该算法不做留存概率预测：SM-2 无概率模型，BKT 的 p 是掌握度。')
    print('  log-loss 0.69 = 瞎猜；FSRS-6 在 srs-benchmark 万人数据集上 0.346。')
    print('  个人样本少时数字波动大，看趋势别抠小数。）')

    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print('JSON 已写入 %s' % args.json_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
