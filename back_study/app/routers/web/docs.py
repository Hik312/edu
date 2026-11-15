# -*- coding: utf-8 -*-
"""整份文档导入：md / txt / pdf / docx → 自动分章 → 逐章阅读（可再调 AI 精读）。

和「卡片」是两回事：卡片是复述用的最小单元，文档是原始资料。
先把资料整份装进来能看能查，比一上来就逼人切卡现实得多。
"""
import base64
import os
import sys
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

import db
import docparse
import docqa
import importer
import classifier
import kbtree
import llm
import pdfmarkup
import transjob
from ...deps import current_user
from ...sse import sse_json_stream
from ...schemas import DocImportIn, DocRenameIn, FolderIn, FolderPatchIn, \
    MoveFolderIn, DocPlaceIn, DocAskIn, GlossaryIn, TranslateIn, \
    QaFeedbackIn, FigureCaptionIn

router = APIRouter(prefix='/api', tags=['文档'])

# ★ 文档是**个人资料**：4 个端点全部要求登录。
# 它们曾经匿名可访问，而 CORS 又是通配 —— 跨源网页能读走你导入的全部资料，
# 还能 DELETE 掉。详见 notes.py 顶上那段说明。


def _raw_state(d):
    """库里的 rawFile 是否**真能在磁盘上找到** → (可用的 rawFile, 是否丢失)。

    data/store/files/ 是本地目录（data/ 不入 git），清理仓库、换机器、只恢复
    数据库都会留下「rawFile 有值、文件却没了」的孤儿记录。原样把 rawFile 交给
    前端，只会换来 PDF 阅读器里一句「HTTP 404 / 打不开这份 PDF」，而这份文档
    其实还有抽取文本可用。

    ★ 所以这里做一次落地校验：文件不在就把 rawFile 收成空串，知识库会自然
      退回文本视图；同时带 rawMissing=True，让界面能说明「原件丢了，这是文本版」。
      只改响应、不改库 —— 文件恢复后 rawFile 自动重新生效。
    """
    raw = (d.get('rawFile') or '').strip()
    if not raw:
        return '', False
    ext = os.path.splitext(raw)[1]
    if docparse.raw_path(d.get('id'), ext):
        return raw, False
    return '', True


@router.get('/docs', summary='文档列表（轻字段）')
def list_docs(category: Optional[str] = Query(None),
              subject: Optional[str] = Query(None),
              user=Depends(current_user)):
    # ★ 用 brief 而不是 load_docs()：后者是全量读（含每篇论文的 chapters+text，
    #   MySQL 下 doc_text 是 MEDIUMTEXT），而这个接口只用到 11 个短字段。
    docs = db.load_docs_brief()
    if category:
        docs = [d for d in docs if d.get('category') == category]
    if subject:
        docs = [d for d in docs if d.get('subject') == subject]
    # 列表不带 chapters：一份八股文几十章，全带上列表接口就废了
    # 但分类字段（domain/tags/rawFile）必须带 —— 知识库页面靠它们做分类树和原件标记
    brief = []
    for d in docs:
        raw_file, raw_missing = _raw_state(d)
        brief.append({
            'id': d.get('id'), 'title': d.get('title'),
            'category': d.get('category'), 'subject': d.get('subject'),
            'domain': d.get('domain') or '',
            'tags': d.get('tags') or [],
            'rawFile': raw_file,
            'rawMissing': raw_missing,
            'isPaper': d.get('isPaper') is True,
            'source': d.get('source'), 'createdAt': d.get('createdAt'),
            'stats': d.get('stats'),
            'aiDone': d.get('aiDone') or 0,
            # ★ brief 行**没有 chapters**（那正是我们要省掉的大字段），
            #   所以不能再用 len(chapters) 兜底 —— 那会让论文的
            #   「N 章 · M 字」恒显示 0 章。改用 stats.chapters 兜，
            #   它是导入时 importer 算好存下来的轻字段。
            'aiTotal': (d.get('aiTotal')
                        or (d.get('stats') or {}).get('chapters')
                        or 0)
        })
    brief.sort(key=lambda x: (x.get('createdAt') or ''), reverse=True)
    return {'ok': True, 'total': len(brief), 'docs': brief}


@router.get('/docs/{did}', summary='文档详情（含全部章节）')
def get_doc(did: str, user=Depends(current_user)):
    # WHERE id=%s 走主键索引；别再写全量读回来线性扫（那是 O(N)，
    # 而且每篇论文的全文都会被读进内存）。
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    # 拷一份再改响应：JSON 后端可能把同一份对象缓存在内存里，
    # 原地清空 rawFile 会把库里的相对路径也一起抹掉。
    d = dict(d)
    raw_before = d.get('rawFile') or ''
    d['rawFile'], d['rawMissing'] = _raw_state(d)
    if d['rawMissing']:
        sys.stderr.write('[docs] 原件缺失，退回文本视图：%s（rawFile=%s）\n'
                         % (did, raw_before))
    return {'ok': True, 'doc': d}


@router.put('/docs/{did}', summary='重命名文档（= 卡片组名，级联刷卡/草稿的 deck）')
def rename_doc(did: str, body: DocRenameIn, user=Depends(current_user)):
    """卡片组没有独立的表：组名就是文档标题，deck 是抄在每张卡上的冗余。
    db.rename_deck 负责三处一起改（文档 + 自定义卡 + 草稿）。"""
    r = db.rename_deck(did, body.title)
    if r is None:
        raise HTTPException(404, '文档不存在')
    if not r.get('ok'):
        raise HTTPException(400, r.get('msg') or '改名失败')
    return r


@router.delete('/docs/{did}', summary='删除文档')
def delete_doc(did: str, user=Depends(current_user)):
    ok = db.delete_doc(did)
    docparse.delete_media(did)          # 图片和文档同生命周期（卡片的图不在这，
    docparse.delete_raw(did)            # 原始文件一起清
    docparse.delete_blocks(did)         # 块侧车也是派生数据，一起清
    # ★ 还要把树里的引用摘掉。树存在 meta 里，和 documents 是**两个存储**，
    #   删文档不会自动清树 —— 留下的死 id 界面上看不见（按 id 查不到文档），
    #   但库里已经不一致了。见 kbtree.drop_doc 的说明。
    t = kbtree.load(db.backend())
    if kbtree.drop_doc(t, did).get('removed'):
        kbtree.save(db.backend(), t)
    return {'ok': ok}                   # 转卡时拷进了 card-<id> 目录）


@router.get('/knowledge/file/{did}', summary='原始文件流式读取（知识库在线预览）')
def get_knowledge_file(did: str,
                       t: Optional[str] = Query(None, description='token（<img>/iframe 发不了 Authorization 头）'),
                       authorization: str = Header(None)):
    """登录后可读原始文件字节。鉴权复用 current_user —— 只是把取 token 的地方放宽到
    `?t=`：PDF 预览用 iframe 加载，浏览器不会带 Authorization 头。"""
    auth = authorization or (('Bearer ' + t) if t else None)
    current_user(authorization=auth)
    # ★ 这里只要 rawFile 一列，用 brief 而不是 doc_get：后者 SELECT * 会把
    #   这篇论文的 chapters+text 一起拉进内存，只为算一个后缀名，不划算。
    d = next((x for x in db.load_docs_brief() if x.get('id') == did), None)
    if not d:
        raise HTTPException(404, '文档不存在')
    raw_file = d.get('rawFile') or ''
    if not raw_file:
        # 纯文本导入本来就没有原件 —— 这不是错误，是这类文档的正常状态
        return JSONResponse(status_code=404, content={
            'ok': False, 'code': 'no_original', 'did': did,
            'msg': '这份文档是纯文本导入，没有原始文件；正文请看文本视图。'
        })
    ext = os.path.splitext(raw_file)[1]
    path = docparse.raw_path(did, ext)
    if not path:
        # ★ 2026-11-02 定位：库里 rawFile 有值、data/store/files/ 下却没有文件
        #   （清理仓库 / 换机器时最容易发生）。原来这里和「纯文本导入」共用一句
        #   404，前端只能显示「打不开这份 PDF」，完全看不出是文件丢了。
        #   改成 410 + 可读原因，并把抽取文本是否还在告诉前端，能自动退回文本版。
        sys.stderr.write('[docs] 原件缺失：%s → %s（data/store/files 下找不到）\n'
                         % (did, raw_file))
        return JSONResponse(status_code=410, content={
            'ok': False, 'code': 'raw_missing', 'did': did,
            'rawFile': raw_file,
            'hasText': bool((d.get('stats') or {}).get('chars')),
            'msg': '原始文件已丢失，原件预览打不开；已抽取的文本还在，可看文本版。',
            'hint': '把原文件重新导入，或恢复到 data/store/files/%s/ 后即可恢复原件预览。'
                    % did
        })
    resp = FileResponse(path, media_type=docparse.raw_mime(path))
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp


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


#: 论文特征词（文件名/首页）。命中任意一个就按「只存原件」处理。
#: 判据刻意保守 —— 误判成论文会让正经技术文档失去分章和全文搜索，
#: 漏判只是走原来的文本路线，不会把资料弄坏。
_PAPER_HINTS = (
    'arxiv', 'paper', 'proceeding', 'conference', 'journal', 'ieee', 'acm',
    'springer', 'elsevier', 'preprint', '预印本', '论文', '学报', '期刊', '会议录',
)
#: 论文首页几乎必然出现的版面标志。**这些词单独出现不能判定** ——
#: 技术博客写 Introduction 也很常见。它们的价值在于**和文件名/其它标志共现**。
_PAPER_STRUCTURE = (
    'abstract', 'introduction', 'related work', 'references',
    'keywords', 'doi:', 'arxiv:', 'et al.', 'fig. ', 'table ',
)


def _looks_like_paper(filename, text):
    """这份 PDF 是不是论文。

    ★ 为什么不能只看文件名：实测一份论文叫 `AutoGen.pdf`，词表里根本没有
      「autogen」。论文标题千变万化，穷举词表注定漏。

    ★ 也不能只看正文特征词：技术博客 / 教程也会有 Abstract、Introduction。

    所以用**组合信号**：文件名命中强特征词，或者首页同时出现多个版面标志
    （如 abstract + references）。单个标志不算，避免把技术文档误判成论文 ——
    误判的代价高：论文路线只存原件不分章，一份正经技术讲义被判成论文
    就失去了全文搜索和 AI 精读能力。
    """
    name = (filename or '').lower()
    if any(h in name for h in _PAPER_HINTS):
        return True
    head = (text or '')[:2500].lower()
    hits = sum(1 for h in _PAPER_STRUCTURE if h in head)
    # 3 个以上版面标志共现，基本只有论文/正式报告会有
    return hits >= 3


#: 导入弹窗提供的三个类型。前两个差别在**怎么显示**（原件优先 vs 文档视图
#: +目录），笔记走和资料一样的路线，只是分类固定，不必再让分类器猜。
DOC_TYPES = ('资料', '论文', '笔记')


def _save_original_only(body, raw_bytes, raw_ext, fname, text='', blocks=None,
                        media=None):
    """论文走这条路：存 PDF 原件做阅读版，**同时**留一份纯文本供检索。

    页面用 iframe 显示原件（浏览器自带阅读器，版面/公式/图表/双栏都准），
    这正是飞书「上传文件以原格式保存」的做法。

    ★ 2026-10-11 改了语义：以前 `text` 刻意留空（「论文的价值在于原样阅读」）。
      但那等于**把论文排除在全文检索和 RAG 之外** —— 用户导入论文正是为了
      「以后能问它」，不让检索等于白导入。双栏抽取的文本确实不适合阅读，
      所以做法是**原件与检索文本分离**：阅读永远走 iframe，抽出来的文本只
      供搜索/RAG，前端不拿它当正文渲染。

    ★ 2026-11-15 补 save_media（评测 VLM 链路时抓到的存量洞）：blocks 里的
      figure 块带 `![](media:...)` token，双语对照页和翻译都要按它渲染原图，
      但这条路线以前只存 raw+blocks、**媒体文件从来没落过盘** ——
      media/ 目录整个是空的，图片 404、VLM 解读找不到文件。multipart
      路线（:399）一直是存的，只有 base64 论文路线漏了。
    """
    doc = {
        'title': (body.title or os.path.splitext(fname or '')[0] or '未命名论文').strip()[:120],
        'source': fname,
        'category': body.category or '论文',
        'subject': body.subject or '',
        'domain': body.domain or '',
        'tags': [],
        'isPaper': True,
        'chapters': [],
        'stats': {'chapters': 0, 'chars': len(text or ''), 'headings': 0},
        'aiDone': 0,
        'aiTotal': 0,
        'text': (text or '')[:400000],
    }
    doc['id'] = db._next_daily_id('doc', db.load_docs_brief())
    doc['rawFile'] = docparse.save_raw(doc['id'], raw_bytes, raw_ext)
    if not doc['rawFile']:
        raise HTTPException(500, '原件保存失败，检查 data/store/files 目录是否可写')
    if media:
        docparse.save_media(doc['id'], media)
    if blocks:
        docparse.save_blocks(doc['id'], blocks)
    return {'ok': True, 'doc': db.upsert_doc(doc), 'paper': True}


@router.post('/import/doc', summary='导入整份文档')
def import_doc(body: DocImportIn, user=Depends(current_user)):
    """`text` 与 `dataB64` 二选一：

     - 粘贴 md / txt → 传 `text`
     - 选文件 → 前端读成 base64 传 `dataB64`（PDF 走可选依赖 pypdf，
       Word 走标准库解析的 importer.extract_docx_bytes）

    PDF 之所以要 base64 而不是 multipart：前端是纯静态页，不引上传库，
    FileReader 一把梭最省事；16MB 上限也是为它放宽的。

    导入时同步做三件事：
      1. 原始文件存进 data/store/files/<docId>/ 供知识库在线预览
      2. 自动分类（规则+LLM）写入 category/domain/tags
      3. `docType`（资料/论文/笔记）决定路线 —— 见下

    ★ 类型判定：**用户手动选的优先**，没选才走 `_looks_like_paper` 自动判断。
      自动判据只认文件名和版面词（arxiv/paper/abstract…），中文论文和
      改过名的 PDF 一律漏判 —— 而漏判的代价不是「多分了章」，而是
      **论文被显示成读不懂的抽取文本，用户看不到原版**。
      论文路线：存原件给 iframe 读，不分章；抽出的文本只进 `text` 供检索/RAG。
    """
    data = body.model_dump(exclude_none=True)
    text = (body.text or '').strip()
    fname = body.filename or ''
    media = []
    raw_bytes = b''
    raw_ext = ''
    # ★ 和下面 doc_type 同一个坑：blocks 只在 `if not text and body.dataB64:`
    #   分支里赋值，纯文本导入走不到，必须在这里给初值 —— 否则下面
    #   `if blocks:` 抛 UnboundLocalError，粘贴文本导入整条 500。
    blocks = None

    # ★ 类型必须在**函数开头**定，不能放在 `if body.dataB64:` 里。
    #   纯文本导入（粘贴 md / 笔记）走不到那个分支，doc_type 会是未定义局部变量
    #   → 下面 `doc['category'] = ... doc_type` 抛 UnboundLocalError → 整个接口 500。
    #   症状是「上传文件正常，粘贴文本全挂」，非常容易误判成两条路本来就不通。
    #   不给或给错值都归auto（自动判断）。
    doc_type = (body.docType or 'auto').strip()
    if doc_type not in DOC_TYPES:
        doc_type = 'auto'

    if not text and body.dataB64:
        try:
            raw_bytes = base64.b64decode(body.dataB64)
        except Exception:
            raise HTTPException(400, '文件解码失败')
        if len(raw_bytes) > docparse.MAX_UPLOAD_BYTES:
            raise HTTPException(400, '文件超过 %dMB，先拆小一点'
                                % (docparse.MAX_UPLOAD_BYTES >> 20))
        low = fname.lower()
        raw_ext = os.path.splitext(low)[1] if '.' in low else ''
        # 老 .doc 是 OLE 二进制，读不了 —— 明确给路，别让它掉进 utf-8
        # 解码出一堆乱码，然后报「没提到有效文字」这种驴唇不对马嘴的错
        if low.endswith('.doc') and not low.endswith('.docx'):
            raise HTTPException(400, '老版 .doc 读不了：用 Word「另存为」选 .docx 再上传')
        try:
            # 统一走 docparse：pdf/docx 抽文字并抠图（按原文顺序插占位符），
            # 其它后缀当纯文本（有人把 pdf 存成 .txt，docparse 看文件头兜底）
            out = docparse.extract(raw_bytes, fname)
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
        blocks = out.get('blocks')
        # 论文分流判定（说明见下方 DOC_TYPES 处）。纯文本导入没这段，
        # 但 doc_type 在函数开头就定好了，两条路共用同一个值。
        is_paper = (doc_type == '论文') or (doc_type == 'auto'
                                           and raw_ext == '.pdf'
                                           and _looks_like_paper(fname, text))
        if is_paper:
            return _save_original_only(body, raw_bytes, raw_ext, fname,
                                       text=text, blocks=blocks, media=media)

        # PDF/Word 的纯文本层没有版面：代码不带围栏、页码混进正文、
        # 标题只是一行普通字。靠 pdfmarkup 把结构找回来（认代码块、
        # 剔页码、按「一、」「1.」这类序号推断标题层级）。
        # md/txt 走 else 分支（本来就有 markdown），不要碰。
        if raw_ext in ('.pdf', '.docx'):
            text = pdfmarkup.annotate_headings(text)

    text = (text or '').strip()
    if len(text) < 20:
        raise HTTPException(400, '没提到有效文字（扫描版 PDF 需要先 OCR）')

    doc = importer.parse_document(text, dict(data, filename=fname))
    # ★ 用户选的类型即最终分类，分类器**不再覆盖**。
    #   「资料/论文/笔记」是用户对这份东西的判断，比关键词规则准；
    #   分类器接着跑只是补 domain 和 tags。
    doc['category'] = body.category or (doc_type if doc_type != 'auto' else '')
    doc['subject'] = body.subject or ''
    doc['domain'] = body.domain or ''
    doc['isPaper'] = False
    doc['source'] = fname
    # ★ 原文留档。知识库渲染 md/txt 走的是这份，不是 chapters 拼的 ——
    #   拼章节会丢标题、切断代码块（分章本来就把代码里的 # comment 当标题），
    #   图片占位也渲染不出来。原件渲染才是「原样」。
    doc['text'] = text[:400000]

    cls = classifier.classify_doc(doc['title'], text, fname)
    if not doc['category']:
        doc['category'] = cls['category']
    if not doc['domain']:
        doc['domain'] = cls['domain']
    doc['tags'] = cls['tags']

    # 先拿到 docId 再一次存全，避免两次 upsert 的数据不一致窗口
    doc['id'] = db._next_daily_id('doc', db.load_docs_brief())
    if raw_bytes:
        doc['rawFile'] = docparse.save_raw(doc['id'], raw_bytes, raw_ext)
    if media:
        docparse.save_media(doc['id'], media)
    if blocks:
        docparse.save_blocks(doc['id'], blocks)
    doc = db.upsert_doc(doc)
    return {'ok': True, 'doc': doc}


# ------------------------------------------------------------------
# 文件夹树（PyCharm 式自建目录）
# ------------------------------------------------------------------
# ★ 设计要点：
#   1. 整棵树是单例状态，存 meta.kb_tree 一行，不是每份文档存一份。
#   2. 树节点只存**文档 id**，不存标题 —— 标题会改，id 不会。
#   3. category/domain 降级成纯数据（仍入库、仍可搜），**不再驱动界面**。
#   4. 所有写操作都是「读-改-整棵写回」。树是单例、几KB 而已，
#      没有并发编辑场景（单人单机），不值得为它引乐观锁。
#   5. 拖拽可能造环（把父拖进自己孩子），必须在**写入前**判 —— 见 kbtree。
#   6. 每次响应都回传整棵 tree：前端不用二次请求就能立刻刷新，
#      也避免了「前端本地树」和「库里真树」两份状态不一致（移动端最容易出）。
# ------------------------------------------------------------------

@router.get('/kb/tree', summary='文件夹树')
def kb_tree(user=Depends(current_user)):
    return {'ok': True, 'tree': kbtree.load(db.backend())}


@router.post('/kb/tree/folder', summary='新建文件夹')
def kb_add_folder(body: FolderIn, user=Depends(current_user)):
    t = kbtree.load(db.backend())
    r = kbtree.add_folder(t, body.parentId, body.name)
    if not r.get('ok'):
        raise HTTPException(400, r.get('msg') or '新建失败')
    kbtree.save(db.backend(), t)
    return {'ok': True, 'node': r['node'], 'tree': t}


@router.put('/kb/tree/folder/{fid}', summary='重命名 / 改折叠状态')
def kb_patch_folder(fid: str, body: FolderPatchIn, user=Depends(current_user)):
    t = kbtree.load(db.backend())
    if body.collapsed is not None:
        r = kbtree.set_collapsed(t, fid, body.collapsed)
    else:
        r = kbtree.rename_folder(t, fid, body.name or '')
    if not r.get('ok'):
        raise HTTPException(400, r.get('msg') or '操作失败')
    kbtree.save(db.backend(), t)
    return {'ok': True, 'tree': t}


@router.delete('/kb/tree/folder/{fid}', summary='删文件夹')
def kb_del_folder(fid: str,
                  mode: str = Query('doc2root',
                                    description='doc2root=文档挪到根 / delete=文档留原地'),
                  user=Depends(current_user)):
    t = kbtree.load(db.backend())
    r = kbtree.delete_folder(t, fid, mode)
    if not r.get('ok'):
        raise HTTPException(400, r.get('msg') or '删除失败')
    kbtree.save(db.backend(), t)
    return {'ok': True, 'moved': r.get('moved') or [], 'tree': t}


@router.post('/kb/tree/move', summary='移动文件夹')
def kb_move_folder(body: MoveFolderIn, user=Depends(current_user)):
    t = kbtree.load(db.backend())
    r = kbtree.move_folder(t, body.id, body.parentId)
    if not r.get('ok'):
        raise HTTPException(400, r.get('msg') or '移动失败')
    kbtree.save(db.backend(), t)
    return {'ok': True, 'tree': t}


@router.post('/kb/tree/docs', summary='把文档放进文件夹（多选=同时属于多个）')
def kb_put_docs(body: DocPlaceIn, user=Depends(current_user)):
    t = kbtree.load(db.backend())
    r = kbtree.put_docs(t, body.docId, body.folderIds)
    if not r.get('ok'):
        raise HTTPException(400, '设置失败')
    kbtree.save(db.backend(), t)
    return {'ok': True, 'tree': t}


@router.post('/docs/{did}/move', summary='直接移动文档到某文件夹')
def kb_move_doc(did: str, body: DocPlaceIn, user=Depends(current_user)):
    """比 kb_put_docs 顺手：路径参数已经给了 docId，前端不用再重复传一遍。"""
    if not db.get_doc(did):
        raise HTTPException(404, '文档不存在')
    t = kbtree.load(db.backend())
    r = kbtree.put_docs(t, did, body.folderIds)
    kbtree.save(db.backend(), t)
    return {'ok': True, 'tree': t}


@router.post('/docs/{did}/reparse', summary='重新解析（补跑代码块/标题结构化）')
def reparse_doc(did: str, user=Depends(current_user)):
    """拿已存的**原始文件**重跑一遍解析，覆盖 text / chapters / 分类。

    ★ 为什么需要它：`pdfmarkup`（认代码块、按序号推标题层级）是后加的，
      在它之前导入的 PDF 存的 text 是**未加工的裸文本** —— 代码没围栏、
      标题没标记，只能重新导入才能用上。重新导入会换新 id、丢章节进度，
      而这里能就地修好同一份文档。
    """
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    ext = os.path.splitext(d.get('rawFile') or '')[1]
    path = docparse.raw_path(did, ext)
    if not path:
        raise HTTPException(400, '这份文档没有留原始文件（纯文本导入的），请重新导入')
    with open(path, 'rb') as f:
        blob = f.read()
    try:
        out = docparse.extract(blob, os.path.basename(path))
    except RuntimeError as e:
        raise HTTPException(400, '解析失败：%s' % (str(e) or '未知错误'))
    text = pdfmarkup.annotate_headings(out['text'])
    if len(text.strip()) < 20:
        raise HTTPException(400, '这次没抽出有效文字')

    parsed = importer.parse_document(text, {'filename': d.get('source')})
    d['title'] = parsed['title'] or d.get('title')
    d['chapters'] = parsed['chapters']
    d['stats'] = parsed['stats']
    d['text'] = text[:400000]
    d['aiDone'] = 0
    d['aiTotal'] = len(parsed['chapters'])
    if not d.get('category') or not d.get('domain'):
        cls = classifier.classify_doc(d['title'], text, d.get('source') or '')
        d['category'] = d.get('category') or cls['category']
        d['domain'] = d.get('domain') or cls['domain']
        d['tags'] = d.get('tags') or cls['tags']
    return {'ok': True, 'doc': db.upsert_doc(d)}


# ------------------------------------------------------------------
# 文档问答（右下角「AI 问答」）
# ------------------------------------------------------------------
# SSE 帧约定（和 /api/agent/ask 保持一致，前端同一套解析器）：
#     event: sources = 命中的片段序号（data 是 JSON 数组），发在 done 之前
#     data: <文本增量>= 正文，换行转义成 \n
#     event: done    = 正文结束
#     event: error   = 出错，data 是人话原因
#
# ★ 为什么要自己发 sources 而不是让模型报「第几节」：
#   模型报的节号是**它数出来的**，偶尔会数错；这里直接把检索层
#   实际用的片段序号给前端，用户能对着原文核对。
@router.post('/docs/{did}/ask', summary='就这份文档提问（SSE 流式）')
def ask_doc(did: str, body: DocAskIn, user=Depends(current_user)):
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    q = (body.question or '').strip()
    if not q:
        raise HTTPException(400, '问题不能为空')

    # ★ 自进化记忆：先查相似历史问答，作为「记忆参考」注入提示词
    #   （只复用被认可过的；被踩的不会进来）。第一次问这份文档时这里是空的，
    #   问得越多、被认可的答案越多，后续相似问题越准 —— 这就是 self-evolving。
    memory = docqa.similar_qa(did, q)

    try:
        msgs, used = docqa.build_messages(d, q, body.history, memory=memory)
    except Exception as e:
        raise HTTPException(500, '检索失败：%s' % e)

    #★ AI 关掉时要在这里挡一次，别把「连接建立成功但永远没有下一个帧」
    #   丢给前端 —— 那表现为按钮一直转圈、没有任何提示，
    #   看起来像功能坏了，而不是像「这个功能没开」。
    if llm.AI_OFF or not llm.list_models():
        raise HTTPException(503, 'AI 没开（环境变量 AI=off，或本机没起 Ollama）')

    # SSE 的「后台线程 + 队列转发」抽到了 app/sse.py ——
    # 翻译端点需要同一套结构（那边一段要 3~8 秒，帧更稀疏）。
    # 复制两份的风险不是「重复代码」，而是两份的心跳/收尾不一致，
    # 症状是「翻译挂住不动」而日志干净。
    def worker(emit):
        emit('event: sources', used)
        buf = []
        try:
            llm.stream_chat(msgs, on_token=lambda p: (buf.append(p), emit('data', p)),
                            model=body.model, temperature=0.25, max_tokens=800)
        except Exception as e:
            emit('event: error', str(e).replace('\n', ' '))
        emit('event: done', '')
        # ★ 回答结束后落盘记忆（自进化）：即使模型答得弱也存，
        #   因为相似问题再来时会作为候选被复用；用户点 👎 才会把它从复用里摘掉。
        ans = ''.join(buf).strip()
        if ans:
            docqa.log_qa(did, {'question': q, 'answer': ans,
                               'sources': used, 'feedback': None,
                               'ts': time.time()})

    return sse_json_stream(worker)


# ------------------------------------------------------------------
# 问答反馈（自进化 RAG 的纠错入口）+ 论文图片图注
# ------------------------------------------------------------------

@router.post('/docs/{did}/qa/feedback', summary='问答反馈（👍/👎，驱动自进化）')
def qa_feedback(did: str, body: QaFeedbackIn, user=Depends(current_user)):
    """给一条问答打反馈。

    ★ good=False 的历史以后不会再被 similar_qa 复用 —— 记忆会
      「忘掉」错误的回答。good=True 只是确认（落库时默认 feedback=None
      即视为可用，这步把显式认可也记下来，便于将来区分「被点赞过」）。"""
    if not db.get_doc(did):
        raise HTTPException(404, '文档不存在')
    ok = docqa.feedback_qa(did, body.question, body.good, body.correction)
    return {'ok': ok}


@router.post('/docs/{did}/figure/caption', summary='视觉模型给图片写中文图注')
def figure_caption(did: str, body: FigureCaptionIn, user=Depends(current_user)):
    """用 qwen2.5vl 给论文里的图（架构图/示意图）写一句中文说明，best-effort。

    ★ 为什么单独一个端点而不是把图注塞进翻译：翻译是「逐段文本」，
      图是独立的视觉对象，混进去会让翻译管道既要读图又要译字。
      这里前端渲染到 `![](media:name)` 时按需调用，拿不到图注就显示
      「原文图片·未译」徽标 —— 论文图片本就不该被「翻译」成文字，
      而是保留原图 + 一句 AI 说明让人秒懂。
    """
    if not db.get_doc(did):
        raise HTTPException(404, '文档不存在')
    p = docparse.media_path(did, body.name)
    if not p:
        raise HTTPException(404, '图片不存在')
    try:
        with open(p, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
    except Exception:
        raise HTTPException(500, '读图失败')
    try:
        cap = llm.vlm_caption(b64, context=body.context or '', timeout=60)
        return {'ok': True, 'caption': cap}
    except Exception as e:
        # ★ 视觉模型没装/挂了：降级返回 ok:false，前端照常显示「未译」徽标，
        #   不因为「图注没生成」就让整段译文报错。
        return {'ok': False, 'caption': '', 'reason': str(e)[:80]}


# ------------------------------------------------------------------
# 论文翻译（英译中 + 双语对照）
# ------------------------------------------------------------------
# ★ 为什么译文的读取**不并进** GET /docs/{did}：
#   那个端点每次返回整份 chapters（几十章几百 KB），
#   只为了看译文却要拉全文；而译文是**逐段完成**的，
#   并进文档详情就意味着「翻 10% 时前端拿到一份不完整的 doc」。
#   分开后前端才能自然显示「已译 26 / 261」。

@router.get('/docs/{did}/translate', summary='译文进度 + 已译内容')
def get_translation(did: str, user=Depends(current_user)):
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    segs = transjob.segments_of(d)
    return {'ok': True,
            'status': transjob.status_of(d),
            'glossary': db.glossary_all(did),
            # ★ 一并返回原文分段：前端靠 seg_i 把译文和原文对上号。
            #   只给译文的话前端不知道「第 12 段是什么」，就没法做对照。
            'segments': [{'i': s['i'], 'src': s['text'],
                          'translate': s.get('translate', True),
                          'type': s.get('type', 'body')} for s in segs],
            'translations': {str(k): v for k, v in db.trans_all(did).items()},
            'translatable': transjob.looks_translatable(d)}


@router.post('/docs/{did}/translate/run', summary='开始/继续翻译（SSE 流式）')
def run_translation(did: str, body: TranslateIn, user=Depends(current_user)):
    """逐段翻译，一段一落库，可随时中断续跑。

    body.mode：
      run（默认）只翻「还没翻好」的段，天然支持续跑
      redo           全部重翻
      redo:N         从第 N 段起重翻
      limit:N        只处理 N 段（试跑 / 调提示词时用）

    body.verify：默认 True = 每段都做回译校验（慢一倍但能发现幻觉）。
    调提示词时可以传 False 快速跑几十段看效果。

    ★ 为什么要 SSE：本地 8B 翻一段 3~8 秒，一篇 261 段就是一两个小时。
      不流式的话前端只能转圈一两个小时（用户以为坏了）或设超时（白跑）。
      配合逐段落库，中途关页面不丢已翻的部分。
    """
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    if llm.AI_OFF or not llm.list_models():
        raise HTTPException(503, 'AI 没开（环境变量 AI=off，或本机没起 Ollama）')
    segs = transjob.segments_of(d)
    if not segs:
        raise HTTPException(400, '这份文档没有可翻译的正文')

    # ★★ 模式解析必须**互斥**，不能共用一个 `if ':' in mode` 拆数字。
    #   原来的写法里 `limit:3` 会同时把 start 设成 3 —— 于是「只翻 3 段」
    #   变成「从第 4 段起翻 3 段」，前 3 段永远不被处理，
    #   而端点返回 200、进度显示「已完成 3 段」，**看起来完全正常**。
    #   这类 bug 只在「调试时想少跑几段」这条路径上出现，
    #   所以真跑整篇时永远发现不了。
    mode = (body.mode or 'run').strip()
    redo = False
    start = 0
    limit = 0
    only = None
    head, _, tail = mode.partition(':')
    n = None
    if ':' in mode:
        try:
            n = int(tail)
        except ValueError:
            n = None
    if head == 'redo':
        redo = True
        start = n or 0
    elif head == 'limit':
        limit = n or 0
    elif head == 'vlm':
        # mode=vlm：只给还没解读的图跑 VLM 中文解读（2026-11-15）。
        # 走同一条 SSE 流、同一个进度条；不碰文本段。
        only = 'vlm'
        if llm.AI_OFF or not llm.vlm_model():
            raise HTTPException(503, 'VLM 不可用（没装视觉模型，如 qwen2.5vl）')
    verify = body.verify

    # ★ 防双跑（2026-11-15）：以前「在不在跑」无状态，刷新页面后用户
    #   再点一次就起第二个并行线程。现在有注册表了，端点先挡一道；
    #   竞态窗口由 transjob.run 的原子 _acquire 兜底（busy 时 error 帧）。
    if transjob.is_running(did):
        raise HTTPException(409, '已有翻译在跑（刷新页面可接管进度，或点停止）')

    def worker(emit):
        done = {'n': 0}

        def on_progress(seg_i, total, row):
            done['n'] += 1
            emit('seg', {'i': seg_i, 'total': total, 'done': done['n'],
                         'zh': row.get('zh') or '',
                         'status': row.get('status') or '',
                         'score': row.get('score'),
                         'missing': row.get('missing') or [],
                         'error': row.get('error') or ''})

        emit('total', {'total': len(segs)})
        res = transjob.run(d, on_progress=on_progress, verify=verify,
                           redo=redo, start=start, limit=limit, only=only)
        if res.get('busy'):
            # 极小竞态：端点检查后另一请求先抢到了槽。如实报错而不是装完成。
            emit('error', {'msg': res.get('msg') or '已有翻译在跑'})
            return
        if res.get('cancelled'):
            # 协作式停止：当前段翻完就断。已翻的都在库里，前端刷新进度条即可。
            emit('cancelled', {'total': len(segs), 'ok': res.get('done', 0),
                               'remaining': res.get('remaining', 0),
                               'status': transjob.status_of(d),
                               'msg': '已停止（已完成的段落都保留）'})
            return
        emit('done', {'total': len(segs), 'ok': res.get('done', 0),
                      'remaining': res.get('remaining', 0),
                      'status': transjob.status_of(d)})

    return sse_json_stream(worker, first=[('total', {'total': len(segs)})])


@router.get('/docs/{did}/translate/status', summary='翻译任务状态（running + 进度）')
def translate_status(did: str, user=Depends(current_user)):
    """刷新页面后靠它恢复「翻译还在跑吗、到哪了」。

    ★ 以前唯一的进度查询是 GET /translate（全量：段落+译文+术语表），
     「查一下还在不在跑」也要拉几百 KB。status 只回轻字段：
     running / startedAt / cancelRequested + status_of 的计数。
     前端轮询它（3s），翻完再拉一次全量。
    """
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    info = transjob.running_info(did)
    vm = ''
    try:
        vm = llm.vlm_model() if not llm.AI_OFF else ''
    except Exception:
        vm = ''
    return {'ok': True, **info,
            'status': transjob.status_of(d),
            'vlm': bool(vm), 'vlmModel': vm}


@router.post('/docs/{did}/translate/stop', summary='请求停止翻译（协作式）')
def translate_stop(did: str, user=Depends(current_user)):
    """置取消标志：当前段翻完就断（单段 3~8 秒内响应）。

    ★ 为什么不是强杀线程：worker 是 daemon 线程，Python 没有安全的
      线程强杀；协作式停止的语义反而更好 —— 「停在这一段的边界上」，
      已翻段落全部落库，续跑从断点继续，不会有半段译文。
    """
    ok = transjob.request_cancel(did)
    return {'ok': True, 'wasRunning': ok,
            'msg': '' if ok else '这份文档当前没有翻译任务在跑'}


@router.post('/docs/{did}/translate/glossary', summary='重抽术语表')
def redo_glossary(did: str, user=Depends(current_user)):
    """重抽术语表。**锁定的条目不会被覆盖** —— 见 transjob.build_glossary。"""
    d = db.get_doc(did)
    if not d:
        raise HTTPException(404, '文档不存在')
    if llm.AI_OFF or not llm.list_models():
        raise HTTPException(503, 'AI 没开')
    g = transjob.build_glossary(d, force=True)
    return {'ok': True, 'count': len(g), 'glossary': db.glossary_all(did)}


@router.put('/docs/{did}/translate/glossary', summary='手动加/改一条术语')
def put_glossary(did: str, body: GlossaryIn, user=Depends(current_user)):
    """手动术语默认 locked=1。

    ★ 为什么默认锁定：用户手敲一个译法就是在纠正机器。
      不锁定的话下次「重抽术语表」会把它冲掉，而用户不会纠正第二次
      —— 这个功能就废了。想让机器重新决定，传 locked=0。
    """
    if not db.get_doc(did):
        raise HTTPException(404, '文档不存在')
    en = (body.en or '').strip()
    if not en:
        raise HTTPException(400, '英文术语不能为空')
    db.glossary_put(did, en, (body.zh or '').strip(),
                    locked=True if body.locked is None else body.locked)
    return {'ok': True, 'glossary': db.glossary_all(did)}


@router.delete('/docs/{did}/translate/glossary', summary='删一条术语')
def del_glossary(did: str, en: str = Query(..., description='英文术语'),
                 user=Depends(current_user)):
    db.glossary_del(did, en)
    return {'ok': True, 'glossary': db.glossary_all(did)}


@router.delete('/docs/{did}/translate', summary='清空这份文档的译文')
def clear_translation(did: str, user=Depends(current_user)):
    """清空译文但**保留术语表** —— 术语是人工劳动成果，换模型重译时还要用。"""
    if not db.get_doc(did):
        raise HTTPException(404, '文档不存在')
    db.trans_clear(did)
    return {'ok': True}
