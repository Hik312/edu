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
import json
import os
import re
import sys
import zipfile

CORE_DIR = os.path.dirname(os.path.abspath(__file__))          # back_study/core
ROOT = os.path.dirname(os.path.dirname(CORE_DIR))               # study（项目根）
STORE_DIR = os.path.join(ROOT, 'data', 'store')
MEDIA_DIR = os.path.join(STORE_DIR, 'media')
#: 结构化块的侧车目录（派生数据，不进 documents 表、不碰 schema）。
#: 和 qa_log 同一个思路：重新导入会覆盖、缺了翻译层退回纯文本分段。
BLOCKS_DIR = os.path.join(STORE_DIR, 'doc_blocks')

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
# 结构化块侧车（公式/参考文献/图片/图内文字/表格/附录 据此「原样保留、不送模型」）
# ---------------------------------------------------------------------------
def _blocks_file(did):
    """块文件的落盘名。docId 是 daily id（如 260101-0007），只含安全字符，
    但统一洗一遍最稳（将来自定义 id 也别把路径搞脏）。"""
    safe = re.sub(r'[^A-Za-z0-9_\-]', '_', str(did or ''))[:80]
    return os.path.join(BLOCKS_DIR, safe + '.json')


def save_blocks(did, blocks):
    """把结构化块存成侧车 JSON。

    ★ 块是**派生数据**（从 PDF 抽出来），不进 documents 表、不碰 schema：
      和 qa_log 同一个思路 —— 重新导入会覆盖、缺了翻译层就退回纯文本分段。
    副作用：翻译层据此让 equation / bibliography 段原样保留（不送模型）、
       figure 段只把 `![](media:)` 交回前端渲染。"""
    if not blocks:
        return
    try:
        os.makedirs(BLOCKS_DIR, exist_ok=True)
        with open(_blocks_file(did), 'w', encoding='utf-8') as f:
            json.dump(blocks, f, ensure_ascii=False)
    except Exception as e:
        sys.stderr.write('[docparse] 存 blocks 失败（降级为纯文本翻译）：%s\n' % e)


def load_blocks(did):
    """读结构化块。没有 / 读坏返回 None（调用方退回文本分段）。"""
    try:
        p = _blocks_file(did)
        if not os.path.isfile(p):
            return None
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def delete_blocks(did):
    """文档删除时把块侧车一起清 —— 和 delete_raw / delete_media 同一道理：
    派生数据和文档同生命周期，留着就是孤儿文件。"""
    try:
        p = _blocks_file(did)
        if os.path.isfile(p):
            os.remove(p)
    except Exception as e:
        sys.stderr.write('[docparse] 清 blocks 失败：%s\n' % e)


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


def _classify_block(txt):
    """把一段抽出来的文字判成：heading/body/caption/equation/bibliography/skip。

    ★ 为什么只靠文本模式、不靠字号：pypdf 的纯文本层拿不到字号，
      PyMuPDF 的 blocks 元组也不带字号；而学术论文的结构高度规整 ——
      章节是「编号段」、图是「Figure/Table…」、参考文献是「[n] 起头 + 引文特征」、
      公式是「含数学符号且短」。这几条模式覆盖了 95% 以上的论文，
      比硬上字体分析稳（字体分析还会把页眉大字号误判成标题）。
    skip = 页码/纯数字行，直接丢弃（不进正文、不翻译）。"""
    t = (txt or '').strip()
    if not t:
        return 'skip'
    if re.fullmatch(r'\d{1,6}', t):
        return 'skip'                                   # 页码行
    # arXiv 侧边水印（每页一条，竖排有时被横抽出来）——纯噪声
    if re.match(r'^arXiv:\d{4}\.\d{4,5}', t):
        return 'skip'
    # 首页脚注（通讯作者邮箱 / 仓库链接，编号顶格）——混进正文极难看
    if re.match(r'^\d{1,2}\s*(Corresponding|email|http|[a-z]+@)', t, re.I):
        return 'skip'
    if re.match(r'^(figure|fig\.?|table|tab\.?|algorithm|listing|plate|diagram|eq\.?|equation)\b',
                t, re.I):
        return 'caption'
    if re.match(r'^[\[\(]\d+[\]\)]', t) and (len(t) > 45 or re.search(
            r'(et al|pp?\.|vol|arxiv|http|doi|journal|conference|in:|'
            r'\bed(s|itors)?\b|press|univ|springer|acm|ieee)', t, re.I)):
        return 'bibliography'
    math = set('βλ∫∑√≈≤≥×→±∂µπθαγδεσφψωΦΨΩ≠≡∈∉⊆⊂∪∩∀∃∇∞')
    if any(c in math for c in t) and len(t) < 260:
        # ★ 字母密度守卫（2026-11-15）：含 ±/µ 等符号且字母占比高的是
        #   **作者行**（"Jieyu Zhang±, ..."），不是公式 —— 作者署名里的
        #   机构上标让它含集合内符号。公式行字母占比低（符号+短变量），
        #   作者行是密集英文（>55%）。误判成 equation 的后果：作者行被
        #   「保留原文」且丢掉 heading/正文语义。
        letters = sum(c.isalpha() for c in t) / max(1, len(t))
        if letters <= 0.55:
            return 'equation'
        return 'body'
    if re.match(r'^\d+(\.\d+)*\s*[/．.．]?\s*\S', t) and len(t) < 82:
        return 'heading'
    if re.match(r'^(abstract|introduction|related work|conclusion|references|'
                r'appendix|acknowledg|background|method|results|discussion|'
                r'overview|preliminaries|experiment|related works?)\b',
                t, re.I) and len(t) < 44:
        return 'heading'
    return 'body'


#: 图题 / 表题前缀（2026-11-15，caption 关联用）。
#: `_classify_block` 把 Figure 和 Table 的题注都判成 'caption'，但挂到图上的
#: 只应该是图题 —— "Table 2: ..." 出现在图正下方时挂上去就是张冠李戴。
_FIG_CAPTION_RE = re.compile(r'^(figure|fig\.?)\s*\d|^图\s*\d', re.I)
_TAB_CAPTION_RE = re.compile(r'^(table|tab\.?)\s*\d|^表\s*\d', re.I)


def _looks_like_label(txt):
    """图内零碎标签的启发式：短、不是完整句子。pdffigures2 的「异常文本」
    思想极简版 —— 标签和正文的最大区别是**标签不成句**。
    误收进 figtext 的代价极低（只是 VLM 解读的提示词素材，不进译文正文），
    漏收的代价是解读卡少素材 —— 所以门槛刻意放宽。"""
    t = (txt or '').strip()
    if not t or len(t) > 60:
        return False
    if t.endswith(('.', '。', '!', '?', '！', '？', ';', '；')):
        return False
    if t.startswith('['):                      # 引文编号行
        return False
    return True


def _link_fig(territory, typ, txt):
    """图领地-题注/图内文字关联的**单步状态机**（纯函数，页内循环调用）。

    ★ 领地是**列表**不是单块（2026-11-15 实测 AutoGen 论文后改的）：
      论文里一张逻辑图常由**多张小位图拼成**（Figure 1 = 15 个子图块连续出现，
      中间夹图表标签），阅读顺序里它们连成一片。单图状态机遇到连续 img
      会「新的关掉旧的」，图题永远只能挂给最后一个子图。领地列表语义：
      连续 img（中间无正文打断）同属一个领地，图题挂给**领地全体** ——
      子图各自的解读卡都能带上正确的图题。

    领地从第一个 img 开始，到题注/长正文/标题结束：
      img*(开/追加) → 零碎块（收进全体 figtext）→ 图题（挂全体并闭合）
    返回 `(新 territory, action)`。action 告诉调用方这个块怎么处置：

      'figtext'  几何命中的图内文字 → 已收进领地全体 figtext（**不独立成段**）
      'label'    短标签（几何阈值漏判成 body 的图内文字）→ 同上
      'caption'  图题 → 已挂领地全体，领地闭合（块照常独立成段、照常翻译）
      'tab'      表题 → 领地闭合（块照常成段）
      'pass'     长正文/标题/公式 → 领地闭合（块照常成段）

    规则细节：
      1. **前缀优先**：图题/表题按前缀认（Figure N / 图 N / Table N / 表 N），
         而不是按块的 type —— `_mark_refs_and_appendix` 会把附录区的
         caption 整体重打成 'appendix'，按 type 判就全漏了。
         Table 题注不挂图（张冠李戴防线），只把领地闭合。
      2. figtext（几何判定命中的图内文字）照旧挂。
      3. **短标签容忍**：图内零碎标签（"Month"、"Example Agent Chat"）大量
         被 `_overlap_ratio>=0.55` 几何阈值漏判成 body/table —— 短且不成句
         的块视为标签收进 figtext。**它们不该独立出现在正文流里**
         （2026-11-15 用户反馈：对照页一半是「图内文字·保留原文」碎片，
         读的时候不知道图长什么样）——调用方按 action 剔除。
      4. 其余（长正文/标题/公式/参考文献）→ 领地结束。
    """
    if not territory:
        return None, 'pass'
    if _FIG_CAPTION_RE.match(txt):
        for blk in territory:
            if not blk.get('caption'):
                blk['caption'] = txt
        return None, 'caption'                 # 一个领地吃一个图题
    if _TAB_CAPTION_RE.match(txt):
        return None, 'tab'                     # 表题：领地到此为止
    if typ == 'figtext':
        for blk in territory:
            blk.setdefault('figtext', []).append(txt)
        return territory, 'figtext'
    if _looks_like_label(txt):
        for blk in territory:
            blk.setdefault('figtext', []).append(txt)
        return territory, 'label'
    return None, 'pass'                        # 长正文/标题/公式：领地结束


def _normalize_heading(t):
    """编号标题统一成 `N. Title`（点号分隔），让下游 importer.detect_heading
    的 `RE_AR_NUM`/`RE_D2` 能认出它是一级/二级标题，分章才立得起来。
    `1 / Introduction` → `1. Introduction`，`2 Related work` → `2. Related work`。"""
    m = re.match(r'^(\d+(?:\.\d+)*)\s*[/．.．]?\s*(.+)$', t)
    if m:
        return '%s. %s' % (m.group(1), m.group(2).strip())
    return t


# 附录 / 参考文献的起点特征（翻译层据此「整节保留原文、不送模型」）。
# ★ 为什么字母编号标题（A. / B.1 …）必须再加「参考文献已出现」这个前置条件：
#   正文里短句块以单个大写字母开头很常见（"A Novel Approach…"），
#   单看字母编号会把正文中段误判成附录起点 —— 而误判的后果是
#   **后半篇全部不翻译**，且接口照常 200、页面照常显示（只是英文），
#   极像「翻译功能坏了」。参考文献之后再出现字母小节，才是附录。
# ★ 字母标题的形态刻意排除「A. 人名」：作者-年份引用条目
#   （"B. (2023). Refiner: …"、"A. Author, Title, 2020"）长得和
#   「A. 小节标题」一模一样 —— 实测 Reflexion 附录被误判到第 10 页的
#   引文上提前开始。所以裸字母后**不许带点**（真实附录标题是
#   "A Evaluation…" 不是 "A. Evaluation…"），带点的只认 "B.1" 这种
#   字母.数字编号，或再带一个括号小标（"D.4.1 (EPM) …"）。
_APPENDIX_HEAD = re.compile(
    r'^(appendix|appendices|supplementary\s+(?:material|appendix|information|'
    r'data|file)|附录)\b', re.I)
_LETTER_HEAD = re.compile(
    r'^(?:[A-Z](?:\.\d+)+\.?|[A-Z])\s+(?:\([A-Z][^)]*\)\s*)?[A-Z]')
_REFS_HEAD = re.compile(r'^(references|bibliography|references and notes)\s*$', re.I)


def _is_appendix_head(t, state):
    """这一块是不是附录的起始小节（A. / Appendix A / 附录…）。"""
    s = re.sub(r'\s+', ' ', (t or '').strip())
    if not s or len(s) > 110:
        return False
    if _APPENDIX_HEAD.match(s):
        return True
    return bool(state['refs_seen'] and _LETTER_HEAD.match(s))


_CITE_FEAT = re.compile(r'\b(19|20)\d{2}\b|arxiv|doi[.:]|https?://|\[\d+\]', re.I)


def _looks_like_refs_start(blocks, i):
    """`References` 标题后面真的跟着引文吗（防目录里的孤行误触）。

    ★ 目录页常有裸的 "References" 一行。若把它当参考文献区起点，
      **后面全部正文都会被标成不译** —— 而接口照常 200、页面照常显示，
      只是整篇没翻，极像「翻译功能坏了」。所以拿标题后 6 块做前瞻：
      至少 2 块带引文特征（年份 / arXiv / DOI / [n]）才算数。
    """
    hits = 0
    for b in blocks[i + 1:i + 7]:
        if b.get('type') == 'figure':
            continue
        if _CITE_FEAT.search(b.get('text') or ''):
            hits += 1
    return hits >= 2


def _mark_paper_title(blocks):
    """页 0 的第一个 body 块若为**论文标题** → 改 type='title'（保留原文不译）。

    论文标题专名密集（"AutoGen: Enabling Next-Gen LLM Applications via
    Multi-Agent Conversation"），8B 模型翻标题质量差且无必要 —— 学术阅读
    惯例标题保留原文。判定：页 0 第一个 body 块 + 后 6 块窗口内有
    作者/机构特征（University / † / ∗ / ± / Research...）。

    ★ 判定窗口为什么是「后 6 块」：标题块下面紧跟着作者行、机构行
      （实测 AutoGen 页 0：标题 → 作者×4 → 机构×2）。窗口里有作者特征
      就说明这个 body 块是标题而不是正文 —— 正文块后面跟的是更多正文。
    """
    author_re = re.compile(r'University|Institute|Research|Corresponding|@[a-z]|†|∗|±|‡', re.I)
    for i, b in enumerate(blocks[:12]):
        if b.get('type') == 'body' and b.get('page', 0) == 0:
            win = ' '.join((blocks[j].get('text') or '')
                           for j in range(i, min(i + 6, len(blocks))))
            if author_re.search(win) and len(b.get('text') or '') < 200:
                b['type'] = 'title'
            return


def _mark_refs_and_appendix(blocks):
    """二次扫描：参考文献区 → 引文续行归 bibliography；附录 → 整节 appendix。

    ★ 为什么放在块序列上二次扫、而不是抽取时顺手标：这两件事都是
      **整节语义**（起点之后到结尾全算），需要跨页状态和「标题是真是假」
      的前瞻确认；抽取主循环是逐页几何逻辑，混在一起两边都难读。
    ★ 参考文献的**续行块**（"preprint arXiv:2304.05128."）不带 [n] 前缀，
      单块分类认不出是引文 —— 只有「References 标题已过」这个区段状态
      能兜住它们，否则会被当正文送进翻译模型（把引文翻成中文）。
    """
    refs_head = False            # References 标题已确认（用于引文续行归位）
    state = {'in_appendix': False, 'refs_seen': False, 'bib_n': 0}
    for i, b in enumerate(blocks):
        typ = b.get('type') or 'body'
        txt = b.get('text') or ''
        norm = re.sub(r'\s+', ' ', txt.strip())
        if typ == 'bibliography':
            state['bib_n'] += 1
            if state['bib_n'] >= 8:
                state['refs_seen'] = True   # 一串引文条目 = 参考文献区（无标题兜底）
        if typ == 'heading' and _REFS_HEAD.match(norm) and _looks_like_refs_start(blocks, i):
            refs_head = True
            state['refs_seen'] = True
        # 引文条目不参与附录起点判定（作者-年份条目长得像 "A. 小节标题"）
        if (typ != 'bibliography' and not state['in_appendix']
                and _is_appendix_head(txt, state)):
            state['in_appendix'] = True
        if state['in_appendix']:
            # figure 块带着 media token，类型留给前端渲染原图
            if typ != 'figure':
                b['type'] = 'appendix'
        elif refs_head and typ == 'body':
            b['type'] = 'bibliography'


def _overlap_ratio(rect, regions):
    """rect 有多大比例落在 regions 里（0~1）。图/表内部文字靠它判定。"""
    area = rect.get_area()
    if area <= 0:
        return 0.0
    best = 0.0
    for r in regions:
        inter = rect & r
        if not inter.is_empty:
            best = max(best, inter.get_area() / area)
    return best


def _looks_tabular(t):
    """表格框里的文字是「单元格碎片」还是「被误圈进来的正文段落」。

    ★ 只对 find_tables 的框用：它会把架构图的方框也当表格（实测 Reflexion
      第 4 页给出跨大半页的 bbox），无条件信任会把正文段落吞成「不译」。
      判据：行短（单元格碎片）+ 句子密度低（正文段落句子多）。
      短行多句的例外（如 "AutoGen: 10/10 | N/A."）宁可归表格 ——
      单元格数字/方法名被模型改写比「一小段没翻」严重得多。"""
    lines = [l.strip() for l in (t or '').splitlines() if l.strip()]
    if not lines or max(len(l) for l in lines) > 90:
        return False
    sents = (t.count('. ') + t.count('。') + t.count('! ') + t.count('? ')
             + t.count('！') + t.count('？'))
    return not (sents >= 2 and len(t) > 140)


def _assign_columns(centers, W):
    """按 x 中心把块聚成 1~2 栏：栏间距太小（< 0.28*页宽）视为单栏。
    返回 {idx: 0|1}。双栏论文若按 y0 直接排会把左右栏交错，
    先分栏再按 y 排才是真阅读顺序。"""
    if not centers:
        return {}
    lo, hi = min(centers), max(centers)
    if hi - lo < W * 0.28:
        return {i: 0 for i in range(len(centers))}
    mid = (lo + hi) / 2
    return {i: (0 if c < mid else 1) for i, c in enumerate(centers)}


def _split_clusters_by_captions(clusters, caption_boxes):
    """题注是天然的**水平切分线**：图和表格之间夹着一行 "Figure 1: ..." / "Table 2: ..."。

    ★ 为什么必须切：Reflexion 第 3 页上，Figure 1 的架构图和它下面的对比表格
      属于两个不同的矢量簇，但表格的横线是「一根根细线」，
      在 `_vector_clusters` 的 min_side 过滤里和分隔线一样被丢掉，
      于是两个东西被 gap 合并规则吸成一个大框 ——
      渲染出来是「架构图 + 整张表格」拼在一起，还顺带把中间的英文题注也框进去。
      靠检测矢量空白带找不到间隙（表格线太扁，投影上处处有值），
      所以这里直接拿题注的文字行当刀。
    """
    import fitz
    if not caption_boxes:
        return list(clusters)
    out = []
    for r in clusters:
        cuts = []
        for cb in caption_boxes:
            # 题注文字行横跨簇的主体宽度，且确实落在簇内部
            if r.y0 + 6 < cb.y0 and cb.y1 < r.y1 - 6:
                if cb.width > r.width * 0.35:
                    cuts.append(((cb.y0 + cb.y1) / 2.0))
        if not cuts:
            out.append(r)
            continue
        cuts.sort()
        # 切口要落在题注文字**上方**，不能落在题注中间：
        #   图的簇在题注上方（切图，题注归译文/题注块），
        #   表格的簇在题注下方（切表，切口紧贴题注底）。
        # 两者都要减掉半个题注行高，否则下一切片顶部会带着半行英文。
        edges = [r.y0] + [c for c in cuts] + [r.y1]
        # 构造每个切口实际落点：把落在题注行内部的切口推到题注上沿
        snapped = []
        for c in cuts:
            top = c
            for cb in caption_boxes:
                if cb.y0 - 1 <= c <= cb.y1 + 1:
                    top = cb.y0 - 1.5
                    break
            snapped.append(top)
        edges = [r.y0] + snapped + [r.y1]
        for i in range(len(edges) - 1):
            top, bot = edges[i], edges[i + 1]
            if bot - top < 30:            # 太薄，切出来也没内容
                continue
            out.append(fitz.Rect(r.x0, top, r.x1, bot))
    return out


def _vector_clusters(page, min_side=8.0, extra_rects=None):
    """把矢量绘图路径聚成「一块图」。返回 [fitz.Rect]（按 y 从上到下）。

    ★ 为什么需要这一步：`page.get_images()` 只能抽出**位图**，
      而 Reflexion / Toolformer 这类论文的架构图是用矢量路径 + 文字画的
      （实测 Reflexion 全文 images=0），于是所有架构图在新管线里也丢了。
      矢量图没有统一的「一张图」对象，只能自己把散落的 path 框聚起来。

    ★ extra_rects（2026-11-15）：**位图 bbox 也进合并池** —— 论文里一张
      逻辑图常是「矢量底板 + 嵌入位图碎片」混编（AutoGen Figure 1 = 15 张
      嵌入位图），逐张抽位图会得到 15 个透明/黑底碎片，谁也读不了。
      把位图框当聚类种子并进来，整簇从页面渲染（渲染器自动合成
      SMask/透明度），出来就是和 PDF 里一样的完整图。

    聚类规则（够用且不易误判）：
      - 丢掉面积过小的碎片（线段、箭头、边框线）和占满整页的背景框；
      - 两个框**间距小于阈值**就合并（相邻的框和箭头本来就属于同一张图）。
    """
    import fitz
    W, H = page.rect.width, page.rect.height
    rects = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return []
    for d in drawings or []:
        try:
            r = d.get('rect')
        except Exception:
            continue
        if r is None or r.is_empty:
            continue
        if r.width < min_side or r.height < min_side:
            continue
        # 整页/近整页的框是页面装饰或背景，不是「一张图」
        if r.width > W * 0.97 and r.height > H * 0.90:
            continue
        rects.append(fitz.Rect(r))
    for r in (extra_rects or []):
        r = fitz.Rect(r)
        if not r.is_empty and not (r.width < 4 or r.height < 4):
            rects.append(r)
    if not rects:
        return []

    # 反复合并「离得近」的框，直到没有可合并的 —— 简单但对图结构够稳
    #
    # ★ 间距自己算，不用 Rect.distance_to_rect()：那个方法是较新 PyMuPDF 才有的，
    #   本机版本没有 → AttributeError 会让**整页**矢量图渲染失败（try 捕获在调用方，
    #   症状是「有的论文能出图、有的论文一张图都没有」，极难归因）。
    gap = max(14.0, min(W, H) * 0.035)

    def _gap(a, b):
        dx = max(0.0, max(a.x0 - b.x1, b.x0 - a.x1))
        dy = max(0.0, max(a.y0 - b.y1, b.y0 - a.y1))
        return (dx * dx + dy * dy) ** 0.5

    merged = True
    while merged:
        merged = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a.intersects(b) or _gap(a, b) <= gap:
                    rects[i] = a | b
                    rects.pop(j)
                    merged = True
                    break
            if merged:
                break
    # 一整页文字的宽度加上小高度，多半是表格线/分隔线而不是插图
    out = []
    for r in rects:
        if r.height < 18 and r.width > W * 0.9:
            continue
        out.append(r)
    out.sort(key=lambda r: r.y0)
    return out


def _render_region(page, rect, zoom=2.4):
    """把页面某块区域渲染成 PNG 字节（矢量架构图 → 可存可显示的位图）。

    zoom 2.4 ≈ 170 DPI：架构图里的小字在 1.0 下糊成一片，
    而放大太多图片字节暴涨，2.4 是「能看清 + 不夸张」的折中。

    ★ 返回 None 的两种情况（都表示「这块不值得当图」）：
      - 渲染失败（PDF 损坏、区域非法）；
      - **几乎全白**：切片切歪了、或框住的是页眉分隔线/章节横线，
        渲出来是一大块白底。用户看到「原文图片 · 未译」下面是一张白图，
        比没有图更糟 —— 白图会被当成「抽图抽空了」的 bug 去排查。"""
    import fitz
    try:
        # 先留一点边距：框是路径的包围盒，箭头/边框常常刚好压在边上
        r = fitz.Rect(rect)
        r.x0 = max(page.rect.x0, r.x0 - 4)
        r.y0 = max(page.rect.y0, r.y0 - 4)
        r.x1 = min(page.rect.x1, r.x1 + 4)
        r.y1 = min(page.rect.y1, r.y1 + 4)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=r, alpha=False)
        # 空白率自检：抽样（不逐像素，太慢）判断是不是白图。
        # `pix.pixel()` 返回 (r,g,b) 元组不是单通道，取灰度均值；
        # 阈值 245 而不是 220 —— 矢量图是**白底黑细线**，线只占几个百分点，
        # 用 220 会把正常的架构图/折线图全判成白图丢掉。
        w, h = pix.width, pix.height
        dark = 0
        total = 0
        step_y = max(1, h // 40)
        step_x = max(1, w // 40)
        for yy in range(0, h, step_y):
            for xx in range(0, w, step_x):
                p = pix.pixel(xx, yy)
                if not isinstance(p, (tuple, list)):
                    p = (p,)
                total += 1
                if sum(p) / len(p) < 245:
                    dark += 1
        if total and dark / total < 0.006:
            return None
        return pix.tobytes('png')
    except Exception:
        return None


def _pick_figure_regions(page, clusters, caption_boxes, W, H, text_boxes=None):
    """给每个矢量簇挑一个该「不该被抽成位图」的：太宽太扁的丢掉。

    caption_boxes：本题注块的 rect，用来给簇做**上下裁剪** ——
    论文里图和题注是紧挨着的，把题注文字框进裁图里会得到「图 + 一行英文」，
    不好看；反过来把图切掉就只剩白边。**同时**用作切分线把图/表分开。

    text_boxes：页面文字块，用来补齐表格最后一行（见下面那段注释）。"""
    import fitz
    out = []
    # 先按题注把簇切开（Reflexion：架构图与下方表格被误吸成一个大框）
    clusters = _split_clusters_by_captions(clusters, caption_boxes)
    for r in clusters:
        if r.height < 40 or r.width < 60:
            continue
        if r.width > W * 0.99 and r.height > H * 0.6:
            continue
        clip = fitz.Rect(r)
        for cb in caption_boxes or []:
            # 题注在簇**下方**且贴得近 → 把下边界收到题注上方。
            # 判定用「题注首行基线贴近下沿」，而不是「题注块整体贴近」：
            # Figure 题注常是三行（. (a) ... . (b) ...），块整体 y1 离图很远，
            # 只看 y0 距离会把整段题注（含图下第二行）一起裁进来 ——
            # 症状是渲染出的图底部挂着一行被切半的英文。
            d = cb.y0 - clip.y1
            if -2 <= d < 34:
                clip.y1 = min(clip.y1, cb.y0 - 2)
            # 题注在簇**上方** → 收上边界
            if cb.y1 <= clip.y0 + 2 and clip.y0 - cb.y1 < 34:
                clip.y0 = max(clip.y0, cb.y1 + 2)
        if clip.height < 36 or clip.width < 50:
            continue
        # ★ 表格的**最后一行**会被腰斩：矢量线（横线）在 clip.y1 就结束了，
        #   但单元格里那行字还往下探出十几 pt（实测 Reflexion 的 "CodeH [12]" 被切一半）。
        #   这里把边界延伸到「紧贴下沿、水平落在本区域内」的文字块底部。
        #   只允许小幅延伸（<=18pt）且要求文字块大部分宽度在区域内 ——
        #   否则下一段的正文会被吸进这张图里。
        if text_boxes:
            bot = clip.y1
            for tb in text_boxes:
                if tb.y0 < clip.y1 - 2 or tb.y0 > clip.y1 + 18:
                    continue
                # ★ 绝不能把题注块吸进来：
                #   题注正好贴着图的下沿，上面刚把 clip.y1 收到它上方，
                #   这里若不排除，边界又会被推回题注底下 —— 净效果是「白裁一刀」，
                #   渲染出来图底部仍挂着被切半的英文（实测 Reflexion Figure 1）。
                if any(tb.intersects(cb) for cb in (caption_boxes or [])):
                    continue
                overlap = min(tb.x1, clip.x1) - max(tb.x0, clip.x0)
                if overlap <= 0 or overlap < (tb.x1 - tb.x0) * 0.5:
                    continue
                bot = max(bot, tb.y1 + 2)
            clip.y1 = min(bot, clip.y1 + 18)
            # ★ 延伸只允许落在「题注行上方」。`get_text('blocks')` 会把
            #   表格末行和它下面的 Figure 题注**合并成同一个文本块** ——
            #   那种块上面已经被 intersects 判据排除掉了，但 clip.y1
            #   仍可能被相邻块带过题注线，表现为图底挂着半行
            #   "Figure 1: Reflexion works..."（实测 Reflexion 第 3 页）。
            #   这里显式把边界钉死在题注之上，兜住这一类。
            for cb in (caption_boxes or []):
                if clip.y1 > cb.y0 - 2 and cb.y0 - clip.y1 < 20:
                    clip.y1 = cb.y0 - 3
        # 切片必须是**正面积**的矩形：题注线可能和簇的上下边界交叉，
        # 裁完之后出现 y1 <= y0 的「倒挂」切片（实测 Reflexion 第 3 页会切出
        # y=225.9..224.4）。交给 _render_region 会被 clamp 成一条白边，
        # 白边再过一次空白率检查会被丢掉 —— 但那是靠"运气"丢的，
        # 这里直接判掉，语义明确。
        if clip.y1 - clip.y0 < 36 or clip.x1 - clip.x0 < 50:
            continue
        out.append(clip)
    return out


def _extract_pdf_pymupdf(data):
    """布局感知抽取（PyMuPDF，无需 GPU）：

    - 真实抽图（`page.get_images`，pypdf 在不少论文上返回 0 张 → 架构图/表格全丢）；
    - 多栏按 x 中心聚簇、再按阅读顺序排（pypdf layout 模式双栏会交错）；
    - 页眉/页脚 + 纯页码行剔除（MEDDxAgent 旧管线抽出行 `13803…13826` 共 24 行
      会被当正文翻译）；
    - 块分类 heading/body/caption/equation/bibliography（图是 figure），
      作为 `blocks` 附加返回，供 Phase 2 翻译层按类型区别对待
      （公式/参考文献/图片/图内文字/表格/附录 不译）；

    `text` 契约保持向后兼容：仍是「阅读顺序正文 + 内联 `![](media:name)` 占位」，
    importer / translate / QA-RAG 全部无感切换、零改动。"""
    import fitz
    doc = fitz.open(stream=data, filetype='pdf')
    media = []
    seen_hash = {}                     # 内容指纹 → 已落盘名（同图跨页复用，不重复存）
    pages_text = []
    blocks_out = []

    for pno, page in enumerate(doc):
        H, W = page.rect.height, page.rect.width
        head_m = max(48.0, H * 0.045)
        foot_m = max(48.0, H * 0.045)

        # ---- 图片：只收集**位图排版框**，不再逐张抽嵌入图（2026-11-15 重构） ----
        # ★ 旧做法 extract_image 逐张抽：论文的嵌入位图常带 SMask（透明底/
        #   半透明渐变），抽出来是黑块或灰底碎片；而且一张逻辑图往往由
        #   十几个位图碎片拼成（AutoGen Figure 1 = 15 张），逐张显示根本
        #   没法读 —— 用户原话「读的时候都不知道该怎么读了」。
        #   新做法：位图 bbox 只当**聚类种子**，与矢量路径合并成视觉簇，
        #   统一从页面整簇渲染（渲染器自动合成透明度），所见即所得。
        img_items = []                 # [(y0, xcenter, token)]
        img_rects = []                 # 位图的实际排版框（聚类种子 + 图内文字判定）
        try:
            for im in page.get_images(full=True):
                xref = im[0] if isinstance(im, (list, tuple)) else im
                try:
                    rects = page.get_image_rects(xref)
                except Exception:
                    continue
                for r0 in (rects or []):
                    if r0 and r0.width > 6 and r0.height > 6:
                        img_rects.append(fitz.Rect(r0))
        except Exception:
            pass

        # ---- 文本块（type==0 才是文字，图片块跳过，图已单独抽） ----
        tb = []
        try:
            for b in page.get_text('blocks'):
                if len(b) < 5:
                    continue
                if len(b) >= 7 and b[6] != 0:
                    continue
                txt = (b[4] or '').strip()
                if not txt:
                    continue
                tb.append((b[0], b[1], b[2], b[3], txt))
        except Exception:
            tb = []

        # 页眉/页脚区：只放过长正文；短行和纯数字都丢（基本是页眉机构名/页码）。
        # 内联页码（"… 37" / "37 …"）也剥掉，否则会混进正文被翻译。
        items = []                     # [(x0,y0,x1,y1,text,type)]
        for (x0, y0, x1, y1, txt) in tb:
            raw = txt
            if y0 < head_m or y1 > H - foot_m:
                s = re.sub(r'^\s*\d+\s*', '', raw)
                s = re.sub(r'\s*\d+\s*$', '', s).strip()
                if not s or len(s) < 4:
                    continue
                raw = s
            typ = _classify_block(raw)
            if typ == 'skip':
                continue
            items.append((x0, y0, x1, y1, raw, typ))

        # ---- 视觉簇：矢量路径 + 位图 bbox 统一聚类，整簇渲染成 PNG ----
        # ★ 旧结构是「位图逐张抽 + 矢量聚类渲染，相交让位」两套并行 ——
        #   位图碎片黑块、逻辑图被拆成 N 段的问题都出在「两套并行」上。
        #   现在 img_rects 作为 extra_rects 进 _vector_clusters 的合并池，
        #   出来的每个簇就是一张完整图（矢量底板 + 位图碎片 + 透明度全合成），
        #   _pick_figure_regions 的收边/过滤逻辑照旧生效。
        vec_rects = []                 # 渲染成功的视觉簇区域（图内文字判定用）
        try:
            import fitz as _fitz
            cap_boxes, txt_boxes = [], []
            for (x0, y0, x1, y1, txt) in tb:
                r = _fitz.Rect(x0, y0, x1, y1)
                if _classify_block(txt) == 'caption':
                    cap_boxes.append(r)
                txt_boxes.append(r)
            for reg in _pick_figure_regions(
                    page, _vector_clusters(page, extra_rects=img_rects),
                    cap_boxes, W, H, txt_boxes):
                png = _render_region(page, reg)
                if not png:
                    continue
                h = hashlib.sha1(png).hexdigest()[:10]
                if h in seen_hash:
                    tname = seen_hash[h]
                else:
                    tname = '%s_fig_p%d.png' % (h, pno)
                    media.append({'name': tname, 'mime': 'image/png', 'data': png})
                    seen_hash[h] = tname
                img_items.append((reg.y0, (reg.x0 + reg.x1) / 2,
                                  '![](media:%s)' % tname))
                vec_rects.append(_fitz.Rect(reg))
        except Exception as e:
            sys.stderr.write('[docparse] 视觉簇渲染失败（该页不处理）：%s\n' % e)

        # ---- 表格框（find_tables）：框内单元格文字「保留原文不译」 ----
        try:
            tab_rects = [fitz.Rect(t.bbox) for t in page.find_tables().tables]
        except Exception:
            tab_rects = []
        fig_rects = img_rects + vec_rects

        # ---- 阅读顺序：先分栏，栏内按 y，同 y 按 x ----
        cen = [(x0 + x1) / 2 for (x0, y0, x1, y1, txt, typ) in items] + \
              [xc for (y0, xc, tok) in img_items]
        colmap = _assign_columns(cen, W)
        n = len(items)
        merged = []
        for k, (x0, y0, x1, y1, txt, typ) in enumerate(items):
            c = colmap[k] if k < n else 0
            merged.append((c, y0, x0, 'text', txt, typ, (x0, y0, x1, y1)))
        for j, (y0, xc, tok) in enumerate(img_items):
            c = colmap[n + j] if n + j < len(cen) else 0
            merged.append((c, y0, xc, 'img', tok, 'figure', None))
        merged.sort(key=lambda m: (m[0], m[1], m[2]))

        lines = []
        territory = None               # 图领地（2026-11-15，语义见 _link_fig）
        for m in merged:
            if m[3] == 'img':
                lines.append(m[4])
                # ★ figure 块必须**带着 media token** 进 blocks：
                #   否则切到「按块翻译」后图片会丢（text 里的 token 不被块引用）。
                #   翻译层对 figure 段原样保留（protect 也会保 token），
                #   前端据此渲染原图 + 「原文图片·未译」徽标。
                blk = {'type': 'figure', 'text': m[4], 'page': pno}
                blocks_out.append(blk)
                # caption/figtext 关联：连续 img 追加进同一领地（合成图场景），
                # 图题挂给领地全体。★ 只加字段不改 text —— srcHash 不变，
                # 旧文档已翻好的译文不会因此失效。
                if territory is None:
                    territory = []
                territory.append(blk)
                continue
            txt, typ = m[4], m[5]
            # ---- 图/表内部文字：跟着原图/表格原样保留，不送模型 ----
            #   架构图的标签（"Experience (long-term memory)"）和表格单元格
            #   （"GPT-3.5-turbo 8 9 7"）被当正文逐段送模型会被改写得面目全非，
            #   而它们本来就以原图/表格形式展示 —— 原样保留最稳。
            #   题注（caption）不在这里拦：题注是给人读的句子，照常翻译。
            #   附录/参考文献区是**整节**语义，放到 _mark_refs_and_appendix
            #   对块序列二次扫描（要跨页状态 + 前瞻确认），不在这里做。
            if typ not in ('caption', 'heading', 'bibliography', 'equation'):
                r = fitz.Rect(*m[6])
                if _overlap_ratio(r, fig_rects) >= 0.55:
                    typ = 'figtext'
                elif _overlap_ratio(r, tab_rects) >= 0.6 and _looks_tabular(txt):
                    typ = 'table'
            if typ == 'heading':
                txt = _normalize_heading(txt)

            # ---- 图内文字：**不进正文流**（2026-11-15 用户反馈）----
            #   信息已并入 figure 块的 figtext 字段 + VLM 解读卡；
            #   独立成段的表现是对照页一半是「图内文字·保留原文」碎片，
            #   读的人反而看不到图。领地开 → 挂全体；领地没开（渲染失败
            #   的簇 / 图 token 在后）→ 直接丢弃，游离的图内文字没有上下文。
            if typ == 'figtext':
                if territory:
                    territory, _ = _link_fig(territory, 'figtext', txt)
                continue

            # ---- 领地内的其它块：短标签并入 figure 块；图题挂领地 ----
            if territory is not None:
                territory, action = _link_fig(territory, typ, txt)
                if action == 'label':
                    continue                 # 已并入 figure 块 figtext，不成段
                if action == 'caption':
                    lines.append(txt)
                    blocks_out.append({'type': 'caption', 'text': txt, 'page': pno})
                    continue                 # 图题照常成段、照常翻译

            lines.append(txt)
            blocks_out.append({'type': typ, 'text': txt, 'page': pno})
        pages_text.append('\n'.join(lines))

    _mark_paper_title(blocks_out)
    _mark_refs_and_appendix(blocks_out)
    return {'text': '\n'.join(pages_text),
            'media': [{'name': m['name'], 'mime': m['mime'], 'data': m['data']}
                      for m in media],
            'blocks': blocks_out}


def _extract_pdf_pypdf(data):
    """旧版 pypdf 实现，作为 PyMuPDF 不可用时的兜底。行为与原先一致。"""
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


def extract_pdf(data):
    """PDF → 正文 + 图片清单（+ 块类型列表）。

    优先 PyMuPDF（布局感知：真抽图、多栏重排、去页码、块分类）；
    装不上或抽失败则退回 pypdf 兜底，宁可碎片也别整份抽不出来。
    两者都没装抛 no_pypdf，上层给 pip install 的路。"""
    try:
        return _extract_pdf_pymupdf(data)
    except Exception as e:
        sys.stderr.write('[docparse] PyMuPDF 抽取失败，退回 pypdf：%s\n' % e)
        return _extract_pdf_pypdf(data)


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
