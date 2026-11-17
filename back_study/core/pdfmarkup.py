# -*- coding: utf-8 -*-
"""把 PDF 抽出来的裸文本，重构成带 markdown 结构的文本。

## 为什么需要它

`docparse.extract_pdf` 用 pypdf 逐页抽纯文本，拿到的东西是**没有结构的**：

    function Demo(target: Function) {      ← 代码，没有任何标记
    console.log(target)                  ← 不知道这是代码
    }                                     ← 渲染成普通段落
    基本语法 TypeScript                   ← 这是标题，但只是普通行
    3                                     ← 这是页码，不是内容

直接丢给 MarkdownRenderer 的后果就是你截图看到的那样：代码是正文、标题全是正文、
页码混在中间。**PDF 的版面信息在纯文本层根本不存在**（字号、缩进、栏位都丢了），
所以这里只能靠特征把它**找回来**。

## 三件事

1. **代码块识别**：连续的、带代码特征的行 → 包 ``` 围栏 + 语言标注
2. **页码/噪声剔除**：纯数字短行、单字符乱码行
3. **标题降噪**：识别 PDF 标题行，但不越级

## 明确不做的事

**不做版面还原**。pypdf 给的坐标信息不足以重建双栏/表格，而 PDF 本身常常
就是排版混乱的（页码混进正文、代码块被页边截断、顺序错乱）。
与其猜错，不如老实标出代码 + 清掉噪声，其余交给人看。
"""
import re

# ---------- 代码特征 ----------
#: 判定「这行像代码」的强信号。命中任意一条就加分。
_CODE_STRONG = [
    re.compile(r'^\s*(function|class|const|let|var|def|import|export|package)\b'),
    re.compile(r'^\s*(interface|type|enum|namespace|struct|impl|public|private|protected)\b'),
    re.compile(r'^\s*(if|for|while|switch|catch|try)\s*[({]'),
    re.compile(r'^\s*(return|throw|break|continue)\b'),
    re.compile(r'^\s*[})\]]+[;,]?\s*$'),                  # 收尾的大括号
    re.compile(r'=>|::|->|\+=|-=|\*=|/='),               # 运算符
    re.compile(r'^\s*@\w+'),                              # 装饰器（TS/Java/Python）
    re.compile(r'console\.(log|warn|error)|print\(|System\.out'),
    re.compile(r'^\s*(</\w+>|/>|<[a-z][\w-]*\s*/?>)'),   # JSX
]
#: 弱信号：只是「长得像代码」，不能单独作为判定依据。
_CODE_WEAK = re.compile(r'[;{}()\[\]]|=>|::|==|!=|&&|\|\||</|/>|=')

#: 语言猜测。按关键字命中率打分，取最高分。
_LANG_HINTS = [
    # TypeScript/JavaScript 的类型标注。: 后跟**任意**标识符也算 ——
    # 只认 string/number/boolean/any 的话，`function f(target: Function)`
    # 这种最常见的签名反而判不出来。
    ('typescript', re.compile(
        r'\b(interface|enum|namespace|declare)\b'
        r'|\b(public|private|protected)\s+\w+\s*[:(]'
        r'|:\s*[A-Z]\w*[\s,){;]|:\s*(string|number|boolean|any|void|unknown)\b'
        r'|=>|\bconsole\.')),
    ('python', re.compile(r'^\s*(def|class)\s+\w+.*:\s*$|^\s*(from|import)\s+\w+\s*$'
                          r'|\bself\.|\bprint\(')),
    ('java', re.compile(r'\b(public|private|protected)\s+(static\s+)?(class|void|int|String)\b'
                        r'|System\.out')),
    ('go', re.compile(r'^\s*func\s+\w*\s*\(|^\s*package\s+\w+|:=|\bfmt\.')),
    ('sql', re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|FROM|WHERE)\b',
                       re.I)),
    ('bash', re.compile(r'^\s*(npm|yarn|git|docker|kubectl|pip|cd|ls|curl)\s')),
]

#: 一段代码至少这么多行才值得包起来（1~2 行多半是正文里的括号/分号）。
_MIN_CODE_LINES = 3
#: 代码行占比低于这个数就不算代码段（正文里夹几行代码很常见）。
_MIN_CODE_RATIO = 0.6

#: 页码：整行只有一个很短的数字，且整篇里这样的行很多。
_PAGE_NO = re.compile(r'^\s*\d{1,4}\s*$')
#: 乱码：PDF 字体缺失时常出现私用区字符（U+E000~U+F8FF）。
_PUA = re.compile(r'[\ue000-\uf8ff]')


def _score_line(s):
    """这行有多像代码。返回 (是否强特征, 命中数)。"""
    strong = any(p.search(s) for p in _CODE_STRONG)
    weak = len(_CODE_WEAK.findall(s))
    return strong, weak


def _guess_lang(lines):
    text = '\n'.join(lines)
    best, best_score = '', 0
    for lang, pat in _LANG_HINTS:
        score = len(pat.findall(text))
        if score > best_score:
            best, best_score = lang, score
    return best or ''


def find_code_spans(lines):
    """找出代码段。返回 [(start, end)]，end 不含（半开区间）。

    判定逻辑：连续若干行里，「强特征行」占多数且总数够 → 整段当代码。
    用强特征而不是弱信号（`=`、`()` 正文里满地都是）是为了不把
    「参数 = 5」「见下表(x)」这类正文误判成代码。
    """
    spans = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i]
        if not s.strip():
            i += 1
            continue
        strong, _ = _score_line(s)
        if not strong:
            i += 1
            continue
        # 从这一行往后吃，吃到「连续两行都不像代码」为止
        j = i
        hits = 0
        last_code = i
        while j < n:
            cur = lines[j]
            if not cur.strip():
                # 段落之间空一行：代码块内部允许，但连着两行空就收
                if j + 1 < n and not lines[j + 1].strip():
                    break
                j += 1
                continue
            st, _ = _score_line(cur)
            if st:
                hits += 1
                last_code = j
            elif j > last_code + 1:
                break
            j += 1
        span = last_code - i + 1
        ratio = hits / float(span) if span else 0
        if span >= _MIN_CODE_LINES and ratio >= _MIN_CODE_RATIO:
            spans.append((i, last_code + 1))
            i = last_code + 1
        else:
            i += 1
    return spans


def drop_page_numbers(lines, threshold=None):
    """剔除页码行。

    阈值自适应：整篇里「纯数字短行」超过 6 行才认定那是页码 ——
    否则一份数学文档里的 `1` `2` `3`（推导步骤）会被整段删掉。
    """
    hits = [i for i, l in enumerate(lines) if _PAGE_NO.match(l) and len(l.strip()) <= 4]
    if threshold is None:
        threshold = 6
    if len(hits) < threshold:
        return lines
    drop = set(hits)
    return [l for i, l in enumerate(lines) if i not in drop]


def clean_pua(lines):
    """去掉 PDF 私用区乱码字符（字体缺失时 pypdf 会吐 U+E000 之类）。"""
    return [_PUA.sub('', l) for l in lines]


def to_markdown(text, min_ratio=_MIN_CODE_RATIO):
    """裸文本 → 结构化 markdown。只做「认代码 + 清噪声」，不动标题层级
    （标题由 importer 的分章负责，这里再判一次会和它打架）。"""
    lines = clean_pua((text or '').replace('\r\n', '\n').split('\n'))
    lines = drop_page_numbers(lines)
    spans = find_code_spans(lines)
    if not spans:
        return '\n'.join(lines).strip()

    out = []
    prev = 0
    for a, b in spans:
        out.extend(lines[prev:a])
        lang = _guess_lang(lines[a:b])
        out.append('```' + lang)
        out.extend(lines[a:b])
        out.append('```')
        prev = b
    out.extend(lines[prev:])
    return '\n'.join(out).strip()


# ---------- 标题层级 ----------
#: 中文数字序：一、二、三 … 一百零八。PDF 的章标题几乎都用这套。
_CN_NUM = '零一二三四五六七八九十百'
#: 明显不是标题的行：纯数字/标点（「55.18%」「3...」「8 ).」），
#: 或序号粘连（「1.0success rate」）。它们能匹配编号正则但毫无意义。
_JUNK_TITLE = re.compile(
    r'^[\s\d.,%+\-–—()（）\[\]?!]+$'    # 纯数字/标点
    r'|^[\d.]+\s*[a-zA-Z]{0,3}$'        # 1.0success 这种粘连
)
#: 「一、」「第二章」「三.」—— 带分隔符的才算标题，正文里的「一」不算。
RE_CN_HEAD = re.compile(r'^\s*([%s]{1,3})\s*[、.．)）]\s*(\S.*)$' % _CN_NUM)
RE_CN_CHAP = re.compile(r'^\s*第\s*([%s]{1,3})\s*[章篇部]\s*(\S.*)$' % _CN_NUM)
#: 阿拉伯数字序：1. 2. 3. / 1.2 / 1.2.3
RE_AR_HEAD = re.compile(r'^\s*(\d{1,2})\s*[、.．)）]\s*(\S.*)$')
RE_AR_NEST = re.compile(r'^\s*(\d{1,2})\.(\d{1,2})\.(\d{1,2})[\s、.．:：]+\s*(\S.*)$')
#: 两段式：「5.2 Conversational AI」「2.1 介绍」。英文论文的小节编号全是这种，
#: 上面那个三段正则接不住，而单段的 RE_AR_HEAD 要求「. 后面紧跟非空白」，
#: 也接不住 —— 于是英文论文的小节标题一个都识别不出来（实测 25 章全平）。
RE_AR_TWO = re.compile(r'^\s*(\d{1,2})\.(\d{1,2})\s+(\S.*)$')


def _cn_to_int(s):
    """中文数字 → int（够用到百，PDF 标题不会超过这个量级）。"""
    digits = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9}
    if s == '十':
        return 10
    if '十' in s:
        a, _, b = s.partition('十')
        return digits.get(a, 1) * 10 + (digits.get(b, 0) if b else 0)
    if len(s) == 1:
        return digits.get(s, 0)
    # 二十一 这种多位
    n = 0
    for ch in s:
        n = n * 10 + digits.get(ch, 0)
    return n


def _is_junk_title(s):
    """明显不是标题的行。

    论文 / Agent 日志类 PDF 里满地都是这种东西：「55.18%」「3...」「8 ).」
    「1.0success rate」—— 它们能匹配编号正则，但作为标题毫无意义，
    混进目录里目录就成了垃圾（实测一份 16 章文档有 5 条这种）。
    """
    t = (s or '').strip()
    if not t:
        return True
    if _JUNK_TITLE.match(t):
        return True
    # 「3...」「8 ).」这类：去掉序号后正文只剩零散符号
    m = re.match(r'^[\d.,]+\s*[\.\)、)]*\s*(.*)$', t)
    return bool(m and len(m.group(1).strip()) < 3)


def detect_title_level(line):
    """判断这行像不像标题，返回 (level, title)；不是返回 None。

    ★ 为什么不用字号：PDF 的字号信息在纯文本层已经丢了（这正是
      docparse 只能拿到散装行的原因）。唯一还在的是**编号本身** ——
      「一、」「三.」「2.」这套序号是作者手动打的，天然带着层级，
      比猜字号可靠得多。

    层级怎么定：
      「一、」「第二章」 → 1（顶层）
      「1. 」「2.」     → 2（顶层之下）
      「1.2.3」        → 按点数

    ★ 长度上限 32 而不是 60：带序号的**整句正文**也会命中
      「1. 装饰器本质是一种特殊的函数，它可以对：类、属性、方法…���」，
      实测这份 PDF 里有 4 处这样的正文被误判成标题（长的 80 字）。
      真正的标题很少超过 30 字；超过就宁可当正文。
    """
    s = (line or '').strip()
    if not s or len(s) > 32 or _is_junk_title(s):
        return None
    m = RE_AR_NEST.match(s)
    if m:
        return (max(1, min(3, len(m.group(1)) + 2)), s)
    m = RE_AR_TWO.match(s)
    if m:
        return (2, s)
    m = RE_CN_CHAP.match(s)
    if m:
        return (1, s)
    m = RE_CN_HEAD.match(s)
    if m:
        return (1, s)
    m = RE_AR_HEAD.match(s)
    if m:
        # 「1.0success rate」这类粘连：序号去掉后正文又以数字开头。
        # 真标题去掉序号后是字母或汉字，不会是数字。
        if m.group(2)[:1].isdigit():
            return None
        return (2, s)
    return None


def annotate_headings(text):
    """把裸文本里的标题行转成 markdown 标题标记。

    ★ 顺序要紧：代码块先圈出来，标题只认**代码块外**的行。
      否则 `for (i = 0; ...)`、`1. 初始化` 这种代码会被当成标题 ——
      先圈代码正好把它们排除掉（见 to_markdown 的处理顺序）。
    """
    md = to_markdown(text)
    out = []
    in_code = False
    for line in md.split('\n'):
        s = line.strip()
        if s.startswith('```'):
            in_code = not in_code
            out.append(line)
            continue
        if in_code or not s:
            out.append(line)
            continue
        d = detect_title_level(s)
        if d:
            lvl, title = d
            out.append('#' * lvl + ' ' + title)
        else:
            out.append(line)
    return '\n'.join(out)