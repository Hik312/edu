# -*- coding: utf-8 -*-
"""文档问答：拿着**当前这份文档**的正文回答右下角的问题。

## 这一版做了什么（上下文增强 + 自进化 RAG）

### 1. 跨语言检索（最关键的修复）
旧版只用「中文分词 bigram 打分」，但论文是**英文**的 —— 中文问题对英文
正文几乎零词面重合，于是 `select` 永远走「零命中 → 取开头几段」的兜底，
答出来的东西和问的毫无关系。**这是这类功能最常见的「明明文档里有却答非所问」。**

修复：把问题扩展成可检索英文文档的词。两层：
- **术语表 zh→en 映射**（翻译时建的 glossary，确定性、零延迟）：用户用中文
  术语问（如「注意力机制」）直接映射到 attention。
- **LLM 把问题译成英文检索词**（best-effort，8 秒超时即放弃）：处理术语表
  没覆盖的说法。`expand_query` 返回英文小写词集合，和原问题的中文 bigram
  一起参与打分。

### 2. 两阶段重排（上下文增强）
关键词召回 top-20 → 交叉编码器（bge-reranker-v2-m3，复用 agent/qa/rerank）
精排 → 取 top-5。关键词召回「全」、交叉编码器「准」，这是工业界标准做法。
重排器没装/超时 → 自动降级为关键词顺序，不阻塞问答。

### 3. 自进化记忆（self-evolving）
每篇文档的问答历史落盘到 `data/store/qa_log/<docId>.json`：
- 回答后把 (问题, 答案, 命中片段, 反馈) 存下来；
- 新问题先查「相似的历史问题」（中文 bigram 重合度），只复用被认可
  （feedback≠false）的，作为参考上下文注入系统提示词；
- 用户点 👍/👎 会改写那条历史的 feedback —— 被踩的以后不再被复用。
这样同一篇文档问得越多、越准，问答质量随时间「长」出来，而不是每次
都从零检索。记忆是「参考」不是「真相」：提示词明确要求以文档片段为准。

## 为什么不上向量库（仍不成立，但补充一句）
单文档问答的语料是几十段、主题连续，关键词 + 重排已经够；为一份文档单独
建向量索引（几百毫秒~几秒、每次切文档重建）得不偿失。真正需要向量的是
「跨几百份文档找相似段落」，那是另一个功能。
"""

import json
import os
import re
import sys

import db
import llm

#: 单块目标长度（字符）。太小则上下文碎、太大则塞不进 8K。
CHUNK_SIZE = 700
#: 块之间重叠。切分点正好落在句子中间时，前半句的答案就丢了
CHUNK_OVERLAP = 120
#: 最终喂给模型的块数（重排后取这么多）。5 块 × 700 字 ≈ 3500 字，
#: 加系统提示词和对话历史仍落在 NUM_CTX=8192 内。
TOP_CHUNKS = 5
#: 关键词召回的候选数（进重排阶段）。20 是本地 CPU 跑 cross-encoder 的甜点
#: （见 agent/qa/rerank.py 顶部的实测：候选再多边际收益递减、延迟线性涨）。
RECALL = 20
#: 单块送进 prompt 的上限，防止某段超长把预算吃光
MAX_CHUNK_CHARS = 900

_BACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # back_study
_ROOT = os.path.dirname(_BACK)                                        # study（项目根）
_STORE = os.path.join(_ROOT, 'data', 'store')

_CJK = r'一-鿿'
_WORD_RE = re.compile(r'[a-zA-Z][a-zA-Z0-9_+#.-]{1,}')

SYS = '''你在回答用户关于**一份文档**的问题。只用下面「文档片段」里的信息作答。

规则：
- 片段里有答案就答，并说明依据在第几节/哪一段；
- 片段里没有答案就直接说「这份文档里没写到」，**不许编**，
  也不要用你训练时的知识补（用户要的是这份文档说了什么，不是这话题一般怎么讲）；
- 允许基于片段做推断，但要用「按片段推断」这样的措辞标明；
- 用中文，回答控制在 200 字以内，能用列表就用列表。'''


#: 把（多半是中文的）问题译成英文检索词。best-effort，失败不影响主流程。
_Q2E_SYS = ('把用户关于一篇英文学术论文的问题，转成用于检索原文的英文关键词。'
            '输出 3-8 个英文单词或短语，用逗号分隔，不要句子、不要解释。'
            '如果问题里已经有英文术语，直接保留。')


def _norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """把长文切成带重叠的小段。

    ★ 按句边界切，而不是按固定字符数硬切：硬切会把句子腰斩，
      恰好把答案切在两半（前半在 chunk A 的尾巴，后半在 chunk B 的头），
      两块的检索分都不高，topN 又挤不进正确答案 —— 这是这类功能
      最常见的「明明文档里有却答不上来」。
    """
    text = text or ''
    if not text.strip():
        return []
    sents = [s for s in re.split(r'(?<=[。！？!?;；\n])', text) if s and s.strip()]
    out, cur = [], ''
    for s in sents:
        while len(s) > size:
            if cur:
                out.append(cur.strip())
                cur = ''
            out.append(s[:size].strip())
            s = s[size - overlap:]
        if len(cur) + len(s) <= size:
            cur += s
        else:
            if cur.strip():
                out.append(cur.strip())
            cur = s[-overlap:] if overlap else ''
            cur += s
    if cur.strip():
        out.append(cur.strip())
    return out


def _terms(q):
    """抽出问题里的检索词：小写英文词 + 中文 bigram。"""
    q = (q or '').lower()
    out = set(_WORD_RE.findall(q))
    cjk = ''.join(re.findall('[' + _CJK + ']+', q))
    for i in range(len(cjk) - 1):
        out.add(cjk[i:i + 2])
    if len(cjk) == 1:
        out.add(cjk)
    return {t for t in out if t.strip()}


def _score(terms, chunk):
    """命中词数 + 归一化一点长度惩罚。

    ★ 为什么要除以长度：不分母的话，模型天生偏好长块 ——
      长块命中词多不是因为相关，而是因为它什么词都沾。
      除以开方（不是长度本身）是对长度惩罚的折中：完全线性惩罚
      会把中等长度的正确块也压下去。
    """
    low = chunk.lower()
    hit = sum(1 for t in terms if t and t in low)
    if not hit:
        return 0.0
    return hit / (len(chunk) ** 0.5)


def _expand_query(query, doc):
    """把（很可能是中文的）问题扩展成可检索英文文档的词。

    两层：
      1. 术语表 zh→en 映射（翻译时建的 glossary，确定性、零延迟）
      2. LLM 把问题译成英文检索词（best-effort，8 秒超时即放弃）
    返回英文小写词集合，和原问题的中文 bigram 一起参与打分。

    ★ 这是「中文问题 vs 英文论文」这道坎的唯一正解：光靠中文 bigram
      去扫英文正文，重合度永远是 0，检索必然退化成「取开头几段」。
    """
    en = set()
    # 1. 术语表（zh→en）。翻译跑过的文档才有；没跑过则跳过，不报错。
    did = doc.get('id') or ''
    try:
        for g in db.glossary_all(did):
            e = (g.get('en') or '').strip().lower()
            if e:
                en.add(e)
    except Exception:
        pass
    # 2. LLM 译词（best-effort）
    q = (query or '').strip()
    if q:
        try:
            tr = llm._call(
                [{'role': 'system', 'content': _Q2E_SYS},
                 {'role': 'user', 'content': q}],
                timeout=8, temperature=0.0, max_tokens=120)
            for w in re.findall(r'[a-zA-Z][a-zA-Z0-9_+#.\-]{1,}', tr or ''):
                en.add(w.lower())
        except Exception:
            # 译词失败不可怕：至少还有术语表 + 原问题里现成的英文词
            pass
    return en


def _rerank(query, chunks):
    """对切块列表做交叉编码器重排。返回 {下标: 相关度} 或 None（降级）。"""
    try:
        from agent.qa.rerank import rerank_texts
    except Exception:
        return None
    try:
        return rerank_texts(query, chunks)
    except Exception as e:
        sys.stderr.write('[docqa] 重排失败（降级为关键词顺序）：%s\n' % e)
        return None


def doc_text(doc):
    """取一份文档可用于问答的正文。

    优先级 text（留档原文）→ chapters 拼接。
    论文不分章，但导入时已经存了抽取文本，所以两者都能答。
    """
    t = (doc.get('text') or '').strip()
    if len(t) >= 200:
        return t
    parts = []
    for c in (doc.get('chapters') or []):
        b = (c.get('body') or '').strip()
        if b:
            parts.append('## %s\n%s' % (c.get('title') or '', b))
    joined = '\n\n'.join(parts)
    return joined if len(joined) > len(t) else t


def select(doc, question, top=TOP_CHUNKS):
    """选出最相关的几块。返回 (picked, weak)。

    picked = [(分数, 序号, 文本)]；weak=True 表示是「零命中兜底」，
    调用方要据此明说「片段可能不相关」，防止模型硬凑答案。

    流程：切块 → 关键词打分(中文 bigram ∪ 扩展英文词) → 召回 top-20
          → 交叉编码器重排 → 取 top-5 → 还原文档顺序。
    """
    text = doc_text(doc)
    if not text.strip():
        return [], False
    chunks = chunk_text(text)
    qterms = _terms(question)
    en = _expand_query(question, doc)
    terms = qterms | en
    if not terms:
        head = chunks[:top]
        return [(0.0, i, c[:MAX_CHUNK_CHARS]) for i, c in enumerate(head)], False

    scored = []
    for i, c in enumerate(chunks):
        s = _score(terms, c)
        if s > 0:
            scored.append((s, i, c))
    scored.sort(key=lambda x: -x[0])

    if not scored:
        # ★ 零命中（连扩展后的英文词都没命中）退回开头几段：
        #   最可能是问题真的和文档无关，但兜底至少让模型能答出
        #   「这篇论文大致在讲什么」或直接说没写到。
        head = chunks[:top]
        return [(0.0, i, c[:MAX_CHUNK_CHARS]) for i, c in enumerate(head)], True

    recall_idx = [i for _s, i, _c in scored[:RECALL]]
    rscores = _rerank(question, [chunks[i] for i in recall_idx])
    if rscores:
        # 重排分重新排序 recall，再取 top-N
        order = sorted(range(len(recall_idx)),
                       key=lambda k: -rscores.get(k, 0.0))
        pick_idx = [recall_idx[k] for k in order[:top]]
    else:
        pick_idx = recall_idx[:top]
    pick_idx.sort()                       # 还原文档顺序：乱序片段易把 A 节结论配到 B 节
    picked = [(next(s for s, i, _c in scored if i == k), k, chunks[k][:MAX_CHUNK_CHARS])
              for k in pick_idx]
    return picked, False


def build_messages(doc, question, history=None, memory=None):
    """拼提示词。返回 (messages, 命中的片段序号列表)。

    memory：自进化记忆，相似历史问答（被认可的）作为参考上下文注入。
    """
    text = doc_text(doc)
    if not text.strip():
        return ([{'role': 'system', 'content': SYS},
                 {'role': 'user',
                  'content': '这份文档没有可检索的正文，无法回答：%s' % question}], [])
    picked, weak = select(doc, question)
    used = [i for _s, i, _c in picked]
    ctx = '\n\n'.join('[片段 %d]\n%s' % (i, _norm(c)) for _s, i, c in picked)
    # ★ 检索零命中被降级成「开头几段」时，要**明说**，
    #   否则模型看到几段不相干的原文会硬凑出一个答案 ——
    #   那正是这类功能最有害的失败：不是拒答，而是一本正经地编。
    if weak:
        ctx = ('（注意：下面的片段与问题**没有检索到关键词重合**，'
               '只是文档开头的兜底内容。若其中确有问题答案就用，否则'
               '直接说「这份文档里没写到」，不要推测。）\n' + ctx)
    msgs = [{'role': 'system', 'content': SYS}]
    # 自进化记忆：把过去被认可的相似问答作为参考 —— 但明确「以片段为准」。
    if memory:
        mem_txt = '\n\n'.join('问：%s\n答：%s' % (m.get('question', ''), m.get('answer', ''))
                              for m in memory)
        msgs.append({'role': 'system', 'content':
                     '【记忆参考】你之前就这份文档回答过类似问题（仅供参考，'
                     '最终必须以下面「文档片段」里的信息为准，片段里没有就直说没写到）：\n'
                     + mem_txt})
    for h in (history or [])[-6:]:
        q = (h.get('question') or '').strip()
        a = (h.get('answer') or '').strip()
        if q and a:
            msgs.append({'role': 'user', 'content': q})
            msgs.append({'role': 'assistant', 'content': a})
    msgs.append({
        'role': 'user',
        'content': '文档标题：%s\n\n文档片段：\n%s\n\n问题：%s'
                   % (_norm(doc.get('title') or '未命名')[:80], ctx, question)
    })
    return msgs, used


# ------------------------------------------------------------------
# 自进化记忆（每文档一份，落盘到 data/store/qa_log/<docId>.json）
# ------------------------------------------------------------------
# ★ 为什么用文件而不是进业务存储后端（MySQL/jsonfile 那套）：
#   它和 profiles.json / cards.override.json 同类 —— 是**派生数据**，
#   丢了不影响任何核心功能，且需要「按文档隔离、随时追加、不碰 schema」。
#   进后端要改 base/mysql/jsonfile/schema 四处，只为存一份调试/进化用的
#   问答历史，不值。documents 本身就没有 user_id 隔离，Q&A 记忆共享也符合
#   单机多人共用的现状。

def _qa_log_path(did):
    return os.path.join(_STORE, 'qa_log', '%s.json' % did)


def load_qa_log(did):
    p = _qa_log_path(did)
    if not os.path.isfile(p):
        return []
    try:
        return json.load(open(p, encoding='utf-8')) or []
    except Exception:
        return []


def log_qa(did, entry):
    """追加一条问答记忆（问答结束后调用）。每文档最多留 200 条。"""
    if not did:
        return
    d = os.path.join(_STORE, 'qa_log')
    try:
        os.makedirs(d, exist_ok=True)
        lst = load_qa_log(did)
        lst.append(entry)
        if len(lst) > 200:
            lst = lst[-200:]
        json.dump(lst, open(_qa_log_path(did), 'w', encoding='utf-8'),
                  ensure_ascii=False)
    except Exception as e:
        sys.stderr.write('[docqa] 记忆落库失败：%s\n' % e)


def _bigram(s):
    s = re.sub(r'\s+', '', (s or ''))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def similar_qa(did, question, k=1, min_overlap=0.34):
    """找相似的历史问题（中文 bigram 重合度）。只取被认可（feedback≠false）的。

    返回 [{question, answer, ...}]，作为「记忆参考」注入提示词 ——
    这就是 self-evolving：被验证过的答案会持续给后续相似问题兜底。
    """
    log = load_qa_log(did)
    qb = _bigram(question)
    best = []
    for e in log:
        if not e.get('answer') or e.get('feedback') is False:
            continue                        # 被踩的、没答案的不再复用
        eb = _bigram(e.get('question') or '')
        if not qb or not eb:
            continue
        ov = len(qb & eb) / (len(qb | eb) + 1e-9)
        if ov >= min_overlap:
            best.append((ov, e))
    best.sort(key=lambda x: -x[0])
    return [e for _, e in best[:k]]


def feedback_qa(did, question, good, correction=None):
    """给最近一条同问题打反馈（👍/👎）。返回是否找到并标记。

    ★ 被踩（good=False）的历史以后不再被 similar_qa 复用 —— 记忆会
      「忘掉」错误的回答，而不是反复误导。这是进化的另一半（纠错）。
    """
    log = load_qa_log(did)
    if not log:
        return False
    qb = _bigram(question)
    target = None
    for e in reversed(log):
        if e.get('question') == question:
            target = e
            break
        eb = _bigram(e.get('question') or '')
        if qb and eb and len(qb & eb) / (len(qb | eb) + 1e-9) >= 0.6:
            target = e
            break
    if target is None:
        return False
    target['feedback'] = bool(good)
    if correction:
        target['correction'] = correction
    try:
        json.dump(log, open(_qa_log_path(did), 'w', encoding='utf-8'),
                  ensure_ascii=False)
        return True
    except Exception:
        return False
