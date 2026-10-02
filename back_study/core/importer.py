# -*- coding: utf-8 -*-
"""导入器：把一段原始文本（网页复制 / 笔记 / 面经）切成草稿卡

两条路：
  1) 本地启发式（默认，零成本）：按标题行切段，连续编号行进 mechanism
  2) LLM 抽取（设了环境变量 LLM_API_KEY 才启用）：输出严格符合 schema 的 JSON

产出都是「草稿」，落盘 data/store/drafts.json，确认补全后再入库，
避免半自动的脏数据直接污染卡库。
"""
import hashlib
import json
import re

import db
import docparse
import llm

TITLE_RES = [
    re.compile(r'^#{1,6}\s+(.+)$'),                     # markdown 标题
    re.compile(r'^【(.+)】\s*$'),                        # 【xxx】
    re.compile(r'^\d{1,2}[.、)]\s*(.+)$'),               # 1. / 1、/ 1)
    re.compile(r'^[一二三四五六七八九十]{1,3}[、.]\s*(.+)$'),  # 一、
    re.compile(r'^第[一二三四五六七八九十\d]+[章节部分]\s*(.*)$')
]
NUM_RE = re.compile(r'^\d{1,2}[.、)]\s+\S')
DASH_RE = re.compile(r'^\s*[-•·*]\s+\S')
BULLET_RE = re.compile(r'^\s*([-•·*]|[①②③④⑤⑥⑦⑧⑨⑩]|\d{1,2}[.、)]|（\d+）)\s*\S')
ORD = '①②③④⑤⑥⑦⑧⑨⑩'


def cut(s, n):
    return s[:n] + '…' if len(s) > n else s


def clean_bullet(line):
    return re.sub(r'^\s*([-•·*]|[①②③④⑤⑥⑦⑧⑨⑩]|\d{1,2}[.、)]|（\d+）)\s*', '', line).strip()


def is_bullet(line):
    return bool(BULLET_RE.match(line))


def mark_list_items(lines):
    """连续编号行（1. 2. 3.）是步骤，不是章节标题。
    之前没做这一步，一张卡被切成了 6 张。"""
    flags = []
    for i, l in enumerate(lines):
        if not (NUM_RE.match(l) or DASH_RE.match(l)):
            flags.append(False)
            continue
        prev = lines[i - 1] if i > 0 else ''
        nxt = lines[i + 1] if i < len(lines) - 1 else ''
        flags.append(bool(NUM_RE.match(prev) or DASH_RE.match(prev)
                          or NUM_RE.match(nxt) or DASH_RE.match(nxt)))
    return flags


def pick_keywords(title, body):
    """英文术语 + 标题 + 正文里重复出现的中文词（n-gram 词频，比硬切词靠谱）"""
    text = (title or '') + ' ' + (body or '')
    en = list(dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z0-9_.]{2,}', text)))[:5]
    cnt = {}
    for run in re.findall(r'[\u4e00-\u9fa5]{4,}', text):
        for n in (2, 3):
            for i in range(len(run) - n + 1):
                g = run[i:i + n]
                cnt[g] = cnt.get(g, 0) + 1
    cn = sorted([g for g, c in cnt.items() if c >= 2], key=lambda g: -cnt[g])[:4]
    merged = [title] + en + cn
    return list(dict.fromkeys([x for x in merged if x]))[:8]


def _draft_ids(text, opts, n):
    """给这一次导入生成 n 个**互相不撞、也能跨批次区分**的草稿 id。

    ★ 为什么不能只用「日期 + 批内序号」：同一天导入第二次，第 1 块又叫
    `imp-20261001-1`，与第一次那份草稿**同名**。后果是三重的：
      1. `publish` 按 id 匹配 cards.custom.json → 第二份发布的卡直接
         **覆盖**第一份已发布的卡；
      2. `drop_draft` 删的是「所有同 id 草稿」→ 发布 B 会把 A 的草稿一起删；
      3. `PUT /api/drafts/{id}` 只命中第一条 → 编辑第二条实际改的是第一条。
    一次「同一天导两次」就全中，不需要 LLM 路径。

    现在把**内容指纹**编进 id：内容不同 → id 必然不同；同一段文字导两次 →
    id 相同（这是想要的，`save_drafts` 按 id upsert 覆盖成同一份，
    而不是并存两条同名草稿）。

    ⚠️ 别在这里加「发现 id 已存在就往后挪一位」的避让循环 —— 我加过，
    然后实测发现它**恰好把幂等性毁掉**：第二次导入同一段文字时，
    避让逻辑看到草稿列表里已有这个 id，就把新 id 挪成 `...-1x`，
    于是同一段资料每导一次就多一条草稿，正是要修的那个毛病。
    id 撞车该在**发布时**判（`publish`：撞到已有卡就报错，不覆盖）。
    """
    stamp = db.today_str().replace('-', '')
    base = '%s-%s' % (stamp, hashlib.md5(text.encode('utf-8')).hexdigest()[:8])
    return ['imp-%s-%d' % (base, i + 1) for i in range(max(1, n))]


def parse_local(text, opts=None):
    opts = opts or {}
    lines = [l.strip() for l in text.replace('\r\n', '\n').split('\n')]
    lines = [l for l in lines if l]
    flags = mark_list_items(lines)

    blocks = []
    cur = None
    for i, line in enumerate(lines):
        title = None
        if not flags[i]:                        # 列表项永不当标题
            for r in TITLE_RES:
                m = r.match(line)
                if m:
                    title = (m.group(1) or line).strip()
                    break
        if title and len(title) <= 60:
            cur = {'title': title, 'body': []}
            blocks.append(cur)
            continue
        if cur is None:
            cur = {'title': '', 'body': []}
            blocks.append(cur)
        cur['body'].append(line)

    cards = []
    ids = _draft_ids(text, opts, len(blocks))
    for i, b in enumerate(blocks):
        bullets = [clean_bullet(l) for l in b['body'] if is_bullet(l)]
        plain = [l for l in b['body'] if not is_bullet(l)]
        title = b['title'] or cut(plain[0] if plain else (bullets[0] if bullets else '未命名'), 30)
        mech = bullets if bullets else [l for l in plain if len(l) > 8]
        if not mech:
            mech = ['（导入时未识别出步骤，需手工补充原理拆解）']
        mech = [(ORD[k] + ' ' + s) if k < len(ORD) else ('%d. %s' % (k + 1, s))
                for k, s in enumerate(mech)]
        cards.append({
            'id': ids[i],
            'domain': opts.get('domain') or '待归类',
            'category': opts.get('category') or '',
            'subject': opts.get('subject') or '',
            'topicPath': list(opts.get('topicPath') or ['导入']),
            'title': title,
            'oneLine': cut(plain[0] if plain else (bullets[0] if bullets else ''), 60),
            'mechanism': mech,
            'keywords': pick_keywords(title, ' '.join(b['body'])),
            'scene': ['（待补充：在你做过的项目里这条用在哪）'],
            'interviewQ': ['（待补充：面试官会怎么追问这条）'],
            '_draft': True,
            '_from': 'local'
        })

    cards = [c for c in cards if c['title'] and c['title'] != '未命名']
    if not cards and text.strip():
        first = text.strip().split('\n')[0]
        cards.append({
            'id': _draft_ids(text, opts, 1)[0],
            'domain': opts.get('domain') or '待归类',
            'category': opts.get('category') or '',
            'subject': opts.get('subject') or '',
            'topicPath': list(opts.get('topicPath') or ['导入']),
            'title': cut(first, 40),
            'oneLine': cut(first, 60),
            'mechanism': [l for l in text.strip().split('\n') if l],
            'keywords': pick_keywords(first, text),
            'scene': ['（待补充）'], 'interviewQ': ['（待补充）'],
            '_draft': True, '_from': 'local'
        })
    return cards


# ---------- 整份文档：自动分章 ----------
# 思路：先认「确定的标题」（markdown #、第X章、多级编号），没有就退化成按长度分块。
# 不做字体/字号分析——纯文本层拿不到；也不做目录页解析——收益低、误伤高。
MD_HEAD = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
RE_CHAPTER = re.compile(r'^第\s*[一二三四五六七八九十百零两\d]+\s*(章|节|讲|部分|篇)(?![\u4e00-\u9fa5])')
RE_D3 = re.compile(r'^\d+\.\d+\.\d+[\s、.:：]+')
RE_D2 = re.compile(r'^\d+\.\d+[\s、.:：]+')
RE_BRACKET = re.compile(r'^【.+】\s*$')
RE_CN_NUM = re.compile(r'^[一二三四五六七八九十]{1,3}[、.．)）]\s*\S')
RE_AR_NUM = re.compile(r'^\d{1,2}[、.．)）]\s*\S')


def detect_heading(line):
    """判断一行是不是章节标题，返回 (level, title)；不是则 None。
    只负责「像不像标题」，连续编号列表由调用方用 mark_list_items 排除。"""
    s = line.strip()
    if not s or len(s) > 60:
        return None
    m = MD_HEAD.match(s)
    if m:
        return (len(m.group(1)), m.group(2).strip())
    if RE_CHAPTER.match(s):
        return (1, s)
    if RE_D3.match(s):
        return (3, s)
    if RE_D2.match(s):
        return (2, s)
    if RE_BRACKET.match(s):
        return (2, s)
    if RE_CN_NUM.match(s):
        return (2, s)
    if RE_AR_NUM.match(s):
        return (2, s)
    return None


#: 分章粒度目标。一章 ≈ 一张卡的素材：5000 字够写清一个考点；
#: 超了说明这一层太粗，往细一层再切（子标题并入后的正文会变小）。
MAX_CHAPTER_CHARS = 5000


def _fold_at(heads, lines, split_lvl):
    """在层级 split_lvl 切一刀：level ≤ split_lvl 的标题开新章，
    内容到下一个「同级或更浅」的标题为止 —— 更深的标题行**原样留在正文里**，
    子层内容完整并进父章，不产生「只有标题没正文」的空壳章。

    返回 (chapters, pre)：pre = 第一个分章标题之前的正文（前言候选，
    比首标题更浅的前导内容也在这里，不丢）。"""
    start = next(k for k, (_, lvl, _) in enumerate(heads) if lvl <= split_lvl)
    pre = '\n'.join(lines[:heads[start][0]]).strip()
    chs = []
    for idx in range(start, len(heads)):
        li, lvl, h = heads[idx]
        if lvl > split_lvl:
            continue                        # 深层标题：不是边界，内容留在本章
        end = len(lines)
        for li2, lvl2, _ in heads[idx + 1:]:
            if lvl2 <= split_lvl:
                end = li2
                break
        chs.append({'level': lvl, 'title': h,
                    'body': '\n'.join(lines[li + 1:end]).strip()})
    return chs, pre


def _fold_chapters(heads, lines):
    """多级标题 → 选一个切分层级折叠成章节。返回 (chapters, pre)。

    选层规则（由粗到细）：先看最粗的层级，切出来**每章正文都不超
    MAX_CHAPTER_CHARS 且至少 2 章**就定下 —— 章越大内容越完整。
    没有任何层够 2 章时（单节文档）取**最细的**尺寸合格层：单节文档里
    最深的标题才是正文的真章名（`# 组标题 / ## 一章` 该切成「一章」，
    而不是把整节折进「组标题」）；每层都塞爆就取最深层，超长由单章上限截。
    正文为空的壳章丢掉（留着只会在解析报告和出卡里变成永远出不了内容的
    死章）；整份文档只有标题没正文的退化情形保留原章，别把 chapters 弄空。"""
    levels = sorted({lvl for _, lvl, _ in heads})
    picked = None                               # 最粗的「≥2 章且尺寸合格」层
    size_ok = None                              # 最细的尺寸合格层（兜底）
    for lvl in levels:
        chs, pre = _fold_at(heads, lines, lvl)
        live = [c for c in chs if (c['body'] or '').strip()]
        if not live:
            continue
        if max(len(c['body']) for c in live) > MAX_CHAPTER_CHARS:
            continue                            # 这一层太粗，往细走
        if len(live) >= 2:
            picked = (chs, pre)
            break                               # 又够粗又够章数 → 定了
        size_ok = (chs, pre)                    # 只有 1 章：继续往细找 ≥2 的
    if picked:
        chs, pre = picked
    elif size_ok:
        chs, pre = size_ok
    else:
        # 每一层都有超大章（标题层级不够深）→ 取最细一层，超长由单章上限截
        chs, pre = _fold_at(heads, lines, levels[-1])
    live = [c for c in chs if (c['body'] or '').strip()]
    return (live or chs), pre


def parse_document(text, opts=None):
    """把一整份文档切成章节树。
    返回 {title, chapters:[{level,title,body}], stats:{chapters,chars,headings}}。

    分章优先级：markdown 标题 > 第X章/节 > 多级编号(N.M) > 括号/中文序号 > 兜底按长度分块。
    切法是**按层级折叠**（见 _fold_chapters）：只在选定层级切，子标题和它的
    内容整块并进父章 —— 一章内容完整，没有空壳章；层级只按「编号深度」粗分，
    够用了——再细的语义层级纯文本也猜不准。"""
    opts = opts or {}
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    stripped = [l.strip() for l in lines]

    # 连续编号列表（1. 2. 3.）是列表项，不该当标题——复用卡片切分那套判断
    nonempty_idx = [i for i, l in enumerate(stripped) if l]
    flags = mark_list_items([stripped[i] for i in nonempty_idx])
    is_list = {}
    for k, i in enumerate(nonempty_idx):
        is_list[i] = flags[k]

    heads = []                                  # (行号, level, 标题)
    for i, s in enumerate(stripped):
        if not s or is_list.get(i):
            continue
        d = detect_heading(s)
        if d:
            heads.append((i, d[0], d[1]))

    chapters = []
    title = (opts.get('title') or '').strip()
    if heads:
        chapters, pre = _fold_chapters(heads, lines)
        if len(pre) > 20:                       # 首个分章标题前有正文 → 当作前言
            chapters.insert(0, {'level': 1, 'title': '前言', 'body': pre})
        if not title:
            # 文档名取「层级最浅、位置最靠前」的那个标题
            title = min(heads, key=lambda x: (x[1], x[0]))[2]

    if not chapters:                            # 全篇没识别出标题 → 按段落+长度兜底
        paras = re.split(r'\n\s*\n', text.strip())
        buf, size = [], 0
        for p in paras:
            if not p.strip():
                continue
            buf.append(p)
            size += len(p)
            if size >= 1800:
                chapters.append({'level': 1, 'title': '', 'body': '\n\n'.join(buf).strip()})
                buf, size = [], 0
        if buf:
            chapters.append({'level': 1, 'title': '', 'body': '\n\n'.join(buf).strip()})
        if not chapters:
            chapters = [{'level': 1, 'title': '', 'body': text.strip()}]
        for i, ch in enumerate(chapters):
            head = ch['body'].split('\n')[0][:24] if ch['body'] else ''
            ch['title'] = ('第%d部分 ' % (i + 1)) + head
        if not title:
            title = opts.get('filename') or '未命名文档'

    base = min(c['level'] for c in chapters)    # 层级归一到从 1 起，前端缩进才好看
    for c in chapters:
        c['level'] = max(1, c['level'] - base + 1)
        c['body'] = c['body'][:20000]           # 单章上限，防一条塞爆前端

    return {'title': title or '未命名文档', 'chapters': chapters,
            'stats': {'chapters': len(chapters), 'chars': len(text), 'headings': len(heads)}}


def extract_pdf_bytes(data):
    """PDF 抽文字。标准库做不到，靠可选的 pypdf。
    没装就抛 no_pypdf，让上层给出「pip install pypdf」的提示，而不是 500。
    （实现已搬到 core/docparse.py —— 那边还负责把 PDF 里的图片抠出来。
     这个名字留给 scripts/gen_docs.py 这类只要文字的调用方。）"""
    return docparse.extract_pdf_bytes(data)


def extract_docx_bytes(data):
    """Word(.docx) 抽文字。实现已搬到 core/docparse.py（那边还负责把
    word/media 里的图片抠出来、按顺序插占位符）—— 这里只留转调，
    免得有第二个「解析 docx」的真相源。"""
    return docparse.extract_docx_bytes(data)


# ---------- 结构精修（cards Agent 的 structure 阶段用） ----------
def structure_items(chapters):
    """把章节摘要成给 llm.refine_structure 的清单：标题/层级/字数/开头。
    正文不带（占上下文），图片占位符从开头里滤掉。"""
    out = []
    for c in chapters:
        body = c.get('body') or ''
        head = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', body).strip()
        out.append({'title': c.get('title') or '',
                    'level': c.get('level') or 1,
                    'chars': len(body),
                    'head': head[:60]})
    return out


def apply_structure(chapters, plan):
    """按结构方案重切章节。返回 (new_chapters, docTitle)。

    方案合法性在这里**严格校验**：idx 必须是 0..n-1 的一个顺序划分
    （每个下标恰好一次、组内升序、组间衔接）。不合法就原样返回 ——
    结构精修是增强不是地基，模型抽风时保留规则初切的结果，别把导入链弄断。
    图片占位符是正文里的普通行，合并 body 时自然跟着走，不需要特殊处理。"""
    groups = (plan or {}).get('chapters') or []
    flat = []
    for g in groups:
        if not isinstance(g, dict) or not isinstance(g.get('idx'), list) \
                or not g['idx']:
            return chapters, ''
        for i in g['idx']:
            if not isinstance(i, int) or i < 0 or i >= len(chapters):
                return chapters, ''
            flat.append(i)
    if flat != list(range(len(chapters))):
        return chapters, ''                     # 漏了 / 重复了 / 乱序 → 拒绝执行

    out = []
    for g in groups:
        mem = [chapters[i] for i in g['idx']]
        level = g.get('level')
        if not isinstance(level, int) or not 1 <= level <= 3:
            level = mem[0].get('level') or 1
        title = str(g.get('title') or '').strip() or (mem[0].get('title') or '')
        body = '\n\n'.join((m.get('body') or '').strip() for m in mem).strip()
        out.append({'level': level, 'title': title[:80], 'body': body[:20000]})

    base = min(c['level'] for c in out)
    for c in out:
        c['level'] = max(1, c['level'] - base + 1)
    return out, str((plan or {}).get('docTitle') or '').strip()


SYS = ('你是技术面试考点结构化助手。把用户给的资料拆成多张「原理卡」，'
       '输出严格 JSON：{"cards":[{id,domain,topicPath[],title,oneLine,analogy,why,'
       'mechanism[],scene[],interviewQ[],keywords[],tags[]}]}。'
       '要求：mechanism 必须是有序步骤（描述它怎么跑，不是定义）；analogy 用一句生活类比；'
       'scene 写真实系统里的具体用法或坑，禁止「广泛应用」这类空话；一张卡只讲一个点。'
       'id 用英文短横线。只输出 JSON。')


def parse_llm(text, opts=None):
    """LLM 抽取：走 llm.py 的统一通道（本机 Ollama 或云端 key），
    不再自己拼 HTTP —— 免得两处各写一份、只改一处导致云端能跑本地不能跑。"""
    opts = opts or {}

    st = llm.status()
    if not st.get('ok'):
        raise RuntimeError('no_key' if llm.provider() == 'cloud' else 'no_model')

    sys_msg = SYS + (' 领域固定为：' + opts['domain'] if opts.get('domain') else '')
    msgs = [{'role': 'system', 'content': sys_msg},
            {'role': 'user', 'content': '请把下面资料拆成原理卡：\n\n' + text[:12000]}]
    raw = llm._call(msgs, st.get('model'), timeout=600, max_tokens=3000)
    try:
        out = llm._clean_json(raw)
    except ValueError:
        raise RuntimeError('llm_not_json')
    if isinstance(out, list):                       # 有的模型直接吐数组
        out = {'cards': out}
    ids = _draft_ids(text, opts, len(out.get('cards') or []))
    cards = []
    for c in out.get('cards', []):
        if not isinstance(c, dict):
            continue
        c['_draft'] = True
        c['_from'] = 'llm'
        c.setdefault('domain', opts.get('domain') or '待归类')
        c.setdefault('topicPath', list(opts.get('topicPath') or ['导入']))
        cards.append(c)
    if not cards:
        raise RuntimeError('llm_not_json')
    # ★ 模型给的 id 一律丢掉，换成我们发的号。
    # 原因：模型不保证全局唯一，实测会出现重复 id（同一批里两张卡同名），
    # 也会撞上已有自定义卡 —— 前者让两张草稿互相覆盖，后者让 publish
    # 变成「静默替换别人已发布的卡」。草稿 id 的权威在我们这边，
    # 不在提示词里。
    for i, c in enumerate(cards):
        c['id'] = ids[i]
    return cards


# ---------- 草稿 ----------
# 一律走 db 的这两个函数，不要直接碰文件 —— 走了 MySQL 后端以后文件里是空的，
# 直接读文件会得到「草稿凭空消失」的假象。
def save_drafts(cards):
    """按 id upsert，不是无脑 append。

    从前是 `all_.extend(cards)`：同一天对同一段资料点两次「导入」就会
    并存两条**同 id** 的草稿，此后「丢弃」一次删两条、「补齐字段」只改
    第一条、「入库」只发布第一条 —— 用户看到的是「改了没生效 / 删了少两条」，
    而且这两条同名草稿在列表里长得一模一样，根本分辨不出来。

    现在草稿 id 带内容指纹（见 `_draft_ids`），所以「同一段资料重复导入」
    必然落到同一个 id 上，upsert 让它**覆盖**成一份 —— 这才符合直觉：
    重复导入同一份东西，本来就该是一件事。
    """
    all_ = db.load_drafts()
    index = {}
    for i, d in enumerate(all_):
        index.setdefault(str(d.get('id') or ''), i)
    for c in cards:
        cid = str(c.get('id') or '')
        if cid and cid in index:
            merged = dict(all_[index[cid]])
            merged.update(c)                 # 新一次导入的字段覆盖旧的
            all_[index[cid]] = merged
        else:
            if cid:
                index[cid] = len(all_)
            all_.append(c)
    db.save_drafts(all_)
    return len(all_)


def list_drafts():
    return db.load_drafts()


def clear_drafts():
    for d in db.load_drafts():
        docparse.delete_media('card-' + str(d.get('id') or ''))
    db.save_drafts([])


def drop_draft(did):
    db.save_drafts([d for d in list_drafts() if d.get('id') != did])
    # 配图随草稿删掉；但同 id 的卡**已发布**时不能删 —— 发布过的卡还指着
    # card-<id> 这个目录（重导入同一份资料会造出同 id 草稿）。
    if did and not any(c.get('id') == did for c in db.load_custom()):
        docparse.delete_media('card-' + str(did))


def validate(c):
    """必填校验。scene 至少 2 条真实场景是项目定的硬规矩。"""
    miss = []
    for k in ['id', 'domain', 'title', 'oneLine', 'mechanism', 'keywords']:
        v = c.get(k)
        if not v or (isinstance(v, list) and not v):
            miss.append(k)
    if len(c.get('scene') or []) < 2:
        miss.append('scene(至少2条)')
    return miss


def publish(did):
    d = next((x for x in list_drafts() if x.get('id') == did), None)
    if d is None:
        return {'ok': False, 'msg': '草稿不存在: ' + did}
    miss = validate(d)
    if miss:
        return {'ok': False, 'msg': '字段不完整: ' + ' / '.join(miss)}
    custom = db.load_custom()
    copy = json.loads(json.dumps(d))
    copy.pop('_draft', None)
    copy.pop('_from', None)
    # ★ 撞 id 必须报错，不能静默替换。
    # 从前的写法是 `for i, c in enumerate(custom): if c['id'] == copy['id']:
    # custom[i] = copy` —— 一张**人工写好、已经发布**的卡就这样被草稿无声覆盖，
    # 而且接口回 ok:true。宁可让人看到「id 已被占用」再去改 id。
    if any(c.get('id') == copy['id'] for c in custom):
        return {'ok': False,
                'msg': '已存在同 id 的卡片（%s）：改一下草稿标题重新导入，'
                       '或先在卡片库里删掉那张再发布' % copy['id']}
    custom.append(copy)
    db.save_custom(custom)
    # 从草稿列表移除，但**不删配图**（drop_draft 会删）：发布的卡还要读
    # card-<id> 目录。直接改列表，语义 = 这张卡搬去正式卡库了。
    db.save_drafts([d for d in list_drafts() if d.get('id') != did])
    return {'ok': True, 'card': copy}
