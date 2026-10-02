# -*- coding: utf-8 -*-
"""给 out_{group}.jsonl 里还没有 diagram 的卡补「过程演示图」（三选一 spec）。

    python add_diagrams.py redis|java|agent|all [--limit 3]

流程：逐卡把 title/oneLine/mechanism/scene/keywords 喂给 qwen3:8b，让它
①判断这张卡值不值得配图（不值得输出 null，硬配反而糟）
②值得就按四种模板之一输出 diagram JSON
→ validate_diagram() 按前端 DiagramView.vue 的消费口径程序化校验
→ 不过线带着理由重试 1 次 → 再不过按 null（放弃）处理
每做完一张立即整文件重写（断点续跑：卡里已有 diagram 键就跳过，
null 也算已处理）。
"""
import io
import json
import os
import re
import sys
import time

_BK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # back_study
sys.path.insert(0, _BK)
sys.path.insert(0, os.path.join(_BK, 'core'))      # venv 有同名 llm 包，core 必须排前面
# 只在控制台不是 utf-8 时才换包装；被 verify 等模块 import 时不再二次包装
# （二次包装会让旧 wrapper 被 GC 时连带关掉底层 buffer）
if 'utf' not in (getattr(sys.stdout, 'encoding', '') or '').lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

import llm                                                             # noqa: E402  core/llm.py

HERE = os.path.dirname(os.path.abspath(__file__))
TEMP = 0.3
MAX_TOKENS = 1400
CALL_TIMEOUT = 300
MAX_ATTEMPTS = 2

DIAGRAM_SYS = '''你是「图示播放器」的内容设计。给一张知识卡，判断值不值得配一张可逐步播放的图示：
适合就输出 diagram JSON，不适合输出 null —— 不是每张卡都需要图（单纯概念定义、
纯清单罗列、没有过程也没有对比的卡直接 null，硬配反而糟）。四种模板：

1) pipeline —— 讲「先后步骤 / 一次调用的流程 / 因果链」：
{"kind":"pipeline","stages":["阶段一","阶段二",...],"frames":[{"s":0,"note":"..."},...]}
- stages 3-6 个，每个 <= 10 字，是流程的各阶段
- frames 3-6 帧，按流程顺序推进；s 是当前走到的下标（0 起）；note 15-50 字，
  讲这一步的关键点/判断/坑，禁止"第一步做了什么"这种没有信息量的复述

2) state-machine —— 讲「状态流转 / 循环 / 闭环」（Agent 循环、锁升级、连接生命周期、
缓存状态机、请求重试状态…）：
{"kind":"state-machine","nodes":[{"id":"a","label":"中文状态名","x":20,"y":30},...],
 "edges":[{"from":"a","to":"b"},...],"frames":[{"n":"a","note":"..."},...]}
- nodes 3-6 个，id 用英文小写单词；x/y 是 0-100 的百分比坐标，摆成两行或环形：
  同一行 x 间隔 >= 25、上下两行 y 用 25/70，别挤成一团
- edges 至少 3 条，from/to 必须是已有节点 id，不许自环
- frames 3-6 帧，n 是当前高亮节点 id，note 15-50 字讲这个状态发生了什么/为什么进入

3) snapshot —— 讲「2-3 个方案并排对比 / 结构组成」（选型对比、架构分块…）：
{"kind":"snapshot","panels":[{"title":"方案名","lines":["要点",...,...]},...],
 "frames":[{"note":"...","active":[0]},...]}
- panels 2-3 个，title <= 8 字；每个 panel 3-4 条要点，每条 <= 22 字
- frames 3-5 帧，active 是本帧要高亮的 panel 下标数组（可多个），
  note 15-50 字讲对比结论/取舍原因

4) arch —— 讲「整体架构 / 组件协作 / 一次请求的调用链」（系统设计、分层结构…）：
{"kind":"arch","nodes":[{"id":"gw","label":"API 网关","x":50,"y":14,"w":22},...],
 "links":[{"from":"gw","to":"svc","label":"转发"},...],
 "frames":[{"n":"gw","note":"..."},...]}
- nodes 4-7 个，id 用英文小写；x/y 是 0-100 百分比坐标，摆成 2-3 层：
  如入口层 y≈14、服务层 y≈50、存储层 y≈84，同层 x 错开 >= 26
- w 是方框宽度百分比，12-26，字多的框给大点
- links 至少 4 条，from/to 必须是已有 id，label 可选（<=6 字，如 调用/写入/订阅）
- frames 3-6 帧，n 是当前点亮的组件 id（也可以是 id 数组，点亮正在协作的
  几个组件），note 15-50 字讲此刻谁在干什么、数据流到哪了

选择原则：步骤流程 → pipeline；状态/循环/流转 → state-machine；并列对比 → snapshot；
组件组成/系统架构/调用链 → arch。
硬要求：
- 图的内容只能来自卡片本身，不许引入卡里没有的技术事实、不许编数字
- 每条 note 都要有信息量（关键判断、数字、原因），不许只重复 stage/node/panel 的名字
- 只输出 JSON（对象或 null），不要解释、不要 markdown 代码块'''

REWRITE = '上一版的 diagram 没通过校验：%s\n修正后重新输出（对象或 null，只输出 JSON，不要解释）。'


def log(group, msg):
    line = '%s [%s] %s' % (time.strftime('%H:%M:%S'), group, msg)
    print(line, flush=True)
    with open(os.path.join(HERE, 'run_diagrams_%s.log' % group), 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# ---------------------------------------------------------------------------
# 校验：口径完全对齐 web/src/components/DiagramView.vue 的消费方式
# ---------------------------------------------------------------------------
def validate_diagram(d):
    """合法返回 None，否则返回原因字符串。"""
    if not isinstance(d, dict):
        return '不是 JSON 对象'
    kind = d.get('kind')
    if kind not in ('pipeline', 'state-machine', 'snapshot', 'arch'):
        return 'kind 不是四种模板之一'
    fr = d.get('frames')
    if not isinstance(fr, list) or not (2 <= len(fr) <= 8):
        return 'frames 须 2-8 帧'
    for i, f in enumerate(fr):
        if not isinstance(f, dict):
            return 'frame%d 不是对象' % i
        note = f.get('note')
        if not isinstance(note, str) or not (10 <= len(note.strip()) <= 90):
            return ('frame%d 的 note 须 10-90 字（当前 %s）'
                    % (i, len(note.strip()) if isinstance(note, str) else '非字符串'))
    if kind == 'pipeline':
        st = d.get('stages')
        if not isinstance(st, list) or not (3 <= len(st) <= 6):
            return 'stages 须 3-6 个'
        for s in st:
            if not isinstance(s, str) or not s.strip() or len(s) > 12:
                return 'stage 为空或超 12 字: %r' % (s[:20] if isinstance(s, str) else s)
        for i, f in enumerate(fr):
            s = f.get('s')
            if not isinstance(s, int) or isinstance(s, bool) or not (0 <= s < len(st)):
                return 'frame%d 的 s=%r 越界' % (i, s)
    elif kind == 'state-machine':
        nd = d.get('nodes')
        if not isinstance(nd, list) or not (3 <= len(nd) <= 6):
            return 'nodes 须 3-6 个'
        ids = []
        for n in nd:
            if not isinstance(n, dict):
                return 'node 不是对象'
            nid, label = n.get('id'), n.get('label')
            if not isinstance(nid, str) or not nid.strip():
                return 'node 缺 id'
            if nid in ids:
                return 'node id 重复: %s' % nid
            if not isinstance(label, str) or not label.strip() or len(label) > 14:
                return 'node %s 的 label 须非空且 <=14 字' % nid
            x, y = n.get('x'), n.get('y')
            if not (isinstance(x, (int, float)) and not isinstance(x, bool)
                    and isinstance(y, (int, float)) and not isinstance(y, bool)
                    and 0 <= x <= 100 and 0 <= y <= 100):
                return 'node %s 缺合法 x/y（0-100，否则叠在中间）' % nid
            ids.append(nid)
        ed = d.get('edges')
        if not isinstance(ed, list) or len(ed) < 3:
            return 'edges 至少 3 条'
        for e in ed:
            if not isinstance(e, dict) or e.get('from') not in ids or e.get('to') not in ids:
                return 'edge 端点不在 nodes 里: %r' % (e,)
            if e.get('from') == e.get('to'):
                return 'edge 自环: %r' % (e,)
        hi = set()
        for i, f in enumerate(fr):
            n = f.get('n')
            if n not in ids:
                return 'frame%d 的 n=%r 不在 nodes 里' % (i, n)
            hi.add(n)
        if len(hi) < 2:
            return 'frames 至少高亮 2 个不同节点'
    elif kind == 'arch':
        nd = d.get('nodes')
        if not isinstance(nd, list) or not (4 <= len(nd) <= 7):
            return 'arch nodes 须 4-7 个'
        ids = []
        for n in nd:
            if not isinstance(n, dict):
                return 'arch node 不是对象'
            nid, label = n.get('id'), n.get('label')
            if not isinstance(nid, str) or not nid.strip():
                return 'arch node 缺 id'
            if nid in ids:
                return 'arch node id 重复: %s' % nid
            if not isinstance(label, str) or not label.strip() or len(label) > 16:
                return 'arch node %s 的 label 须非空且 <=16 字' % nid
            x, y = n.get('x'), n.get('y')
            if not (isinstance(x, (int, float)) and not isinstance(x, bool)
                    and isinstance(y, (int, float)) and not isinstance(y, bool)
                    and 0 <= x <= 100 and 0 <= y <= 100):
                return 'arch node %s 缺合法 x/y（0-100）' % nid
            w = n.get('w')
            if w is not None and (not isinstance(w, (int, float)) or isinstance(w, bool)
                                  or not (10 <= w <= 40)):
                return 'arch node %s 的 w 须 10-40' % nid
            ids.append(nid)
        lk = d.get('links')
        if not isinstance(lk, list) or len(lk) < 4:
            return 'arch links 至少 4 条'
        for l in lk:
            if not isinstance(l, dict) or l.get('from') not in ids or l.get('to') not in ids:
                return 'arch link 端点不在 nodes 里: %r' % (l,)
            if l.get('from') == l.get('to'):
                return 'arch link 自环: %r' % (l,)
            lb = l.get('label')
            if lb is not None and (not isinstance(lb, str) or len(lb) > 8):
                return 'arch link label 须 <=8 字'
        hi = set()
        for i, f in enumerate(fr):
            n = f.get('n')
            ns = n if isinstance(n, list) else [n]
            if not ns or any(x not in ids for x in ns):
                return 'frame%d 的 n=%r 含不在 nodes 里的 id' % (i, n)
            hi.update(ns)
        if len(hi) < 2:
            return 'frames 至少点亮 2 个不同组件'
    else:  # snapshot
        pn = d.get('panels')
        if not isinstance(pn, list) or not (2 <= len(pn) <= 3):
            return 'panels 须 2-3 个'
        for p in pn:
            if not isinstance(p, dict):
                return 'panel 不是对象'
            t = p.get('title')
            if not isinstance(t, str) or not t.strip() or len(t) > 10:
                return 'panel title 须非空且 <=10 字'
            ls = p.get('lines')
            if not isinstance(ls, list) or not (3 <= len(ls) <= 4):
                return 'panel %s 的 lines 须 3-4 条' % t
            for l in ls:
                if not isinstance(l, str) or not l.strip() or len(l) > 26:
                    return 'panel %s 有 line 为空或超 26 字' % t
        hi = set()
        for i, f in enumerate(fr):
            act = f.get('active')
            if not isinstance(act, list) or not act:
                return 'frame%d 缺 active' % i
            if not all(isinstance(a, int) and not isinstance(a, bool) and 0 <= a < len(pn)
                       for a in act):
                return 'frame%d 的 active 越界' % i
            hi.update(act)
        if len(hi) < len(pn):
            return '所有帧没有覆盖全部 panel（对比图要每个都点到）'
    return None


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------
def card_digest(c):
    mech = '；'.join(c.get('mechanism') or [])
    scene = '；'.join(c.get('scene') or [])
    return ('知识卡：\n标题：%s\n一句话结论：%s\n原理：%s\n场景：%s\n术语：%s'
            % (c.get('title', ''), c.get('oneLine', ''), mech,
               scene, '、'.join(c.get('keywords') or [])))


def gen_diagram(card, model):
    """返回 (spec|None, reason)。None + '' 表示模型判断不适合（放弃）。"""
    sys_msg = {'role': 'system', 'content': DIAGRAM_SYS}
    user_msg = {'role': 'user', 'content': card_digest(card)}
    msgs = [sys_msg, user_msg]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = llm._call(msgs, model, CALL_TIMEOUT, temperature=TEMP,
                            max_tokens=MAX_TOKENS)
            out = llm._clean_json(raw)
            if isinstance(out, dict) and 'diagram' in out and len(out) <= 2:
                out = out.get('diagram')
            if out is None:
                return None, ''                       # 模型判定不适合
            if not isinstance(out, dict):
                raise RuntimeError('llm_not_json')
            err = validate_diagram(out)
            if err is None:
                return out, ''
            last_err = err
        except Exception as e:
            last_err = '生成失败：%s' % e
        if attempt < MAX_ATTEMPTS:
            msgs = [sys_msg, user_msg,
                    {'role': 'user', 'content': REWRITE % last_err}]
    log('!', '校验两次不过，按放弃处理：%s —— %s'
        % (card.get('id'), last_err[:120]))
    return None, ''


def process_group(group, model, limit=None, retry_null=False):
    out_path = os.path.join(HERE, 'out_%s.jsonl' % group)
    if not os.path.exists(out_path):
        print('%s: 没有 %s，跳过' % (group, out_path))
        return 0
    cards = []
    with open(out_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                cards.append(json.loads(line))
    if retry_null:
        todo = [c for c in cards if 'diagram' in c and c['diagram'] is None]
    else:
        todo = [c for c in cards if 'diagram' not in c]
    if limit:
        todo = todo[:limit]
    log(group, '开始：共 %d 张，待补图 %d 张%s，model=%s'
        % (len(cards), len(todo),
           '（%s%s）' % ('retry-null ' if retry_null else '',
                         'limit=%d' % limit if limit else ''), model))
    ok = skip = 0
    t0 = time.time()
    for i, c in enumerate(todo, 1):
        t1 = time.time()
        spec, _ = gen_diagram(c, model)
        c['diagram'] = spec                     # dict 或 null；null=已判定不配图
        with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
            for x in cards:
                f.write(json.dumps(x, ensure_ascii=False) + '\n')
        ms = int((time.time() - t1) * 1000)
        if spec:
            ok += 1
            log(group, '[%d/%d] 图  %-40s %-14s %d帧 %dms'
                % (i, len(todo), c['id'], spec['kind'], len(spec['frames']), ms))
        else:
            skip += 1
            log(group, '[%d/%d] —   %-40s 判定不配图 %dms'
                % (i, len(todo), c['id'], ms))
    log(group, '完成：配图 %d，判定不配 %d，用时 %d 秒'
        % (ok, skip, int(time.time() - t0)))
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    if not args:
        print(__doc__)
        return 1
    model = llm.pick_model()
    if not model:
        print('没有可用的本地模型（ollama 没起来？）')
        return 1
    groups = ['redis', 'java', 'agent', 'cs'] if args[0] == 'all' else [args[0]]
    retry_null = '--retry-null' in sys.argv
    for g in groups:
        process_group(g, model, limit, retry_null=retry_null)
    return 0


if __name__ == '__main__':
    sys.exit(main())
