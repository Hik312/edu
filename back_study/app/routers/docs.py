# -*- coding: utf-8 -*-
"""整份文档导入：md / txt / pdf / docx → 自动分章 → 逐章阅读（可再调 AI 精读）。

和「卡片」是两回事：卡片是复述用的最小单元，文档是原始资料。
先把资料整份装进来能看能查，比一上来就逼人切卡现实得多。
"""
import base64
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse

import db
import docparse
import importer
from ..deps import current_user
from ..schemas import DocImportIn

router = APIRouter(prefix='/api', tags=['文档'])

# ★ 文档是**个人资料**：4 个端点全部要求登录。
# 它们曾经匿名可访问，而 CORS 又是通配 —— 跨源网页能读走你导入的全部资料，
# 还能 DELETE 掉。详见 notes.py 顶上那段说明。


@router.get('/docs', summary='文档列表（轻字段）')
def list_docs(category: Optional[str] = Query(None),
              subject: Optional[str] = Query(None),
              user=Depends(current_user)):
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
def get_doc(did: str, user=Depends(current_user)):
    d = next((x for x in db.load_docs() if x.get('id') == did), None)
    if not d:
        raise HTTPException(404, '文档不存在')
    return {'ok': True, 'doc': d}


@router.delete('/docs/{did}', summary='删除文档')
def delete_doc(did: str, user=Depends(current_user)):
    ok = db.delete_doc(did)
    docparse.delete_media(did)          # 图片和文档同生命周期（卡片的图不在这，
    return {'ok': ok}                   # 转卡时拷进了 card-<id> 目录）


@router.get('/media/{owner}/{name}', summary='读图片（文档 / 卡片）')
def get_media(owner: str, name: str,
              t: Optional[str] = Query(None, description='token（<img> 发不了 Authorization 头）'),
              authorization: str = Header(None)):
    """登录后可读。鉴权复用 current_user —— 只是把取 token 的地方放宽到
    `?t=`：页面里 `<img src="/api/media/...">` 浏览器不会带 Authorization 头，
    逐张 fetch 转 blob 又要处理一大堆加载状态，不值。

    owner/name 的路径穿越在 docparse.media_path 里挡（只放行 SAFE_NAME）。"""
    auth = authorization or (('Bearer ' + t) if t else None)
    current_user(authorization=auth)            # 没登录 → 401，同其它文档端点
    p = docparse.media_path(owner, name)
    if not p:
        raise HTTPException(404, '图片不存在')
    return FileResponse(p, media_type=docparse.mime_of(name))


@router.post('/import/doc', summary='导入整份文档')
def import_doc(body: DocImportIn, user=Depends(current_user)):
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
    media = []

    if not text and body.dataB64:
        try:
            raw = base64.b64decode(body.dataB64)
        except Exception:
            raise HTTPException(400, '文件解码失败')
        low = fname.lower()
        # 老 .doc 是 OLE 二进制，读不了 —— 明确给路，别让它掉进 utf-8
        # 解码出一堆乱码，然后报「没提到有效文字」这种驴唇不对马嘴的错
        if low.endswith('.doc') and not low.endswith('.docx'):
            raise HTTPException(400, '老版 .doc 读不了：用 Word「另存为」选 .docx 再上传')
        try:
            # 统一走 docparse：pdf/docx 抽文字并抠图（按原文顺序插占位符），
            # 其它后缀当纯文本（有人把 pdf 存成 .txt，docparse 看文件头兜底）
            out = docparse.extract(raw, fname)
        except RuntimeError as e:
            code = str(e)
            if code == 'no_pypdf':
                # 给路，不只是报错：扫描版 PDF 本来也抽不出文字
                raise HTTPException(400, 'PDF 解析需要 pypdf：pip install pypdf'
                                         '（或把文档存成 md/txt，或复制文字粘贴导入）')
            if code == 'no_docx':
                raise HTTPException(400, '这份 Word 解析失败：只支持 .docx'
                                         '（xlsx / 老 .doc 不行，把文字粘贴进来也行）')
            raise HTTPException(400, '文件解析失败，把文字粘贴进来也行')
        text = out['text']
        media = out['media']

    text = (text or '').strip()
    if len(text) < 20:
        raise HTTPException(400, '没提到有效文字（扫描版 PDF 需要先 OCR）')

    doc = importer.parse_document(text, dict(data, filename=fname))
    doc['category'] = body.category or ''
    doc['subject'] = body.subject or ''
    doc['domain'] = body.domain or ''
    doc['source'] = fname
    doc = db.upsert_doc(doc)
    # 图片在拿到 doc id 之后才落盘 → data/store/media/<docId>/。
    # 正文里的 `![](media:x)` 占位就是靠这个目录显示出来的（GET /api/media/…）
    if media:
        docparse.save_media(doc['id'], media)
    return {'ok': True, 'doc': doc}
