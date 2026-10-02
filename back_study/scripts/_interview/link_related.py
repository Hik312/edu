# -*- coding: utf-8 -*-
"""给全库卡片补 related（卡片间关联 —— 详情页「相关卡片」+ 知识图谱的边）。

    python link_related.py             # 词法召回 + LLM 精选 + 写回（默认）
    python link_related.py --lexical   # 只跑词法，不调 LLM（快，先看效果）

related 的契约（check.js 逐条校验，改格式前先看 check.js 147 行附近）：
    [{"id": "目标卡id", "kind": "prereq|extends|compare", "note": "为什么连（人话）"}]
- id 必须真实存在、不许自环；kind 只有三种；note 空白直接判坏
- 手写卡（aizhuan.js 那 42 条）是人挑的精品边：**只增不改**，
  新算出来的关系先按 id 去重再合并，且排在手写边之后（不会被裁掉）

真相源按 id 分两路（和 emit_js 同口径）：
- out_{group}.jsonl 里的卡 → 回写 jsonl（之后 emit_js 出库）
- 其余卡（手写/旧脚本生成） → 原位 patch data/*.js 的 JSON 数组
  （emit 只重写 gen_interview_*.js，手写文件不会被覆盖，所以原位改是安全的）

三步：
1) 召回：keywords/tags/标题 token 的 Jaccard + 同科目/同专题加权，
   每卡取 top8 候选（分数 >= 0.08 才算候选）
2) 精选：每批 5 卡喂 qwen3:8b，从候选里挑 0-4 条真正有讲解关系的，
   并按 {id,kind,note} 格式**双向**输出；按 (cid, 候选集指纹) 缓存
3) 合并：手写边优先保留 → 双向补齐 → 按召回分裁到每卡最多 5 条

写完后跑 emit_js → dbseed --sync 才会进库。
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
if 'utf' not in (getattr(sys.stdout, 'encoding', '') or '').lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

import llm                                                             # noqa: E402  core/llm.py

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(_BK, '..', 'data'))
GROUPS = ['agent', 'redis', 'java', 'cs']
CACHE_PATH = os.path.join(HERE, 'related_llm_cache.json')

MIN_SCORE = 0.08        # 召回门槛（低于此不进候选）
CAND_TOP = 8            # 每卡候选数
MAX_RELATED = 5         # 每卡最终最多几条
BATCH = 5               # LLM 每批几张卡
TEMP = 0.2
CALL_TIMEOUT = 180
MAX_ATTEMPTS = 2
KINDS = ('prereq', 'extends', 'compare')

SYS = '''你在给知识卡片库建「相关卡片」索引。目标是让读者点开一张卡时，
底部 2-5 张「相关卡片」确实能互相讲清楚：同一机制的上下游、对比面、
同一主题的深浅层、同一问题的不同侧面。

- 只挑有真实讲解关系的，宁缺毋滥 —— 都不相关就输出空数组，禁止凑数
  （同科目但不同主题不算关系）
- kind 只能三选一：
  prereq  = A 是理解 B 的前置（先 A 后 B）
  extends = A 往下走到 B，或 A 的一个具体面由 B 承接
  compare = 两者并列，放一起比着看才明白
- note 是人话（15-45 字），写清「从这张卡的视角，为什么要看另一张」，
  禁止空话（如「两者有关联」），也不要出现「前者/后者」
- 每对关系输出**两个方向各一条**（a→b 与 b→a），note 各写各的视角
- 每张卡 0-5 条，互不影响；只输出 JSON，不要解释'''

# ★ 这两个模板**不能用 str.format 喂参数**：正文里的 JSON 字面量 {"<目标卡id>": …}
#   会被 format 当成替换字段，直接 KeyError（2026-10-02 真踩过：79 个批次
#   全在调模型之前就炸了，related 静默退化成词法版）。用 str.replace 占位符。
USER_TMPL = '''目标卡（每批多张，逐张判断）：
{targets}

每张卡的候选（可能有多个，id 相同只出现一次）：
{cands}

输出 JSON：{"<目标卡id>": [{"id": "<候选id>", "kind": "prereq|extends|compare", "note": "..."}, ...], ...}
- 只输出有选中的卡；一张都不选的卡不要出现在结果里
- 每对关系两个方向各一条：候选卡作为目标卡时，它自己的候选里应有反向那条
- 只输出 JSON'''


# ---------- 读 ----------

def parse_js(path):
    """data/*.js → (text, arr_start, arr_end, arr)；非卡片文件返回 None。"""
    text = open(path, encoding='utf-8').read()
    m = re.search(r'var\s+\w+\s*=\s*\[', text)
    if not m:
        return None
    start = text.index('[', m.start())
    try:
        arr, end = json.JSONDecoder().raw_decode(text, start)
    except ValueError:
        return None
    if not isinstance(arr, list) or not arr or not isinstance(arr[0], dict) \
            or 'title' not in arr[0]:
        return None
    return text, start, end, arr


def load_all():
    """id → card。jsonl（interview 卡）优先；data/*.js 只补非 jsonl 的卡。

    返回 (cards, src, js_files, existing)
      src      id → ('jsonl', path) | ('js', path)
      existing id → 既有 related（手写边，只增不改的基线）
    """
    cards, src = {}, {}
    for g in GROUPS:
        p = os.path.join(HERE, 'out_%s.jsonl' % g)
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8') as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                if c['id'] in src:
                    print('  !! jsonl 重复 id %s (%s:%d)，忽略后一条' % (c['id'], p, ln))
                    continue
                cards[c['id']] = c
                src[c['id']] = ('jsonl', p)
    n_jsonl = len(cards)

    js_files = {}
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith('.js'):
            continue
        path = os.path.join(DATA_DIR, name)
        parsed = parse_js(path)
        if not parsed:
            continue
        text, start, end, arr = parsed
        js_files[path] = [text, start, end, arr]
        for c in arr:
            cid = c.get('id')
            if not cid or cid in src:
                continue            # jsonl 卡以 jsonl 为准
            cards[cid] = c
            src[cid] = ('js', path)
    existing = {i: [r for r in (c.get('related') or []) if isinstance(r, dict)]
                for i, c in cards.items()}
    n_hand = sum(1 for v in existing.values() if v)
    print('卡片 %d 张：jsonl %d + data/*.js %d（%d 个文件）；既有手写边 %d 张'
          % (len(cards), n_jsonl, len(cards) - n_jsonl, len(js_files), n_hand))
    return cards, src, js_files, existing


# ---------- 词法召回 ----------

def _tok(s):
    """ascii 单词 + 中文二元组（标题都是中英混排，bigram 比分词省事且够用）。"""
    s = (s or '').lower()
    out = set(re.findall(r'[a-z0-9+#.]{2,}', s))
    for run in re.findall(r'[\u4e00-\u9fff]+', s):
        if len(run) == 1:
            out.add(run)
        for i in range(len(run) - 1):
            out.add(run[i:i + 2])
    return out


def _jac(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _kw(c):
    return _tok(' '.join(c.get('keywords') or [])) | _tok(' '.join(c.get('tags') or []))


def _score(a, b, ka, ta, kb, tb):
    s = 0.45 * _jac(ka, kb) + 0.35 * _jac(ta, tb) \
        + 0.20 * _jac(set(a.get('tags') or []), set(b.get('tags') or []))
    if a.get('subject') and a.get('subject') == b.get('subject'):
        s += 0.10
    pa, pb = a.get('topicPath') or [], b.get('topicPath') or []
    if len(pa) >= 2 and len(pb) >= 2 and pa[0] == pb[0] and pa[1] == pb[1]:
        s += 0.10
    return round(s, 4)


def recall(cards):
    """id → [(cand_id, score), ...]（按分数降序，最多 CAND_TOP 条）。"""
    ids = list(cards)
    tok = {i: _tok(cards[i].get('title')) for i in ids}
    kw = {i: _kw(cards[i]) for i in ids}
    best = {i: [] for i in ids}
    for x in range(len(ids)):
        a = ids[x]
        for y in range(x + 1, len(ids)):
            b = ids[y]
            s = _score(cards[a], cards[b], kw[a], tok[a], kw[b], tok[b])
            if s < MIN_SCORE:
                continue
            best[a].append((b, s))
            best[b].append((a, s))
    for i in ids:
        best[i] = sorted(best[i], key=lambda t: -t[1])[:CAND_TOP]
    return best


# ---------- LLM 精选 ----------

def _load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            return json.load(open(CACHE_PATH, encoding='utf-8'))
        except ValueError:
            pass
    return {}


def _save_cache(cache):
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def _norm_entries(raw):
    """LLM 输出 → 合规 entry 列表（kind 白名单、note 非空、id 合法由调用方兜）。"""
    out = []
    for e in raw or []:
        if isinstance(e, str):
            e = {'id': e}
        if not isinstance(e, dict):
            continue
        cid, kind, note = e.get('id'), e.get('kind'), (e.get('note') or '').strip()
        if not cid or kind not in KINDS or not note:
            continue
        out.append({'id': cid, 'kind': kind, 'note': note})
    return out


def _ask(model, cards, targets, cands_by_id):
    tgt = '\n'.join('- [%s] %s | %s' % (c['id'], c.get('title'), (c.get('oneLine') or '')[:60])
                    for c in targets)
    cand_lines = []
    for c in targets:
        cand_lines.append('[%s]' % c['id'])
        for cid, s in cands_by_id[c['id']]:
            cand_lines.append('  - [%s] %s (%.2f)' % (cid, cards[cid].get('title'), s))
    cand_lines_str = '\n'.join(cand_lines)
    msgs = [{'role': 'system', 'content': SYS},
            {'role': 'user', 'content':
                USER_TMPL.replace('{targets}', tgt).replace('{cands}', cand_lines_str)}]
    raw = llm._call(msgs, model, CALL_TIMEOUT, temperature=TEMP, max_tokens=2400)
    return llm._clean_json(raw)


def _lexical_entries(cards, cands):
    """词法兜底/--lexical：kind 用启发式，note 说清重叠在哪（不调模型）。"""
    picked = {}
    for cid, cl in cands.items():
        sel = [(x, s) for x, s in cl if s >= 0.15]
        entries = []
        for oid, s in sel:
            a, b = cards[cid], cards[oid]
            pa, pb = a.get('topicPath') or [], b.get('topicPath') or []
            kind = 'compare' if a.get('subject') != b.get('subject') else 'extends'
            if len(pa) >= 2 and pa[:2] == pb[:2]:
                note = '同属「%s / %s」，放一起看的是同一主题的两个面' % (pa[0], pa[1])
            else:
                shared = sorted(_kw(a) & _kw(b))[:3]
                note = '关键词重叠（%s），与这张卡讲的是同一批概念' % '、'.join(shared)
            entries.append({'id': oid, 'kind': kind, 'note': note})
        picked[cid] = entries
    return picked


def llm_pick(cards, cands, model):
    """id → [entry, ...]。命中缓存的卡不调模型。"""
    cache = _load_cache()
    picked = {}
    todo = []
    for cid, cl in cands.items():
        fp = ','.join('%s:%s' % t for t in cl)          # 候选集指纹
        hit = cache.get(cid)
        if isinstance(hit, dict) and hit.get('fp') == fp:
            picked[cid] = _norm_entries(hit.get('rel'))
        else:
            todo.append(cid)
    print('缓存命中 %d，待 LLM %d' % (len(cands) - len(todo), len(todo)))

    t0 = time.time()
    for bi in range(0, len(todo), BATCH):
        batch = todo[bi:bi + BATCH]
        targets = [cards[i] for i in batch]
        last = None
        out = None
        for _ in range(MAX_ATTEMPTS):
            try:
                out = _ask(model, cards, targets, cands)
                break
            except Exception as e:                      # noqa: BLE001 重试时吞掉
                last = e
        if isinstance(out, dict):
            for cid in batch:
                allowed = {x for x, _ in cands[cid]} | {cid}
                entries = [e for e in _norm_entries(out.get(cid)) if e['id'] in allowed
                           and e['id'] != cid]
                entries = entries[:MAX_RELATED * 2]      # 双向输出，上限放宽一倍
                picked[cid] = entries
                fp = ','.join('%s:%s' % t for t in cands[cid])
                cache[cid] = {'fp': fp, 'rel': entries}
        else:
            print('  批 %d-%d 失败（%s），词法兜底' % (bi, bi + len(batch) - 1, last))
            for cid in batch:
                picked[cid] = _lexical_entries(cards, {cid: cands[cid]})[cid]
        done = bi + len(batch)
        print('  LLM %d/%d  %.0fs' % (done, len(todo), time.time() - t0))
        _save_cache(cache)
    return picked


# ---------- 合并写回 ----------

def merge(cards, cands, picked, existing):
    """手写边优先 → LLM/词法边去重合并 → 双向补齐 → 每卡裁到 MAX_RELATED。"""
    rel = {i: [] for i in cards}
    seen = {i: set() for i in cards}

    def put(a, b, entry):
        if a == b or b not in cards or b in seen[a]:
            return
        seen[a].add(b)
        rel[a].append(dict(entry, id=b))

    # 1) 手写基线（只增不改，不参与裁剪预算之外的重排）
    for i, entries in existing.items():
        for e in entries:
            if e.get('id') in cards and e.get('id') != i:
                put(i, e['id'], e)
    # 2) 算出来的边
    for a, entries in picked.items():
        score_of = dict(cands.get(a, []))
        ordered = sorted(entries, key=lambda e: -score_of.get(e['id'], 0.0))
        for e in ordered:
            if len(rel[a]) >= MAX_RELATED:
                break
            put(a, e['id'], e)
    # 3) 双向补齐：a 有 b 而 b 没 a → 反向条目（kind 反着放，note 沿用）
    flip = {'prereq': 'extends', 'extends': 'prereq', 'compare': 'compare'}
    for a in list(rel):
        for e in list(rel[a]):
            b = e['id']
            if a not in seen[b] and len(rel[b]) < MAX_RELATED:
                put(b, a, dict(e, kind=flip.get(e['kind'], e['kind'])))
    return rel


def write_back(final, src, js_files):
    # 1) jsonl：整文件重写（一行一卡，字段顺序保持 load 时的插入序）
    by_file = {}
    for cid, p in src.items():
        if p[0] == 'jsonl':
            by_file.setdefault(p[1], []).append(cid)
    for p, cids in sorted(by_file.items()):
        lines, n = [], 0
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                if c['id'] in final and c.get('related') != final[c['id']]:
                    c['related'] = final[c['id']]
                    n += 1
                lines.append(json.dumps(c, ensure_ascii=False))
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('  jsonl %s：更新 %d 条' % (os.path.basename(p), n))

    # 2) data/*.js：只动非 jsonl 卡所在文件，原位替换数组区间
    touched = {}
    for cid, p in src.items():
        if p[0] == 'js':
            touched.setdefault(p[1], set()).add(cid)
    for path, cids in sorted(touched.items()):
        text, start, end, arr = js_files[path]
        n = 0
        for c in arr:
            if c.get('id') in cids and c.get('related') != final.get(c['id'], []):
                c['related'] = final.get(c['id'], [])
                n += 1
        if not n:
            continue
        new_text = text[:start] + json.dumps(arr, ensure_ascii=False, indent=2) + text[end:]
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_text)
        print('  data %s：更新 %d 条' % (os.path.basename(path), n))


# ---------- main ----------

def main():
    lexical_only = '--lexical' in sys.argv[1:]
    cards, src, js_files, existing = load_all()
    t0 = time.time()
    cands = recall(cards)
    n_with = sum(1 for v in cands.values() if v)
    print('召回：有候选 %d/%d 张  %.1fs' % (n_with, len(cards), time.time() - t0))

    if lexical_only:
        picked = _lexical_entries(cards, cands)
    else:
        model = llm.pick_model()
        print('模型：%s' % model)
        picked = llm_pick(cards, cands, model)

    final = merge(cards, cands, picked, existing)
    n_rel = sum(1 for v in final.values() if v)
    kinds = {}
    for v in final.values():
        for e in v:
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print('成图：%d/%d 张有 related，共 %d 条边 %s'
          % (n_rel, len(final), sum(len(v) for v in final.values()), kinds))
    write_back(final, src, js_files)
    print('完成 %.0fs。下一步：emit_js all → verify → dbseed --sync → check.js'
          % (time.time() - t0))


if __name__ == '__main__':
    main()
