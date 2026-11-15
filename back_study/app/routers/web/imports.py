# -*- coding: utf-8 -*-
"""导入：粘贴文本 → 切分成草稿卡；草稿补齐字段后入库。

草稿是个「缓冲区」不是「卡」：机器切的字段永远差口气（尤其是 scene —— 必须写
你项目里真实用在哪，编不出来），所以强制人工过一道再入库。

题库导入（/import/qa，2026-11-15）：确定性解析 GitHub 上现成的问答资料
（JavaGuide / CS-Notes / 政治笔记 / Anki 导出），不走 AI —— 见
importer.parse_qa 的头注释。两步走：dry-run 预览 → 用户勾选 → commit。
"""
import sys

from fastapi import APIRouter, Depends, HTTPException

import db
import importer
import llm
from ...deps import current_user
from ...schemas import DraftPatch, ImportQaIn, ImportTextIn, PublishIn

router = APIRouter(prefix='/api', tags=['导入'])

# ★ 导入链路全部要求登录：
#   1. 草稿是个人数据（清空全部草稿曾经匿名可调）；
#   2. /api/import 会串行触发大模型调用，匿名可刷 = 免费烧你的算力。


@router.post('/import', summary='粘贴文本 → 切成草稿卡')
def import_text(body: ImportTextIn, user=Depends(current_user)):
    text = (body.text or '').strip()
    if len(text) < 10:
        raise HTTPException(400, '正文太短')

    opts = body.model_dump(exclude_none=True)
    try:
        # useLLM 两条通道都认：本机 Ollama 或云端 key，哪个可用走哪个。
        # 模型没起来也不要报错给用户 —— 本地规则切分虽然粗糙，但立刻能用。
        if body.useLLM and llm.status().get('ok'):
            cards, src = importer.parse_llm(text, opts), 'llm'
        else:
            cards, src = importer.parse_local(text, opts), 'local'
    except RuntimeError as e:
        if str(e) == 'no_key':
            raise HTTPException(400, '没有可用的大模型：本机起 Ollama 或设 LLM_API_KEY')
        sys.stderr.write('[import] %s\n' % e)
        cards, src = importer.parse_local(text, opts), 'local(fallback)'
    except Exception as e:
        sys.stderr.write('[import] %s\n' % e)
        cards, src = importer.parse_local(text, opts), 'local(fallback)'

    importer.save_drafts(cards)
    return {'ok': True, 'from': src, 'count': len(cards), 'drafts': cards}


@router.get('/drafts', summary='草稿列表')
def list_drafts(user=Depends(current_user)):
    return {'ok': True, 'drafts': importer.list_drafts()}


# ---------- 题库导入（2026-11-15） ----------
@router.post('/import/qa', summary='题库导入：解析预览（不落库）')
def import_qa_preview(body: ImportQaIn, user=Depends(current_user)):
    """把 markdown 问答 / Anki txt / Obsidian SR 解析成卡，**只回预览不落库**。

    返回 cards（草稿形状，含分配好的 id）+ skipped（没解析成的及原因）。
    前端渲染预览表让用户逐卡勾选，勾完带着 ids 打 /import/qa/commit。
    解析是确定性的：同一份 text + fmt + opts 两次调用结果逐位一致 ——
    这是 commit 阶段「服务端重解析、只信 id」的前提。
    """
    text = (body.text or '').strip()
    if len(text) < 10:
        raise HTTPException(400, '正文太短')
    try:
        r = importer.parse_qa(text, body.fmt, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {'ok': True, 'fmt': r['fmt'], 'cards': r['cards'],
            'skipped': r['skipped'], 'count': len(r['cards'])}


@router.post('/import/qa/commit', summary='题库导入：勾选的卡批量存为草稿')
def import_qa_commit(body: ImportQaIn, user=Depends(current_user)):
    """**服务端重新解析**再按 id 过滤入库 —— 不信任客户端回传的卡片内容。

    单次上限 500 张（一天刷 100 张是队列硬上限，500 张草稿够用几个星期；
    更大的资料分几次导，顺便逼着按科目分开）。
    """
    text = (body.text or '').strip()
    if len(text) < 10:
        raise HTTPException(400, '正文太短')
    want = {str(x) for x in (body.ids or [])}
    if not want:
        raise HTTPException(400, '没有勾选任何卡（ids 为空）')
    try:
        r = importer.parse_qa(text, body.fmt, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(400, str(e))
    by_id = {c['id']: c for c in r['cards']}
    picked = [by_id[i] for i in want if i in by_id]
    missing = len(want) - len(picked)
    if not picked:
        raise HTTPException(400, '勾选的 id 一张都对不上（文本是不是换过了？）')
    picked = picked[:500]
    importer.save_drafts(picked)
    return {'ok': True, 'count': len(picked), 'missing': missing,
            'drafts': picked}


@router.delete('/drafts', summary='清空全部草稿')
def clear_drafts(user=Depends(current_user)):
    importer.clear_drafts()
    return {'ok': True}


# 这条必须写在 /drafts/{did} 之前吗？不必须 —— 方法不同（POST vs PUT/DELETE），
# 不会互相吃掉。但放在前面读起来更顺。
@router.post('/drafts/publish', summary='草稿入库成为正式卡')
def publish_draft(body: PublishIn, user=Depends(current_user)):
    r = importer.publish(body.id)
    if not r.get('ok'):
        raise HTTPException(400, r['msg'])
    return r


@router.put('/drafts/{did}', summary='补齐草稿字段')
def update_draft(did: str, body: DraftPatch, user=Depends(current_user)):
    patch = body.model_dump(exclude_unset=True)
    drafts = importer.list_drafts()
    for i, d in enumerate(drafts):
        if d.get('id') == did:
            d.update(patch)
            d['id'] = did
            drafts[i] = d
            db.save_drafts(drafts)
            return {'ok': True, 'draft': d}
    raise HTTPException(404, '草稿不存在')


@router.delete('/drafts/{did}', summary='丢弃草稿')
def drop_draft(did: str, user=Depends(current_user)):
    importer.drop_draft(did)
    return {'ok': True}
