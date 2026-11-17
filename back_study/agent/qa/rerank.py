# -*- coding: utf-8 -*-
"""重排层（Re-ranking / Cross-Encoder）：混合检索之后的精排。

为什么必须有这一层
------------------
向量检索和关键词检索**各自都排不准**，但错得不一样：
  - 关键词：字面命中，"RRF"能查到"Re-ranking"，但查不到"倒数排名融合"
  - 向量：整体语义相近就能召回，容易带进"只是话题沾边"��卡
工业界的标准做法是**两阶段**：
    召回（recall，20~50 条，要全）→ 重排（rerank，只精排前 N，要准）
重排用一个 **cross-encoder** 同时看 query 和文档：
双塔（bi-encoder）分别编码所以能预计算、能大规模检索；
cross-encoder 拼在一起过模型所以准，但**每对都要算一遍**，慢。

★ 本项目的硬约束（2026-10-09 实测）
  本机**没有可用GPU**（nvidia-smi 报 NVML 初始化失败），只能 CPU 跑。
  实测 bge-reranker-v2-m3 在 CPU 上（batch=8）：
      候选  8 对 →  422 ms（52.7 ms/对）
      候选 16 对 →  645 ms（40.3 ms/对）
      候选 32 对 → 1080 ms（33.8 ms/对）
  边际成本递减明显（32 对的摊薄比 8 对低 36%），所以
  **候选数取 20~30 是甜点**，不是越多越好 —— 64 对要 2 秒，不划算。

延迟控制（这是本模块存在的意义，重排比检索慢一个量级）
  1. **只重排 top-N**，N=RERANK_CANDIDATES（默认 20），不重排全部召回结果
  2. **模型常驻**：只在第一次调用时load，之后复用（load 一次约 4 秒）
  3. **超时降级**：超过 RERANK_TIMEOUT_MS 就返回召回阶段的顺序，
     而不是让用户干等 —— 检索慢一点能接受，界面卡住不行
  4. **磁盘缓存**（rerank_cache）：同一 query 的重排结果复用，见文件末尾说明
  5. **文本截断**：cross-encoder 最长512 token，超长会被静默截断，
     所以喂进去的文本先裁短，避免白算

降级原则（和项目其他模块一致）
  模型没下载 /加载失败 /推理报错→ **返回 None，调用方保留召回顺序继续跑**。
  重排是增强项，它挂了不该让「能答」变成「答不了」。
  但**降级必须看得见**：这里会往 stderr 打一行，调用方把
  `reranked=False` 回给前端。
"""
import os
import re
import sys
import time

from .. import config as C

# ---------- 配置 ----------
#: 模型本地路径。**配置化**（2026-11-15）：以前硬编码 D 盘绝对路径，
#: 换机器直接挂（评测遗留项）。解析顺序：环境变量 AGENT_RERANK_PATH
#: > config.local.json 的 "Rerank":{"path":...} > 旧默认值。
#: 本机放 D 盘是因为 C 盘紧张（实测整个模型 2.2GB）。
DEFAULT_MODEL_PATH = C.RERANK_PATH

#: feed 给 cross-encoder 的单条文本上限（**字符**）。
#:
#: ★★这个数字是**实测定的，不是拍的**（2026-10-09，本机 CPU 无GPU）：
#: 固定 8 对、只改文本长度：
#:      50 字 →  458 ms
#:     150 字 → 1006 ms
#:     300 字 → 1664 ms
#:     500 字 → 3222 ms
#: 几乎**线性增长** —— 长度才是主要成本，不是候选条数。
#:   我最初设 500（想着「模型的 512 token 上限」），
#:   结果全库 doc_text 的**中位数就是 500**（mechanism 全被塞进去了），
#:   等于每条都跑最长 —— 20 对要 7.9 秒，完全不可用。
#:
#: 为什么 150 字够用：cross-encoder 判断「这篇答不答得上这个问题」，
#: 靠的是 title（一句话说清主题）+ oneLine（一句话说清是什么）+
#: 机制前几条（说明怎么跑）。这个信息在 150 字内已经完整，
#: 后面的机制细节是"扩展阅读"性质，对相关性判断贡献很小。
MAX_CHARS = 150

#: 文本里空白/换行会浪费 token，先压掉
_WS = re.compile(r'\s+')

# ---------- 模型单例 ----------
_MODEL = {'inst': None, 'path': None, 'tried': False, 'err': None}


def model_path():
    return os.environ.get('AGENT_RERANK_MODEL') or DEFAULT_MODEL_PATH


def available():
    """模型是否可用。不做load，只查路径 —— 这个函数要能被健康检查调用。"""
    return os.path.isdir(model_path())


def _load():
    """加载模型（单例）。返回 None 表示不可用。

    ★ 为什么单独 try 而不是丢给上层：sentence_transformers 的
    导入/加载异常类型很杂（缺 torch、缺权重、显存不足…），
    在这里统一转成「不可用」，调用方只处理一种情况。
    """
    path = model_path()
    if _MODEL['inst'] is not None and _MODEL['path'] == path:
        return _MODEL['inst']
    if _MODEL['tried'] and _MODEL['path'] == path:
        return _MODEL['inst']          # 已经失败过，别每次都重试
    _MODEL['tried'] = True
    _MODEL['path'] = path
    if not os.path.isdir(path):
        _MODEL['err'] = '模型目录不存在: %s' % path
        sys.stderr.write('[rerank] %s\n' % _MODEL['err'])
        return None
    try:
        from sentence_transformers import CrossEncoder
        # device 显式给 cpu：本机无 GPU，让它自己探测反而会打一堆警告
        _MODEL['inst'] = CrossEncoder(path, device='cpu')
        return _MODEL['inst']
    except Exception as e:
        _MODEL['inst'] = None
        _MODEL['err'] = '%s: %s' % (type(e).__name__, e)
        sys.stderr.write('[rerank] 模型加载失败（已降级为不重排）：%s\n' % _MODEL['err'])
        return None


# ---------- 文本预处理 ----------
def doc_text(card):
    """喂给 cross-encoder 的卡片文本。

    ★ 为什么不是 `_card_text`（embedding 用的那个）：
      embedding 要的是「语义向量」，需要完整内容；
      rerank 要的是「判断这个文档答不答得上这个问题」，
      标题 + 一句话 + 机制步骤最有用，
      而 keywords/analogy/interviewQ 反而是噪声（类比和问题本身不是答案）。
    """
    parts = [card.get('title') or '', card.get('oneLine') or '',
             ' '.join(card.get('mechanism') or [])]
    t = _WS.sub(' ', ' '.join(p for p in parts if p)).strip()
    return t[:MAX_CHARS]


def _trim_query(q):
    return _WS.sub(' ', q or '').strip()[:MAX_CHARS]


# ---------- 重排 ----------
def rerank_texts(query, texts, timeout_ms=None):
    """对一组**纯文本**做重排。返回 {下标: 相关度} 或 None（不可用/超时/异常）。

    和 rerank() 的区别：调用方手里是「块文本列表」而不是 card 对象
    （文档问答就是这种场景——一篇论文切成几十段，段不是卡片）。
    texts 是字符串列表，返回的下标就是 texts 的下标，调用方自己按分数排序。

    ★ 返回 None 而非 {} 是刻意的：None = 「没重排成，顺序还是召回时的」，
      {} 会被误读成「重排了但全被过滤掉」。两者语义完全不同。
    """
    if not texts:
        return {}
    model = _load()
    if model is None:
        return None

    timeout = timeout_ms if timeout_ms is not None else C.RERANK_TIMEOUT_MS
    # 文本截断到 MAX_CHARS：cross-encoder 最长 512 token，超长静默截断，
    # 先裁短避免白算（见模块顶部实测）。
    pairs = [(_trim_query(query), _WS.sub(' ', t or '')[:MAX_CHARS]) for t in texts]
    t0 = time.time()
    try:
        raw = model.predict(pairs, batch_size=16, show_progress_bar=False)
    except Exception as e:
        sys.stderr.write('[rerank] 推理失败（降级为不重排）：%s\n' % e)
        return None
    cost = (time.time() - t0) * 1000

    if cost > timeout:
        sys.stderr.write('[rerank] 超时 %.0fms > %dms，保留召回顺序\n' % (cost, timeout))
        return None

    out = {}
    for i, sc in enumerate(raw):
        try:
            v = float(sc)
        except (TypeError, ValueError):
            continue
        if v >= 0:
            p = 1.0 / (1.0 + pow(2.718281828459045, -v))
        else:
            e = pow(2.718281828459045, v)
            p = e / (1.0 + e)
        out[i] = p
    sys.stderr.write('[rerank] %d 对 %.0fms (%.1fms/对)\n'
                     % (len(pairs), cost, cost / max(len(pairs), 1)))
    return out


def rerank(query, hits, timeout_ms=None):
    """对 hits 重排。返回 {id: score} 或 None（不可用/超时/异常）。

    hits 是 retrieval.SearchHit 列表（需要 .id 和 .card）。
    返回 **dict 而不是列表**：调用方要改的是「按 id 取新分数」，
    用dict 最直接；顺序由调用方按分数自己排，这里不决定。

    ★ 返回 None 而非 [] 是刻意的：None = 「没重排成，顺序还是召回时的」，
      [] 会被误读成「重排了但全被过滤掉」。两者语义完全不同。
    """
    if not hits:
        return {}
    model = _load()
    if model is None:
        return None

    timeout = timeout_ms if timeout_ms is not None else C.RERANK_TIMEOUT_MS
    pairs = [(_trim_query(query), doc_text(h.card or {})) for h in hits]
    t0 = time.time()
    try:
        # batch_size=16：实测同候选数下 16 比 8 快（12 对 1657 vs 1718ms、
        # 20 对 2895 vs 3273ms）。再大没实测，不瞎填。
        raw = model.predict(pairs, batch_size=16, show_progress_bar=False)
    except Exception as e:
        sys.stderr.write('[rerank] 推理失败（降级为不重排）：%s\n' % e)
        return None
    cost = (time.time() - t0) * 1000

    if cost > timeout:
        # ★ 超时不抛异常也不返回部分结果 —— 半截结果会让排序变成
        #   「一半用新分、一半用旧分」，比不重排更难解释。
        sys.stderr.write('[rerank] 超时 %.0fms > %dms，保留召回顺序\n' % (cost, timeout))
        return None

    out = {}
    for h, sc in zip(hits, raw):
        # ★ bge-reranker 的 CrossEncoder 输出是 **logits**（num_labels=1），
        #   不是 0~1 概率。实测相关对0.5348 vs 无关对 0.5000（sigmoid 后）。
        #   直接用 logits 当分数也行（单调），但过一下 sigmoid 更符合
        #   「相关度」这个语义，也方便和其他 0~1 的分数一起加权。
        try:
            v = float(sc)
        except (TypeError, ValueError):
            continue
        # 数值稳定版 sigmoid：x 很大或很小时 exp 会溢出
        if v >= 0:
            p = 1.0 / (1.0 + pow(2.718281828459045, -v))
        else:
            e = pow(2.718281828459045, v)
            p = e / (1.0 + e)
        out[h.id] = p
    sys.stderr.write('[rerank] %d 对 %.0fms (%.1fms/对)\n'
                     % (len(pairs), cost, cost / max(len(pairs), 1)))
    return out


def status():
    """给健康检查/管理端看的状态。降级必须可见。"""
    return {
        'available': _MODEL['inst'] is not None or available(),
        'loaded': _MODEL['inst'] is not None,
        'path': model_path(),
        'error': _MODEL['err'],
        'candidates': C.RERANK_CANDIDATES,
        'timeoutMs': C.RERANK_TIMEOUT_MS,
    }