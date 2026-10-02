# -*- coding: utf-8 -*-
"""cards Agent 的执行层 —— 怎么跑起来（对应 qa/runtime.py 的角色）。

职责边界：
    graph     只管状态流转（nodes/graph 不碰磁盘）
    runtime   装图缓存、读文档、幂等判断、落盘（存草稿 + 拷图片）
    router    HTTP 形状（app/routers/agent.py）

跑之前的模型/依赖检查在 router 做（没装 langgraph → 503），
llm 层错误原样抛 RuntimeError，router 映射成 LLM_ERR 文案（502）。
"""
import re
import time

import db            # core/db.py
import docparse      # core/docparse.py
import importer      # core/importer.py
import llm           # core/llm.py

from . import dedup
from . import graph

_G = {}               # 图编译一次缓存住（编译有成本，invoke 很便宜）

#: 标题命中就直接判剔除的非正文章节（规则先判，剩下的才交给模型）。
#: 全匹配而不是 search：「数据结构目录详解」这种正文标题不能误杀。
#: 「附录」不在此列 —— 附录A 常是公式表/速查表，剔了可惜。
RULE_DROP = re.compile(
    r'^\s*(?:目\s*录|contents?|参考\s*文献|references?|致\s*谢|'
    r'acknowledg\w*|前\s*言|序\s*言|扉\s*页|版权(?:声明|页)?|封面|封底)'
    r'\s*[\.。:：]?\s*$', re.I)


def _g(name):
    if name not in _G:
        _G['refine'] = graph.build_refine()
        _G['chapter'] = graph.build_chapter()
    return _G[name]


def _card_id(doc_id, index):
    """和 nodes._build_card 同一套 id 规则（只看 docId+下标，不掺标题）——
    幂等判断必须和生成对得上，改这里要一起改。"""
    import hashlib
    return 'ag-' + hashlib.md5(
        ('%s:%d' % (doc_id, index)).encode('utf-8')
    ).hexdigest()[:8]


def run_structure(doc_id):
    """structure 阶段：LLM 定切分点 → 重切 → 落库。返回给前端的摘要。

    refined=False 是正常结果（没装模型 / 方案不合法），msg 里有理由。"""
    doc = db.get_doc(doc_id)
    if not doc:
        raise KeyError('doc_not_found')
    out = _g('refine').invoke({'doc': doc, 'plan': {}, 'refined': False, 'msg': ''})
    refined = bool(out.get('refined'))
    if refined:
        doc = db.upsert_doc(out['doc'])         # 精修后的 chapters 真正落库
    chs = doc.get('chapters') or []
    return {'refined': refined,
            'msg': out.get('msg') or '',
            'chapters': len(chs),
            'chars': sum(len(c.get('body') or '') for c in chs),
            'doc': doc}


def run_parse(doc_id):
    """内容解析：规则预判 + LLM 判定每章有用与否 → 报告落库。

    流程位置：structure（定分章点）之后、chapter（出卡）之前 —— 报告必须
    基于最终章节下标，否则结构一精修下标全错位。
    模型不可用**不抛**：规则那部分（封面/目录/参考文献）照样能剔，
    model_ok/msg 把原因带回给前端提示，502 会让用户连规则结果都拿不到。
    """
    doc = db.get_doc(doc_id)
    if not doc:
        raise KeyError('doc_not_found')
    chs = doc.get('chapters') or []
    if not chs:
        raise KeyError('no_chapters')

    # 1) 规则先判明显的非正文（不花模型）
    rules = {}
    for i, c in enumerate(chs):
        t = (c.get('title') or '').strip()
        if RULE_DROP.match(t):
            rules[i] = '疑似「%s」，非正文' % t[:14]

    # 2) 模型判剩下的（全量清单喂给它，idx 才和原下标对得上；
    #    规则已命中的以规则为准 —— 规则是硬知识，模型偶尔被标题带偏）
    by_model = {}
    model_ok, msg = True, ''
    try:
        out = llm.parse_content(importer.structure_items(chs),
                                doc.get('title') or '')
        by_model = {r['idx']: r for r in out['chapters']}
    except RuntimeError as e:
        model_ok, msg = False, str(e)   # no_model / ai_off / llm_not_json…

    # 3) 合并：规则 > 模型 > 默认保留（漏判只是多张卡，误剔是丢内容）
    rows = []
    for i in range(len(chs)):
        if i in rules:
            rows.append({'index': i, 'keep': False,
                         'reason': rules[i], 'by': 'rule'})
            continue
        m = by_model.get(i)
        if m is not None:
            rows.append({'index': i, 'keep': bool(m['keep']),
                         'reason': m.get('reason') or '', 'by': 'ai'})
        else:
            rows.append({'index': i, 'keep': True, 'reason': '',
                         'by': '' if model_ok else 'fallback'})

    parse = {'at': time.strftime('%Y-%m-%d %H:%M:%S'),
             'model_ok': model_ok, 'msg': msg, 'chapters': rows}
    doc['parse'] = parse
    doc = db.upsert_doc(doc)
    return {'parse': parse, 'doc': doc, 'model_ok': model_ok, 'msg': msg}


def run_parse_keeps(doc_id, keeps):
    """保存用户在解析报告上的勾选调整（确认环节）。keeps: {index: bool}。

    改过的行 by='user'：报告页能看出哪些是自己调过的，重新解析会覆盖。"""
    doc = db.get_doc(doc_id)
    if not doc:
        raise KeyError('doc_not_found')
    parse = doc.get('parse')
    if not parse:
        raise KeyError('no_parse')
    changed = 0
    for row in parse.get('chapters') or []:
        # schema 把 keeps 定成 Dict[str, bool]（JSON 键只能是字符串）
        k = keeps.get(str(row['index']))
        if isinstance(k, bool) and k != row['keep']:
            row['keep'] = k
            row['by'] = 'user'
            changed += 1
    parse['at'] = time.strftime('%Y-%m-%d %H:%M:%S')  # 调整也算一次确认时间
    doc['parse'] = parse
    doc = db.upsert_doc(doc)
    return {'parse': parse, 'changed': changed, 'doc': doc}


def run_chapter(doc_id, index, force=False):
    """chapter 阶段：一章跑完整张图，草稿 + 图片落盘。返回摘要。

    幂等：同 id 草稿已存在且没 force → skipped，前端逐章轮询时这正是
    「断点续跑」的实现（重跑只补没生成过的章）。"""
    doc = db.get_doc(doc_id)
    if not doc:
        raise KeyError('doc_not_found')
    chs = doc.get('chapters') or []
    if not (0 <= index < len(chs)):
        raise KeyError('bad_index')
    ch = chs[index]
    body = ch.get('body') or ''
    if len(body.strip()) < 20:
        return {'skipped': True, 'reason': 'empty',
                'msg': '章节太短，跳过（%d 字）' % len(body.strip())}

    cid = _card_id(doc_id, index)
    if not force:
        for d in importer.list_drafts():
            if d.get('id') == cid:
                return {'skipped': True, 'reason': 'exists', 'draft': d,
                        'msg': '已生成过（断点续跑自动跳过）'}

    out = _g('chapter').invoke({'doc': doc, 'index': index, 'chapter': ch,
                                'captions': {}, 'tries': 0, 'ok': False,
                                'msg': ''})
    card = out.get('card')
    if not card:
        # draft 里 RuntimeError(llm_not_json) 会先抛到这；这里是兜底
        raise RuntimeError(out.get('msg') or '生成失败')

    # 出卡前去重：同一份资料重复导入、相邻章内容重叠时别再进池。
    # embedding 不可用时 find_dup 返回 None → 照常放行（去重是增强不是闸门）
    dup = dedup.find_dup(card)
    if dup:
        return {'skipped': True, 'reason': 'duplicate',
                'msg': '和已有卡《%s》重复（相似度 %.2f），已跳过'
                       % (dup['title'] or dup['id'], dup['sim'])}

    # 图片在**这一章的最终卡**定稿后才拷：id 稳定，重试不会留孤儿图。
    # 拷到 card-<id> 目录 → 卡片不随源文档删除而丢图。
    # owner 用 card['id']（生成后的权威值）—— 它和上面预判的 cid 同源，
    # 但以实际落盘的 id 为准，图片永远跟着草稿走。
    names = docparse.MEDIA_TOKEN.findall(body)
    copied = docparse.copy_media(doc_id, 'card-' + card['id'], names)
    if copied:
        cap = out.get('captions') or {}
        card['images'] = [{'name': c['name'], 'src': c['src'],
                           'caption': cap.get(c['name']) or ''}
                          for c in copied]
    importer.save_drafts([card])
    return {'skipped': False, 'ok': bool(out.get('ok')), 'draft': card,
            'msg': out.get('msg') or '',
            'images': len(card.get('images') or [])}
