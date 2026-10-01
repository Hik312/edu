# -*- coding: utf-8 -*-
"""本地大模型精读：给章节补「一句话 / 类比 / 重点 / 原理拆解」。

**为什么没有用 LangGraph 或 LangChain。**
抽取本身就是一次结构化生成：给提示词 → 收 JSON → 不合法就重问一次。
所谓「自检」就是 `if 类比里混进了技术词: 重问`，几十行就写完了。
引入编排框架要换来一整棵依赖树、每次启动多等几秒、出错时多一层要读的栈，
换来的收益是零 —— 这里没有多步规划、没有工具选择、没有条件分支图。

**`/api/llm/status` 返回 `ok:false` 是正常状态，不是故障。**
AI 是可选增强，平台没有一处核心功能依赖它。所以这里坚持返 200，
而不是抛 503 —— 前端据此把 AI 那一块换成提示文字，其余照常。
"""
from fastapi import APIRouter, Depends, HTTPException

import db
import importer
import llm
from ..config import LLM_ERR
from ..deps import current_user
from ..schemas import EnrichIn, ToCardIn

router = APIRouter(prefix='/api', tags=['AI 精读'])

#: 一次精读请求最多允许的章节数。不带 indexes 时默认是「整篇逐章」，
#: 大文档会有几十上百章 → 串行调几十次模型、几分钟不返回。
#: 匿名可调时这是个白烧算力的口子；限个上限，超了让人分批点。
MAX_ENRICH_CHAPTERS = 200


def _llm_fail(e):
    """内部代号 → 人话 → 502。面板上写「no_model」没人看得懂。"""
    return HTTPException(502, LLM_ERR.get(str(e), str(e)))


@router.get('/llm/status', summary='AI 精读可用性')
def llm_status():
    st = llm.status()
    st['ok'] = bool(st.get('ok'))
    return st                      # 注意：ok 可能是 false，但 HTTP 仍然是 200


@router.post('/llm/enrich', summary='精读一章 / 多章 / 一整段文字')
def enrich(body: EnrichIn, user=Depends(current_user)):
    return _enrich_doc(body) if body.docId else _enrich_text(body)


def _enrich_text(body: EnrichIn):
    """不挂文档，直接精读一段文字（网页上「精读这段」按钮用）。"""
    text = (body.text or '').strip()
    if len(text) < 20:
        raise HTTPException(400, '正文太短，没啥可精读的')
    try:
        ai = llm.enrich(body.title or '', text, model=body.model)
    except RuntimeError as e:
        raise _llm_fail(e)
    return {'ok': True, 'ai': ai}


def _enrich_doc(body: EnrichIn):
    d = db.get_doc(body.docId)
    if not d:
        raise HTTPException(404, '文档不存在')
    chs = d.get('chapters') or []

    idxs = body.indexes
    if not idxs:
        idxs = [body.index] if body.index is not None else list(range(len(chs)))
    idxs = [i for i in idxs if isinstance(i, int) and 0 <= i < len(chs)]
    if not idxs:
        raise HTTPException(400, '章节下标无效')
    if len(idxs) > MAX_ENRICH_CHAPTERS:
        raise HTTPException(400, '一次最多精读 %d 章（这次 %d 章），请分批'
                                 % (MAX_ENRICH_CHAPTERS, len(idxs)))

    skipped, fail, targets = [], [], []
    for i in idxs:
        ch = chs[i]
        # 纯标题行（文档大标题、章标题）正文是空的，精读不出东西。
        # 必须跳过：否则批量精读会因为「第一章是空的」而整批失败。
        if len((ch.get('body') or '').strip()) < 20:
            skipped.append({'index': i, 'title': ch.get('title') or ''})
            continue
        targets.append((i, ch))

    done = []
    if targets:
        try:
            if len(targets) == 1:
                # 只点了一章就单章调 —— 别为了一个小请求先垫一批的延迟
                i, ch = targets[0]
                res = [llm.enrich(ch.get('title'), ch.get('body'),
                                  model=body.model, self_check=body.selfCheck)]
                meta = {'model': llm.pick_model(), 'provider': llm.provider()}
            else:
                # 批量一次送 4 章，15 章从 90s 压到 ~30s。
                # 代价是 7B 会把 A 章内容安到 B 章头上（随机复现），
                # 所以 llm.enrich_many 内部带对齐质检，对不上的整批退回单章。
                res, meta = llm.enrich_many(
                    [{'title': c.get('title'), 'body': c.get('body')} for _, c in targets],
                    model=body.model, batch=int(body.batch or 4))
        except RuntimeError as e:
            raise _llm_fail(e)
        except Exception as e:
            raise HTTPException(502, '调用失败：%s' % e)

        for (i, _ch), ai in zip(targets, res):
            if isinstance(ai, dict) and (ai.get('oneLine') or ai.get('mechanism')):
                ai.pop('_meta', None)          # 批量模式带的内部对齐分数，别落盘
                done.append({'index': i, 'ai': ai})
            else:
                fail.append({'index': i, 'msg': '这一章没抽出结果，单章重试看看'})

    if done:
        doc = db.set_doc_ai(body.docId, done, meta)
        if doc is None:
            raise HTTPException(404, '文档不存在')
        return {'ok': True, 'done': len(done), 'failed': fail,
                'skipped': skipped, 'doc': doc}

    if skipped and not fail:
        raise HTTPException(400, '这些章节没有正文（只有标题），没啥可精读的')
    raise HTTPException(502, fail[0]['msg'] if fail else '精读失败')


@router.post('/llm/to-card', summary='把某章的精读结果变成草稿卡')
def to_card(body: ToCardIn, user=Depends(current_user)):
    """复用「草稿 → 补 scene → 入库」那条流程，不另开一条入库路径。
    这样导入的资料和手写的卡，进库前都过同一道关卡。"""
    d = db.get_doc(body.docId)
    if not d:
        raise HTTPException(404, '文档不存在')
    chs = d.get('chapters') or []
    if not (0 <= body.index < len(chs)):
        raise HTTPException(400, '章节下标无效')

    ch = chs[body.index]
    ai = ch.get('ai') or body.ai
    if not ai:
        raise HTTPException(400, '这一章还没精读，先点「AI 精读」')

    card = llm.to_card(ch, ai, {'category': d.get('category'),
                                'subject': d.get('subject'),
                                'domain': d.get('domain'),
                                'topicPath': ['导入', (d.get('title') or '')[:20]],
                                # 卡片组：这份文档就是这些卡的「文件夹」
                                'deck': (d.get('title') or '')[:60],
                                'deckId': d.get('id')})
    cur = importer.list_drafts()
    cur.append(card)
    db.save_drafts(cur)
    return {'ok': True, 'draft': card}
