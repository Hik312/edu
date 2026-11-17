# -*- coding: utf-8 -*-
"""按 manifest 批量生成「面试知识卡」→ out_{group}.jsonl（逐卡落盘、断点续跑）。

用法：
    python gen_interview_cards.py redis [--limit 3]
    python gen_interview_cards.py all

流水线（每张卡）：
    素材清洗截断 → 富卡提示词（1000 字标准）→ llm._call（qwen3:8b）
    → _clean_json → 字段收拾 → 程序化自检（对齐分/关键词/场景数/字数下限）
    → 不过线带着具体理由重写一版（最多 2 次）→ 还不过记入 failed_{group}.jsonl
闸门口径与 agent/cards/nodes.py 的 ground() 一致（align>=0.08、
scene>=2、正文合计下限 = min(800, 源文无空白字数*0.55)）。
"""
import io
import json
import os
import re
import sys
import time

_BK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # back_study
sys.path.insert(0, _BK)
sys.path.insert(0, os.path.join(_BK, 'core'))      # 注意：venv 里有同名 llm 包，core 必须排前面
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

import llm                                                             # noqa: E402  core/llm.py

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_CAP = 6000          # 提示词里参考资料上限（与 agent 的 CARDS_MAX_BODY 同口径）
MAX_ATTEMPTS = 2
MIN_ALIGN = 0.08        # agent/config.py CARDS_MIN_ALIGN
TEMP = 0.4
MAX_TOKENS = 3072
CALL_TIMEOUT = 600

INTERVIEW_SYS = '''你是「面试知识卡」出题人。用户会给你一道面试题和一份参考资料，把它们整理成一张学习卡片，只输出 JSON：
{"title":"卡片标题","oneLine":"定义式结论(30-60字)","analogy":"生活类比(40-90字)",
 "why":"为什么是这样(80-150字)","mechanism":["原理步骤，6-8条，每条60-120字"],
 "keywords":["参考资料里真实出现的术语，3-6个"],"scene":["场景1","场景2","场景3"],
 "interviewQ":["追问1（答：要点）","追问2（答：要点）"]}

内容要充足 —— 这张卡是讲义不是目录，每个字段都得写够：
- title：给定的是本卡的题目或考点 —— 写成 <=30 字的问句式标题，考点不许换；
- oneLine 是**定义**：先讲清「这个知识点是什么、干什么用」，30-60字；
- mechanism 6-8 条、每条 60-120 字、**总字数不少于 400 字**：第①条先给出定义/本质
  （它到底是什么），之后按因果顺序讲「它怎么跑」，把因果链讲完整 —— 读者只看
  mechanism 就该懂这个原理怎么工作；不许把 oneLine 换个说法抄一遍；每条写成完整
  的一句话：做了什么/怎么做的 + 为什么这样/结果如何，短于 40 字视为没写完（只写
  半句步骤名不算）；
- why 80-150 字：讲透「为什么需要它、为什么是这样」（问题背景→为什么旧办法不行→
  它解决在哪），不许只写一句"为了解决xx问题"；
- scene 至少 3 条、每条 40-80 字：真实场景（什么系统、什么情况下用、有什么坑），
  禁止「广泛应用」「在实际开发中很重要」这类空话；
- interviewQ 3-4 条：面试官真会问的追问，每条后面跟「（答：…）」给出答案要点
  （要点 40-80 字），不是只列问题；
- 整张卡正文（oneLine+why+mechanism+scene+interviewQ 合计）目标 **1000 字左右**
  —— 字数是目标，下面的事实红线优先：参考资料较短时写到信息量的极限即可，
  绝不注水、不许车轱辘话重复；
事实红线：
- **所有事实必须来自参考资料**：oneLine / why / mechanism / keywords 里的名词和数字
  必须在参考资料中出现过，不许编造没有的接口名、版本号、数字；定义也从参考资料概括；
- keywords 只挑**参考资料出现过**的术语，原样抄写，不许同义替换、不许翻成英文；
- analogy 必须是日常生活场景（排队/图书馆/快递/做饭/开车/整理房间），不许出现任何技术词。
提交前自检：把 oneLine+why+mechanism+scene+interviewQ 加起来数一遍，不足 800 字就是
没写够 —— 回去把短条扩长再输出。
只输出 JSON，不要 markdown 代码块，不要任何解释。'''

REWRITE = ('上一版没有通过自检：%s\n'
           '重写一版：把没达标的字段扩写到位，事实只用参考资料里出现过的；仍然只输出 JSON。')


def log(group, msg):
    line = '%s [%s] %s' % (time.strftime('%H:%M:%S'), group, msg)
    print(line, flush=True)
    with open(os.path.join(HERE, 'run_%s.log' % group), 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def clean_text(t):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'<[^>]+>', '', t)
    keep = []
    for line in t.split('\n'):
        s = line.strip()
        if s in ('TIP', '<TIP>') or s.startswith('想深入了解') \
           or s.startswith('想更详细了解') or '可以看这篇' in s:
            continue
        keep.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(keep)).strip()


def clean_card(out):
    """模型输出收拾 —— 口径抄 agent/cards/nodes.py 的 _clean_card。"""
    def s(v, n):
        return ('' if v is None else str(v)).strip()[:n]

    def arr(v, n, each):
        if not isinstance(v, list):
            v = [v] if v else []
        return [t for t in (s(x, each) for x in v) if t][:n]

    return {
        'title': s(out.get('title') or out.get('卡片标题'), 60) or '未命名',
        'oneLine': s(out.get('oneLine') or out.get('一句话'), 140),
        'analogy': s(out.get('analogy') or out.get('类比'), 140),
        'why': s(out.get('why'), 200),
        'mechanism': arr(out.get('mechanism') or out.get('原理步骤'), 10, 180),
        'keywords': arr(out.get('keywords'), 8, 30),
        'scene': arr(out.get('scene'), 5, 160),
        'interviewQ': arr(out.get('interviewQ'), 4, 200),
    }


def assemble(entry, out):
    card = {
        'id': entry['id'],
        'domain': entry['domain'],
        'category': 'work',
        'subject': entry['subject'],
        'topicPath': entry['topicPath'],
        'tags': entry['tags'],
    }
    card.update(out)
    card['related'] = []
    return card


def validate(card, src, floor):
    """返回 (fatal, info, score, total) —— 口径同 nodes.py 的 ground()，但把
    「个别关键词被改写剔除」降级成提示：那是 8B 的口癖问题，卡本身仍对齐
    （align 分兜底）；只有关键词全掉才算致命。"""
    fatal, info = [], []
    low = re.sub(r'\s+', '', src).lower()
    kept = [k for k in (card.get('keywords') or [])
            if re.sub(r'\s+', '', k).lower() in low]
    dropped = [k for k in (card.get('keywords') or []) if k not in kept]
    card['keywords'] = kept
    score = llm.align_score(src, {'oneLine': card.get('oneLine'),
                                  'mechanism': card.get('mechanism'),
                                  'points': kept})
    if score < MIN_ALIGN:
        fatal.append('内容和参考资料重合度过低（%.2f < %.2f）' % (score, MIN_ALIGN))
    if dropped:
        info.append('关键词已剔除（原文没有）：%s' % '、'.join(dropped[:3]))
    if not card.get('keywords'):
        fatal.append('关键词全部不在参考资料里')
    if not card.get('scene') or len(card['scene']) < 2:
        fatal.append('场景不足 2 条')
    total = (len(card.get('oneLine') or '') + len(card.get('why') or '')
             + sum(len(x) for x in (card.get('mechanism') or []))
             + sum(len(x) for x in (card.get('scene') or []))
             + sum(len(x) for x in (card.get('interviewQ') or [])))
    if total < floor:
        fatal.append(
            '正文合计 %d 字偏短（目标1000，本卡下限 %d）：'
            'mechanism 每条扩到 60-120 字、why 展开到 80-150 字、'
            'scene 每条 40-80 字、追问答案 40-80 字' % (total, floor))
    return fatal, info, score, total


def load_source(entry):
    if entry.get('src_inline'):
        return clean_text(entry['src_inline'])
    with open(entry['src_path'], encoding='utf-8') as f:
        return clean_text(f.read())


def gen_one(entry, model):
    """生成一张卡。返回 (card|None, reason, score, total, tries)。"""
    src = load_source(entry)[:SRC_CAP]
    src_nows = re.sub(r'\s+', '', src)
    if len(src_nows) < 300:
        return None, '素材过短(%d字)' % len(src_nows), 0, 0, 0
    floor = min(800, int(len(src_nows) * 0.55))
    sys_msg = {'role': 'system', 'content': INTERVIEW_SYS}
    user_msg = {'role': 'user',
                'content': '面试题：%s\n\n参考资料：\n%s' % (entry['title_hint'], src)}
    msgs = [sys_msg, user_msg]
    fatal, info, score, total, card = ['(未生成)'], [], 0.0, 0, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = llm._call(msgs, model, CALL_TIMEOUT, temperature=TEMP,
                            max_tokens=MAX_TOKENS)
            out = llm._clean_json(raw)
            if isinstance(out, list):
                out = out[0] if out else {}
            if not isinstance(out, dict):
                raise RuntimeError('llm_not_json')
            card = assemble(entry, clean_card(out))
            fatal, info, score, total = validate(card, src, floor)
        except Exception as e:                              # 单次失败不掀桌
            fatal, card = ['生成失败：%s' % e], None
        if not fatal:
            return card, ('；'.join(info) if info else ''), score, total, attempt
        if attempt < MAX_ATTEMPTS:
            msgs = [sys_msg, user_msg]
            if card is not None:
                msgs.append({'role': 'assistant',
                             'content': json.dumps(card, ensure_ascii=False)[:800]})
            msgs.append({'role': 'user',
                         'content': REWRITE % ('；'.join(fatal + info))})
    return None, '；'.join(fatal + info), score, total, MAX_ATTEMPTS


def run_group(group, model, limit=None):
    with open(os.path.join(HERE, 'manifest_%s.json' % group), encoding='utf-8') as f:
        manifest = json.load(f)
    out_path = os.path.join(HERE, 'out_%s.jsonl' % group)
    fail_path = os.path.join(HERE, 'failed_%s.jsonl' % group)
    done = set()
    if os.path.exists(out_path):
        with open(out_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        done.add(json.loads(line)['id'])
                    except ValueError:
                        pass
    todo = [e for e in manifest if e['id'] not in done]
    if limit:
        todo = todo[:limit]
    log(group, '开始：清单 %d，已完成 %d，本轮待生成 %d，model=%s'
        % (len(manifest), len(done), len(todo), model))
    ok_n = fail_n = 0
    t_group = time.time()
    for i, e in enumerate(todo, 1):
        t0 = time.time()
        card, reason, score, total, tries = gen_one(e, model)
        ms = int((time.time() - t0) * 1000)
        if card:
            with open(out_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(card, ensure_ascii=False) + '\n')
            ok_n += 1
            log(group, '[%d/%d] OK   %-42s %4d字 score=%.2f tries=%d %dms%s'
                % (i, len(todo), card['id'], total, score, tries, ms,
                   ('  注: ' + reason) if reason else ''))
        else:
            fail_n += 1
            with open(fail_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({'id': e['id'], 'reason': reason[:300]}, 
                                   ensure_ascii=False) + '\n')
            log(group, '[%d/%d] FAIL %-42s %s %dms'
                % (i, len(todo), e['id'], reason[:160], ms))
    log(group, '完成：成功 %d，失败 %d，用时 %d 秒'
        % (ok_n, fail_n, int(time.time() - t_group)))
    return fail_n


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
    fails = 0
    for g in groups:
        fails += run_group(g, model, limit)
    return 1 if fails and args[0] != 'all' else 0


if __name__ == '__main__':
    sys.exit(main())
