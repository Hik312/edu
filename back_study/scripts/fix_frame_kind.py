"""修 state-machine 卡的 frames 字段：s -> n。

起因：19 张新卡（2026-10-09 之前几轮生成的）把 frames 写成了
      {"s": 序号, "note": "..."} —— 那是 **pipeline** 的格式。
      state-machine 要求 {"n": 节点id, "note": "..."}，
      check.js 的 `ids.indexOf(f.n) < 0` 因此报 BAD frame node。

★ 为什么这个 bug 藏了这么久：这批卡所在的文件里，
  前端和 check.js 都看不到它们（少了 `module.exports`），
  所以「看起来全绿」实际是没测到。修了导出才暴露出来。

映射方式：按 frames 的序号去取 nodes[同序号].id。
  理由：生成时是按顺序逐节点标注的，且已验证这些卡的
  frames 数量都<= nodes 数量；数量对不上的卡**不猜，直接报错**，
  宁可让人来看一眼，也不填一个可能错误的节点 id。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data')
SKIP = ('catalog.js', 'roles.js', 'directions.js')


def read_cards(path):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'(\[.*\])\s*;', src, re.S)
    if not m:
        return None
    return src[:m.start(1)], json.loads(m.group(1)), src[m.end(1):]


def main():
    dry = '--dry-run' in sys.argv
    if not os.path.isdir(DATA):
        raise SystemExit('数据目录不存在：%s' % DATA)

    fixed = 0
    undecidable = []
    touched = {}
    for name in sorted(f for f in os.listdir(DATA)
                       if f.endswith('.js') and f not in SKIP):
        got = read_cards(os.path.join(DATA, name))
        if not got:
            continue
        pre, cards, suf = got
        dirty = False
        for c in cards:
            d = c.get('diagram')
            if not d or d.get('kind') != 'state-machine':
                continue
            frames = d.get('frames') or []
            nodes = d.get('nodes') or []
            nids = [n.get('id') for n in nodes]
            # 已经是对的（frames 用 n）就跳过
            if all('n' in f for f in frames):
                continue
            # frames 全用 s → 按序号映射到 nodes
            if any('n' in f for f in frames):
                undecidable.append((name, c['id'], 'frames 里 s/n 混用'))
                continue
            if len(frames) > len(nodes):
                undecidable.append((name, c['id'],
                                    'frames %d > nodes %d，无法按序号映射'
                                    % (len(frames), len(nodes))))
                continue
            for i, f in enumerate(frames):
                if f.get('s') is not None:
                    f['n'] = nids[i]
                    del f['s']
            fixed += 1
            dirty = True
            print('  %-22s %-24s frames %d 条 -> n=%s' % (
                name, c['id'], len(frames),
                ','.join(f['n'] for f in frames)))
        if dirty:
            touched[name] = (pre, cards, suf)

    if undecidable:
        print('\n★ 以下卡不能按序号自动映射，需要人工看：')
        for n, cid, why in undecidable:
            print('    %s / %s：%s' % (n, cid, why))

    if touched and not dry:
        for name, (pre, cards, suf) in touched.items():
            open(os.path.join(DATA, name), 'w', encoding='utf-8').write(
                pre + json.dumps(cards, ensure_ascii=False, indent=2) + suf)

    print('%s修复 %d 张卡的 state-machine frames，改动 %d 个文件' % (
        '[dry-run] ' if dry else '', fixed, len(touched)))


if __name__ == '__main__':
    main()