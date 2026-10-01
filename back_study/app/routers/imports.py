# -*- coding: utf-8 -*-
"""导入：粘贴文本 → 切分成草稿卡；草稿补齐字段后入库。

草稿是个「缓冲区」不是「卡」：机器切的字段永远差口气（尤其是 scene —— 必须写
你项目里真实用在哪，编不出来），所以强制人工过一道再入库。
"""
import sys

from fastapi import APIRouter, Depends, HTTPException

import db
import importer
import llm
from ..deps import current_user
from ..schemas import DraftPatch, ImportTextIn, PublishIn

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
