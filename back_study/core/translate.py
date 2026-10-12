# -*- coding: utf-8 -*-
"""论文英译中：术语锁定 + 数字保护 + 分段带上下文 + 回译校验。

## 为什么准确性要靠这几层，而不是靠「提示词写得好」
本地只有 qwen3:8b，让它直接翻一篇英文学术论文，失败模式是**看不出来的**：
句子通顺、术语看着对，但数字错了、术语前后不一致、还会自己补原文没有的话。
这种译文比报错更糟 —— 用户读得下去，发现不了自己漏了信息。
所以这里的设计原则是：**凡是能确定性算出来的东西，一律不让模型碰。**

## 四道保障，按「确定性」从高到低排

### 1. 数字 / 引用 / 公式保护（正则，完全确定性）
翻译前把 `12.5%`、`[12]`、`(Wei et al., 2020)`、`$O(n \log n)$` 这类片段抠出来
换成占位符 `⟦P1⟧`，译完原样填回。
★ 这一环**没有任何模型参与**，所以它不会错。实测 ReAct 论文里
  百分比 29 处、`[n]` 引用 12 处 —— 占比不低，全靠模型「小心点」必然漏。

### 2. 术语锁定（术语表 + 全文强制一致）
先扫全文抽高频专业术语建术语表，翻译时整表进提示词并要求同一术语只有一个译法。
★ 学术翻译质量的第一道分水岭不是「句子通顺」而是「术语统一」：
  ReAct 译成「反应」和译成「ReAct 推理-行动交织」在同一篇里混着出现，
  读者会以为是两个不同的东西。

### 3. 分段 + 上下文窗口（解决跨段指代与术语漂移）
按语义段落切，每段带**前后各一段的原文摘要 + 已译前文的术语提示**。
单独翻一段，it / they / this method 指什么模型只能猜。

### 4. 回译校验（唯一能自动发现幻觉的手段）
译文再翻回英文，与原文比语义。差距大的标出来让人重翻。
★ 注意它的**局限**：回译距离只能发现「明显偏了」，
  发现不了「数字错了」——那类错误得靠第 1 层的正则来堵。
  所以第 4 层是补充，不是主防线。
"""
import json
import re

# ------------------------------------------------------------------
# 常量
# ------------------------------------------------------------------

#: 每段最多送多少字符进模型。中文译文的 token 密度比英文高，
#: 900 字英文 ≈ 650 字中文，留足余量不会顶到 NUM_CTX。
#: 调大是为了让「一段就是一个自然段」尽量成立：大多数自然段
#: 都在 900 字以内，能整段进模型，避免把一段腰斩成几刀。
SEG_MAX = 900
#: 段间重叠（同 docqa.chunk_text 的理由：答案可能被腰斩）
SEG_OVERLAP = 120
#: 前后各带几段做上下文
CTX_PREV = 1
CTX_NEXT = 1
#: 单次翻译的批量段数。8B 本地一次只吃得住两三段，
#: 批量大了容易「把上一段的术语用到下一段」。
BATCH = 2
#: 回译校验的通过阈值（0~1 的对齐分，语义越像分越高）
VERIFY_MIN = 0.62
#: 术语表最多放多少条进提示词。太多会挤掉正文预算。
GLOSSARY_MAX = 60

# ------------------------------------------------------------------
# 1. 数字 / 引用 / 公式保护
# ------------------------------------------------------------------
# ★ 顺序有意义：先抠「成对的」和「带上下文的」，剩下的交给通用规则。
#   如果先抠裸数字，`[12]` 里的 12 会被先抠走，留下 `[⟦P1⟧]`，
#   回填时括号没了 —— 症状是译文里引用标记消失，而很难定位。
_PROTECT_RULES = [
    # 论文图片 / 架构图占位符：![...](media:name)。
    # ★ 必须最先保护：它是「图片」不是「文字」，模型若当文本处理会丢失，
    #   而前端要据此渲染原图 + 「未译」徽标。占位后译文里只剩 ⟦Pn⟧，
    #   回填时原样恢复成 ![](media:name)。
    re.compile(r'!\[\]\(media:[^)]+\)'),
    # 行内公式：$...$ / \(...\)/ \[...\]
    re.compile(r'\$[^$\n]{1,200}\$'),
    re.compile(r'\\\([^()\\]{1,200}\\\)|\\\[[^[\]\\]{1,200}\\\]'),
    # 整行公式（pypdf 抽出来的公式常常独占一行）
    re.compile(r'^[ \t]*[A-Za-z\\][^\n]{0,160}[=≈][^\n]{0,160}$', re.M),
    # 引用：作者 (2020) / [3, 5] / [12]
    re.compile(r'\[[\d,\s–\-]{1,30}\](?![\(\[])'),
    re.compile(r'\([A-Z][A-Za-z\'\-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?\)'),
    re.compile(r'\b[A-Z][A-Za-z\'\-]+\s+et\s+al\.\s*,?\s*(?:19|20)\d{2}'),
    # 百分比 / 数值带单位
    re.compile(r'[±]?\d[\d,]*\.?\d*\s*(?:%|percent|×|x)\b'),
    # 数字范围 1-5 / 3~7
    re.compile(r'\b\d+(?:\.\d+)?\s*[–\-~]\s*\d+(?:\.\d+)?\b'),
    # 版本号 / 数据集规模 175B
    re.compile(r'\b\d+(?:\.\d+)?\s*[BMKTG]\b'),
    # 图/表/公式编号 Figure 3 / Table 2 / Eq. (5) —— 编号本身要跟着译文走
    re.compile(r'\b(?:Figure|Fig\.|Table|Tab\.|Eq\.|Equation|Algorithm|Section|Appendix)'
               r'\.?\s*\(?\w{0,12}\d+\)?'),
    # URL / DOI / arXiv
    re.compile(r'https?://\S+|arXiv:\d{4}\.\d{4,5}|doi:\S+'),
    # 剩下的裸数字（含小数），放最后
    re.compile(r'[±]?\d[\d,]*(?:\.\d+)?%?'),
]
_PLACEHOLDER = '⟦P%d⟧'
_PLACEHOLDER_RE = re.compile(r'⟦P(\d+)⟧')

#: 占位符里的内容会被模型看到，必须让它**原样保留**。
#   模型最常见的破坏方式：把 ⟦P1⟧ 写成 P1、⟦P3⟧（漏复制一个），
#   或者干脆「解释」一下。所以提示词里明确要求，且事后校验。
_PLACEHOLDER_PROMPT = ('文中形如 ⟦P1⟧ ⟦P2⟧ 的标记是原文里的数字/公式/引用，'
                       '**必须原样照抄，一个字符都不能改、不能增删、不能解释**。')


def protect(text):
    """把数字等替换成占位符。返回 (保护后文本, 占位符原值列表)。

    ★★★ 算法：**收集所有规则的所有匹配，按起点位置贪心取不重叠的**。
      不是「一条规则跑完再跑下一条」—— 那会踩两个坑：

      1. **占位符套占位符**：`[12]` 先变成 `⟦P1⟧`，后面的裸数字规则
         再把里面的 `1` 抠走，得到 `⟦P⟦P2⟧⟧`。回填后译文里
         **残留 ⟦Pn⟧ 字面量**，而数字看着是对的 —— 这种错误最难发现。
      2. **位置靠后的规则挡住靠前的**（这个更隐蔽）：
         规则表里「(Wei et al., 2020)」在前、URL 在后，
         但两个匹配的**起点顺序**可能相反。若按规则顺序跑，
         靠后的引用先占位，再跑 URL 规则时它的匹配区间与已占位区间
         相交 → 被跳过 → URL 没保护 → 后面裸数字规则
         把 `arXiv.org/abs/2210.03629` 里的 `2210.03629` 抠走，
         URL 当场烂掉。
      改成按位置贪心后，两个坑一起消失：位置冲突时先到先得。

    贪心而不是「最长匹配优先」：占位符本身只有 5~6 字符，
    不存在「短匹配吃掉长匹配」的问题，位置优先就够了。"""
    cands = []
    for pri, rx in enumerate(_PROTECT_RULES):
        for m in rx.finditer(text):
            # 零宽匹配会让 while 循环死转，直接丢弃
            if m.end() > m.start():
                cands.append((m.start(), m.end(), pri, m.group(0)))
    # 起点升序；同起点时规则表靠前的优先（更具体的规则写在前面）
    cands.sort(key=lambda x: (x[0], x[2]))

    out = []
    vals = []
    cur = 0
    for a, b, _pri, raw in cands:
        if a < cur:            # 与已取的区间重叠，跳过
            continue
        out.append(text[cur:a])
        vals.append(raw)
        out.append(_PLACEHOLDER % len(vals))
        cur = b
    out.append(text[cur:])
    return ''.join(out), vals


def restore(text, vals):
    """把占位符填回原值。

    ★ 必须容忍「模型没原样抄」：占位符缺了/多了/写错了，
      直接抛异常会让整篇翻译白跑一次。这里逐个尝试填回，
      填不回去的**保留原文里的对应片段**（宁可多个占位符，
      也不能让译文里凭空少一个数字）。
    """
    def sub(m):
        i = int(m.group(1))
        return vals[i - 1] if 1 <= i <= len(vals) else m.group(0)
    return _PLACEHOLDER_RE.sub(sub, text)


def placeholders_ok(translated, n_expected):
    """校验**模型返回的译文**里占位符是否齐全。返回 (是否完整, 缺哪些)。

    ★★★ 必须在**回填之前**调用，传的是模型原始返回的字符串。
      传回填后的译文是**必然报缺失**的 —— 因为占位符已经被换成
      数字了，⟦P1⟧ 根本不存在于回填结果里。
      这不是模型的问题，是我第一次写调用处时的顺序错误；
      症状极像「模型漏抄了 12 个占位符」，差点被当成模型能力问题
      去调提示词。**判据函数的输入语义必须写在 docstring 第一行。**

    为什么要在意：8B 模型漏抄占位符的概率不低，而漏掉一个数字的
    译文用户读三遍都发现不了 —— 那是这类功能最隐蔽的失败。
    """
    got = {int(x) for x in _PLACEHOLDER_RE.findall(translated or '')}
    missing = [i for i in range(1, n_expected + 1) if i not in got]
    return (not missing), missing


# ------------------------------------------------------------------
# 2. 术语抽取
# ------------------------------------------------------------------

SYS_GLOSSARY = '''你是学术术语表抽取器。给一篇计算机/机器学习论文的正文，抽出其中
**专业术语**（英文原文 → 推荐中文译法）。

要求：
1. 只收**专业术语/专有方法名/缩写**，不要收普通词汇（如 "the model"、"training"）。
2. 术语必须是原文里**真实出现过**的词，不许臆造。
3. 中文译法要**简洁准确**，符合中文技术读者的习惯（如 attention→注意力、
   embedding→嵌入、trajectory→轨迹），不要用生僻同义词。
4. 按重要度排序，最多 40 条。
5. **只输出 JSON**，格式：{"terms": [{"en":"Attention", "zh":"注意力"}, ...]}
不要 markdown 代码块，不要任何解释。'''


def extract_terms(text, model=None, top=40, timeout=300):
    """抽术语表。失败时**返回空表而不是抛异常** ——
    没有术语表的翻译质量差一些，但能用；抛异常则整篇翻译都做不了。"""
    sample = text[:6000]
    try:
        raw = llm_call(
            [{'role': 'system', 'content': SYS_GLOSSARY},
             {'role': 'user', 'content':
              '以下是一篇论文的正文节选，请抽取术语表：\n\n' + sample}],
            model=model, timeout=timeout, temperature=0.1, max_tokens=2400)
    except Exception:
        return []
    # ★★ 截断的 JSON 必须能**部分解析**，不能整段丢掉。
    #   40 条术语的 JSON 约 2000+ token，而 8B 出字慢、max_tokens
    #   给小了就会在数组中间断掉（实测 1400 tokens 时稳定截断）。
    #   原来的写法是 json.loads 失败 → 直接返回空表 ——
    #   **表现是「术语抽取功能正常返回了 0 条」**，不报错、不留痕，
    #   翻译仍然照跑，只是悄悄失去了术语一致性保障。
    #   修复方向：优先完整解析，失败则补上右括号 + 清掉尾部逗号再试。
    items = _parse_terms(raw)
    out, seen = [], set()
    for it in items:
        if not isinstance(it, dict):
            continue
        en = (it.get('en') or '').strip()
        zh = (it.get('zh') or '').strip()
        if not en or not zh or len(en) > 40 or len(zh) > 20:
            continue
        if en.lower() in seen:
            continue
        # ★ 校验原文里真的有这个词。模型很爱「顺手补全」出
        #   看起来合理但原文没写的术语 —— 那会让后面的翻译
        #   强行按一个不存在的术语对齐，反而降低质量。
        if en.lower() not in text.lower():
            continue
        seen.add(en.lower())
        out.append({'en': en, 'zh': zh})
        if len(out) >= top:
            break
    return out


def _parse_terms(raw):
    """从模型返回里抠出术语数组，**容忍被max_tokens 截断**。

    两级策略：
      1. 先按完整 JSON 解析（模型听话时走这条）
      2. 失败则逐个抓 `{...}` —— 术语对象的结构是扁平的
         （`{"en": "...", "zh": "..."}`），里面**没有嵌套对象**，
         所以正则抓单层对象是安全的。
    ★ 为什么不用「补右括号再parse」：数组里最后一个元素可能缺右括号，
      补了之后 json 能parse 出**别的**结构（比如把下一个段落吞进来），
      得到看似成功实则错位的结果 —— 那种错误比直接失败难查得多。
    """
    raw = _strip_fence(raw)
    if not raw:
        return []
    try:
        j = json.loads(raw)
        if isinstance(j, dict) and isinstance(j.get('terms'), list):
            return j['terms']
    except Exception:
        pass
    out = []
    for m in re.finditer(r'\{[^{}]*\}', raw):
        try:
            v = json.loads(m.group(0))
        except Exception:
            continue
        if isinstance(v, dict):
            out.append(v)
    return out


def glossary_prompt(terms):
    """把术语表拼成提示词片段。

    ★ 接受 **list[dict] 或 dict{en: zh}** 两种形态。
      这不是图省事 —— 调用链上有两处天然不同的形态：
        · transjob.build_glossary 返回 dict（按 en 索引，便于覆盖锁定项）
        · 用户从库里读出来的是 list（按字母排序，要给人看）
      之前只吃list，于是 build_glossary 的产物一进来就
      `TypeError: unhashable type: 'slice'`，而这个错被 run() 的
      except 吞掉 → **261 段全部标 bad、0 秒跑完、一条错误都没有**。
      ★ 教训：批量循环里的异常处理必须同时打 stderr，
        否则「所有条目都失败」会被误读成「数据本来就没有」。
    """
    if not terms:
        return ''
    if isinstance(terms, dict):
        items = [{'en': k, 'zh': v.get('zh') if isinstance(v, dict) else v}
                 for k, v in terms.items()]
    else:
        items = list(terms)
    items = [t for t in items if (t.get('en') or '').strip()
             and (t.get('zh') or '').strip()]
    if not items:
        return ''
    # 长的术语排在前面：截断到 GLOSSARY_MAX 时保住最重要的
    items = sorted(items, key=lambda t: -len(t['en']))[:GLOSSARY_MAX]
    lines = '\n'.join('- %s → %s' % (t['en'], t['zh']) for t in items)
    return ('全文术语表（**同一术语全文只能用一个译法，必须严格照此翻译**）：\n'
            + lines)


# ------------------------------------------------------------------
# 3. 分段
# ------------------------------------------------------------------
# 复用 docqa 的切法：按句边界切 + 重叠。理由同上（答案被腰斩）。
# 这里不直接 import docqa 是为了让 translate 独立可测，
# 但**切法必须保持一致** —— 不一致会导致同一篇文档在
# 「问答」和「翻译」两个功能里对「第 7 段」的理解不同，
# 出问题时极难定位。

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+|(?<=[。！？])\s*|\n{2,}')

#: 段落分隔：空行（一个以上）即视为新段落。先按它拆，翻译才是一段一段的。
_PARAS = re.compile(r'\n\s*\n+')


def segment(text, size=SEG_MAX, overlap=SEG_OVERLAP):
    """切段。返回 [{i, text}]。

    ★★★ 以「自然段」为翻译单位（用户明确要求一段一段翻）：
    1. 先按空行 `\n\n+` 把正文拆成**段落**，段落之间绝不混到一起；
    2. 段落内部再按句边界切，把长段落切成不超过 size 的块，
       但**块与块仍属于同一段**，不会把下一段的开头接上来；
    3. 单句超过 size（极少见）才硬切，硬切处保留 overlap 防句子腰斩。

    为什么不能像旧版那样「按 700 字累积、跨段拼块」：
    那样一个块常常以「上一段的尾巴 + 下一段的开头」组成，
    模型收到的是两段拼接的上下文，指代和术语都乱，
    而且右栏显示的编号也不对应真实段落 —— 用户看到的就是「翻译没按段来」。
    """
    text = (text or '').strip()
    if not text:
        return []
    paras = [p.strip() for p in _PARAS.split(text) if p and p.strip()]
    segs = []
    for para in paras:
        # 段落内按句边界拆（句子不会跨段）
        parts = [s.strip() for s in _SENT_SPLIT.split(para) if s and s.strip()]
        if not parts:
            continue
        cur = ''
        for p in parts:
            # 单句超长：硬切（保留 overlap 给下一刀）
            while len(p) > size:
                if cur:
                    segs.append(cur.strip())
                    cur = ''
                segs.append(p[:size].strip())
                p = p[size - (overlap or 0):]
            if len(cur) + len(p) <= size:
                cur += (' ' if cur else '') + p
            else:
                if cur.strip():
                    segs.append(cur.strip())
                cur = p  # 段落内不跨段 carry overlap，保持段内连续
                cur = cur.strip()
        if cur.strip():
            segs.append(cur.strip())
    return [{'i': i, 'text': s} for i, s in enumerate(segs)]


# ------------------------------------------------------------------
# 4. 翻译提示词
# ------------------------------------------------------------------

SYS_TRANS = '''你是英文学术论文的专业译者。把用户给的论文段落译成中文。

硬性要求：
1. **绝对忠实**。只译原文写了的意思，不许补充、不许解释、不许总结，
   不许加入原文没有的内容（这是学术翻译最重要的一条）。
2. **不漏不并**。逐句翻译，**不要漏掉原文任何一句**，也**不要把多句并成一句**
   （合并会丢掉句间逻辑）。译文的句子数量应与原文大致相当。
3. **限定词也要译出**。typically / generally / in most cases / to some extent /
   usually / often 这类限定词必须翻出来（如「通常」「在多数情况下」「在一定程度上」），
   不能为了读起来顺就省略 —— 学术结论的强弱全靠它们。
4. **拿不准就保留英文**。遇到不确定的专业表述，保留英文并在括号里给中文
   （如 sparse attention（稀疏注意力）），不要凭空意译或编造译名。
5. 专有名词、方法名、缩写**保留英文原文**（如 ReAct、Transformer、
   chain-of-thought 首次出现可写成「思维链（CoT）」，之后统一用 CoT）。
6. 专业术语按术语表译；不在术语表里的按中文技术圈通行译法。
7. 句子用中文语序重组，不要逐词对译（"a total of 3" → "共3 个"，
   不是 "一个总共的 3 个"）。
8. 保留原文的段落编号、标题层级、列表结构。
9. 公式、变量、函数名保持原样，用 $...$ 包住。
10. 英文人名、地名、机构名保留英文。
11. 只输出译文本身，不要解释、不要加"译文："之类的前缀。
12. **避免翻译腔和固定套路**：不要不论长短都套"值得注意的是""综上所述"
   "具体而言"之类机械垫词；原文没写的总括句、评价句、过渡句都不要加，
   原文是平铺直叙的陈述就平铺直叙地译。但原文本身的逻辑连接词
   （因此/然而/换言之）和真正存在的结论句要如实译出，不要为了去模板把意思删掉。

''' + _PLACEHOLDER_PROMPT

#: 回译用的提示词。**不提原文**，只把译文翻回英文 ——
#   这样拿到的是「译文自身的信息量」，与原文比对才有意义。
SYS_BACK = '''把中文译文译回英文。只要英文，不要解释。
专有名词保留英文，公式与数字原样保留。
只输出英文译文。'''


def build_segment_messages(seg, segs, terms):
    """给某段拼提示词。带前后文以解决跨段指代。"""
    i = seg['i']
    msgs = [{'role': 'system', 'content': SYS_TRANS + glossary_prompt(terms)}]
    ctx = []
    for j in range(max(0, i - CTX_PREV), min(len(segs), i + CTX_NEXT + 1)):
        if j == i:
            continue
        ctx.append('[第%d段%s]\n%s' % (j + 1, '（上文）' if j < i else '（下文）',
                                       segs[j]['text'][:360]))
    if ctx:
        msgs.append({
            'role': 'user',
            'content': '以下是同一篇论文的相邻段落，仅供你判断术语和指代的一致性，'
                       '**不要翻译它们**：\n\n' + '\n\n'.join(ctx)
        })
    msgs.append({
        'role': 'user',
        'content': '请翻译这一段：\n\n' + seg['text']
    })
    return msgs


# ------------------------------------------------------------------
# 5. 回译校验
# ------------------------------------------------------------------

def back_verify(src, zh, model=None, timeout=240):
    """回译比对。返回 (是否通过, 对齐分, 回译英文)。"""
    if not (zh or '').strip():
        return False, 0.0, ''
    try:
        back = llm_call(
            [{'role': 'system', 'content': SYS_BACK},
             {'role': 'user', 'content': zh}],
            model=model, timeout=timeout, temperature=0.1, max_tokens=900)
    except Exception:
        # 回译失败**不等于**译文错（可能只是模型/连接问题）。
        # 判为「无法校验」，交给上层决定是标黄还是标红。
        return True, -1.0, ''
    score = align_score(src, back)
    return score >= VERIFY_MIN, score, back


def align_score(src, back):
    """原文与回译的对齐分（0~1）。复用 llm.align_score 的 bigram 思路。
    这里自己算而不调llm.align_score：那是对齐「AI 摘要 vs 原文」，
    词表不同（摘要更短），阈值不通用。"""
    a = _bigrams(src)
    b = _bigrams(back)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    # 用调和平均：只看覆盖率的话，回译把所有词都堆一遍就能刷高
    return 2.0 * inter / (len(a) + len(b))


def _bigrams(s):
    s = re.sub(r'\s+', ' ', (s or '').lower())
    w = re.findall(r'[a-z0-9]+', s)
    if not w:
        return set()
    g = set()
    for i in range(len(w) - 1):
        g.add(w[i] + ' ' + w[i + 1])
    for x in w:
        g.add(x)
    return g


# ------------------------------------------------------------------
# 顶层接口
# ------------------------------------------------------------------

def doc_text(doc):
    """取一份文档的正文（翻译与问答共用同一口径）。

    直接从 docqa 借，不自己再写一遍 —— 两处各写一份「优先 text、
    退回 chapters 拼接」的逻辑，早晚会在某篇特殊文档上分叉，
    而症状是「问答能读到、翻译读不到」。
    """
    from docqa import doc_text as _d
    return _d(doc)


def _strip_fence(s):
    """剥掉 ```json 围栏。模型有时不听指令，但内容是对的。"""
    s = (s or '').strip()
    if s.startswith('```'):
        s = re.sub(r'^```[a-zA-Z]*\s*', '', s)
        s = re.sub(r'```\s*$', '', s).strip()
    return s


def _llm_call(messages, model, timeout, temperature, max_tokens):
    # 延迟 import：core.llm 有 20 秒的模型探测缓存，
    # 在 import 期调用会拖慢所有导入它的模块。
    import llm
    return llm._call(messages, model, timeout,
                     temperature=temperature, max_tokens=max_tokens)


llm_call = _llm_call