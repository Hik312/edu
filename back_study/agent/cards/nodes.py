# -*- coding: utf-8 -*-
"""cards Agent 的节点 —— 每步具体做什么。图（graph.py）只负责把它们连起来。

节点契约和 qa/nodes.py 一样：收整个 state，返回**要修改的字段**。

两种节点两类活：
    refine / captions   不重试（失败就带着理由结束 —— 精修和图注都是增强）
    draft / ground      要重试（ground 判不合格就回炉，最多 C.MAX_TRIES 次）
                        —— 这正是「文不对题」的刹车，也是这张图存在的理由
"""
import hashlib
import json
import re
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage

from .. import config as C          # 公共层：agent/config.py
from .. import model as M           # 公共层：agent/model.py

import docparse                     # core/docparse.py：图片占位符与媒体读写
import importer                     # core/importer.py：分章与结构重切
import llm                          # core/llm.py：结构精修 / VLM / 对齐打分


class RefineState(TypedDict):
    """structure 图里流动的东西。"""
    doc: dict        # 文档（含 chapters）
    plan: dict       # llm.refine_structure 拿回的方案（没拿到是 {}）
    refined: bool    # 方案是否真的执行并落盘（runtime 负责落）
    msg: str


class ChapterState(TypedDict, total=False):
    """chapter 图里流动的东西。"""
    doc: dict        # 文档（含 chapters）
    index: int       # 本章下标
    chapter: dict    # 本章 {title, body, ...}（body 里带 ![](media:x) 占位）
    captions: dict   # 图片名 → VLM 图注（没装视觉模型就是空 dict）
    card: dict       # 生成的草稿卡（还没拷图 —— 拷图在 runtime，避免重试
                     #  换了标题改了 id 之后留下孤儿图片）
    tries: int       # 已尝试次数，防止死循环
    ok: bool         # ground 的对齐结果
    msg: str         # 给前端看的过程说明 / 不合格原因


# ---------------------------------------------------------------------------
# 提示词（和用它的节点放一起，理由同 qa/nodes.py）
# ---------------------------------------------------------------------------
CARD_SYS = '''你是「原理卡片」出题人。把用户给的一章资料整理成一张学习卡片，只输出 JSON：
{"title":"卡片标题","oneLine":"定义式结论(30-60字)","analogy":"生活类比(40-90字)",
 "why":"为什么是这样(80-150字)","mechanism":["原理步骤，6-8条，每条60-120字"],
 "keywords":["原文里真实出现的术语，3-6个"],"scene":["场景1","场景2","场景3"],
 "interviewQ":["追问1（答：要点）","追问2（答：要点）"]}

内容要充足 —— 这张卡是讲义不是目录，每个字段都得写够：
- title 抓本章最核心的考点（<=30字），不是照抄章节标题；
- oneLine 是**定义**：先讲清「这个知识点是什么、干什么用」，30-60字；
- mechanism 6-8 条、每条 60-120 字、**总字数不少于 400 字**：第①条先给出
  定义/本质（它到底是什么），之后按因果顺序讲「它怎么跑」，把因果链讲完整
  —— 读者只看 mechanism 就该懂这个原理怎么工作；不许把 oneLine 换个说法抄一遍；
  每条写成完整的一句话：做了什么/怎么做的 + 为什么这样/结果如何，短于 40 字
  视为没写完（只写半句步骤名不算）；
- why 80-150 字：讲透「为什么需要它、为什么是这样」（问题背景→为什么旧办法
  不行→它解决在哪），不许只写一句"为了解决xx问题"；
- scene 至少 3 条、每条 40-80 字：真实场景（什么系统、什么情况下用、有什么坑），
  禁止「广泛应用」「在实际开发中很重要」这类空话；
- interviewQ 3-4 条：面试官真会问的追问，每条后面跟「（答：…）」给出答案要点
  （要点 40-80 字），不是只列问题；
- 整张卡正文（oneLine+why+mechanism+scene+interviewQ 合计）目标 **1000 字左右**
  —— 字数是目标，下面的事实红线优先：原文较短时写到信息量的极限即可，
  绝不注水、不许车轱辘话重复、不许编造原文没有的内容；
事实红线：
- **所有事实必须来自原文**：oneLine / why / mechanism / keywords 里的名词和数字
  必须在原文中出现过，不许编造原文没有的接口名、版本号、数字；定义也从原文概括；
- keywords 只挑**原文出现过**的术语，原样抄写，不许同义替换、不许翻成英文；
- analogy 必须是日常生活场景（排队/图书馆/快递/做饭/开车/整理房间），
  不许出现任何技术词；
- 正文里的【图注：…】是原文配图的说明：图里展示的流程或结构可以融进 mechanism，
  但仍然不许编造图注以外的内容。
提交前自检：把 oneLine+why+mechanism+scene+interviewQ 加起来数一遍，
不足 800 字就是没写够 —— 回去把短条扩长再输出。
只输出 JSON，不要 markdown 代码块，不要任何解释。'''

REWRITE = ('上一版没有通过对齐自检：%s\n'
           '重写一版：只用原文里出现过的事实和术语，宁可少写也不要编。仍然只输出 JSON。')


# ---------------------------------------------------------------------------
# structure 图的节点
# ---------------------------------------------------------------------------
def refine(state: RefineState) -> dict:
    """结构精修：规则初切的清单交给 LLM 定切分点，然后 importer 执行重切。

    失败**不抛**：精修是增强不是地基，模型没装 / 抽风时保留原分章，
    带上理由结束 —— 后面的转卡照跑。这是和 draft 节点（失败要重试）
    明确不同的地方。"""
    doc = state['doc']
    chs = doc.get('chapters') or []
    if not chs:
        return {'refined': False, 'msg': '文档没有章节，无从精修'}
    try:
        plan = llm.refine_structure(importer.structure_items(chs),
                                    doc.get('title') or '')
    except RuntimeError as e:
        return {'plan': {}, 'refined': False,
                'msg': '结构精修没跑成（%s），保留规则分章' % str(e)}
    new_chs, doc_title = importer.apply_structure(chs, plan)
    if not new_chs or len(new_chs) == 0:
        return {'plan': plan, 'refined': False, 'msg': '方案没通过校验，保留规则分章'}
    merged = dict(doc)
    merged['chapters'] = new_chs
    merged['stats'] = {
        'chapters': len(new_chs),
        'chars': sum(len(c.get('body') or '') for c in new_chs),
        'headings': sum(1 for c in new_chs if c.get('title')),
    }
    # 文档标题**不动**：它同时是卡片组（deck）的名字，已发布的草稿靠它对组。
    # 模型给的 docTitle 只放进行为说明里，不做破坏性改名。
    msg = '分章 %d → %d%s' % (len(chs), len(new_chs),
                              ('（建议标题：%s）' % doc_title) if doc_title else '')
    return {'doc': merged, 'plan': plan, 'refined': True, 'msg': msg}


# ---------------------------------------------------------------------------
# chapter 图的节点
# ---------------------------------------------------------------------------
def captions(state: ChapterState) -> dict:
    """给本章的图片配图注（VLM 看图说一句）。

    没装视觉模型 → 空 dict 继续走（图片照样进卡，只是没 caption）；
    单图失败 → 跳过该图，不断整章。图注不是主产物，别让它拦住转卡。"""
    doc = state['doc']
    ch = state['chapter']
    names = docparse.MEDIA_TOKEN.findall(ch.get('body') or '')
    if not names:
        return {'captions': {}}
    try:
        vlm = llm.vlm_model()
    except Exception:
        vlm = ''
    if not vlm:
        return {'captions': {},
                'msg': '没装视觉模型，图片只搬运不生成图注（ollama pull qwen2.5vl:7b）'}
    caps = {}
    did = doc.get('id') or ''
    ctx = ch.get('title') or doc.get('title') or ''
    for n in dict.fromkeys(names):              # 去重且保序
        blob = docparse.read_media(did, n)
        if not blob:
            continue
        try:
            caps[n] = llm.vlm_caption(docparse.to_b64(blob), ctx, model=vlm)
        except Exception:
            caps[n] = ''                        # 单图失败：没图注也比没图片好
    return {'captions': caps}


def _inline_captions(body, captions):
    """把 `![](media:x)` 换成 `【图注：…】` —— 文本模型看不到图，
    但配图的说明它能用（提示词里明确允许融进 mechanism）。"""
    def rep(m):
        name = m.group(1)
        cap = (captions or {}).get(name) or ''
        return ('【图注：%s】' % cap) if cap else '【图片】'
    return docparse.MEDIA_TOKEN.sub(rep, body or '')


def _clean_card(out):
    """收拾模型输出：类型、长度、空值。模型不听话是常态，不收拾前端会崩。"""
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


def _build_card(doc, index, out):
    """草稿卡骨架。字段口径对齐 llm.to_card —— 走的还是同一条
    「草稿 → 补 scene → 发布」链路，只是 id 前缀换成 ag-（agent 出的）。

    id = md5(docId:index)[:8]：**只看文档和章节下标，不掺标题**。
    从前掺了标题，而 runtime 预判 id 用章节标题、这里用模型出的卡标题，
    两处对不上 → 断点续跑永远命不中、图片拷进了另一个 owner 目录。
    下标在一份文档里唯一，同章重跑同 id → save_drafts 幂等覆盖。"""
    cid = 'ag-' + hashlib.md5(
        ('%s:%d' % (doc.get('id'), index)).encode('utf-8')
    ).hexdigest()[:8]
    card = {
        'id': cid,
        'domain': doc.get('domain') or '待归类',
        'category': doc.get('category') or '',
        'subject': doc.get('subject') or '',
        'topicPath': ['导入', (doc.get('title') or '')[:20]],
        'title': out.get('title') or '未命名',
        'oneLine': out.get('oneLine') or '',
        'analogy': out.get('analogy') or '',
        'why': out.get('why') or out.get('oneLine') or '',
        'mechanism': out.get('mechanism') or [],
        'keywords': out.get('keywords') or [],
        'scene': out.get('scene') or [],
        'interviewQ': out.get('interviewQ') or [],
        '_draft': True,
        '_from': 'agent-cards',
        'deck': str(doc.get('title') or '')[:60],
        'deckId': doc.get('id') or '',
    }
    if out.get('images'):
        card['images'] = out['images']
    return card


def draft(state: ChapterState) -> dict:
    """生成卡片。「事实必须来自原文」写在提示词里 —— 8B 模型不看着这句，
    很乐意给你编一段很像真的。生成后由 ground 再验一道。"""
    doc = state['doc']
    ch = state['chapter']
    body = _inline_captions(ch.get('body'), state.get('captions'))
    user = '文档：%s\n章节标题：%s\n\n正文：\n%s' % (
        (doc.get('title') or '（无标题文档）')[:60],
        ch.get('title') or '（无标题）',
        body[:C.CARDS_MAX_BODY])
    msgs = [SystemMessage(content=CARD_SYS), HumanMessage(content=user)]
    # 重试时把不合格原因喂回去，别让它原样再来一遍
    if state.get('tries', 0) >= 1 and state.get('msg'):
        msgs.append(SystemMessage(
                    content='上一版：' + json.dumps(state.get('card') or {},
                                                    ensure_ascii=False)[:800]))
        msgs.append(HumanMessage(content=REWRITE % state['msg']))
    r = M.chat(temperature=C.TEMPERATURE).invoke(msgs)
    out = llm._clean_json(getattr(r, 'content', '') or '')
    if isinstance(out, list):
        out = out[0] if out else {}
    if not isinstance(out, dict):
        raise RuntimeError('llm_not_json')
    card = _build_card(doc, state['index'], _clean_card(out))
    return {'card': card, 'tries': state.get('tries', 0) + 1}


def ground(state: ChapterState) -> dict:
    """对齐自检：这版卡是不是这一章的（文不对题的刹车）。

    两道程序化检查（不花模型钱、结果稳定）：
      1. align_score —— 卡面文字与原文的字符二元组重合度，和 enrich_many
         用的是同一个指标（复用被验证过的阈值口径）；
      2. keywords 必须真在原文里（原文没有的术语直接踢掉，踢光了判不合格）。
    判不合格不丢结果：route 放行时还是会存，只是标 ok=False 让前端提示
    「这章要人工把关」—— 宁可给个要复核的草稿，也不要卡死在循环里。"""
    ch = state['chapter']
    card = state['card']
    body = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', ch.get('body') or '')
    # 关键词匹配先把空白去掉再比：中文 md 常在词中间硬折行（「疏忽\n概率」），
    # 不去空白会把原文里明明有的关键词误判成不存在 → 整章被打成 ok=False
    low = re.sub(r'\s+', '', body).lower()
    kept = [k for k in (card.get('keywords') or [])
            if re.sub(r'\s+', '', k).lower() in low]
    dropped = [k for k in (card.get('keywords') or []) if k not in kept]
    card['keywords'] = kept
    score = llm.align_score(body, {'oneLine': card.get('oneLine'),
                                   'mechanism': card.get('mechanism'),
                                   'points': card.get('keywords')})
    min_align = C.CARDS_MIN_ALIGN
    reasons = []
    if score < min_align:
        reasons.append('内容和原文重合度过低（%.2f < %.2f）' % (score, min_align))
    if dropped:
        reasons.append('关键词 %s 在原文中不存在，已剔除' % '、'.join(dropped[:3]))
    if not card.get('keywords'):
        reasons.append('关键词全部不在原文里')
    if not card.get('scene') or len(card['scene']) < 2:
        reasons.append('场景不足 2 条')
    # 内容长度闸门（用户口径：正文合计 1000 字左右）。固定下限会把源文很短的
    # 章打成不合格，所以下限跟着源文走（源文的 55%，封顶 800）。命中后走
    # REWRITE 重写 —— 差距以具体数字喂回去，模型第二版基本能写够。
    total = (len(card.get('oneLine') or '') + len(card.get('why') or '')
             + sum(len(x) for x in (card.get('mechanism') or []))
             + sum(len(x) for x in (card.get('scene') or []))
             + sum(len(x) for x in (card.get('interviewQ') or [])))
    src_chars = len(re.sub(r'\s+', '', ch.get('body') or ''))
    floor = min(800, int(src_chars * 0.55))
    if total < floor:
        reasons.append(
            '正文合计 %d 字偏短（目标1000，本章下限 %d）：'
            'mechanism 每条扩到 60-120 字、why 展开到 80-150 字、'
            'scene 每条 40-80 字、追问答案 40-80 字' % (total, floor))
    ok = not reasons
    return {'card': card, 'ok': ok,
            'msg': '；'.join(reasons) if reasons else '对齐通过（%.2f）' % score}


def route(state: ChapterState) -> str:
    """条件边：合格结束；不合格重写；次数用完也放行（带 ok=False 落盘）。"""
    if state.get('ok') or state.get('tries', 0) >= C.MAX_TRIES:
        return 'end'
    return 'retry'
