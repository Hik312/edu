# -*- coding: utf-8 -*-
"""整份文档导入：md / txt / pdf / docx → 自动分章 → 逐章阅读（可再调 AI 精读）。

和「卡片」是两回事：卡片是复述用的最小单元，文档是原始资料。
先把资料整份装进来能看能查，比一上来就逼人切卡现实得多。
"""
import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import db
import importer
from ..schemas import DocImportIn

router = APIRouter(prefix='/api', tags=['文档'])


@router.get('/docs', summary='文档列表（轻字段）')
def list_docs(category: Optional[str] = Query(None),
              subject: Optional[str] = Query(None)):
    docs = db.load_docs()
    if category:
        docs = [d for d in docs if d.get('category') == category]
    if subject:
        docs = [d for d in docs if d.get('subject') == subject]
    # 列表不带 chapters：一份八股文几十章，全带上列表接口就废了
    brief = [{'id': d.get('id'), 'title': d.get('title'),
              'category': d.get('category'), 'subject': d.get('subject'),
              'source': d.get('source'), 'createdAt': d.get('createdAt'),
              'stats': d.get('stats'),
              'aiDone': d.get('aiDone') or 0,
              'aiTotal': d.get('aiTotal') or len(d.get('chapters') or [])}
             for d in docs]
    brief.sort(key=lambda x: (x.get('createdAt') or ''), reverse=True)
    return {'ok': True, 'total': len(brief), 'docs': brief}


@router.get('/docs/{did}', summary='文档详情（含全部章节）')
def get_doc(did: str):
    d = next((x for x in db.load_docs() if x.get('id') == did), None)
    if not d:
        raise HTTPException(404, '文档不存在')
    return {'ok': True, 'doc': d}


@router.delete('/docs/{did}', summary='删除文档')
def delete_doc(did: str):
    return {'ok': db.delete_doc(did)}


@router.post('/import/doc', summary='导入整份文档')
def import_doc(body: DocImportIn):
    """`text` 与 `dataB64` 二选一：

    - 粘贴 md / txt → 传 `text`
    - 选文件 → 前端读成 base64 传 `dataB64`（PDF 走可选依赖 pypdf，
      Word 走标准库解析的 importer.extract_docx_bytes）

    PDF 之所以要 base64 而不是 multipart：前端是纯静态页，不引上传库，
    FileReader 一把梭最省事；16MB 上限也是为它放宽的。
    """
    data = body.model_dump(exclude_none=True)
    text = (body.text or '').strip()
    fname = body.filename or ''

    if not text and body.dataB64:
        try:
            raw = base64.b64decode(body.dataB64)
        except Exception:
            raise HTTPException(400, '文件解码失败')
        # 后缀看不出 PDF 就看文件头 —— 有人会把 pdf 存成 .txt
        if fname.lower().endswith('.pdf') or raw[:4] == b'%PDF':
            try:
                text = importer.extract_pdf_bytes(raw)
            except RuntimeError as e:
                if str(e) == 'no_pypdf':
                    # 给路，不只是报错：扫描版 PDF 本来也抽不出文字
                    raise HTTPException(400, 'PDF 解析需要 pypdf：pip install pypdf'
                                             '（或把文档存成 md/txt，或复制文字粘贴导入）')
                raise
        elif fname.lower().endswith('.doc'):
            # 老 .doc 是 OLE 二进制，读不了 —— 明确给路，别让它掉进 utf-8
            # 解码出一堆乱码，然后报「没提到有效文字」这种驴唇不对马嘴的错
            raise HTTPException(400, '老版 .doc 读不了：用 Word「另存为」选 .docx 再上传')
        elif fname.lower().endswith('.docx') or raw[:4] == b'PK\x03\x04':
            # PK 魔数兜底：有人传 .docx 但后缀改成了别的
            try:
                text = importer.extract_docx_bytes(raw)
            except RuntimeError:
                raise HTTPException(400, '这份 Word 解析失败：只支持 .docx'
                                         '（xlsx / 老 .doc 不行，把文字粘贴进来也行）')
        else:
            text = raw.decode('utf-8', 'ignore')

    text = (text or '').strip()
    if len(text) < 20:
        raise HTTPException(400, '没提到有效文字（扫描版 PDF 需要先 OCR）')

    doc = importer.parse_document(text, dict(data, filename=fname))
    doc['category'] = body.category or ''
    doc['subject'] = body.subject or ''
    doc['domain'] = body.domain or ''
    doc['source'] = fname
    return {'ok': True, 'doc': db.upsert_doc(doc)}
