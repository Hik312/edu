# -*- coding: utf-8 -*-
"""整份文件的解析：PDF / Word / md / txt → 正文（含图片占位） + 图片清单。

职责边界（和 importer.py 的分工，别把两边的活混着写）：
- **这里**管「文件字节 → 文字 + 图片」：格式解包、把图片抠出来、按原文
  顺序把占位符插回正文、图片落盘 / 读取 / 删除。
- **importer.py** 管「文字 → 章节」：标题识别、切分、层级。
  正文里的图片占位符就是普通文本行，跟着文字一起进分章，天然落到
  图片所在的那一章 —— 两边不需要互相感知。

图片从文档到卡片的完整链路（改动前先读这段）：

    解析期   word/media/image1.png ──存──▶ data/store/media/<docId>/image1.png
             正文里插一行 `![](media:image1.png)`（跟文档顺序走）
    转卡期   agent/cards 把用到的图拷到 data/store/media/card-<cardId>/，
             卡片 images[].src = /api/media/card-<cardId>/image1.png
             —— **拷贝而不是引用**：源文档删了，卡片的图还在。
    展示端   GET /api/media/{owner}/{name}（登录后可读，owner 只允许
             \w-. 字符，路径穿越在 media_path 里挡掉）

老 .doc（OLE 二进制）与扫描版 PDF（抽不出字）不在这条链上 ——
报错和「给路」是 routers/docs.py 的事，这里只抛内部代号 no_doc / no_pypdf。
"""
import base64
import hashlib
import os
import re
import zipfile

CORE_DIR = os.path.dirname(os.path.abspath(__file__))          # back_study/core
ROOT = os.path.dirname(os.path.dirname(CORE_DIR))               # study（项目根）
STORE_DIR = os.path.join(ROOT, 'data', 'store')
MEDIA_DIR = os.path.join(STORE_DIR, 'media')

# 正文里的图片占位：和 markdown 图片语法同形，所以前端拿它当普通 ![]() 渲染即可
MEDIA_TOKEN = re.compile(r'!\[\]\(media:([A-Za-z0-9_.\- ]+)\)')
# owner / 文件名只允许这些字符 —— 一切路径读写先过这两个闸
SAFE_NAME = re.compile(r'^[A-Za-z0-9_.\-]{1,80}$')

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
PKG_REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'
VML = '{urn:schemas-microsoft-com:vml}'

MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp',
        '.svg': 'image/svg+xml', '.emf': 'image/x-emf', '.wmf': 'image/x-wmf',
        '.tif': 'image/tiff', '.tiff': 'image/tiff'}

#: 单个上传文件的原始字节上限（40MB）。前端按同一个数校验。
#:
#: ★ 为什么不写 60MB：上传走 base64，膨胀 4/3，40MB → 约 53MB 请求体，
#:   再加 JSON 外壳仍低于 app/config.py 的 MAX_BODY(64MB)。两个数必须配套改 ——
#:   前端放宽而服务端没放宽，表现是「大文件传一半被拒」，比一开始就拒绝更难查。
MAX_UPLOAD_BYTES = 40 * 1024 * 1024


def mime_of(name):
    return MIME.get(os.path.splitext(name)[1].lower(), 'application/octet-stream')


def _safe_basename(name):
    """zip 里的图片名可能带路径（word/media/image1.png），只留文件名并洗成
    **ASCII 安全名**：中文/空格/特殊字符全换 `_`。

    为什么要洗到 ASCII：SAFE_NAME（media_path 的闸）只放行 [A-Za-z0-9_.-]，
    中文名会在读图时 404；空格在 URL 里也要转义。在**生成名**这一步就洗掉，
    后面存、取、拷、URL 四处看到的是同一个干净名字。

    只换成 ASCII：保留扩展名（.png 的点不能吃掉），也别 strip ——
    '图片.png' → '_.png' 是合法名（SAFE_NAME 放行），去重靠调用方的指纹后缀。
    """
    base = os.path.basename(name or '').strip().replace('\\', '/')
    base = os.path.basename(base)
    base = re.sub(r'[^A-Za-z0-9_.\-]', '_', base) or 'image'
    return base[:80]


# ---------------------------------------------------------------------------
# 分派
# ---------------------------------------------------------------------------
def extract(data, filename=''):
    """按文件类型分派，返回 {'text': str, 'media': [{name,mime,data:bytes}]}。

    失败抛 RuntimeError('no_doc'|'no_docx'|'no_pypdf')，上层负责说人话。
    `data` 是完整文件字节；`media` 为空表示这份文件没有可用图片（或纯文本）。"""
    fname = (filename or '').lower()
    if fname.endswith('.doc') and not fname.endswith('.docx'):
        raise RuntimeError('no_doc')
    if fname.endswith('.pdf') or data[:4] == b'%PDF':
        return extract_pdf(data)
    if fname.endswith('.docx') or data[:4] == b'PK\x03\x04':
        return extract_docx(data)
    return {'text': data.decode('utf-8', 'ignore'), 'media': []}


# ---------------------------------------------------------------------------
# docx：zip 拆包，document.xml 出文字，word/media 出图片
# ---------------------------------------------------------------------------
def extract_docx(data):
    """Word(.docx) → 正文（图片按文档顺序插占位符） + 图片清单。

    不装 python-docx：为「抽文字+抽图」多背一个跨机器要装的依赖，不值。
    标题识别走 Word 自己的大纲标记（w:outlineLvl / Heading 样式 id），
    转成 markdown `#` 后交给 importer.parse_document —— 分章全项目只有一套。

    zip 只在 with 里打开：媒体文件先整个读进内存（图片本来就是几 MB 级），
    解析正文时文档已关闭 —— 否则 pull_media 会在关掉的 zip 上读文件。"""
    import io
    from xml.etree import ElementTree as ET

    if data[:4] != b'PK\x03\x04':
        raise RuntimeError('no_docx')
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        raise RuntimeError('no_docx')
    with z:
        try:
            xml = z.read('word/document.xml')
        except Exception:
            raise RuntimeError('no_docx')

        # 关系表：rId → media/image1.png（没有 rels 的裸文档当空表处理）
        rels = {}
        try:
            rr = ET.fromstring(z.read('word/_rels/document.xml.rels'))
            for rel in rr:
                rid = rel.get('Id') or ''
                tgt = rel.get('Target') or ''
                if rid and tgt:
                    rels[rid] = tgt
        except Exception:
            rels = {}

        # 媒体文件先整个读进内存，出 with 后 zip 就关了
        blobs = {}
        for item in z.namelist():
            if item.startswith('word/media/') and not item.endswith('/'):
                try:
                    blobs[item.replace('\\', '/')] = z.read(item)
                except Exception:
                    pass

        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            raise RuntimeError('no_docx')

    # rId 占位符 → 正文行，按文档顺序填
    media = []          # [{name, mime, data, _path}]
    seen_path = {}      # zip 路径 → 已收的文件名

    def pull_media(rid):
        tgt = rels.get(rid) or ''
        if not tgt:
            return None
        path = tgt.lstrip('/')
        if not path.startswith('word/'):
            path = 'word/' + path
        path = path.replace('\\', '/')
        if path not in blobs:
            return None
        if path in seen_path:
            return seen_path[path]
        name = _safe_basename(os.path.basename(path))
        # 两个不同文件洗完同名时（少见），加指纹后缀区分
        if any(m['name'] == name for m in media):
            name = hashlib.sha1(path.encode('utf-8')).hexdigest()[:8] + '_' + name
        media.append({'name': name, 'mime': mime_of(name),
                      'data': blobs[path], '_path': path})
        seen_path[path] = name
        return name

    def para_text(p):
        # 按文档顺序收 w:t；w:tab / w:br 当空格 —— 制表符丢了不影响阅读，
        # 但完全不收会把两个词黏在一起
        out = []
        for node in p.iter():
            if node.tag == W + 't':
                out.append(node.text or '')
            elif node.tag in (W + 'tab', W + 'br'):
                out.append(' ')
        return ''.join(out).strip()

    def para_images(p):
        """这一段里嵌的图片（按出现顺序），返回占位符列表。"""
        tokens = []
        for node in p.iter():
            rid = None
            if node.tag == A + 'blip':
                rid = node.get(R + 'embed') or node.get(R + 'link')
            elif node.tag == VML + 'imagedata':
                rid = node.get(R + 'id')
            if not rid:
                continue
            name = pull_media(rid)
            if name:
                tok = '![](media:%s)' % name
                if tok not in tokens:
                    tokens.append(tok)
        return tokens

    def heading_level(p):
        """返回 1~6 的标题层级，不是标题返回 0。"""
        pr = p.find(W + 'pPr')
        if pr is None:
            return 0
        ol = pr.find(W + 'outlineLvl')
        if ol is not None:
            v = ol.get(W + 'val')
            if v is not None and v.isdigit() and int(v) <= 5:
                return int(v) + 1
        st = pr.find(W + 'pStyle')
        if st is not None:
            v = (st.get(W + 'val') or '').strip()
            m = re.match(r'^(?:[Hh]eading|标题)\s*([1-6])$', v)
            if m:
                return int(m.group(1))
        return 0

    lines = []
    for p in root.iter(W + 'p'):
        txt = para_text(p)
        pics = para_images(p)
        if not txt and not pics:
            continue
        lvl = heading_level(p)
        line = ''
        if txt:
            line = ('#' * lvl + ' ' + txt) if lvl else txt
        if pics:
            line = (line + ' ' if line else '') + ' '.join(pics)
        lines.append(line)

    return {'text': '\n'.join(lines),
            'media': [{'name': m['name'], 'mime': m['mime'], 'data': m['data']}
                      for m in media]}


# ---------------------------------------------------------------------------
# PDF：pypdf 抽文字 + 逐页抽图
# ---------------------------------------------------------------------------
def _collapse_blank_runs(text, keep=2):
    """把连续 3 行以上的空行压到 keep 行。

    layout 模式为了还原版面会灌大量空行（一页正文能多出几十行空白），
    直接拿去分章会把章节撑得稀碎、目录全是空条目。
    """
    out = []
    run = 0
    for line in (text or '').split('\n'):
        if line.strip():
            run = 0
            out.append(line)
            continue
        run += 1
        if run <= keep:
            out.append('')
    return '\n'.join(out).rstrip()


def extract_pdf(data):
    """PDF → 正文（图片占位跟在所属页的文字后） + 图片清单。

    依赖可选的 pypdf：没装抛 no_pypdf（上层给 pip install 的路）。
    `page.images` 是 pypdf 3.9+ 的接口，旧版没有就只出文字 —— 图片是增强，
    不为它把整条导入链断掉。

    ★ 为什么优先 layout 模式：默认模式只按 PDF 内部流的顺序吐字，
      空格和换行全丢，实测一份 TypeScript 讲义抽出来是
      「装饰器是⼀个应⽤在类声明上的函数」这种**每行都断开**的碎片，
      标题、项目符号、代码块的连续性全没了。
      layout 模式按坐标还原版面，标题层级和列表结构能保住，
      实测同一份文件可读性差别是数量级的。

      layout 模式是 pypdf 3.9+ 的 `extraction_mode='layout'`，
      老版本 / 某些加密 PDF 会抛异常 —— 捕住退回默认模式，
      宁可碎片也别整份抽不出来。
    """
    import io
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader           # 老包名，兼容一下
        except ImportError:
            raise RuntimeError('no_pypdf')

    reader = PdfReader(io.BytesIO(data))
    media = []
    pages = []
    for pg in reader.pages:
        txt = ''
        try:
            txt = pg.extract_text(extraction_mode='layout') or ''
        except Exception:
            try:
                txt = pg.extract_text() or ''
            except Exception:
                txt = ''
        # layout 模式会灌一堆空行进去（保留版面就是这么个代价），
        # 三连以上压成两行：段落之间要留呼吸，但十几行空白会把章节撑散
        txt = _collapse_blank_runs(txt)
        toks = []
        try:
            for im in pg.images:                   # pypdf>=3.9；旧版没这个属性
                blob = im.data
                if not blob:
                    continue
                name = _safe_basename(getattr(im, 'name', '') or 'page.png')
                name = hashlib.sha1(blob).hexdigest()[:8] + '_' + name
                if any(m['name'] == name for m in media):
                    continue
                media.append({'name': name, 'mime': mime_of(name), 'data': blob})
                toks.append('![](media:%s)' % name)
        except Exception:
            pass
        if toks:
            txt = (txt + '\n' if txt else '') + ' '.join(toks)
        pages.append(txt)
    return {'text': '\n'.join(pages),
            'media': [{'name': m['name'], 'mime': m['mime'], 'data': m['data']}
                      for m in media]}


# 兼容旧名：scripts/gen_docs.py 等只要文字不要图的调用还挂在这两个名字上。
# 语义不变（返回 str），实现已经搬进 extract_pdf / extract_docx。
def extract_pdf_bytes(data):
    return extract_pdf(data)['text']


def extract_docx_bytes(data):
    return extract_docx(data)['text']


# ---------------------------------------------------------------------------
# 图片落盘 / 读取（全项目唯一碰 data/store/media/ 的地方）
# ---------------------------------------------------------------------------
def save_media(owner, media_list):
    """把图片存进 data/store/media/<owner>/，返回落盘的文件名列表。

    owner 是隔离域：文档用 docId，卡片用 card-<cardId>。重传同名覆盖
    （同一份文档重新导入本来就该覆盖）。"""
    if not media_list:
        return []
    _check_owner(owner)
    d = os.path.join(MEDIA_DIR, owner)
    os.makedirs(d, exist_ok=True)
    names = []
    for m in media_list:
        name = _safe_basename(m.get('name') or '')
        if not name:
            continue
        with open(os.path.join(d, name), 'wb') as f:
            f.write(m.get('data') or b'')
        names.append(name)
    return names


def media_path(owner, name):
    """校验并返回绝对路径；不合法返回 None（路径穿越在这里挡死）。"""
    if not _check_owner(owner) or not SAFE_NAME.match(name or ''):
        return None
    p = os.path.realpath(os.path.join(MEDIA_DIR, owner, name))
    root = os.path.realpath(MEDIA_DIR)
    if not p.startswith(root + os.sep):
        return None
    if not os.path.isfile(p):
        return None
    return p


def media_names(owner):
    """owner 下现有的图片名（没有目录返回空列表）。"""
    if not _check_owner(owner):
        return []
    d = os.path.join(MEDIA_DIR, owner)
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d)
                  if os.path.isfile(os.path.join(d, n)) and SAFE_NAME.match(n))


def delete_media(owner):
    """删掉一个隔离域的全部图片（文档删除时调）。"""
    if not _check_owner(owner):
        return
    import shutil
    d = os.path.join(MEDIA_DIR, owner)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def copy_media(src_owner, dst_owner, names):
    """把 src_owner 下的几张图拷进 dst_owner（转卡时用：卡片的图不随源文档消失）。
    返回 [{name, src, mime}]，src 是前端可直接用的 URL。"""
    out = []
    for n in names or []:
        p = media_path(src_owner, n)
        if not p:
            continue
        if not _check_owner(dst_owner):
            continue
        dd = os.path.join(MEDIA_DIR, dst_owner)
        os.makedirs(dd, exist_ok=True)
        with open(p, 'rb') as f:
            blob = f.read()
        with open(os.path.join(dd, n), 'wb') as f:
            f.write(blob)
        out.append({'name': n, 'src': media_url(dst_owner, n), 'mime': mime_of(n)})
    return out


def media_url(owner, name):
    return '/api/media/%s/%s' % (owner, name)


def read_media(owner, name):
    """读图片字节，失败返回 None。路由层负责 404。"""
    p = media_path(owner, name)
    if not p:
        return None
    with open(p, 'rb') as f:
        return f.read()


def _check_owner(owner):
    return bool(owner) and bool(SAFE_NAME.match(owner))


def to_b64(blob):
    return base64.b64encode(blob).decode('ascii')


# ---------------------------------------------------------------------------
# 原始文件落盘 / 读取（知识库在线预览源文档用）
# ---------------------------------------------------------------------------
RAW_DIR = os.path.join(STORE_DIR, 'files')

RAW_EXT = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.md': 'text/markdown',
    '.txt': 'text/plain',
}


def save_raw(doc_id, data, ext=''):
    """把上传的原始文件字节存进 data/store/files/<docId><ext>。

    ext 只允许字母数字（.pdf/.md/...），docId 走 SAFE_NAME —— 两者都不放行
    路径分隔符，read_raw 的路径拼接是安全的。返回相对 store 的路径
    （如 files/doc-xxx.pdf），供前端拼预览 URL；存不下返回空串。"""
    if not doc_id or not data:
        return ''
    ext = (ext or '').lower()
    if not ext or not re.match(r'^[a-z0-9.]+$', ext) or '..' in ext:
        return ''
    if not SAFE_NAME.match(doc_id):
        return ''
    d = os.path.join(RAW_DIR, doc_id)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, doc_id + ext)
    try:
        with open(path, 'wb') as f:
            f.write(data)
    except Exception:
        return ''
    return 'files/%s%s' % (doc_id, ext)


def raw_path(doc_id, ext=''):
    """原始文件绝对路径；不存在返回 None。ext 缺省时按 RAW_EXT 的顺序挨个试。

    ★ 兜底顺序别漏 .docx：早期文档的 rawFile 字段为空（那会儿还没这个功能），
      只认 pdf/md/txt 的话，Word 资料明明文件就在那儿却报 404。

    ★ ext 必须容忍**前导点**（2026-10-11 修）：调用方拿到的后缀一律来自
      `os.path.splitext(rawFile)[1]`，那就是 '.pdf'。而下面这条正则要求
      首字符是字母数字，于是 '.pdf' 被判非法 → 直接 return None →
      「原件明明在磁盘上，预览永远 404」。
      这是个**静默失败**：不报错、不打日志，只是原件永远显示不出来，
      和「raw_file 列不存在」叠在一起时极难定位 —— 补了列还是 404。
      所以这里先剥掉前导点再校验，两种写法（'.pdf' / 'pdf'）都能用。
    """
    if not doc_id or not SAFE_NAME.match(doc_id):
        return None
    ext = (ext or '').lstrip('.').lower()
    if ext and not re.match(r'^[a-z0-9]+(\.[a-z0-9]+)*$', ext):
        return None
    ext = '.' + ext if ext else ''
    d = os.path.join(RAW_DIR, doc_id)
    cands = [doc_id + ext] if ext else [doc_id + e for e in RAW_EXT]
    for name in cands:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return os.path.realpath(p)
    return None


def delete_raw(doc_id):
    """文档删除时连原始文件一起清。"""
    if not doc_id or not SAFE_NAME.match(doc_id):
        return
    import shutil
    d = os.path.join(RAW_DIR, doc_id)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def raw_mime(path):
    ext = os.path.splitext(path or '')[1].lower()
    return RAW_EXT.get(ext, 'application/octet-stream')
