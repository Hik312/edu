# -*- coding: utf-8 -*-
"""卡片校验 / 自纠 —— 拿联网资料核对卡片内容。

两种用法：
  verify_cards(cards)   react 问答后，对**引用到的**那几张卡逐张联网核对，
                       返回「有错」的修正建议（列表）。这是主路径。
  verify(query/card_id) 单独校验一张卡（保留接口，按需/调试用）。

★ 为什么不自动落库：
  校验是「模型判定本地知识过时/有误」，自动改就变成"AI 偷偷改知识库"，
  错了难追溯。所以这里只产出 proposed_patch，落库走 db.apply_card_patch，
  必须由用户点了「修正」才发生（前端在聊天流里反问）。
"""
import json

from langchain_core.messages import SystemMessage, HumanMessage

from .. import model as M
import llm as core_llm
from ..qa import websearch

try:
    from ..servers import github_resource_mcp as gh
    _HAVE_GH = True
except Exception:
    gh = None
    _HAVE_GH = False

# 允许模型建议修改的字段（必须是卡片已有字段，避免它凭空造键、写坏结构）
_PATCH_FIELDS = ['oneLine', 'mechanism', 'why', 'analogy', 'scene', 'keywords', 'interviewQ']
# 参与校验 / 给模型看的卡片字段
_SHOW_FIELDS = ['id', 'title', 'oneLine', 'mechanism', 'why', 'analogy', 'scene', 'keywords', 'interviewQ']
# react 回答后最多校验几张（用户选的「前 2-3 张」；再多每问要跑多次联网+模型，太慢）
MAX_VERIFY = 3

VERIFY_SYS = """你是一名严谨的卡片质量校验员。下面给你一张本地知识卡片的内容，
以及从网络（网页搜索 + Github 仓库）检索来的参考资料。请判断本地卡片的
内容是否正确、是否过时、是否有明显错误。

校验规则：
- 只依据【网络资料】和常识判断；网络资料不足时，verdict 填 "unknown"，不要编造结论。
- 若本地卡片某字段与资料明显冲突、严重过时或遗漏关键事实，提出修改建议。
- 修改建议写在 proposed_patch 里：键必须是卡片已有字段
  （oneLine / mechanism / why / analogy / scene / keywords / interviewQ），
  值为修正后的**完整内容**（不是 diff，直接给改好后的整段）。
- 每条 issue 必须说清：哪个字段、为什么错或过期、依据（引用【网络资料】里的编号如 [1]）。
- 没有问题时 verdict 填 "correct"，proposed_patch 为空 {}。

只输出一个 JSON 对象，不要任何解释文字，格式如下：
{
  "verdict": "correct | partial | wrong | unknown",
  "summary": "一句话结论",
  "issues": [{"field": "mechanism", "why": "…与资料冲突…", "ref": "[1]"}],
  "proposed_patch": {"mechanism": "…改正后的完整内容…"}
}"""


def _web_and_gh(kw):
    """按关键词拉网页 + Github 资料。失败都返回空/说明，不抛。"""
    web = websearch.web_search(kw, limit=6)
    gh_txt = gh.github_search(kw, kind='repo', limit=5) if _HAVE_GH else ''
    return web, gh_txt


def _judge(card, web, gh_txt):
    """LLM 把一张卡的本地内容 vs 联网资料对比，返回
    {verdict, summary, issues, proposed_patch}。模型不可用也不抛，
    返回 unknown + 说明（联网资料已给，调用方可人工比对）。"""
    card_blob = {k: card.get(k) for k in _SHOW_FIELDS if k in card}
    card_text = json.dumps(card_blob, ensure_ascii=False, indent=2)
    web_text = '\n'.join('[%d] %s\n%s\n%s' % (i + 1, w['title'], w['url'], w['snippet'])
                         for i, w in enumerate(web or [])) or '（本次联网无结果）'
    human = ('本地卡片：\n%s\n\n【网络资料 网页】\n%s\n\n【网络资料 Github】\n%s\n\n'
             '请按系统指示校验，只输出 JSON。'
             % (card_text, web_text, gh_txt or '（无）'))
    out = {'verdict': 'unknown', 'summary': '', 'issues': [], 'proposed_patch': {}}
    try:
        raw = M.chat(temperature=0).invoke(
            [SystemMessage(VERIFY_SYS), HumanMessage(human)]).content
        parsed = core_llm._clean_json(raw)
        out['verdict'] = parsed.get('verdict', 'unknown')
        out['summary'] = parsed.get('summary', '')
        out['issues'] = parsed.get('issues', []) or []
        out['proposed_patch'] = {
            k: v for k, v in (parsed.get('proposed_patch') or {}).items()
            if k in _PATCH_FIELDS and v not in (None, '', [], {})
        }
    except Exception as e:
        out['summary'] = '模型校验失败（%s），但联网资料已拉回，你可人工比对。' % e
    return out


BATCH_VERIFY_SYS = """你是一名严谨的卡片质量校验员。下面给了多张本地知识卡片的内容，
以及每张卡对应的网络（网页 + Github）参考资料。请**逐张独立**判断内容是否正确/过时/有明显错误。

规则（对每张卡独立判断）：
- 只依据该卡的【网络资料】和常识；某张卡资料不足时 verdict 填 "unknown"、不要编造、proposed_patch 留空 {}。
- 有错/过时的字段写进该卡的 proposed_patch，键必须是卡片已有字段
  （oneLine/mechanism/why/analogy/scene/keywords/interviewQ），值是改正后的**完整内容**（非 diff）。
- 每条 issue 说清字段、为什么错、依据（引用该卡资料里的编号如 [1]）。
- 没问题或资料不足的卡，proposed_patch 为空 {}。

只输出一个 JSON 对象，格式：
{"results":[{"id":"卡片id","verdict":"correct|partial|wrong|unknown","summary":"一句话结论",
 "issues":[{"field":"mechanism","why":"…","ref":"[1]"}],"proposed_patch":{}}]}"""


def _judge_batch(cards, webmap):
    """一次 LLM 调用比对**所有**卡片，返回 {card_id: result}。

    ★ 为什么批量：逐张判别时每张卡都要把「整卡+联网资料」喂模型一遍（实测每张
    20~60s，3 张近 3 分钟，聊天根本没法用）。合成一次调用后只读一遍所有卡，
    实测降到 ~30~50s。联网仍然逐张搜（保证每张卡都有真实证据，不靠编）。"""
    parts = []
    for c in cards:
        blob = {k: c.get(k) for k in _SHOW_FIELDS if k in c}
        wt = '\n'.join('[%d] %s | %s | %s' % (i + 1, w['title'], w['url'], w['snippet'])
                       for i, w in enumerate(webmap.get(c['id']) or [])) or '（无）'
        parts.append('卡片 id=%s\n标题=%s\n内容=%s\n该卡网络资料：\n%s'
                     % (c['id'], c.get('title'),
                        json.dumps(blob, ensure_ascii=False), wt))
    human = ('\n\n====\n\n'.join(parts)
             + '\n\n请逐张校验，只输出 JSON。')
    out = {}
    try:
        raw = M.chat(temperature=0).invoke(
            [SystemMessage(BATCH_VERIFY_SYS), HumanMessage(human)]).content
        parsed = core_llm._clean_json(raw)
        for r in parsed.get('results', []) or []:
            cid = r.get('id')
            if not cid:
                continue
            out[cid] = {
                'verdict': r.get('verdict', 'unknown'),
                'summary': r.get('summary', ''),
                'issues': r.get('issues', []) or [],
                'proposed_patch': {k: v for k, v in (r.get('proposed_patch') or {}).items()
                                   if k in _PATCH_FIELDS and v not in (None, '', [], {})},
            }
    except Exception as e:
        # 模型失败：不给建议（宁可不说，也不要瞎改知识库）
        sys_stderr_warn('批量校验模型失败：%s' % e)
    return out


def sys_stderr_warn(msg):
    import sys
    sys.stderr.write('[verify] %s\n' % msg)


def verify_cards(cards, user_id=None):
    """校验一批（react 引用到的）卡片，返回**有错**的修正建议列表。

    入参 cards 是卡片 dict 列表（RAG 命中的），最多取前 MAX_VERIFY 张。
    逐张联网拿证据 + 一次批量 LLM 判别；只返回 proposed_patch 非空的（= 真发现要改的）。
    """
    picked = [c for c in (cards or []) if c.get('id')][:MAX_VERIFY]
    if not picked:
        return []
    webmap = {}
    for c in picked:
        web, _gh = _web_and_gh((c.get('title') or '').strip())
        webmap[c['id']] = web
    judged = _judge_batch(picked, webmap)
    out = []
    for c in picked:
        r = judged.get(c['id'])
        if not r or not r['proposed_patch']:
            continue
        out.append({
            'card_id': c['id'],
            'title': c.get('title'),
            'oneLine': c.get('oneLine'),
            'summary': r['summary'],
            'issues': r['issues'],
            'proposed_patch': r['proposed_patch'],
            'web': webmap.get(c['id']) or [],
        })
    return out


def verify(query=None, card_id=None, user_id=None):
    """单独校验一张卡（按 card_id 或 query 定位），返回完整结果（含无错的情况）。"""
    from ..qa import tools as qa_tools
    if card_id:
        card = qa_tools.find_card(card_id)
    else:
        hits = qa_tools.rank((query or '').strip(), limit=3)
        card = hits[0] if hits else None
    if not card:
        return {'ok': False, 'msg': '没在卡片库里找到相关卡片，换个关键词试试',
                'query': query, 'card_id': card_id}
    web, gh_txt = _web_and_gh((query or card.get('title') or '').strip())
    r = _judge(card, web, gh_txt)
    return {
        'ok': True,
        'card_id': card.get('id'),
        'card_title': card.get('title'),
        'verdict': r['verdict'],
        'summary': r['summary'],
        'issues': r['issues'],
        'proposed_patch': r['proposed_patch'],
        'web': web,
        'github': gh_txt,
    }