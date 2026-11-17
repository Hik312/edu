# -*- coding: utf-8 -*-
"""把 link_related 词法兜底写出来的 related 清掉，给 LLM 精选版让路。

    python reset_related.py

只清「算出来的」边，不动人写的：aizhuan.js（42 条带 note 的手写边）原样保留。
清完跑 link_related.py 重新生成。
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_related import DATA_DIR, GROUPS, HERE, parse_js                # noqa: E402

if 'utf' not in (getattr(sys.stdout, 'encoding', '') or '').lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

# 手写边所在文件：只剔词法模板生成的，人写的不动。
# ★ 教训（2026-10-02 真踩）：最初只列了 aizhuan.js，结果 springboot.js 里
#   人写的 20 条边被整文件清空（事后靠 git show HEAD:data/springboot.js 找回）。
#   手写边不只在一个文件里 —— 加 KEEP 前先 git grep '"kind"' data/ 认一遍。
KEEP = {'aizhuan.js', 'springboot.js'}

# 词法兜底产出的 note 模板（_lexical_entries）——按前缀识别，别误伤人写的
LEX_PREFIX = ('同属「', '关键词重叠（')


def main():
    # 1) jsonl（interview 卡，related 全是上一轮算的）
    for g in GROUPS:
        p = os.path.join(HERE, 'out_%s.jsonl' % g)
        if not os.path.exists(p):
            continue
        import json
        lines, n = [], 0
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                if c.get('related'):
                    c['related'] = []
                    n += 1
                lines.append(json.dumps(c, ensure_ascii=False))
        if n:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(lines) + '\n')
        print('jsonl %s：清 %d 条' % (g, n))

    # 2) data/*.js：普通文件清空；aizhuan 只剔词法模板边（人写的 42 条留下）
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith('.js'):
            continue
        path = os.path.join(DATA_DIR, name)
        parsed = parse_js(path)
        if not parsed:
            continue
        text, start, end, arr = parsed
        n = 0
        for c in arr:
            rel = c.get('related')
            if not rel:
                continue
            if name in KEEP:
                keep = [e for e in rel
                        if not (isinstance(e, dict)
                                and (e.get('note') or '').startswith(LEX_PREFIX))]
                if len(keep) != len(rel):
                    c['related'] = keep
                    n += len(rel) - len(keep)
            else:
                c['related'] = []
                n += len(rel)
        if not n:
            continue
        import json
        new_text = text[:start] + json.dumps(arr, ensure_ascii=False, indent=2) + text[end:]
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_text)
        print('data %s：清 %d 条' % (name, n))

    # 3) LLM 缓存（上一轮全是失败，理应为空，顺手删干净）
    cache = os.path.join(HERE, 'related_llm_cache.json')
    if os.path.exists(cache):
        os.remove(cache)
        print('已删 LLM 缓存')
    print('完成。下一步：python link_related.py')


if __name__ == '__main__':
    main()
